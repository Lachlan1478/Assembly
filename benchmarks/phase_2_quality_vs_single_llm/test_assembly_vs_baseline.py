# test_assembly_vs_baseline.py
# Phase 2 Benchmark: Compare Assembly output to single LLM baseline

import json
import os
import random
import sys
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from src.idea_generation.generator import multiple_llm_idea_generator
from baseline_single_llm import generate_idea_single_llm


def run_single_comparison(
    inspiration: str,
    prompt_id: str,
    model: str = "gpt-4o-mini",
    mode: str = "medium",
) -> dict:
    """
    Run a single comparison between Assembly and baseline.

    Args:
        inspiration: The domain/context prompt
        prompt_id: Identifier for this prompt
        model: Model to use
        mode: Assembly mode

    Returns:
        Comparison result dictionary
    """
    print(f"\n{'='*50}")
    print(f"Running comparison for: {prompt_id}")
    print(f"{'='*50}")

    result = {
        "prompt_id": prompt_id,
        "inspiration": inspiration,
        "timestamp": datetime.now().isoformat(),
        "assembly": {"success": False, "idea": None, "error": None},
        "baseline": {"success": False, "idea": None, "error": None},
    }

    # Generate with baseline (single LLM)
    print("\n[1/2] Generating baseline (single LLM)...")
    try:
        baseline_result = generate_idea_single_llm(
            inspiration=inspiration,
            model=model,
        )
        if baseline_result.get("idea"):
            result["baseline"]["success"] = True
            result["baseline"]["idea"] = baseline_result["idea"]
            result["baseline"]["tokens_used"] = baseline_result.get("tokens_used")
            print(f"      Baseline idea: {baseline_result['idea'].get('title', 'Untitled')}")
        else:
            result["baseline"]["error"] = baseline_result.get("error", "No idea extracted")
            print(f"      Baseline failed: {result['baseline']['error']}")
    except Exception as e:
        result["baseline"]["error"] = str(e)
        print(f"      Baseline error: {e}")

    # Generate with Assembly (multi-persona)
    print("\n[2/2] Generating with Assembly (multi-persona)...")
    try:
        ideas = multiple_llm_idea_generator(
            inspiration=inspiration,
            number_of_ideas=1,
            mode=mode,
        )
        if ideas and len(ideas) > 0:
            result["assembly"]["success"] = True
            result["assembly"]["idea"] = ideas[0]
            print(f"      Assembly idea: {ideas[0].get('title', 'Untitled')}")
        else:
            result["assembly"]["error"] = "No ideas returned"
            print(f"      Assembly failed: No ideas returned")
    except Exception as e:
        result["assembly"]["error"] = str(e)
        print(f"      Assembly error: {e}")

    return result


def run_comparison(
    prompts: list[dict],
    model: str = "gpt-4o-mini",
    mode: str = "medium",
    output_dir: str = "results",
    anonymize: bool = True,
) -> dict:
    """
    Run comparison test across multiple prompts.

    Args:
        prompts: List of prompt dictionaries with 'id' and 'inspiration'
        model: Model to use
        mode: Assembly mode
        output_dir: Directory to save results
        anonymize: Whether to randomize A/B order for blind scoring

    Returns:
        Aggregated results dictionary
    """
    print(f"\n{'='*60}")
    print("PHASE 2: Assembly vs Single LLM Comparison")
    print(f"{'='*60}")
    print(f"Prompts: {len(prompts)}")
    print(f"Model: {model}")
    print(f"Mode: {mode}")
    print(f"{'='*60}")

    results = {
        "test_name": "assembly_vs_baseline",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "model": model,
            "mode": mode,
            "num_prompts": len(prompts),
            "anonymized": anonymize,
        },
        "comparisons": [],
        "summary": {
            "total": len(prompts),
            "both_successful": 0,
            "assembly_only": 0,
            "baseline_only": 0,
            "both_failed": 0,
        },
    }

    for i, prompt in enumerate(prompts):
        print(f"\n--- Prompt {i+1}/{len(prompts)} ---")

        comparison = run_single_comparison(
            inspiration=prompt["inspiration"],
            prompt_id=prompt["id"],
            model=model,
            mode=mode,
        )

        # Track success rates
        assembly_ok = comparison["assembly"]["success"]
        baseline_ok = comparison["baseline"]["success"]

        if assembly_ok and baseline_ok:
            results["summary"]["both_successful"] += 1
        elif assembly_ok:
            results["summary"]["assembly_only"] += 1
        elif baseline_ok:
            results["summary"]["baseline_only"] += 1
        else:
            results["summary"]["both_failed"] += 1

        # Anonymize for blind scoring if requested
        if anonymize and assembly_ok and baseline_ok:
            # Randomly assign to A or B
            if random.random() < 0.5:
                comparison["idea_a"] = comparison["assembly"]["idea"]
                comparison["idea_b"] = comparison["baseline"]["idea"]
                comparison["mapping"] = {"A": "assembly", "B": "baseline"}
            else:
                comparison["idea_a"] = comparison["baseline"]["idea"]
                comparison["idea_b"] = comparison["assembly"]["idea"]
                comparison["mapping"] = {"A": "baseline", "B": "assembly"}
        else:
            comparison["idea_a"] = comparison.get("assembly", {}).get("idea")
            comparison["idea_b"] = comparison.get("baseline", {}).get("idea")
            comparison["mapping"] = {"A": "assembly", "B": "baseline"}

        results["comparisons"].append(comparison)

    # Calculate summary stats
    results["summary"]["assembly_success_rate"] = (
        (results["summary"]["both_successful"] + results["summary"]["assembly_only"])
        / len(prompts) * 100
    )
    results["summary"]["baseline_success_rate"] = (
        (results["summary"]["both_successful"] + results["summary"]["baseline_only"])
        / len(prompts) * 100
    )

    # Print summary
    print(f"\n{'='*60}")
    print("COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"Both successful: {results['summary']['both_successful']}/{len(prompts)}")
    print(f"Assembly success rate: {results['summary']['assembly_success_rate']:.1f}%")
    print(f"Baseline success rate: {results['summary']['baseline_success_rate']:.1f}%")

    # Save results
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(
        output_dir,
        f"comparison_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")
    print("\nNext step: Use scoring.py to evaluate the anonymized pairs")

    return results


if __name__ == "__main__":
    from prompts import BENCHMARK_PROMPTS

    # Run quick test with first 2 prompts
    run_comparison(
        prompts=BENCHMARK_PROMPTS[:2],
        mode="fast",
        output_dir="results",
    )
