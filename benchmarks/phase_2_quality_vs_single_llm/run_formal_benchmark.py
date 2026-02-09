# run_formal_benchmark.py
# Formal 3-way benchmark with automated LLM-as-judge scoring
# Compares: Single-shot vs Iterative vs Assembly+Convergence

import json
import os
import sys
import io
import random
from datetime import datetime

# UTF-8 output for Windows
if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from src.idea_generation.generator import multiple_llm_idea_generator
from baseline_single_llm import generate_idea_single_llm
from iterative_single_llm import generate_idea_iterative
from scoring import score_idea_llm, compare_n_scores, aggregate_n_way_results, IdeaScore
from prompts import BENCHMARK_PROMPTS


def build_scoreable_idea(approach: str, result: dict) -> dict:
    """
    Build a unified idea dict suitable for LLM scoring, regardless of approach.
    For assembly+convergence, merge convergence output into the idea for richer scoring.
    """
    idea = result.get("idea", {})
    if not idea:
        return None

    if approach == "assembly" and result.get("convergence"):
        conv = result["convergence"]
        # Merge convergence fields into a comprehensive scoreable representation
        merged = dict(idea)  # Start with raw Assembly idea
        merged["convergence_product_name"] = conv.get("product_name", "")
        merged["convergence_pitch"] = conv.get("one_sentence_pitch", "")
        merged["convergence_target_user_icp"] = conv.get("target_user_icp", "")
        merged["convergence_mvp_bullets"] = conv.get("mvp_bullets", [])
        merged["convergence_monetization_model"] = conv.get("monetization_model", "")
        merged["convergence_key_differentiator"] = conv.get("key_differentiator", "")
        merged["convergence_what_we_are_not_doing"] = conv.get("what_we_are_not_doing", [])
        merged["convergence_risks"] = conv.get("risks_unknowns", [])
        merged["convergence_7_day_plan"] = conv.get("next_7_day_plan", [])
        return merged

    return idea


