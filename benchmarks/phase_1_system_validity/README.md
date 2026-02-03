# Phase 1: System Validity Benchmark

**Goal:** Prove the system works reliably and as intended.

---

## Purpose

Before comparing Assembly to alternatives, we must establish that the system operates correctly:
- Conversations complete without failure
- Personas stay in character
- Outputs are structured and reproducible

---

## Benchmarks

| Benchmark | Target | Test |
|-----------|--------|------|
| End-to-end reliability | 100% completion | Run 10 identical prompts |
| Persona role adherence | >=90% in-role | Analyze conversation logs |
| Output structure | Consistent JSON | Validate output schema |
| Content variation | Differs across runs | Compare outputs |

---

## Tests

### `test_end_to_end_reliability.py`

Runs `multiple_llm_idea_generator()` with 10 identical prompts and checks:
- All runs complete without error
- Outputs differ in content but share structure
- Logs: failures, role drift, premature conclusions

### `test_persona_role_adherence.py`

Analyzes conversation logs for role consistency:
- Metric: % of turns where persona stays in character
- Target: >=90%

---

## Running Phase 1

```bash
python benchmarks/phase_1_system_validity/main.py
```

## Configuration

Edit `main.py` to configure:
- `MODEL_NAME`: Model to use (default: "gpt-4o-mini")
- `NUM_RUNS`: Number of test runs (default: 10)
- `INSPIRATION`: Standard test prompt

---

## Gate

> System can run unattended with acceptable reliability

If this gate fails:
- Debug failure modes
- Fix reliability issues before proceeding to Phase 2
