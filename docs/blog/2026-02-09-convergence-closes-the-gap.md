# Convergence Closes the Gap: Assembly Catches Iterative

**Date:** February 9, 2026

---

## Previously

In our [last post](./2026-02-03-iterative-beats-assembly.md), we ran a 3-way benchmark and got humbled. A simple 4-turn self-critique loop (Iterative) beat our 15-30 turn multi-persona system (Assembly) on commercial viability. The scores:

| Approach | Finance | Remote Work | Health | Avg |
|----------|---------|-------------|--------|-----|
| Single-shot | 13 | 12 | 13 | 12.7 |
| **Assembly** | 18 | 15 | 17 | **16.7** |
| **Iterative** | 19 | 17 | 19 | **18.3** |

Assembly was strong on specificity. Iterative was strong on commercial clarity. We said: "The question isn't 'is Assembly better?' It's 'when is Assembly better, and at what?'"

Now we have an answer.

---

## What We Built: The Convergence Phase

The diagnosis was clear: Assembly produces technically rich output (named components, decision frameworks, concrete mechanisms) but stops short of commercial polish. No product name. No pricing. No go-to-market.

So we added a 3-turn **convergence phase** that runs after the multi-persona debate:

1. **Synthesize** — A "Decision Owner" reads the full conversation and drafts a product spec
2. **Critique** — A skeptical investor tears it apart (positioning, feasibility, commercial viability)
3. **Refine** — The Decision Owner incorporates critiques and outputs a final structured spec

The output is a locked schema:

```
product_name, one_sentence_pitch, target_user_icp,
mvp_bullets (max 5), monetization_model, key_differentiator,
what_we_are_not_doing, risks_unknowns (top 3), next_7_day_plan
```

Controlled by `enable_convergence_phase` in config. Enabled for medium/standard/deep modes. Disabled for fast mode.

### Implementation

Three files changed:

- **`src/idea_generation/convergence.py`** — The core 3-turn pipeline
- **`src/idea_generation/config.py`** — New flag per mode
- **`src/idea_generation/generator.py`** — Calls convergence after idea extraction, returns `{"ideas": [...], "convergence": {...}}`

---

## The Test

We ran Assembly + Convergence on the finance domain (same prompt as the original benchmark):

> *Domain: Personal finance. Target: Young professionals new to investing. Primary outcome: Build confidence in investment decisions.*

**Mode:** Medium (4 phases, ~35 turns). **Model:** gpt-5.1.

### What Assembly Produced (Pre-Convergence)

The multi-persona debate generated 12 novel personas across 4 phases:

- **Phase 1** (Investor Profile Mapping): BalanceSheetRiskMapper, TimeHorizonSegmenter, RiskComfortCalibrator, EmotionalTriggerMapper
- **Phase 2** (Confidence Barrier Diagnosis): ChoiceSetCompressionAnalyzer, JargonObstructionClassifier, DecisionConsequenceOpacityMapper, DefaultPathIntimidationAssessor
- **Phase 3** (Simple Investing Foundations): Used archive personas (CFO, Contrarian, Designer, Facilitator) due to a connection timeout
- **Phase 4** (Solution Commitment Synthesis): FirstStepConstraintSelector, FrictionBarrierDecomposer, ConfidenceEvidenceBinder, CommitmentCheckpointScheduler

35 turns of debate produced the idea: **"Adaptive Buffer-Gated Investing Coach"** — technically deep, with 15 must-haves including "complexity score / knob budget engine" and "scenario-aware safety constraints."

But no product name. No pricing. No action plan.

### What Convergence Produced

The 3-turn convergence pipeline transformed it into:

**Product:** BufferFirst

**Pitch:** "A paycheck-safe auto-invest plan that won't move money until your bills and emergency cushion are covered."

**ICP:** US salaried professionals in their first 5 years of full-time work.

**MVP (5 bullets):**
- Paycheck-linked fixed ACH (one account, no real-time balance inference)
- 5-minute upfront safety setup (essentials, cash, desired cushion)
- Two-phase automation (build cushion first, then invest)
- Safety pause with one-tap override
- Monthly 2-minute status recap

**Monetization:** Free under $2,500; 0.20% AUM above that; optional $5-9/mo employer-sponsored subscription.

**What we're NOT doing:** No real-time multi-account inference. No multiple goals/envelopes. No stock picking.

**7-day plan:** User interviews (days 1-2) → tech architecture scoping (days 3-4) → waitlist landing page A/B test (days 5-7).

### The Critique Was Real

The self-critique step identified three genuine risks:

1. **Positioning:** "Refusing to invest until a 3-month buffer is met" sounds like a roadblock, not a feature. Hard to market against "start investing with $5" apps.
2. **Feasibility:** The "single simple rule" hides brittle plumbing (bank connectivity, ACH timing, overdraft avoidance).
3. **Commercial:** AUM-based revenue on small, slowly growing balances with deliberate caps = thin margins and long payback periods.

