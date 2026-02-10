# When Self-Critique Beats Multi-Persona: Our First 3-Way Benchmark

**Date:** February 3, 2026

---

## The Question

We built Assembly to prove that multi-persona AI conversations produce better ideas than single LLM calls. But *how much* better? And compared to what?

Today we ran our first 3-way benchmark. The results surprised us.

---

## The Contenders

| Approach | Description | API Calls |
|----------|-------------|-----------|
| **Single-shot** | One prompt with team-of-experts framing | 1 |
| **Iterative** | 4-turn self-refinement (propose → critique → improve → finalize) | 4 |
| **Assembly** | Multi-persona debate with phases | ~15-30 |

Same model (gpt-5.1). Same prompts. Three domains: personal finance, remote work, health.

---

## The Scores

We scored on 4 criteria (1-5 each): Novelty, Feasibility, Specificity, Commercial Clarity.

| Approach | Finance | Remote Work | Health | **Avg** |
|----------|---------|-------------|--------|---------|
| Assembly | 18 | 15 | 17 | **16.7** |
| Iterative | 19 | 17 | 19 | **18.3** |
| Single-shot | 13 | 12 | 13 | **12.7** |

**Iterative won all three.**

---

## What Happened?

Assembly excels at **specificity**. Our finance idea had named components like "Bayesian RiskToleranceMapper" and "MoneyEmotionConstraintTagger". Technical depth was consistently high.

But Iterative's **self-critique step** forced addressing weaknesses. ClarityVest (iterative) pivoted mid-generation from "generic confidence app" to "portfolio cleanup + employer plan interpreter"—a sharper market position.

Single-shot produced... what any consultant would say. Generic. Safe. Forgettable.

---

## The Insight

Assembly produces **technically detailed** ideas.
Iterative produces **commercially refined** ideas.

Different strengths. Neither is strictly better—depends what you're optimizing for.

---

## What We Built Today

### 1. 3-Way Benchmark Infrastructure

```bash
python benchmarks/phase_2_quality_vs_single_llm/main.py --mode three_way
```

Runs all three approaches, anonymizes as A/B/C, stores mapping for blind scoring.

### 2. Value Accumulation Metric

New tool to measure per-turn value in conversations:

- `new_concept` — Did this turn introduce something new?
- `builds_on_prior` — Does it reference earlier ideas?
- `concrete_artifact` — Specific feature, metric, example?
- `challenges_assumption` — Pushback on prior claims?

This lets us quantify *why* multi-turn beats single-shot (when it does).

### 3. Gap Signal (Nudge-Based Steering)

Added lightweight nudges every 4 turns:

```
[Optional consideration: The discussion hasn't touched on specific user segments yet.]
```

Key design: **nudge, not rule**. Personas can ignore it. Clears after one use. Keeps conversations on track without heavy-handed control.

---

## Next Steps

1. Run more prompts (n=3 is small)
2. Test if gap nudges improve Assembly's commercial clarity scores
3. Measure value accumulation curves to see where Assembly's extra turns add (or don't add) value

---

## The Uncomfortable Truth

More API calls ≠ better ideas.

A 4-turn self-critique loop beat our 15-30 turn multi-persona system on commercial viability. That's humbling. But it's also data.

The question isn't "is Assembly better?" It's "when is Assembly better, and at what?"

We're building the tools to answer that.

---

*This is post #1 in our build log. We're documenting Assembly's development in public—wins, losses, and uncomfortable truths.*
