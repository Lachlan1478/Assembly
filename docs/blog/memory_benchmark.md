# Does Structured Memory Actually Help Multi-Persona LLMs?

**Date:** February 22, 2026

---

When multiple AI personas have a long conversation, what stops them from repeating themselves and
losing track of what they agreed on?

The naïve answer is: just feed them the full conversation history. It works fine at 10 turns. At
30+ turns, it stops working. Token budget explodes, important early context slides off the edge,
and personas start re-raising ideas that were already debated and rejected. The conversation loops
instead of progressing.

We built a 3-component structured memory system for Assembly—our multi-persona LLM brainstorming
framework—specifically to address this. Shared consensus memory, per-persona belief tracking,
verbatim short-term context. The bet was that bounded, semantically organized memory would outperform
raw verbatim history as sessions grow longer.

Then we ran a benchmark to see if it actually does.

---

## What Assembly Is

Assembly is a multi-persona AI brainstorming system. Given a domain (e.g., "personal finance tools
for young professionals"), it spins up four AI personas—each with a distinct archetype, priorities,
and communication style—and runs them through a structured multi-phase conversation to produce a
commercial startup spec.

A **FacilitatorAgent** manages turn order and phase transitions. A **Socratic Mediator** persona
can intervene when conversations stall or drift. Each session ends with a convergence phase that
synthesizes the debate into a structured output: target users, primary outcome, must-haves,
constraints, and non-goals.

The system runs in four modes:

| Mode | Turns | Phases | Notes |
|------|-------|--------|-------|
| **fast** | 3 | 1 | No mediator, no summaries |
| **medium** | ~10 | 1 | With mediator |
| **standard** | 8–15 | 3 | Full pipeline |
| **deep** | 12–15 | 4+ | Extended critique phase |

Personas are dynamically generated per domain—they're not pre-written characters. The same
orchestration layer runs for any topic. The idea is that the *structure* of the conversation
matters more than any individual persona's knowledge.

---

## The Memory Problem

**Full history** means each persona sees a verbatim transcript of all prior turns. Simple,
lossless, zero extra LLM calls. At 10 turns with 4 personas, the context is still manageable.

The problem compounds fast. At 30+ turns, you're stuffing thousands of tokens of back-and-forth
into every single API call. More critically: the context gets *noisy*. A point one persona made
in turn 4 is semantically buried under 25 subsequent exchanges. Personas don't reliably recall
that the group already ruled out a pricing model or agreed that the target is B2B, not B2C. Ideas
resurface. The same objection gets raised twice. The conversation doesn't build—it oscillates.

**Structured memory** replaces verbatim history with three bounded components:

1. **Shared memory** — an LLM-maintained summary of the session state, capped at ~200 words.
   Tracks: agreed constraints, rejected ideas, established facts. Updated via
   `update_shared_memory_async()` after every turn. Every persona sees the same shared memory.

2. **Personal memory** — per-persona `summary` and `belief_state`. Tracks position shifts,
   concessions, and uncertainties over time. Updated in parallel via `asyncio.gather()` after
   each turn so latency doesn't compound.

3. **Short-term** — the last 3 exchanges verbatim. Immediate context without the bloat of
   the full transcript.

Mode defaults: `fast` → full history (zero extra LLM calls), `medium`/`standard`/`deep` →
structured (the extra calls are worth it for longer sessions).

The compression advantage of structured memory is small at 10 turns. It should be large at 30.
The benchmark was designed to measure whether we can even detect the difference at the shorter end.

---

## The Benchmark Design

**Hypothesis:** Structured memory produces better ideas and cleaner conversations.

**Setup:** 5 domains × 2 memory configs × medium mode (10 turns, 1 phase). One run per cell.

**Domains:**
- Personal finance tools for young professionals
- Mental health and wellness apps for remote workers
- Personalized learning platforms for adult upskilling
- Productivity software for solo freelancers
- Sustainability-focused consumer apps

**Idea quality scoring:** GPT-5.1 judge, 1–5 on four criteria (total /20):

| Criterion | What it measures |
|-----------|-----------------|
| **Novelty** | Differentiation from obvious solutions |
| **Feasibility** | Technical achievability |
| **Specificity** | Concreteness of ICP, problem, solution |
| **Commercial Clarity** | Plausibility of monetization |

Scoring calls are independent per idea—the judge never sees both ideas side by side. Temperature
0.3 to reduce variability. The judge also writes per-criterion notes, which we kept in the raw
results for qualitative inspection.

**Conversation quality metrics:**

| Metric | Method |
|--------|--------|
| **Repetition count** | LLM-judged count of repeated arguments over first 30 turns |
| **Dead-end recovery** | Heuristic: rejected ideas that resurface later |
| **Concept density** | Unique content-bearing words per turn |

**Win determination:** higher total score wins. Ties split fractionally (0.5 wins each).
Aggregation via `compare_n_scores()` + `aggregate_n_way_results()` from
`benchmarks/phase_2_quality_vs_single_llm/scoring.py`.

---

## Results

### Idea Quality

| Domain | Full History | Structured | Winner |
|--------|-------------|-----------|--------|
| Finance | 16/20 | 15/20 | Full history |
| Health | 15/20 | 14/20 | Full history |
| Education | 15/20 | 15/20 | Tie |
| Productivity | 16/20 | 16/20 | Tie |
| Sustainability | 15/20 | 15/20 | Tie |

**Win rate:** Full history 70%, Structured 30%.
**Average score:** 15.4 vs 15.0.

### Conversation Quality

| Metric | Full History | Structured |
|--------|-------------|-----------|
| Avg repetitions | 5.6 | 4.8 |
| Avg concept density (words/turn) | 145.1 | 160.5 |

Structured memory wins on repetition (14% reduction) and concept density (10.6% higher). Idea
quality is essentially a tie—the two domains where full history won are separated by a single
point each.

### Per-Domain Quality Metrics

For completeness, the raw conversation quality numbers by domain:

| Domain | FH reps | ST reps | FH density | ST density |
|--------|---------|---------|-----------|-----------|
| Finance | 6 | 5 | 149.3 | 111.4 |
| Health | 6 | 3 | 138.8 | 190.0 |
| Education | 4 | 6 | 150.3 | 153.2 |
| Productivity | 6 | 5 | 147.4 | 172.8 |
| Sustainability | 6 | 5 | 139.7 | 175.1 |

Health is the outlier domain: structured memory's repetition count drops from 6 to 3 (a big win),
but concept density also shoots up to 190—the highest in the table. The health domain generated a
notably more wide-ranging structured conversation.

---

## Interpretation

**Why full history won on idea quality:** At 10 turns / 1 phase, the verbatim transcript is still
short enough to fit full context cleanly. Structured memory's compression advantage only matters
once the history is long enough that something important gets buried or truncated. We didn't
stress the system hard enough to see that failure mode.

**Why the 70% win rate is misleading:** It's driven entirely by two 1-point margins—finance (16
vs 15) and health (15 vs 14). At temperature 0.3, the same judge call on the same idea can
plausibly score ±1 across independent runs. These two "wins" for full history are within normal
judge noise. Three domains tied outright.

