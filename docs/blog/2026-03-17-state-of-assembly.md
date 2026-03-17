# Assembly: State of the Project (March 2026)

**Date:** March 17, 2026

---

## What Is Assembly?

Assembly is a multi-persona AI brainstorming system. You give it a domain — "personal finance tools for young professionals" — and it spins up several AI personas with distinct archetypes, runs them through a structured multi-phase debate, and outputs a commercial startup spec.

The central hypothesis: a structured argument between different perspectives produces better ideas than asking one LLM the same question, no matter how cleverly you phrase it.

We've been building and testing that hypothesis since October 2025. This post is a full account of what's been built, what the data shows, and where we're going.

---

## The Journey

### October 2025 — First Principles

The original idea was broader: use AI personas to not just generate a startup concept, but build the whole app. Stage 1 produces ideas. Stage 2 writes a spec. Stage 3 submits it to Base44 (a no-code builder) and gets a working prototype back.

Stage 3 never shipped. We parked the browser automation and went deeper on Stage 1, because Stage 1 was the interesting part. Getting from an inspiration to a commercially useful idea spec is where the real work happens, and we wanted to understand it before automating past it.

What we had at the start: a `Persona` class wrapping LLM calls, six hardcoded personas (Founder, Designer, Researcher, Tech Lead, CFO, Contrarian), seven fixed conversation phases, and a `meeting_facilitator()` loop that orchestrated it all.

What we quickly realised: fixed personas are a ceiling. The same six people discussing personal finance and discussing remote work productivity are the same six people. We needed the personas themselves to be generated from the domain.

---

### Late 2025 — Dynamic Personas and the Facilitator

The biggest architectural shift early on was moving from static to dynamic persona generation. Instead of loading `founder.json` and `designer.json`, a `PersonaManager` now generates fresh personas per phase, tailored to the domain and the phase's goal.

For a finance domain, Phase 1 might generate: *BalanceSheetRiskMapper*, *TimeHorizonSegmenter*, *RiskComfortCalibrator*, *EmotionalTriggerMapper*. Personas that actually know what they're doing in this space, not generic advisors.

This changed the output quality noticeably. The conversations became more specific, less generic. The ideas started to look like they'd been designed by people who'd thought about the problem, not summarised from a Wikipedia article.

Alongside this: the `FacilitatorAgent` took over turn management. Rather than round-robin, it decides who speaks next based on recent exchanges, novelty gaps, and whether anyone's been ignored. A `MediatorPersona` was added for longer sessions — a neutral voice that intervenes when conversations stall, arguments become circular, or key concepts need defining.

---

### February 2026 — Benchmarks: The Uncomfortable Data

The first real stress test was a 3-way benchmark. We ran the same prompts through:

1. **Single-shot** — one prompt, team-of-experts framing, one LLM call
2. **Iterative** — four sequential turns: initial proposal → self-critique (3 weaknesses) → address critiques → finalise
3. **Assembly** — multi-persona structured debate

Same model (gpt-5.1). Same prompts. Blind scoring by an LLM judge on four criteria: novelty, feasibility, specificity, commercial clarity.

**Assembly didn't win.**

| Approach | Finance | Remote Work | Health | Avg |
|----------|---------|-------------|--------|-----|
| Single-shot | 13 | 12 | 13 | 12.7 |
| **Assembly** | 18 | 15 | 17 | **16.7** |
| **Iterative** | 19 | 17 | 19 | **18.3** |

Iterative won all three domains. The diagnosis: Assembly's multi-persona debate produces technically deep output with named components, decision frameworks, and concrete mechanisms — but stops before commercial polish. No product name. No pricing. No go-to-market path. Iterative's self-critique step directly forces addressing weaknesses, and commercial viability is always a weakness.

This was useful. It told us what was missing.

---

### February 2026 — The Convergence Phase

The fix was a 3-turn **convergence phase** appended to the end of Assembly's debate:

1. **Synthesize** — A Decision Owner reads the full conversation and drafts a product spec
2. **Critique** — A skeptical investor challenges positioning, feasibility, and commercial viability
3. **Refine** — The Decision Owner incorporates critiques and outputs a locked schema

The output schema: product name, one-sentence pitch, target ICP, MVP bullets (max 5), monetisation model, key differentiator, what we're NOT doing, top 3 risks, 7-day action plan.

Test run: the multi-persona debate produced **"Adaptive Buffer-Gated Investing Coach"** — technically detailed, with 15 must-haves and sophisticated mechanisms, but no name and no pricing. The convergence phase turned it into:

> **BufferFirst** — "A paycheck-safe auto-invest plan that won't move money until your bills and emergency cushion are covered." Free under $2,500; 0.20% AUM above; optional $5–9/mo employer subscription. 7-day plan: user interviews → architecture → waitlist A/B test.

The scores:

