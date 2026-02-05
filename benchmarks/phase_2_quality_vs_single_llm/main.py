# main.py
# Phase 2: Quality vs Single LLM Benchmark Wrapper
# Runs comparison test with configurable parameters

import argparse
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

# =============================================================================
# CONFIGURATION (defaults, can be overridden via CLI)
# =============================================================================

DEFAULT_MODEL = "gpt-5.1"
DEFAULT_NUM_PROMPTS = 3  # Reduced for API quota conservation
DEFAULT_ASSEMBLY_MODE = "fast"  # Assembly mode: "fast", "medium", "standard", "deep"

# Output directory for results
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")

# Anonymize outputs for blind scoring
ANONYMIZE = True

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 2 Benchmark: Assembly vs Baselines")
    parser.add_argument(
        "--mode",
        choices=["two_way", "three_way"],
        default="two_way",
        help="Comparison mode: two_way (Assembly vs single-shot) or three_way (Assembly vs single-shot vs iterative)"
    )
    parser.add_argument(
        "--prompts",
        type=int,
        default=DEFAULT_NUM_PROMPTS,
        help=f"Number of prompts to test (default: {DEFAULT_NUM_PROMPTS})"
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--assembly-mode",
        choices=["fast", "medium", "standard", "deep"],
        default=DEFAULT_ASSEMBLY_MODE,
        help=f"Assembly mode (default: {DEFAULT_ASSEMBLY_MODE})"
    )
    args = parser.parse_args()

    from prompts import BENCHMARK_PROMPTS
    from test_assembly_vs_baseline import run_comparison, run_three_way_comparison
    from scoring import aggregate_results, check_phase2_gate

    print("=" * 70)
    if args.mode == "three_way":
        print("PHASE 2: 3-WAY BENCHMARK (Assembly vs Single-shot vs Iterative)")
    else:
        print("PHASE 2: ASSEMBLY VS SINGLE LLM BENCHMARK")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Model: {args.model}")
    print(f"Comparison mode: {args.mode}")
    print(f"Assembly mode: {args.assembly_mode}")
    print(f"Prompts: {args.prompts}")
    print(f"Anonymized: {ANONYMIZE}")
    print("=" * 70)

    # Validate configuration
    num_prompts = args.prompts
    if num_prompts > len(BENCHMARK_PROMPTS):
        print(f"[!] Requested {num_prompts} prompts but only {len(BENCHMARK_PROMPTS)} available")
        num_prompts = len(BENCHMARK_PROMPTS)

    # Select prompts
    prompts = BENCHMARK_PROMPTS[:num_prompts]
    print(f"\nUsing prompts: {[p['id'] for p in prompts]}")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Run comparison based on mode
    if args.mode == "three_way":
        results = run_three_way_comparison(
            prompts=prompts,
            model=args.model,
            mode=args.assembly_mode,
            output_dir=OUTPUT_DIR,
            anonymize=ANONYMIZE,
        )

        # Print next steps for 3-way
        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("""
1. Open the results JSON file in the results/ directory
2. For each comparison, review idea_a, idea_b, idea_c (anonymized)
3. Score using: python scoring.py results/<filename>.json --mode three_way
4. The scoring tool will:
   - Guide you through evaluating each trio
   - Calculate win rates per approach
   - Compare Assembly vs both baselines

Scoring criteria (1-5 each):
- Novelty: Is the idea non-obvious?
- Feasibility: Could this be built and sold?
- Specificity: Are ICP, problem, solution concrete?
- Commercial Clarity: Is monetization obvious?
""")

        # Summary
        print("-" * 70)
        print(f"Assembly success rate: {results['summary']['assembly_success_rate']:.1f}%")
        print(f"Single-shot success rate: {results['summary']['single_shot_success_rate']:.1f}%")
        print(f"Iterative success rate: {results['summary']['iterative_success_rate']:.1f}%")
        print(f"All three successful: {results['summary']['all_successful']}/{num_prompts}")
        print("-" * 70)

        if results['summary']['all_successful'] < num_prompts:
            print("\n[!] Some generations failed - investigate before scoring")

    else:
        results = run_comparison(
            prompts=prompts,
            model=args.model,
            mode=args.assembly_mode,
            output_dir=OUTPUT_DIR,
            anonymize=ANONYMIZE,
        )

        # Print next steps
        print("\n" + "=" * 70)
        print("NEXT STEPS")
        print("=" * 70)
        print("""
1. Open the results JSON file in the results/ directory
2. For each comparison, review idea_a and idea_b (anonymized)
3. Score using: python scoring.py results/<filename>.json
4. The scoring tool will:
   - Guide you through evaluating each pair
   - Calculate win rates and score differences
   - Check if Phase 2 gate is passed

Scoring criteria (1-5 each):
- Novelty: Is the idea non-obvious?
- Feasibility: Could this be built and sold?
- Specificity: Are ICP, problem, solution concrete?
- Commercial Clarity: Is monetization obvious?

Target metrics:
- Assembly wins >= 70% of comparisons
- Assembly scores >= 20% higher on average
""")

        # Summary
        print("-" * 70)
        print(f"Assembly success rate: {results['summary']['assembly_success_rate']:.1f}%")
        print(f"Baseline success rate: {results['summary']['baseline_success_rate']:.1f}%")
        print(f"Both successful: {results['summary']['both_successful']}/{num_prompts}")
        print("-" * 70)

        if results['summary']['both_successful'] < num_prompts:
            print("\n[!] Some generations failed - investigate before scoring")