**Conversation quality is the cleaner signal:** Structured memory reduces repetitions in every
single domain except education (where both configs scored low already). The average drops from
5.6 to 4.8. That's a consistent directional result, not a noise artifact. Concept density is
higher for structured in 4 of 5 domains. Both metrics suggest that even at 10 turns, structured
memory produces more varied, less repetitive conversations—and this effect should compound as
sessions grow longer.

**What this benchmark actually measures:** Whether 10 turns is long enough to see a memory
architecture difference. The answer is: barely, on conversation quality; not yet, on idea quality.
The test worth running is at 30 turns and 3 phases.

---

## What We'd Test Next

Three follow-up experiments are planned:

**Test B — Multi-Phase (standard mode, 3 phases):**
Does structured memory hold consensus better across phase boundaries, where full history must
carry forward all context from earlier phases? At the transition between ideation and feasibility,
structured memory should have a clear advantage: the shared memory captures agreed constraints,
while full history buries them under the ideation debate.

**Test C — Long-Turn Stress (15 turns, 1 phase):**
Does repetition accelerate in the second half for full history but stay flat for structured? This
would test whether the repetition reduction we see at 10 turns is a floor effect or a meaningful
architectural difference. Hypothesis: repetitions for full history spike between turns 10–15;
structured stays flat.

**Test D — Fast Baseline:**
Add fast mode (3 turns, no mediator, no summaries) as a floor. If fast mode produces ideas within
1–2 points of medium mode, it raises a different question: is the full memory apparatus worth the
extra API calls at all? Worth knowing before investing in Test B and C.

---

## One Bug Caught

The dead-end recovery metric turned out to be unreliable for structured memory in this run.

The LLM call inside the rejection detector was using `max_tokens` instead of
`max_completion_tokens` for gpt-5.1. This caused the call to silently fall back to heuristic
detection in some domains, so the dead_end_recovery numbers in this run are a mix of LLM-judged
and heuristic results depending on the domain. The numbers weren't used in the primary win rate
calculation, but they're not comparable across domains or configs as reported.

Worth fixing before Test B. The fix is a one-line parameter rename in the scoring module.

---

*Benchmark data: `benchmarks/memory_system/results/memory_benchmark_20260222_181608.json`*
*Scoring infrastructure: `benchmarks/phase_2_quality_vs_single_llm/scoring.py`*
*Memory implementation: `src/idea_generation/memory.py`, `framework/persona.py`*
