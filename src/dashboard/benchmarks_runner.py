"""
Assembly Dashboard — Benchmark registry and runner.

BENCHMARKS   : metadata list describing every benchmark (id, name, params, …)
get_benchmark_results(id) : load the most-recent saved result file, or None
run_benchmark(id, queue, loop, params) : execute in the calling thread (use
    run_in_executor), streaming print() output to the asyncio queue.
"""

import contextlib
import glob
import io
import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

BENCHMARKS: List[Dict[str, Any]] = [
    {
        "id": "phase1_reliability",
        "name": "End-to-End Reliability",
        "category": "Phase 1 — System Validity",
        "description": (
            "Assembly chains together many LLM calls, async persona updates, and "
            "structured JSON extraction across multiple phases. Before any quality "
            "claim can be trusted, we need to know: does the system reliably produce "
            "a complete, valid idea output every time it runs? Without this guarantee "
            "every downstream benchmark is meaningless — you can't measure idea quality "
            "if the pipeline randomly fails or returns malformed output."
        ),
        "how_it_runs": (
            "Runs the full Assembly pipeline N times against the same fixed inspiration "
            "prompt (personal finance tools for young professionals). Each output is "
            "validated against the required idea schema — title, description, "
            "target_users, must_haves, constraints, non_goals. Failures are classified "
            "as either completion failures (pipeline crashed or timed out) or structure "
            "failures (output produced but fields are missing or malformed). "
            "Gate: 100 % completion rate and ≥ 90 % structurally valid outputs."
        ),
        "params": {
            "num_runs": {"type": "int", "default": 3, "label": "Number of runs", "min": 1, "max": 10},
            "mode": {
                "type": "select",
                "options": ["fast", "medium"],
                "default": "fast",
                "label": "Assembly mode",
            },
        },
        "results_dir": "benchmarks/phase_1_system_validity/results",
        "results_pattern": "reliability_test_*.json",
    },
    {
        "id": "phase1_role_adherence",
        "name": "Persona Role Adherence",
        "category": "Phase 1 — System Validity",
        "description": (
            "Assembly's core value comes from distinct perspectives clashing — a market "
            "researcher challenges assumptions differently than a risk analyst. If "
            "personas drift out of character and start speaking generically, the "
            "multi-persona debate collapses to a single averaged voice and loses its "
            "advantage over a plain GPT call. This test measures whether each persona "
            "consistently reasons from their assigned viewpoint throughout the full "
            "conversation, not just their opening turn."
        ),
        "how_it_runs": (
            "Runs one full Assembly session to produce conversation logs, then scores "
            "every persona turn for role adherence. A turn is 'in-role' when it "
            "contains reasoning patterns characteristic of the persona's archetype "
            "(e.g. a risk analyst raises constraints and failure modes; a market "
            "researcher references user segments and willingness to pay) and avoids "
            "content outside their defined scope. Each turn is scored 1–5; a score "
            "of ≥ 3 counts as in-role. "
            "Gate: ≥ 90 % of all turns scored in-role."
        ),
        "params": {
            "mode": {
                "type": "select",
                "options": ["fast", "medium"],
                "default": "fast",
                "label": "Assembly mode",
            },
        },
        "results_dir": "benchmarks/phase_1_system_validity/results",
        "results_pattern": "role_adherence_test_*.json",
    },
    {
        "id": "phase2_two_way",
        "name": "Assembly vs Single LLM (2-way)",
        "category": "Phase 2 — Quality vs Single LLM",
        "description": (
            "The central hypothesis behind Assembly: a structured multi-persona debate "
            "produces better startup ideas than asking a single LLM directly — even "
            "when that single prompt is carefully crafted to instruct the model to "
            "reason as a team of experts. This test puts that claim to the test head-"
            "to-head, using an independent LLM as a blind judge to eliminate bias."
        ),
        "how_it_runs": (
            "Runs N real-world inspiration prompts (spanning finance, health, remote "
            "work, and more) through both approaches independently. Ideas are "
            "anonymised (A/B, randomly assigned) so the judge cannot tell which "
            "system produced them. The judge scores each idea on four criteria: "
            "novelty (is this idea surprising and non-obvious?), feasibility (could "
            "this realistically be built?), specificity (are the target user and "
            "solution concrete?), and commercial clarity (is the monetisation path "
            "clear?), each 1–5. "
            "Gate: Assembly wins ≥ 70 % of comparisons and scores ≥ 20 % higher on average."
        ),
        "params": {
            "num_prompts": {"type": "int", "default": 3, "label": "Number of prompts", "min": 1, "max": 10},
            "assembly_mode": {
                "type": "select",
                "options": ["fast", "medium"],
                "default": "fast",
                "label": "Assembly mode",
            },
        },
        "results_dir": "benchmarks/phase_2_quality_vs_single_llm/results",
        "results_pattern": "comparison_results_*_scored.json",
    },
    {
        "id": "phase2_three_way",
        "name": "Assembly vs Single LLM vs Iterative (3-way)",
        "category": "Phase 2 — Quality vs Single LLM",
        "description": (
            "A sceptic might argue: why pay for a multi-agent system when you can "
            "just ask the same LLM to critique and improve its own output? Iterative "
            "self-refinement is a real and cheap alternative. This test adds that as "
            "a third baseline alongside the single-shot approach, so all three "
            "strategies are ranked blind by the same judge on the same prompts."
        ),
        "how_it_runs": (
            "Runs N prompts through three approaches: (1) Single-shot — one prompt "
            "instructing GPT to reason as a team of experts and produce a structured "
            "idea. (2) Iterative — 4 sequential turns with the same model: initial "
            "proposal → self-critique identifying 3 weaknesses → address each "
            "critique with concrete refinements → finalise to JSON. (3) Assembly — "
            "multi-persona structured debate across phases with a mediator persona. "
            "All three outputs are anonymised (A/B/C, randomly assigned) then scored "
            "by an LLM judge on the same 4-criterion rubric: novelty, feasibility, "
            "specificity, and commercial clarity (each 1–5)."
        ),
        "params": {
            "num_prompts": {"type": "int", "default": 3, "label": "Number of prompts", "min": 1, "max": 10},
            "assembly_mode": {
                "type": "select",
                "options": ["fast", "medium"],
                "default": "fast",
                "label": "Assembly mode",
            },
        },
        "results_dir": "benchmarks/phase_2_quality_vs_single_llm/results",
        "results_pattern": "three_way_comparison_*_scored.json",
    },
    {
        "id": "memory_benchmark",
        "name": "Full History vs Structured Memory",
        "category": "Memory System",
        "description": (
            "As Assembly conversations grow longer, feeding the full transcript to "
            "every persona on every turn becomes expensive and eventually hits model "
            "context limits. Structured memory is the proposed solution: instead of "
            "the full history, each persona receives a shared consensus summary "
            "(what the group has agreed on and ruled out), their own belief-state "
            "evolution (how their position has shifted), and only the last 3 exchanges "
            "verbatim. This benchmark tests a critical question: does that compression "
            "hurt idea quality, or does the tighter, more curated context actually "
            "improve it by reducing noise?"
        ),
        "how_it_runs": (
            "Runs Assembly twice on the same inspiration domain — once with "
            "full_history (entire conversation transcript injected into every persona "
            "prompt each turn) and once with structured memory (shared consensus + "
            "personal belief state + 3-turn verbatim window). Both output ideas are "
            "scored by an LLM judge on novelty, feasibility, specificity, and "
            "commercial clarity (each 1–5). Conversation quality is measured "
            "independently across three signals: repetition count (how often the "
            "same idea surfaces without development), dead-end recovery (how often "
            "the conversation escapes stuck or circular patterns), and concept density "
            "(unique concepts introduced per turn — higher means the conversation is "
            "covering more ground per token spent)."
        ),
        "params": {
            "domains": {
                "type": "multiselect",
                "options": ["finance", "health", "education", "productivity", "sustainability"],
                "default": ["finance"],
                "label": "Domains",
            },
            "mode": {
                "type": "select",
                "options": ["fast", "medium"],
                "default": "medium",
                "label": "Assembly mode",
            },
        },
        "results_dir": "benchmarks/memory_system/results",
        "results_pattern": "memory_benchmark_*.json",
    },
]