| Criterion | Iterative | Assembly (raw) | Assembly + Convergence |
|-----------|:---------:|:--------------:|:----------------------:|
| Novelty | 4 | 4 | 4 |
| Feasibility | 4 | 4 | 4 |
| Specificity | 4 | **5** | **5** |
| Commercial Clarity | **5** | 3 | 4 |
| **Total** | **17** | **16** | **17** |

Assembly + Convergence tied Iterative at 17/20. Specificity advantage held. Commercial clarity closed from 3 to 4. The convergence phase kept everything that was good about the debate and added the commercial layer it was missing.

---

### February 2026 — Memory Architecture

The second major problem addressed in February was memory. At 10 turns with 4 personas, feeding the full conversation history to each persona on each turn is fine. At 30+ turns, the context becomes noisy — important early agreements are buried, personas re-raise rejected ideas, the conversation oscillates instead of building.

We built a 3-component structured memory system:

1. **Shared memory** — an LLM-maintained summary of the session state (~200 words). Agreed constraints, rejected ideas, key decisions. Updated after every turn via `update_shared_memory_async()`. Every persona sees the same shared memory.
2. **Personal memory** — per-persona `summary` and `belief_state`. Tracks position shifts, concessions, uncertainties over 3 turns. Updated in parallel via `asyncio.gather()` so latency doesn't compound.
3. **Short-term** — the last 3 exchanges verbatim. Immediate context without the full transcript.

Mode defaults: `fast` stays on full history (no extra LLM calls, fast is meant to be fast). `medium`/`standard`/`deep` use structured.

We ran a 5-domain benchmark to measure the effect:

| Domain | Full History | Structured | Winner |
|--------|:-----------:|:---------:|--------|
| Finance | 16/20 | 15/20 | Full History |
| Health | 15/20 | 14/20 | Full History |
| Education | 15/20 | 15/20 | Tie |
| Productivity | 16/20 | 16/20 | Tie |
| Sustainability | 15/20 | 15/20 | Tie |

Idea quality was too close to call — the two full history "wins" are single-point margins within judge noise. But conversation quality told a cleaner story:

- Structured memory: 14% fewer repetitions per domain
- Structured memory: 10.6% higher concept density (unique concepts per turn)

Both metrics were consistent across domains. The interpretation: at 10 turns, the history isn't long enough for full history to fail badly. The advantage should compound as sessions grow to 30+ turns.

---

### March 2026 — The Dashboard

With the core system working and benchmarked, we built a dashboard to make the system observable and runnable without touching the command line.

**What the dashboard does:**

- **Run tab** — configure an Assembly session (inspiration, mode, number of ideas, personas, mediator toggle, convergence toggle, model override) and watch it run in real time. Live conversation stream via WebSocket, turn counter, cost meter, phase progress.
- **Benchmarks tab** — five benchmark cards, each runnable from the browser with configurable parameters. Live log stream while running. Results stored as JSON, displayed with status badges and plain-English interpretation.
- **Home page** — landing view introducing Assembly, with navigation cards to Run, Benchmarks, and How it Works.
- **How it Works page** — nine-section walkthrough covering the full pipeline: inspiration → phase generation → persona creation → conversation loop → memory system → mediator → idea tracking → belief states → convergence output.

The server is a FastAPI/uvicorn app (`src/dashboard/server.py`). Benchmarks run in a thread pool via `run_in_executor` and stream output to the browser through WebSockets.

The dashboard was also deployed to Railway with single-user auth — a `DASHBOARD_PASSWORD` environment variable gates access.

---

## Current Benchmark Results (March 15, 2026)

We ran all five benchmarks as a full suite. Here's where things stand.

### Phase 1: System Validity

