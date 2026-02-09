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
from iterative_single_llm import generate_idea_iterative


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


def run_single_three_way_comparison(
    inspiration: str,
    prompt_id: str,
    model: str = "gpt-4o-mini",
    mode: str = "medium",
) -> dict:
    """
    Run a single 3-way comparison between Assembly, single-shot team, and iterative refinement.

    Args:
        inspiration: The domain/context prompt
        prompt_id: Identifier for this prompt
        model: Model to use
        mode: Assembly mode

    Returns:
        Comparison result dictionary
    """
    print(f"\n{'='*50}")
    print(f"Running 3-way comparison for: {prompt_id}")
    print(f"{'='*50}")

    result = {
        "prompt_id": prompt_id,
        "inspiration": inspiration,
        "timestamp": datetime.now().isoformat(),
        "assembly": {"success": False, "idea": None, "error": None, "tokens_used": None},
        "single_shot": {"success": False, "idea": None, "error": None, "tokens_used": None},
        "iterative": {"success": False, "idea": None, "error": None, "tokens_used": None},
    }

    # Generate with single-shot (team-of-experts prompt)
    print("\n[1/3] Generating single-shot (team-of-experts)...")
    try:
        single_shot_result = generate_idea_single_llm(
            inspiration=inspiration,
            model=model,
        )
        if single_shot_result.get("idea"):
            result["single_shot"]["success"] = True
            result["single_shot"]["idea"] = single_shot_result["idea"]
            result["single_shot"]["tokens_used"] = single_shot_result.get("tokens_used")
            print(f"      Single-shot idea: {single_shot_result['idea'].get('title', 'Untitled')}")
        else:
            result["single_shot"]["error"] = single_shot_result.get("error", "No idea extracted")
            print(f"      Single-shot failed: {result['single_shot']['error']}")
    except Exception as e:
        result["single_shot"]["error"] = str(e)
        print(f"      Single-shot error: {e}")

    # Generate with iterative refinement
    print("\n[2/3] Generating iterative (4-turn refinement)...")
    try:
        iterative_result = generate_idea_iterative(
            inspiration=inspiration,
            model=model,
        )
        if iterative_result.get("idea"):
            result["iterative"]["success"] = True
            result["iterative"]["idea"] = iterative_result["idea"]
            result["iterative"]["tokens_used"] = iterative_result.get("total_tokens")
            result["iterative"]["turns"] = iterative_result.get("turns", [])
            print(f"      Iterative idea: {iterative_result['idea'].get('title', 'Untitled')}")
        else:
            result["iterative"]["error"] = iterative_result.get("error", "No idea extracted")
            print(f"      Iterative failed: {result['iterative']['error']}")
    except Exception as e:
        result["iterative"]["error"] = str(e)
        print(f"      Iterative error: {e}")

    # Generate with Assembly (multi-persona + convergence)
    print("\n[3/3] Generating with Assembly (multi-persona + convergence)...")
    try:
        output = multiple_llm_idea_generator(
            inspiration=inspiration,
            number_of_ideas=1,
            mode=mode,
        )
        # Handle both return formats: dict (convergence enabled) or list (convergence disabled)
        if isinstance(output, dict):
            ideas = output.get("ideas", [])
            convergence = output.get("convergence")
        else:
            ideas = output if output else []
            convergence = None

        if ideas and len(ideas) > 0:
            result["assembly"]["success"] = True
            result["assembly"]["idea"] = ideas[0]
            result["assembly"]["convergence"] = convergence
            title = convergence.get("product_name", ideas[0].get("title", "Untitled")) if convergence else ideas[0].get("title", "Untitled")
            print(f"      Assembly idea: {title}")
        else:
            result["assembly"]["error"] = "No ideas returned"
            print(f"      Assembly failed: No ideas returned")
    except Exception as e:
        result["assembly"]["error"] = str(e)
        print(f"      Assembly error: {e}")

    return result