# ---------------------------------------------------------------------------
# Results loading
# ---------------------------------------------------------------------------

def get_benchmark_results(benchmark_id: str) -> Optional[Dict[str, Any]]:
    """Return the most-recent saved result for a benchmark, or None."""
    bm = next((b for b in BENCHMARKS if b["id"] == benchmark_id), None)
    if not bm:
        return None
    pattern = str(Path(bm["results_dir"]) / bm["results_pattern"])
    files = sorted(glob.glob(pattern))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as f:
        data = json.load(f)
    data["_result_file"] = files[-1]
    return data


def list_all_results(benchmark_id: str) -> List[Dict[str, Any]]:
    """Return metadata for every saved result file (newest first)."""
    bm = next((b for b in BENCHMARKS if b["id"] == benchmark_id), None)
    if not bm:
        return []
    pattern = str(Path(bm["results_dir"]) / bm["results_pattern"])
    files = sorted(glob.glob(pattern), reverse=True)
    out = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)
            out.append({
                "file": f,
                "timestamp": data.get("timestamp") or data.get("benchmark_config", {}).get("timestamp"),
                "summary": data.get("summary") or data.get("aggregated"),
            })
        except Exception:
            pass
    return out


# ---------------------------------------------------------------------------
# Queue writer — thread-safe stdout redirect
# ---------------------------------------------------------------------------