**End-to-End Reliability** — 2/3 runs completed. The one failure: a Windows file encoding error (Unicode non-breaking hyphen U+2011 couldn't be written with the default codec). Not an AI failure — the pipeline ran correctly and produced a valid idea. Structure was 100% valid on successful runs.

**Persona Role Adherence** — 95.2% in-role across 36 exchanges. One persona (context-switch load evaluator) drifted slightly. Gate passes (≥90%). The persona system is functioning as intended.

### Phase 2: Quality vs Single LLM

**2-Way (Assembly vs Single-shot):**

| Metric | Assembly | Single-shot |
|--------|----------|-------------|
| Avg score | 15.7/20 | 15.0/20 |
| Wins | 2/3 | 0/3 |
| Ties | 1 | — |

Assembly never lost. The strict gate (70% win rate, 20% improvement) wasn't met because the margin is only 4.4% — but the direction is consistent. The baseline uses a strong team-of-experts prompt, which is the right thing to compare against.

**3-Way (Assembly vs Single-shot vs Iterative):**

| Domain | Assembly | Iterative | Single-shot |
|--------|:--------:|:---------:|:-----------:|
| Finance | 16 | 15 | 15 |
| Remote Work | 16 | 16 | 15 |
| Health | 16 | 17 | 15 |
| **Avg** | **16.0** | **16.0** | **15.0** |

Assembly and Iterative tied at 16/20 average. Single-shot never won. Assembly consistently scored higher on novelty. Iterative scored higher on commercial clarity on the health domain (4 vs 3) — the one area where iterative self-critique still has an edge.

**Memory Benchmark:**

| Config | Score | Concept Density |
|--------|-------|----------------|
| Structured | 16/20 | 173 concepts/turn |
| Full History | 15/20 | 107 concepts/turn |

Structured memory won. 62% more unique concepts explored per turn, and a 1-point higher idea quality score. This is a single-domain run (finance), so we can't draw strong conclusions — but the direction matches the earlier multi-domain run's conversation quality findings.

---

## What We've Learned

**1. Self-critique is the key variable.** Assembly and Iterative both use it (convergence phase = Assembly's self-critique). Single-shot never wins because it never critiques. The difference between Assembly and Iterative is *what gets critiqued* — Iterative critiques a single LLM's first draft; Assembly critiques the synthesis of a multi-expert debate.

**2. Assembly's strength is depth, not breadth.** Across every run, Assembly consistently scores highest on specificity and novelty. The multi-persona debate generates more unusual angles and more concrete technical frameworks than either baseline. Its weakness has always been commercial packaging — which is what the convergence phase addresses.

**3. Dynamic personas matter more than conversation length.** In our February test, Phase 3 fell back to generic archived personas due to a connection error. Those generic personas showed significantly higher repetition rates than the dynamically generated domain-specific ones. The domain specificity of the personas matters more than how many turns they get.

**4. Memory architecture works in the right direction.** Structured memory reduces repetitions and increases concept density even at 10 turns. The benefit should compound at 30+ turns. Fast mode stays on full history for good reason — no extra LLM calls, no latency overhead — but medium/standard/deep use structured by default.

**5. The scoring ceiling is commercial clarity.** Every approach scores 3–4 out of 5 on commercial clarity. Nobody produces a fully worked-out monetisation strategy from a brainstorm. This is likely a prompt and schema problem — the convergence phase's output schema forces a pricing model and 7-day plan, which is better than nothing, but explicit go-to-market and willingness-to-pay validation are still weak.

---

## Where Things Stand

| Component | Status |
|-----------|--------|
| Persona system (dynamic generation) | Done |
| Facilitator with novelty tracking | Done |
| Mediator persona with trigger system | Done |
| Gap detection + turn nudges | Done |
| Convergence phase | Done |
| Structured memory (3-component) | Done |
| Belief state tracking | Done |
| Async parallel updates | Done |
| LLM-as-judge scoring | Done |
| 3-way benchmark infrastructure | Done |
| Memory benchmark | Done |
| Assembly dashboard (run + benchmarks) | Done |
| Home + How It Works pages | Done |
| Railway deployment + auth | Done |
| Assembly beats Iterative consistently | In progress |
| Standard/deep mode benchmark | Next |
| Multi-phase memory benchmark | Next |
| Commercial clarity improvement | Next |

---

## What's Next

**Run standard mode benchmarks.** All quality benchmarks so far have used fast or medium mode. Standard mode runs 8 turns across all dynamically generated phases. The hypothesis — that more turns and more phases give Assembly a larger advantage — hasn't been tested yet. This is the most important experiment remaining.

**Multi-phase memory test.** The memory benchmark at 10 turns was inconclusive on idea quality. The real test is at 3 phases where structured memory has to carry consensus across phase boundaries. This should be the clearest signal we can get on whether the architecture actually works.

**Fix the commercial clarity gap.** The convergence phase closes Assembly's commercial gap but doesn't fully close it. The next iteration might involve an explicit monetisation critic in the debate phase itself, not just in convergence — someone whose job is to push on pricing and distribution at every turn.

**The `max_tokens` bug.** Several places in the codebase still use `max_tokens` instead of `max_completion_tokens` for gpt-5.1. This causes silent fallbacks in the rejection detector and dead-end recovery metric. One-line fix; just needs doing.

---

## The Honest Version

Assembly produces consistently better ideas than asking one LLM the same question. It never loses to single-shot. It ties Iterative, which is a 4-call refinement loop, using significantly more compute.

The gap between Assembly and Iterative is small and fluctuating. At 15–17 API calls for Assembly vs 4 for Iterative, that's a hard gap to justify on quality alone — especially when the difference is often 0–1 points on commercial clarity.

The case for Assembly isn't "it scores higher on benchmarks." It's "it produces different output." The specificity, the technical frameworks, the domain-specific reasoning — that's genuinely different from what a self-critique loop produces, and useful for different purposes. Iterative produces commercial pitches. Assembly produces product architecture.

Whether there's a use case where that distinction matters enough to pay for is the real question. We're still finding out.

---

*Post #4 in our build log. The full benchmark data is in `benchmarks/`. Code is on GitHub.*

*Previous posts: [When Self-Critique Beats Multi-Persona](./2026-02-03-iterative-beats-assembly.md) | [Convergence Closes the Gap](./2026-02-09-convergence-closes-the-gap.md) | [Does Structured Memory Actually Help?](./memory_benchmark.md)*