def run_formal_benchmark(
    domain_ids: list = None,
    model: str = "gpt-5.1",
    assembly_mode: str = "medium",
    judge_model: str = "gpt-5.1",
    output_dir: str = "results",
):
    """
    Run formal 3-way benchmark with automated LLM-as-judge scoring.

    Args:
        domain_ids: List of domain IDs to test (default: finance, remote_work, health)
        model: Model for idea generation
        assembly_mode: Assembly mode (fast/medium/standard/deep)
        judge_model: Model for LLM-as-judge scoring
        output_dir: Directory to save results
    """
    if domain_ids is None:
        domain_ids = ["finance", "remote_work", "health"]

    # Get prompts
    prompts = [p for p in BENCHMARK_PROMPTS if p["id"] in domain_ids]
    if not prompts:
        print(f"[!] No prompts found for domain IDs: {domain_ids}")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    print("=" * 70)
    print("FORMAL 3-WAY BENCHMARK: Single-shot vs Iterative vs Assembly+Convergence")
    print("=" * 70)
    print(f"Domains: {', '.join(domain_ids)}")
    print(f"Generation Model: {model}")
    print(f"Judge Model: {judge_model}")
    print(f"Assembly Mode: {assembly_mode}")
    print(f"Timestamp: {timestamp}")
    print("=" * 70)

    all_comparisons = []
    all_scored = []

    for i, prompt in enumerate(prompts):
        domain_id = prompt["id"]
        inspiration = prompt["inspiration"]

        print(f"\n{'='*70}")
        print(f"DOMAIN {i+1}/{len(prompts)}: {domain_id.upper()}")
        print(f"{'='*70}")

        results = {}

        # === 1. Single-shot ===
        print(f"\n[1/3] Generating single-shot (team-of-experts)...")
        try:
            ss_result = generate_idea_single_llm(inspiration=inspiration, model=model)
            if ss_result.get("idea"):
                results["single_shot"] = {"success": True, "idea": ss_result["idea"]}
                print(f"      Title: {ss_result['idea'].get('title', 'Untitled')}")
            else:
                results["single_shot"] = {"success": False, "error": ss_result.get("error", "No idea")}
                print(f"      FAILED: {results['single_shot']['error']}")
        except Exception as e:
            results["single_shot"] = {"success": False, "error": str(e)}
            print(f"      ERROR: {e}")

        # === 2. Iterative ===
        print(f"\n[2/3] Generating iterative (4-turn refinement)...")
        try:
            it_result = generate_idea_iterative(inspiration=inspiration, model=model)
            if it_result.get("idea"):
                results["iterative"] = {"success": True, "idea": it_result["idea"]}
                print(f"      Title: {it_result['idea'].get('title', 'Untitled')}")
            else:
                results["iterative"] = {"success": False, "error": it_result.get("error", "No idea")}
                print(f"      FAILED: {results['iterative']['error']}")
        except Exception as e:
            results["iterative"] = {"success": False, "error": str(e)}
            print(f"      ERROR: {e}")

        # === 3. Assembly + Convergence ===
        print(f"\n[3/3] Generating Assembly + Convergence (multi-persona + refinement)...")
        try:
            output = multiple_llm_idea_generator(
                inspiration=inspiration,
                number_of_ideas=1,
                mode=assembly_mode,
            )
            if isinstance(output, dict):
                ideas = output.get("ideas", [])
                convergence = output.get("convergence")
            else:
                ideas = output if output else []
                convergence = None

            if ideas and len(ideas) > 0:
                results["assembly"] = {
                    "success": True,
                    "idea": ideas[0],
                    "convergence": convergence,
                }
                title = convergence.get("product_name", ideas[0].get("title", "Untitled")) if convergence else ideas[0].get("title", "Untitled")
                print(f"      Title: {title}")
                print(f"      Convergence: {'Yes' if convergence else 'No'}")
            else:
                results["assembly"] = {"success": False, "error": "No ideas returned"}
                print(f"      FAILED: No ideas returned")
        except Exception as e:
            results["assembly"] = {"success": False, "error": str(e)}
            print(f"      ERROR: {e}")

        # Store raw comparison
        comparison = {
            "domain_id": domain_id,
            "inspiration": inspiration,
            "timestamp": datetime.now().isoformat(),
            "results": {k: {**v, "convergence": v.get("convergence")} if k == "assembly" else v for k, v in results.items()},
        }
        all_comparisons.append(comparison)

        # === Score with LLM Judge ===
        print(f"\n{'~'*50}")
        print(f"SCORING {domain_id.upper()} with LLM Judge...")
        print(f"{'~'*50}")

        scores = {}
        for approach in ["single_shot", "iterative", "assembly"]:
            if results.get(approach, {}).get("success"):
                scoreable = build_scoreable_idea(approach, results[approach])
                if scoreable:
                    print(f"\n  Scoring {approach}...")
                    score = score_idea_llm(
                        idea=scoreable,
                        inspiration=inspiration,
                        model=judge_model,
                    )
                    scores[approach] = score
                    print(f"    Novelty={score.novelty} Feasibility={score.feasibility} "
                          f"Specificity={score.specificity} Commercial={score.commercial_clarity} "
                          f"Total={score.total}")
                    print(f"    Notes: {score.notes[:100]}...")

        # Compare scores for this domain
        if len(scores) >= 2:
            scored_result = compare_n_scores(scores)
            scored_result["domain_id"] = domain_id
            scored_result["mapping"] = {k: k for k in scores.keys()}  # Identity mapping (not anonymized)
            all_scored.append(scored_result)

            print(f"\n  Winner: {scored_result['winner']}")
            print(f"  Totals: {scored_result['totals']}")

    # === Aggregate Results ===
    print(f"\n\n{'='*70}")
    print("FINAL AGGREGATED RESULTS")
    print(f"{'='*70}")

    if all_scored:
        aggregated = aggregate_n_way_results(
            all_scored,
            approach_mapping={"single_shot": "single_shot", "iterative": "iterative", "assembly": "assembly"}
        )

        # Print per-domain results
        print("\nPER-DOMAIN SCORES:")
        print("-" * 70)
        print(f"{'Domain':<15} {'Single-shot':<15} {'Iterative':<15} {'Assembly+Conv':<15} {'Winner':<15}")
        print("-" * 70)
        for scored in all_scored:
            domain = scored.get("domain_id", "?")
            totals = scored.get("totals", {})
            winner = scored.get("winner", "?")
            print(f"{domain:<15} {totals.get('single_shot', '-'):<15} {totals.get('iterative', '-'):<15} {totals.get('assembly', '-'):<15} {winner:<15}")

        # Print aggregated results
        print(f"\n{'='*70}")
        print("APPROACH SUMMARY:")
        print("-" * 70)
        print(f"{'Approach':<20} {'Wins':<10} {'Win Rate':<12} {'Avg Score':<12}")
        print("-" * 70)
        for approach in ["single_shot", "iterative", "assembly"]:
            stats = aggregated.get("by_approach", {}).get(approach, {})
            if stats:
                print(f"{approach:<20} {stats['wins']:<10.1f} {stats['win_rate']:<12.1f}% {stats['avg_score']:<12.1f}")

        # Print per-criteria breakdown
        print(f"\n{'='*70}")
        print("PER-CRITERIA BREAKDOWN (average across domains):")
        print("-" * 70)
        criteria_totals = {approach: {"novelty": 0, "feasibility": 0, "specificity": 0, "commercial_clarity": 0, "count": 0}
                          for approach in ["single_shot", "iterative", "assembly"]}

        for scored in all_scored:
            details = scored.get("score_details", {})
            for approach, detail in details.items():
                if approach in criteria_totals:
                    for criterion in ["novelty", "feasibility", "specificity", "commercial_clarity"]:
                        criteria_totals[approach][criterion] += detail.get(criterion, 0)
                    criteria_totals[approach]["count"] += 1

        print(f"{'Criterion':<22} {'Single-shot':<15} {'Iterative':<15} {'Assembly+Conv':<15}")
        print("-" * 70)
        for criterion in ["novelty", "feasibility", "specificity", "commercial_clarity"]:
            row = f"{criterion:<22}"
            for approach in ["single_shot", "iterative", "assembly"]:
                ct = criteria_totals[approach]
                avg = ct[criterion] / ct["count"] if ct["count"] > 0 else 0
                row += f" {avg:<14.1f}"
            print(row)

        # Save results
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"formal_benchmark_{timestamp}.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "config": {
                    "generation_model": model,
                    "judge_model": judge_model,
                    "assembly_mode": assembly_mode,
                    "domains": domain_ids,
                    "timestamp": timestamp,
                },
                "comparisons": all_comparisons,
                "scored_comparisons": all_scored,
                "aggregated": aggregated,
                "criteria_averages": {
                    approach: {
                        criterion: ct[criterion] / ct["count"] if ct["count"] > 0 else 0
                        for criterion in ["novelty", "feasibility", "specificity", "commercial_clarity"]
                    }
                    for approach, ct in criteria_totals.items()
                },
            }, f, indent=2, default=str)
        print(f"\nResults saved to: {output_file}")

    else:
        print("\nNo valid scored comparisons to aggregate.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run formal 3-way benchmark with LLM scoring")
    parser.add_argument(
        "--domains",
        nargs="+",
        default=["finance", "remote_work", "health"],
        help="Domain IDs to benchmark (default: finance remote_work health)"
    )
    parser.add_argument(
        "--model",
        default="gpt-5.1",
        help="Model for idea generation (default: gpt-5.1)"
    )
    parser.add_argument(
        "--assembly-mode",
        default="medium",
        choices=["fast", "medium", "standard", "deep"],
        help="Assembly mode (default: medium)"
    )
    parser.add_argument(
        "--judge-model",
        default="gpt-5.1",
        help="Model for LLM-as-judge scoring (default: gpt-5.1)"
    )
    args = parser.parse_args()

    run_formal_benchmark(
        domain_ids=args.domains,
        model=args.model,
        assembly_mode=args.assembly_mode,
        judge_model=args.judge_model,
    )
