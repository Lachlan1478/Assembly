# Phase 2: Quality vs Single LLM Benchmark

**Goal:** Validate the core hypothesis - Assembly beats single LLM.

---

## Purpose

This benchmark tests Assembly's core hypothesis:

> Structured multi-persona collaboration produces higher-quality, more commercially viable startup ideas than a single large language model prompt.

---

## Experiment Design

For **10 startup prompts**:

1. Generate output using a single LLM prompt (baseline)
2. Generate output using Assembly (multi-persona)
3. Blind-score both outputs using evaluation criteria

---

## Target Metrics

| Metric | Target | Description |
|--------|--------|-------------|
| Win Rate | >= 70% | Assembly wins majority of comparisons |
| Score Improvement | >= 20% | Assembly scores higher on average |

---

## Evaluation Criteria

All outputs scored on 1-5 scale:

| Criterion | Description |
|-----------|-------------|
| Novelty | Is the idea non-obvious or differentiated? |
| Feasibility | Could this realistically be built and sold? |
| Specificity | Are ICP, problem, and solution concrete? |
| Commercial Clarity | Is monetisation obvious and credible? |

Total score: 4-20 points per idea.

---

## Files

| File | Purpose |
|------|---------|
| `prompts.py` | 10 diverse startup domain prompts |
| `baseline_single_llm.py` | Single LLM idea generator |
| `test_assembly_vs_baseline.py` | Comparison test runner |
| `scoring.py` | Evaluation criteria and scoring functions |
| `main.py` | Wrapper script with configuration |

---

## Running Phase 2

```bash
python benchmarks/phase_2_quality_vs_single_llm/main.py
```

## Configuration

Edit `main.py` to configure:
- `MODEL_NAME`: Model to use (default: "gpt-4o-mini")
- `NUM_PROMPTS`: Number of prompts to test (default: 10)
- `OUTPUT_DIR`: Directory for results

---

## Scoring Process

1. Run `main.py` to generate paired outputs
2. Results saved to `OUTPUT_DIR/comparison_results_*.json`
3. Open results file and use `scoring.py` functions for manual evaluation
4. Aggregate scores to determine win rate

---

## Gate

> If Assembly does not win >= 70% of comparisons, revisit persona design or facilitator logic.

Per BENCHMARKS.md:
- Pause feature development
- Diagnose failure mode
- Either redesign personas or sunset the project
