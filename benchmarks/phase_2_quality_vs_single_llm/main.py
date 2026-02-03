# main.py
# Phase 2: Quality vs Single LLM Benchmark Wrapper
# Runs comparison test with configurable parameters

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
NUM_PROMPTS = 3  # Reduced for API quota conservation
MODE = "fast"  # Assembly mode: "fast", "medium", "standard", "deep"

# Output directory for results
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "results")

# Anonymize outputs for blind scoring
ANONYMIZE = True

# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    from prompts import BENCHMARK_PROMPTS
    from test_assembly_vs_baseline import run_comparison
    from scoring import aggregate_results, check_phase2_gate

    print("=" * 70)
    print("PHASE 2: ASSEMBLY VS SINGLE LLM BENCHMARK")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Model: {MODEL_NAME}")
    print(f"Mode: {MODE}")
    print(f"Prompts: {NUM_PROMPTS}")
    print(f"Anonymized: {ANONYMIZE}")
    print("=" * 70)

    # Validate configuration
    if NUM_PROMPTS > len(BENCHMARK_PROMPTS):
        print(f"[!] Requested {NUM_PROMPTS} prompts but only {len(BENCHMARK_PROMPTS)} available")
        NUM_PROMPTS = len(BENCHMARK_PROMPTS)

    # Select prompts
    prompts = BENCHMARK_PROMPTS[:NUM_PROMPTS]
    print(f"\nUsing prompts: {[p['id'] for p in prompts]}")

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Run comparison
    results = run_comparison(
        prompts=prompts,
        model=MODEL_NAME,
        mode=MODE,
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
    print(f"Both successful: {results['summary']['both_successful']}/{NUM_PROMPTS}")
    print("-" * 70)

    if results['summary']['both_successful'] < NUM_PROMPTS:
        print("\n[!] Some generations failed - investigate before scoring")