class _QueueWriter(io.TextIOBase):
    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self._q = queue
        self._loop = loop

    def write(self, s: str) -> int:
        stripped = s.rstrip("\n")
        if stripped:
            try:
                self._loop.call_soon_threadsafe(
                    self._q.put_nowait,
                    {"type": "benchmark_log", "line": stripped, "ts": time.time()},
                )
            except Exception:
                pass
        return len(s)

    def flush(self):
        pass


# ---------------------------------------------------------------------------
# Public runner
# ---------------------------------------------------------------------------

def run_benchmark(
    benchmark_id: str,
    queue: asyncio.Queue,
    loop: asyncio.AbstractEventLoop,
    params: Dict[str, Any],
) -> None:
    """
    Execute the requested benchmark in the calling thread (intended for
    loop.run_in_executor).  Streams print() output to *queue* and emits a
    benchmark_complete or benchmark_error event when done.
    """
    writer = _QueueWriter(queue, loop)

    def emit(event: Dict[str, Any]) -> None:
        try:
            loop.call_soon_threadsafe(queue.put_nowait, event)
        except Exception:
            pass

    bm = next((b for b in BENCHMARKS if b["id"] == benchmark_id), None)
    if not bm:
        emit({"type": "benchmark_error", "message": f"Unknown benchmark '{benchmark_id}'"})
        return

    try:
        with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
            result = _dispatch(benchmark_id, params)
        emit({"type": "benchmark_complete", "result": result, "ts": time.time()})
    except Exception as exc:
        emit({
            "type": "benchmark_error",
            "message": str(exc),
            "detail": traceback.format_exc(),
            "ts": time.time(),
        })


# ---------------------------------------------------------------------------
# Dispatch to individual runners
# ---------------------------------------------------------------------------

def _dispatch(benchmark_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
    if benchmark_id == "phase1_reliability":
        return _run_phase1_reliability(params)
    if benchmark_id == "phase1_role_adherence":
        return _run_phase1_role_adherence(params)
    if benchmark_id == "phase2_two_way":
        return _run_phase2_two_way(params)
    if benchmark_id == "phase2_three_way":
        return _run_phase2_three_way(params)
    if benchmark_id == "memory_benchmark":
        return _run_memory_benchmark(params)
    raise ValueError(f"Unknown benchmark id: {benchmark_id}")


# ---------------------------------------------------------------------------
# Individual runners
# ---------------------------------------------------------------------------

def _model_for_mode(mode: str) -> str:
    try:
        from src.idea_generation.config import MODE_CONFIGS
        return MODE_CONFIGS.get(mode, {}).get("model", "gpt-5.1")
    except Exception:
        return "gpt-5.1"


def _run_phase1_reliability(params: Dict[str, Any]) -> Dict[str, Any]:
    from benchmarks.phase_1_system_validity.test_end_to_end_reliability import run_reliability_test
    from benchmarks.phase_1_system_validity.prompts import STANDARD_INSPIRATION

    mode = params.get("mode", "fast")
    model = _model_for_mode(mode)
    return run_reliability_test(
        inspiration=STANDARD_INSPIRATION,
        model_name=model,
        num_runs=int(params.get("num_runs", 3)),
        mode=mode,
        output_dir="benchmarks/phase_1_system_validity/results",
    )


def _run_phase1_role_adherence(params: Dict[str, Any]) -> Dict[str, Any]:
    from benchmarks.phase_1_system_validity.test_end_to_end_reliability import run_reliability_test
    from benchmarks.phase_1_system_validity.test_persona_role_adherence import run_role_adherence_test
    from benchmarks.phase_1_system_validity.prompts import STANDARD_INSPIRATION

    mode = params.get("mode", "fast")
    model = _model_for_mode(mode)

    # Generate a fresh run to produce conversation logs
    print("Generating conversation logs for role adherence analysis…")
    run_reliability_test(
        inspiration=STANDARD_INSPIRATION,
        model_name=model,
        num_runs=1,
        mode=mode,
        output_dir="benchmarks/phase_1_system_validity/results",
    )

    # Find most recent full_conversation.json
    log_files = sorted(glob.glob("conversation_logs/**/full_conversation.json", recursive=True))
    logs_path = log_files[-1] if log_files else None
    if logs_path:
        print(f"Analysing logs: {logs_path}")

    return run_role_adherence_test(
        logs_path=logs_path,
        use_llm=False,
        model_name="heuristic",
        output_dir="benchmarks/phase_1_system_validity/results",
    )


def _run_phase2_two_way(params: Dict[str, Any]) -> Dict[str, Any]:
    from benchmarks.phase_2_quality_vs_single_llm.test_assembly_vs_baseline import run_comparison
    from benchmarks.phase_2_quality_vs_single_llm.prompts import BENCHMARK_PROMPTS
    from benchmarks.phase_2_quality_vs_single_llm.scoring import (
        score_idea_llm, compare_scores, aggregate_results, check_phase2_gate,
    )

    mode = params.get("assembly_mode", "fast")
    model = _model_for_mode(mode)
    num_prompts = int(params.get("num_prompts", 3))
    selected = BENCHMARK_PROMPTS[:num_prompts]

    output_dir = "benchmarks/phase_2_quality_vs_single_llm/results"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"Running {num_prompts} prompt(s) through Assembly ({mode}) and single-shot GPT…")
    results = run_comparison(
        prompts=selected,
        model=model,
        mode=mode,
        output_dir=output_dir,
        anonymize=True,
    )

    print("Scoring with LLM judge…")
    scored_comparisons = []
    for comp in results.get("comparisons", []):
        insp = comp.get("inspiration", "")
        assembly_idea = (comp.get("assembly") or {}).get("idea") or {}
        baseline_idea = (comp.get("baseline") or {}).get("idea") or {}
        score_assembly = score_idea_llm(assembly_idea, insp, model)
        score_baseline = score_idea_llm(baseline_idea, insp, model)
        comparison = compare_scores(score_assembly, score_baseline)
        scored_comparisons.append({
            **comp,
            "assembly_score": score_assembly.__dict__ if hasattr(score_assembly, "__dict__") else vars(score_assembly),
            "baseline_score": score_baseline.__dict__ if hasattr(score_baseline, "__dict__") else vars(score_baseline),
            "comparison": comparison,
        })

    aggregated = aggregate_results([c["comparison"] for c in scored_comparisons])
    gate = check_phase2_gate({"aggregated": aggregated})
    final = {
        **results,
        "comparisons": scored_comparisons,
        "aggregated": aggregated,
        "gate": gate,
    }

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(output_dir) / f"comparison_results_{ts}_scored.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, default=str)
    print(f"Saved: {out_path}")
    return final


