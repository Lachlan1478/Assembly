# main.py
# Phase 1: System Validity Benchmark Wrapper
# Runs all Phase 1 tests with configurable parameters

import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

MODEL_NAME = "gpt-5.1"
NUM_RUNS = 3
MODE = "fast"  # "fast", "medium", "standard", "deep"

INSPIRATION = """
Goal: Create a startup that helps young professionals learn to invest.

Domain: Personal finance
Target users: Young professionals (25-35) new to investing
Primary outcome: Build confidence in making investment decisions

Problem: Most investment apps are overwhelming for beginners.
They present too much information without guidance, leading to
analysis paralysis and poor decisions.

Task: Propose a specific startup idea (with a name) that solves this
problem. The solution should provide a simpler, more guided experience
that builds investment knowledge gradually.
"""

# Output directory for results
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")

# Role adherence analysis settings
USE_LLM_FOR_ROLE_ANALYSIS = True  # Set True for more accurate (but costly) analysis

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    from test_end_to_end_reliability import run_reliability_test
    from test_persona_role_adherence import run_role_adherence_test

    print("=" * 70)
    print("PHASE 1: SYSTEM VALIDITY BENCHMARK")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Model: {MODEL_NAME}")
    print(f"Mode: {MODE}")
    print(f"Runs: {NUM_RUNS}")
    print("=" * 70)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Track overall results
    phase_results = {
        "reliability": None,
        "role_adherence": None,
        "all_gates_passed": False,
    }

    # -------------------------------------------------------------------------
    # Test 1: End-to-End Reliability
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 1: END-TO-END RELIABILITY")
    print("=" * 70)

    reliability_results = run_reliability_test(
        inspiration=INSPIRATION,
        model_name=MODEL_NAME,
        num_runs=NUM_RUNS,
        mode=MODE,
        output_dir=OUTPUT_DIR,
    )
    phase_results["reliability"] = reliability_results

    # -------------------------------------------------------------------------
    # Test 2: Persona Role Adherence
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("TEST 2: PERSONA ROLE ADHERENCE")
    print("=" * 70)

    role_results = run_role_adherence_test(
        logs_path=None,  # Use most recent logs
        use_llm=USE_LLM_FOR_ROLE_ANALYSIS,
        model_name=MODEL_NAME,
        output_dir=OUTPUT_DIR,
    )
    phase_results["role_adherence"] = role_results

    # -------------------------------------------------------------------------
    # Phase 1 Summary
    # -------------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("PHASE 1 SUMMARY")
    print("=" * 70)

    reliability_passed = reliability_results.get("summary", {}).get("gate_passed", False)
    role_passed = role_results.get("summary", {}).get("gate_passed", False)
    all_passed = reliability_passed and role_passed

    phase_results["all_gates_passed"] = all_passed

    print(f"\nReliability Gate: {'PASS' if reliability_passed else 'FAIL'}")
    if reliability_results.get("summary"):
        print(f"  - Success rate: {reliability_results['summary'].get('success_rate_percent', 0):.1f}%")
        print(f"  - Structure validity: {reliability_results['summary'].get('structure_valid_percent', 0):.1f}%")

    print(f"\nRole Adherence Gate: {'PASS' if role_passed else 'FAIL'}")
    if role_results.get("summary"):
        print(f"  - Adherence rate: {role_results['summary'].get('adherence_rate_percent', 0):.1f}%")
        print(f"  - Average score: {role_results['summary'].get('average_score', 0):.2f}/5")

    print("\n" + "-" * 70)
    if all_passed:
        print("PHASE 1 RESULT: ALL GATES PASSED")
        print("System is ready for Phase 2 benchmarking.")
    else:
        print("PHASE 1 RESULT: GATES FAILED")
        print("Address reliability issues before proceeding to Phase 2.")
    print("-" * 70)