def run_three_way_comparison(
    prompts: list[dict],
    model: str = "gpt-4o-mini",
    mode: str = "medium",
    output_dir: str = "results",
    anonymize: bool = True,
) -> dict:
    """
    Run 3-way comparison test across multiple prompts.

    Compares:
    - A. Single-shot team-of-experts (one prompt)
    - B. Iterative refinement (4 sequential turns)
    - C. Assembly (multi-persona with phases)

    Args:
        prompts: List of prompt dictionaries with 'id' and 'inspiration'
        model: Model to use
        mode: Assembly mode
        output_dir: Directory to save results
        anonymize: Whether to randomize A/B/C order for blind scoring

    Returns:
        Aggregated results dictionary
    """
    print(f"\n{'='*60}")
    print("PHASE 2: 3-Way Comparison (Single-shot vs Iterative vs Assembly)")
    print(f"{'='*60}")
    print(f"Prompts: {len(prompts)}")
    print(f"Model: {model}")
    print(f"Mode: {mode}")
    print(f"{'='*60}")

    results = {
        "test_name": "three_way_comparison",
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
            "all_successful": 0,
            "assembly_success": 0,
            "single_shot_success": 0,
            "iterative_success": 0,
        },
    }

    for i, prompt in enumerate(prompts):
        print(f"\n--- Prompt {i+1}/{len(prompts)} ---")

        comparison = run_single_three_way_comparison(
            inspiration=prompt["inspiration"],
            prompt_id=prompt["id"],
            model=model,
            mode=mode,
        )

        # Track success rates
        assembly_ok = comparison["assembly"]["success"]
        single_shot_ok = comparison["single_shot"]["success"]
        iterative_ok = comparison["iterative"]["success"]

        if assembly_ok:
            results["summary"]["assembly_success"] += 1
        if single_shot_ok:
            results["summary"]["single_shot_success"] += 1
        if iterative_ok:
            results["summary"]["iterative_success"] += 1
        if assembly_ok and single_shot_ok and iterative_ok:
            results["summary"]["all_successful"] += 1

        # Anonymize for blind scoring if requested (and all three succeeded)
        if anonymize and assembly_ok and single_shot_ok and iterative_ok:
            # Create random assignment
            approaches = ["assembly", "single_shot", "iterative"]
            random.shuffle(approaches)

            comparison["idea_a"] = comparison[approaches[0]]["idea"]
            comparison["idea_b"] = comparison[approaches[1]]["idea"]
            comparison["idea_c"] = comparison[approaches[2]]["idea"]
            comparison["mapping"] = {
                "A": approaches[0],
                "B": approaches[1],
                "C": approaches[2]
            }
        else:
            # Non-anonymized fallback
            comparison["idea_a"] = comparison.get("single_shot", {}).get("idea")
            comparison["idea_b"] = comparison.get("iterative", {}).get("idea")
            comparison["idea_c"] = comparison.get("assembly", {}).get("idea")
            comparison["mapping"] = {
                "A": "single_shot",
                "B": "iterative",
                "C": "assembly"
            }

        results["comparisons"].append(comparison)

    # Calculate summary stats
    total = len(prompts)
    results["summary"]["assembly_success_rate"] = results["summary"]["assembly_success"] / total * 100
    results["summary"]["single_shot_success_rate"] = results["summary"]["single_shot_success"] / total * 100
    results["summary"]["iterative_success_rate"] = results["summary"]["iterative_success"] / total * 100
    results["summary"]["all_successful_rate"] = results["summary"]["all_successful"] / total * 100

    # Print summary
    print(f"\n{'='*60}")
    print("3-WAY COMPARISON SUMMARY")
    print(f"{'='*60}")
    print(f"All three successful: {results['summary']['all_successful']}/{total}")
    print(f"Assembly success rate: {results['summary']['assembly_success_rate']:.1f}%")
    print(f"Single-shot success rate: {results['summary']['single_shot_success_rate']:.1f}%")
    print(f"Iterative success rate: {results['summary']['iterative_success_rate']:.1f}%")

    # Save results
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(
        output_dir,
        f"three_way_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to: {output_file}")
    print("\nNext step: Use scoring.py to evaluate the anonymized A/B/C ideas")

    return results


if __name__ == "__main__":
    import argparse
    from prompts import BENCHMARK_PROMPTS

    parser = argparse.ArgumentParser(description="Run benchmark comparisons")
    parser.add_argument(
        "--mode",
        choices=["two_way", "three_way"],
        default="two_way",
        help="Comparison mode: two_way (Assembly vs baseline) or three_way (Assembly vs single-shot vs iterative)"
    )
    parser.add_argument(
        "--prompts",
        type=int,
        default=2,
        help="Number of prompts to test (default: 2)"
    )
    parser.add_argument(
        "--assembly-mode",
        choices=["fast", "medium", "thorough"],
        default="fast",
        help="Assembly mode (default: fast)"
    )
    args = parser.parse_args()

    if args.mode == "three_way":
        run_three_way_comparison(
            prompts=BENCHMARK_PROMPTS[:args.prompts],
            mode=args.assembly_mode,
            output_dir="results",
        )
    else:
        run_comparison(
            prompts=BENCHMARK_PROMPTS[:args.prompts],
            mode=args.assembly_mode,
            output_dir="results",
        )
