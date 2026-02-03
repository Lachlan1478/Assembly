# test_end_to_end_reliability.py
# Phase 1 Benchmark: Verify system completes runs consistently

import json
import os
import sys
from datetime import datetime
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from src.idea_generation.generator import multiple_llm_idea_generator


def validate_idea_structure(idea: dict) -> tuple[bool, list[str]]:
    """
    Validate that an idea has the expected structure.

    Returns:
        Tuple of (is_valid, list_of_missing_fields)
    """
    required_fields = [
        "title",
        "description",
        "target_users",
        "primary_outcome",
        "must_haves",
        "constraints",
        "non_goals",
    ]

    missing = [field for field in required_fields if field not in idea]
    return len(missing) == 0, missing


def run_reliability_test(
    inspiration: str,
    model_name: str = "gpt-4o-mini",
    num_runs: int = 10,
    mode: str = "medium",
    output_dir: Optional[str] = None,
) -> dict:
    """
    Run multiple identical prompts and check for consistent completion.

    Args:
        inspiration: The prompt to test with
        model_name: Model to use (note: mode config may override)
        num_runs: Number of identical runs
        mode: Run mode ("fast", "medium", "standard", "deep")
        output_dir: Directory to save results (optional)

    Returns:
        Dictionary with test results
    """
    print(f"\n{'='*60}")
    print("PHASE 1: End-to-End Reliability Test")
    print(f"{'='*60}")
    print(f"Runs: {num_runs}")
    print(f"Mode: {mode}")
    print(f"{'='*60}\n")

    results = {
        "test_name": "end_to_end_reliability",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "model_name": model_name,
            "num_runs": num_runs,
            "mode": mode,
        },
        "runs": [],
        "summary": {
            "total_runs": num_runs,
            "successful": 0,
            "failed": 0,
            "valid_structure": 0,
            "invalid_structure": 0,
        },
    }

    for run_num in range(1, num_runs + 1):
        print(f"\n--- Run {run_num}/{num_runs} ---")
        run_result = {
            "run_number": run_num,
            "success": False,
            "error": None,
            "ideas_generated": 0,
            "structure_valid": False,
            "missing_fields": [],
            "idea_titles": [],
        }

        try:
            import traceback
            ideas = multiple_llm_idea_generator(
                inspiration=inspiration,
                number_of_ideas=1,
                mode=mode,
            )

            if ideas and isinstance(ideas, list):
                run_result["success"] = True
                run_result["ideas_generated"] = len(ideas)
                run_result["idea_titles"] = [
                    idea.get("title", "Untitled") for idea in ideas
                ]

                # Validate structure of first idea
                if ideas:
                    is_valid, missing = validate_idea_structure(ideas[0])
                    run_result["structure_valid"] = is_valid
                    run_result["missing_fields"] = missing

                    if is_valid:
                        results["summary"]["valid_structure"] += 1
                    else:
                        results["summary"]["invalid_structure"] += 1

                results["summary"]["successful"] += 1
                print(f"[OK] Run {run_num} completed successfully")
                print(f"     Ideas: {run_result['idea_titles']}")
            else:
                run_result["error"] = "No ideas returned or invalid format"
                results["summary"]["failed"] += 1
                print(f"[FAIL] Run {run_num}: No ideas returned")

        except Exception as e:
            run_result["error"] = str(e)
            results["summary"]["failed"] += 1
            print(f"[FAIL] Run {run_num}: {e}")
            traceback.print_exc()

        results["runs"].append(run_result)

    # Calculate success rate
    success_rate = results["summary"]["successful"] / num_runs * 100
    structure_rate = results["summary"]["valid_structure"] / max(results["summary"]["successful"], 1) * 100

    results["summary"]["success_rate_percent"] = success_rate
    results["summary"]["structure_valid_percent"] = structure_rate

    # Print summary
    print(f"\n{'='*60}")
    print("RELIABILITY TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Successful runs: {results['summary']['successful']}/{num_runs} ({success_rate:.1f}%)")
    print(f"Valid structure: {results['summary']['valid_structure']}/{results['summary']['successful']} ({structure_rate:.1f}%)")
    print(f"Failed runs: {results['summary']['failed']}")

    # Check gate
    gate_passed = success_rate == 100 and structure_rate >= 90
    results["summary"]["gate_passed"] = gate_passed

    if gate_passed:
        print("\n[PASS] Gate passed: System is reliable")
    else:
        print("\n[FAIL] Gate failed: System needs improvement")
        if success_rate < 100:
            print(f"       - Completion rate {success_rate:.1f}% < 100%")
        if structure_rate < 90:
            print(f"       - Structure validity {structure_rate:.1f}% < 90%")

    # Save results if output directory specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(
            output_dir,
            f"reliability_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_file}")

    return results


if __name__ == "__main__":
    from prompts import STANDARD_INSPIRATION

    run_reliability_test(
        inspiration=STANDARD_INSPIRATION,
        num_runs=3,  # Reduced for quick testing
        mode="fast",
        output_dir="results",
    )
