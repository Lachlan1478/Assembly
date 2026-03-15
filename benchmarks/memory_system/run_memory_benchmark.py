# run_memory_benchmark.py
# Dynamic N-way memory system comparison benchmark
#
# Usage:
#   python benchmarks/memory_system/run_memory_benchmark.py --domains finance --mode medium
#   python benchmarks/memory_system/run_memory_benchmark.py --domains finance healthcare --mode fast
#   python benchmarks/memory_system/run_memory_benchmark.py  # uses defaults

import json
import os
import argparse
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional

from dotenv import load_dotenv
load_dotenv()

from src.idea_generation.generator import multiple_llm_idea_generator
from benchmarks.phase_2_quality_vs_single_llm.scoring import (
    score_idea_llm,
    compare_n_scores,
    aggregate_n_way_results,
    IdeaScore,
)


# --- Registry: add new memory systems here without changing the runner ---
MEMORY_CONFIGS = [
    {
        "name": "full_history",
        "memory_mode": "full_history",
        "label": "Full History (baseline)",
        "config_overrides": {
            "phase_selection": "first_n",
            "num_phases": 1,
            "enable_convergence_phase": False,
        },
    },
    {
        "name": "structured",
        "memory_mode": "structured",
        "label": "Structured (shared+personal+3-turn)",
        "config_overrides": {
            "phase_selection": "first_n",
            "num_phases": 1,
            "enable_convergence_phase": False,
        },
    },
    # Future extension example:
    # {"name": "graph", "memory_mode": "graph", "label": "Graph Memory", "config_overrides": {}},
]

# --- Domain registry: add new test domains here ---
DOMAIN_PROMPTS = {
    "finance": "Personal finance tools for young professionals aged 22-35",
    "health": "Mental health and wellness apps for remote workers",
    "education": "Personalized learning platforms for adult upskilling",
    "productivity": "Productivity software for solo freelancers and consultants",
    "sustainability": "Sustainability-focused consumer apps and services",
}


@dataclass
class ConversationQualityMetrics:
    """Metrics measuring conversation quality independent of idea quality."""
    repetition_count: int       # Times a point/idea raised more than once (LLM judge)
    dead_end_recovery: int      # Times a rejected idea resurfaced in later turns
    concept_density: float      # Unique substantive concepts per turn