def _run_phase2_three_way(params: Dict[str, Any]) -> Dict[str, Any]:
    from benchmarks.phase_2_quality_vs_single_llm.test_assembly_vs_baseline import run_three_way_comparison
    from benchmarks.phase_2_quality_vs_single_llm.prompts import BENCHMARK_PROMPTS
    from benchmarks.phase_2_quality_vs_single_llm.scoring import (
        score_idea_llm, compare_n_scores, aggregate_n_way_results,
    )

    mode = params.get("assembly_mode", "fast")
    model = _model_for_mode(mode)
    num_prompts = int(params.get("num_prompts", 3))
    selected = BENCHMARK_PROMPTS[:num_prompts]

    output_dir = "benchmarks/phase_2_quality_vs_single_llm/results"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"Running {num_prompts} prompt(s) — Assembly / single-shot / iterative…")
    results = run_three_way_comparison(
        prompts=selected,
        model=model,
        mode=mode,
        output_dir=output_dir,
        anonymize=True,
    )

    print("Scoring with LLM judge…")
    approach_mapping = {"assembly": "Assembly", "single_shot": "Single-shot GPT", "iterative": "Iterative GPT"}
    scored_comparisons = []
    for comp in results.get("comparisons", []):
        insp = comp.get("inspiration", "")
        scores = {}
        for key in ("assembly", "single_shot", "iterative"):
            idea = (comp.get(key) or {}).get("idea") or {}
            s = score_idea_llm(idea, insp, model)
            scores[key] = s
        n_comp = compare_n_scores(scores)
        scored_comparisons.append({**comp, "n_way_scores": n_comp})

    aggregated = aggregate_n_way_results(scored_comparisons, approach_mapping)
    final = {**results, "comparisons": scored_comparisons, "aggregated": aggregated}

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = Path(output_dir) / f"three_way_comparison_{ts}_scored.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, default=str)
    print(f"Saved: {out_path}")
    return final


def _run_memory_benchmark(params: Dict[str, Any]) -> Dict[str, Any]:
    from benchmarks.memory_system.run_memory_benchmark import run_memory_benchmark

    domains = params.get("domains", ["finance"])
    if isinstance(domains, str):
        domains = [domains]
    mode = params.get("mode", "medium")

    output_dir = "benchmarks/memory_system/results"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"Running memory benchmark on domains: {domains} (mode: {mode})…")
    return run_memory_benchmark(
        domain_ids=domains,
        assembly_mode=mode,
        judge_model=_model_for_mode(mode),
        output_dir=output_dir,
    )