These critiques directly improved the final output — the refined spec addressed them by simplifying to fixed ACH pulls (no real-time inference), adding the employer subscription channel, and narrowing scope aggressively.

---

## The Scores

We used an LLM-as-judge (gpt-5.1) to score both the raw Assembly output and the Assembly + Convergence output on the same 4 criteria.

| Criterion | Single-shot | Iterative | Assembly (raw) | Assembly + Convergence |
|-----------|:-----------:|:---------:|:--------------:|:----------------------:|
| Novelty | 3 | 4 | 4 | 4 |
| Feasibility | 4 | 4 | 4 | 4 |
| Specificity | 3 | 4 | **5** | **5** |
| Commercial Clarity | 3 | **5** | 3 | 4 |
| **Total** | **13** | **17** | **16** | **17** |

### Reading the Table

**Assembly + Convergence ties Iterative at 17/20**, but with a different strength profile:

- Assembly + Convergence leads on **Specificity** (5 vs 4). The multi-persona debate produces concrete technical frameworks that a 4-turn self-critique can't match.
- Iterative still leads on **Commercial Clarity** (5 vs 4). Its focused self-critique is tighter on monetization and go-to-market.
- Convergence closed a 1-point gap on commercial clarity (3→4) without losing any specificity.

The net effect: Assembly went from **losing by 1 point** to **tied**, while keeping its depth advantage.

---

## What We Learned

### 1. Convergence is an amplifier, not a replacement

The convergence phase doesn't replace the multi-persona debate — it refines its output. Without the 35-turn conversation producing "emergency buffer gate," "complexity quota," and "tiered risk-capacity bands," the convergence phase would have nothing rich to work with.

### 2. Self-critique is the key ingredient

Both Iterative and Convergence use self-critique. That's the common factor that separates them from raw Assembly and single-shot. The difference is what gets critiqued:

- **Iterative** critiques a single LLM's first draft
- **Convergence** critiques the synthesis of a 35-turn multi-expert debate

Richer input → richer critique → richer output.

### 3. Commercial clarity is learnable

Assembly's weakness was never the ideas — it was the packaging. Adding a structured output schema (product name, MVP bullets, pricing, 7-day plan) forced the system to produce commercially legible output. The schema is the teacher.

### 4. Dynamic personas outperform archive personas

During the test, Phase 3 fell back to archived generic personas (CFO, Contrarian, Designer) due to a connection error. Those personas showed **higher repetition rates** (flagged 3 times for repeating points) compared to dynamically generated domain-specific personas (flagged 0-2 times). Dynamic generation matters.

---

## Technical Notes

### Bugs Found During Testing

1. **`max_tokens` parameter error with gpt-5.1** — The rejection detection module uses `max_tokens` but gpt-5.1 requires `max_completion_tokens`. Non-blocking (graceful failure) but needs fixing.

2. **Off-by-one in turn limit** — Phase 4 ran turn 7/6 (100%), suggesting the boundary check fires one turn late.

3. **Network resilience** — A connection error during Phase 3 persona generation caused a ~10 hour pause (overnight). The archive fallback recovered the session, but retry logic would prevent the delay.

### New Infrastructure

- **`scoring.py: score_idea_llm()`** — Automated LLM-as-judge scoring function. Sends idea + rubric to a judge model and parses structured scores. Enables repeatable benchmarking without manual input.

- **`run_formal_benchmark.py`** — Automated 3-way benchmark runner with LLM scoring. Generates all approaches, scores them, and produces comparison tables.

---

## Where We Are Now

| Milestone | Status |
|-----------|--------|
| Multi-persona debate produces technically rich ideas | Done |
| 3-way benchmark infrastructure | Done |
| Value accumulation metrics | Done |
| Gap signal nudges | Done |
| Convergence phase for commercial refinement | Done |
| Assembly ties Iterative on overall quality | **Done** |
| Assembly beats Iterative consistently | Next |

---

## Next Steps

1. **Run convergence across all 3 domains** (remote work, health) to confirm the finance result generalizes
2. **Fix the `max_tokens` → `max_completion_tokens` bug** for clean gpt-5.1 compatibility
3. **Add retry logic** to persona generation to prevent network timeout fallbacks
4. **Test whether deeper modes (standard/deep) push Assembly + Convergence past Iterative** — the hypothesis is that more turns → more raw material → better convergence output

---

## The Story So Far

Post 1: Iterative beat Assembly. Self-critique mattered more than conversation depth.

Post 2: We added self-critique to Assembly. Now they're tied — but Assembly keeps its depth advantage.

The next post should be about Assembly pulling ahead. Or about why it doesn't. Either way, we'll have the data.

---

*Post #2 in our build log. Assembly's development in public — wins, losses, and incremental progress.*