def _count_repetitions_llm(logs: list, inspiration: str, judge_model: str) -> int:
    """
    Use LLM to count how many times the same point was raised more than once.
    Returns count of repetitions (0 = clean conversation).
    """
    from openai import OpenAI
    client = OpenAI()

    if not logs:
        return 0

    conversation_text = "\n".join(
        f"Turn {ex.get('turn', '?')} - {ex.get('speaker', '?')}: {ex.get('content', '')[:300]}"
        for ex in logs[:30]  # cap at 30 turns for token budget
    )

    prompt = f"""You are reviewing a brainstorming conversation about: {inspiration}

CONVERSATION (truncated):
{conversation_text}

Count how many times the same idea, point, or argument was raised more than once across different turns.
Each repeated instance counts as 1 repetition (e.g., if idea X is mentioned 3 times, that's 2 repetitions).

Respond ONLY with a JSON object:
{{"repetition_count": <integer>, "notes": "<brief explanation>"}}"""

    try:
        response = client.chat.completions.create(
            model=judge_model,
            messages=[
                {"role": "system", "content": "You are a conversation analyst. Count repetitions accurately. Output only JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
        )
        content = response.choices[0].message.content
        start = content.find('{')
        end = content.rfind('}')
        data = json.loads(content[start:end+1])
        return max(0, data.get("repetition_count", 0))
    except Exception as e:
        print(f"[!] Repetition count LLM call failed: {e}")
        return 0


def _count_dead_end_recoveries(logs: list) -> int:
    """
    Heuristic: count how many times a speaker appears to re-raise an idea
    after it was referred to as 'rejected', 'dismissed', or 'that won't work'.
    """
    rejection_signals = {"rejected", "dismissed", "won't work", "already tried", "ruled out", "abandoned"}
    rejected_concepts: list[str] = []
    recovery_count = 0

    for ex in logs:
        content_lower = ex.get("content", "").lower()
        # Detect rejections
        for signal in rejection_signals:
            if signal in content_lower:
                # Extract rough concept (first 60 chars after signal)
                idx = content_lower.find(signal)
                snippet = content_lower[max(0, idx - 30): idx + 60]
                rejected_concepts.append(snippet)
                break

        # Detect recoveries: current exchange mentions a snippet from a previously rejected concept
        for concept in rejected_concepts:
            # Very rough heuristic: check if 5+ word overlap
            concept_words = set(concept.split())
            content_words = set(content_lower.split())
            overlap = concept_words & content_words
            if len(overlap) >= 5:
                recovery_count += 1
                break

    return recovery_count


def _compute_concept_density(logs: list) -> float:
    """
    Rough concept density: unique noun phrases (4+ chars) per turn.
    Avoids LLM call for cost efficiency.
    """
    if not logs:
        return 0.0

    seen_words: set[str] = set()
    for ex in logs:
        words = ex.get("content", "").lower().split()
        for w in words:
            if len(w) >= 4:
                seen_words.add(w)

    return len(seen_words) / len(logs) if logs else 0.0


def _compute_quality_metrics(
    logs: list,
    inspiration: str,
    judge_model: str,
) -> ConversationQualityMetrics:
    """Compute all three conversation quality metrics for a run."""
    return ConversationQualityMetrics(
        repetition_count=_count_repetitions_llm(logs, inspiration, judge_model),
        dead_end_recovery=_count_dead_end_recoveries(logs),
        concept_density=_compute_concept_density(logs),
    )


def _run_single_config(
    domain_prompt: str,
    memory_config: dict,
    assembly_mode: str,
    judge_model: str,
) -> dict:
    """
    Run Assembly under a single memory config, score the output idea, and
    compute conversation quality metrics.

    Returns:
        Dict with idea, score, quality metrics, and raw logs.
    """
    print(f"  [>] Running memory_mode='{memory_config['memory_mode']}' ({memory_config['label']})...")

    # Temporarily override the memory_mode in the mode config
    # We do this by monkey-patching MODE_CONFIGS for this run
    from src.idea_generation import config as cfg_module
    original_mode_config = cfg_module.MODE_CONFIGS[assembly_mode].copy()
    cfg_module.MODE_CONFIGS[assembly_mode]["memory_mode"] = memory_config["memory_mode"]
    for key, val in memory_config.get("config_overrides", {}).items():
        cfg_module.MODE_CONFIGS[assembly_mode][key] = val

    try:
        result = multiple_llm_idea_generator(
            inspiration=domain_prompt,
            number_of_ideas=1,
            mode=assembly_mode,
        )
    finally:
        # Restore original config
        cfg_module.MODE_CONFIGS[assembly_mode] = original_mode_config

    # Extract idea
    if isinstance(result, dict):
        ideas = result.get("ideas", [])
    else:
        ideas = result if isinstance(result, list) else []

    idea = ideas[0] if ideas else {"title": "No idea generated", "description": "Run failed"}

    # Score with LLM judge
    print(f"    [>] Scoring idea...")
    score = score_idea_llm(idea=idea, inspiration=domain_prompt, model=judge_model)

    # Load logs for quality metrics
    try:
        with open("meeting_logs.txt", "r", encoding="utf-8") as f:
            logs = json.load(f)
    except Exception:
        logs = []

    quality = _compute_quality_metrics(logs, domain_prompt, judge_model)

    return {
        "memory_config": memory_config["name"],
        "label": memory_config["label"],
        "idea": idea,
        "score": score.to_dict(),
        "quality_metrics": asdict(quality),
        "logs_count": len(logs),
    }


def run_memory_benchmark(
    domain_ids: list,
    memory_configs: list = None,
    assembly_mode: str = "medium",
    judge_model: str = "gpt-5.1",
    output_dir: str = "results",
) -> dict:
    """
    For each domain, run Assembly under each memory config, score all with
    LLM judge, compare using compare_n_scores() and aggregate_n_way_results().

    Args:
        domain_ids: List of domain keys from DOMAIN_PROMPTS (e.g. ["finance", "health"])
        memory_configs: List of memory config dicts (defaults to MEMORY_CONFIGS registry)
        assembly_mode: Assembly run mode ("fast", "medium", "standard", "deep")
        judge_model: LLM model for scoring
        output_dir: Directory to save results JSON

    Returns:
        Full results dict with per-domain comparisons and aggregated stats
    """
    if memory_configs is None:
        memory_configs = MEMORY_CONFIGS

    os.makedirs(output_dir, exist_ok=True)

    all_comparisons = []
    all_quality = {cfg["name"]: [] for cfg in memory_configs}

    print(f"\n{'='*60}")
    print(f"MEMORY BENCHMARK: {len(domain_ids)} domain(s) × {len(memory_configs)} config(s)")
    print(f"Assembly mode: {assembly_mode} | Judge: {judge_model}")
    print(f"Memory configs: {[c['name'] for c in memory_configs]}")
    print(f"{'='*60}\n")

    for domain_id in domain_ids:
        domain_prompt = DOMAIN_PROMPTS.get(domain_id)
        if not domain_prompt:
            print(f"[!] Unknown domain '{domain_id}', skipping. Valid: {list(DOMAIN_PROMPTS.keys())}")
            continue

        print(f"\n--- Domain: {domain_id} ---")
        print(f"    Prompt: {domain_prompt[:80]}...")

        domain_results = {}
        for mem_cfg in memory_configs:
            run_result = _run_single_config(
                domain_prompt=domain_prompt,
                memory_config=mem_cfg,
                assembly_mode=assembly_mode,
                judge_model=judge_model,
            )
            domain_results[mem_cfg["name"]] = run_result
            all_quality[mem_cfg["name"]].append(run_result["quality_metrics"])

        # N-way score comparison for this domain
        scores: Dict[str, IdeaScore] = {}
        for cfg_name, run_data in domain_results.items():
            s = run_data["score"]
            scores[cfg_name] = IdeaScore(
                novelty=s["novelty"],
                feasibility=s["feasibility"],
                specificity=s["specificity"],
                commercial_clarity=s["commercial_clarity"],
                notes=s.get("notes", ""),
            )

        comparison = compare_n_scores(scores)
        comparison["domain"] = domain_id
        comparison["domain_prompt"] = domain_prompt
        comparison["run_details"] = domain_results
        all_comparisons.append(comparison)

        # Print per-domain summary
        print(f"\n  Results for domain '{domain_id}':")
        for cfg_name, score_obj in scores.items():
            label = next(c["label"] for c in memory_configs if c["name"] == cfg_name)
            print(f"    {label}: total={score_obj.total}/20 "
                  f"(N={score_obj.novelty} F={score_obj.feasibility} "
                  f"S={score_obj.specificity} C={score_obj.commercial_clarity})")
        print(f"  Winner: {comparison['winner']}")

    # Aggregate across all domains
    approach_mapping = {cfg["name"]: cfg["name"] for cfg in memory_configs}
    aggregated = aggregate_n_way_results(all_comparisons, approach_mapping)

    # Aggregate quality metrics
    quality_summary = {}
    for cfg_name, metrics_list in all_quality.items():
        if not metrics_list:
            continue
        quality_summary[cfg_name] = {
            "avg_repetition_count": sum(m["repetition_count"] for m in metrics_list) / len(metrics_list),
            "avg_dead_end_recovery": sum(m["dead_end_recovery"] for m in metrics_list) / len(metrics_list),
            "avg_concept_density": sum(m["concept_density"] for m in metrics_list) / len(metrics_list),
        }

    results = {
        "benchmark_config": {
            "domains": domain_ids,
            "assembly_mode": assembly_mode,
            "judge_model": judge_model,
            "memory_configs": [c["name"] for c in memory_configs],
            "timestamp": datetime.now().isoformat(),
        },
        "comparisons": all_comparisons,
        "aggregated": aggregated,
        "quality_summary": quality_summary,
    }

    # Print final summary table
    print(f"\n{'='*60}")
    print("FINAL RESULTS — IDEA QUALITY")
    print(f"{'='*60}")
    for cfg_name, stats in aggregated.get("by_approach", {}).items():
        label = next((c["label"] for c in memory_configs if c["name"] == cfg_name), cfg_name)
        print(f"  {label}:")
        print(f"    Win rate:  {stats['win_rate']:.1f}%")
        print(f"    Avg score: {stats['avg_score']:.2f}/20")

    print(f"\n{'='*60}")
    print("FINAL RESULTS — CONVERSATION QUALITY")
    print(f"{'='*60}")
    for cfg_name, q in quality_summary.items():
        label = next((c["label"] for c in memory_configs if c["name"] == cfg_name), cfg_name)
        print(f"  {label}:")
        print(f"    Avg repetitions:    {q['avg_repetition_count']:.1f}")
        print(f"    Avg dead-end recov: {q['avg_dead_end_recovery']:.1f}")
        print(f"    Avg concept density:{q['avg_concept_density']:.1f} concepts/turn")

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"memory_benchmark_{timestamp}.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\n[OK] Results saved to: {output_file}")

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Benchmark N memory systems against each other using Assembly + LLM judge"
    )
    parser.add_argument(
        "--domains",
        nargs="+",
        default=["finance"],
        help=f"Domain IDs to test. Available: {list(DOMAIN_PROMPTS.keys())} (default: finance)"
    )
    parser.add_argument(
        "--mode",
        choices=["fast", "medium", "standard", "deep"],
        default="medium",
        help="Assembly run mode (default: medium)"
    )
    parser.add_argument(
        "--judge",
        default="gpt-5.1",
        help="LLM model to use as judge (default: gpt-5.1)"
    )
    parser.add_argument(
        "--output-dir",
        default="benchmarks/memory_system/results",
        help="Directory to save results (default: benchmarks/memory_system/results)"
    )

    args = parser.parse_args()

    run_memory_benchmark(
        domain_ids=args.domains,
        memory_configs=MEMORY_CONFIGS,
        assembly_mode=args.mode,
        judge_model=args.judge,
        output_dir=args.output_dir,
    )
