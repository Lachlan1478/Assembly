# Assembly Benchmarks

This directory contains structured benchmarks to validate Assembly's core hypothesis:

> Structured multi-persona collaboration produces higher-quality, more commercially viable startup ideas than a single large language model prompt.

## Benchmark Phases

| Phase | Purpose | Target |
|-------|---------|--------|
| Phase 1 | System Validity | Prove reliable, consistent operation |
| Phase 2 | Quality vs Single LLM | Validate multi-persona outperforms baseline |

For full benchmark specifications, see [docs/BENCHMARKS.md](../docs/BENCHMARKS.md).

---

## Phase 1: System Validity

**Location:** `phase_1_system_validity/`

**Goal:** Prove the system works reliably and as intended.

**Tests:**
- `test_end_to_end_reliability.py` - Run 10 identical prompts, check completion
- `test_persona_role_adherence.py` - Measure role drift (target: >=90% in-role)

**Gate:** System can run unattended with acceptable reliability.

```bash
python benchmarks/phase_1_system_validity/main.py
```

---

## Phase 2: Quality vs Single LLM

**Location:** `phase_2_quality_vs_single_llm/`

**Goal:** Validate the core hypothesis - Assembly beats single LLM.

**Tests:**
- `baseline_single_llm.py` - Single LLM call generator for comparison
- `test_assembly_vs_baseline.py` - Side-by-side comparison (10 prompts)
- `scoring.py` - Evaluation criteria (novelty, feasibility, specificity, commercial clarity)

**Target Metrics:**
- Assembly wins >= 70% of comparisons
- Assembly scores >= 20% higher on average

```bash
python benchmarks/phase_2_quality_vs_single_llm/main.py
```

---

## Evaluation Criteria

All outputs are scored on:

| Criterion | Description | Scale |
|-----------|-------------|-------|
| Novelty | Is the idea non-obvious or differentiated? | 1-5 |
| Feasibility | Could this realistically be built and sold? | 1-5 |
| Specificity | Are ICP, problem, and solution concrete? | 1-5 |
| Commercial Clarity | Is monetisation obvious and credible? | 1-5 |

Total score: 4-20 points per idea.

---

## Results

Benchmark results are saved to `results/` directory in each phase folder.
