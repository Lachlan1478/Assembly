# Assembly: Execution Plan, Benchmarks & Agent Anchor

This document serves **two purposes**:

1. A **Notion-ready execution tracker** (tasks, benchmarks, gates)
2. A **reference / anchor document** for AI tools (Claude, ChatGPT, agents) to understand the *intent, success criteria, and evaluation standards* of the Assembly project

---

## 1. Project Intent (Anchor Section)

### What Assembly Is

Assembly is a **multi-agent AI system** designed to generate and refine startup ideas through structured collaboration between role-specific personas (e.g. Founder, CFO, Designer, Critic) under a Facilitator.

### Core Hypothesis

> Structured multi-persona collaboration produces higher-quality, more commercially viable startup ideas than a single large language model prompt.
> 

Assembly exists to *test and operationalise this hypothesis*.

### What “Success” Means

Assembly is successful if it can **consistently outperform a single-LLM baseline** on idea quality, usefulness, and commercial clarity.

---

## 2. Non-Goals (Important)

Assembly is **not** currently optimised for:

- UI polish
- Scale or throughput
- Agent marketplaces
- Enterprise deployment
- Model benchmarking for academic purposes

All decisions should prioritise **thinking quality and output usefulness**.

---

## 3. Evaluation Criteria (Global)

All outputs should be judged on:

| Criterion | Description |
| --- | --- |
| Novelty | Is the idea non-obvious or differentiated? |
| Feasibility | Could this realistically be built and sold? |
| Specificity | Are ICP, problem, and solution concrete? |
| Commercial Clarity | Is monetisation obvious and credible? |

Scoring scale: **1 (poor) → 5 (excellent)**

---

## 4. Execution Phases & Benchmarks

---

### Phase 1 — System Validity

**Goal:** Prove the system works reliably and as intended.

### Benchmarks

- [ ]  Conversations complete end-to-end without failure
- [ ]  Personas stay in role ≥ 90% of turns
- [ ]  Facilitator enforces stage transitions
- [ ]  Outputs are structured and reproducible

### Tests

- Run **10 identical prompts**
- Outputs must differ in content but not structure
- Log role drift, hallucinations, and premature conclusions

**Gate:**

> System can run unattended with acceptable reliability
> 

---

### Phase 2 — Quality Benchmark vs Single LLM

**Goal:** Validate the core hypothesis.

### Experiment

For **10 startup prompts**:

1. Generate output using a single ChatGPT-style prompt
2. Generate output using Assembly
3. Blind-score both outputs

### Target Metrics

- Assembly wins ≥ **70%** of comparisons
- Assembly scores ≥ **20% higher** on average total score

**Gate:**

> If this fails, revisit persona design or facilitator logic
> 

---

### Phase 3 — User Value Validation

**Goal:** Determine if outputs are meaningfully better for humans.

### Benchmarks

- [ ]  One-sentence input → structured, board-ready output
- [ ]  Clear ICP, monetisation, and risks included

### User Test

Give outputs to:

- 3 founders
- 2 operators
- 1 finance-focused skeptic

Ask only:

> “Is this better than ChatGPT? Why or why not?”
> 

**Gate:**

> ≥ 4/6 say yes without prompting
> 

---

### Phase 4 — Monetisation Signal

**Goal:** Test willingness to pay.

### Benchmarks

- [ ]  Clear target user defined
- [ ]  Clear value promise articulated
- [ ]  Tangible output artifact (PDF / Notion / Pitch outline)

### Test

- Fake pricing page ($20–$30 per deep run)
- Show example outputs

**Gate:**

> ≥ 2 people explicitly say they would pay
> 

---

### Phase 5 — Strategic Moat (Optional)

**Goal:** Move beyond prompt engineering.

### Moat Indicators

- Personas retain memory or bias
- Facilitator adapts flow based on quality
- Outputs improve with iteration
- System demonstrates preference for high-quality ideas

---

## 5. North-Star Metrics

These metrics override all feature work:

1. Win-rate vs single LLM
2. Average output score
3. Repeat usage
4. Explicit willingness to pay

If these stagnate, **stop building features**.

---

## 6. Notion Execution Tracker (Paste into Notion)

### Project Dashboard

| Phase | Status | Owner | Gate Passed | Notes |
| --- | --- | --- | --- | --- |
| Phase 1 – System Validity | ⬜ |  | ⬜ |  |
| Phase 2 – LLM Benchmark | ⬜ |  | ⬜ |  |
| Phase 3 – User Value | ⬜ |  | ⬜ |  |
| Phase 4 – Monetisation | ⬜ |  | ⬜ |  |
| Phase 5 – Moat | ⬜ |  | ⬜ |  |

---

### Experiment Log

| Date | Prompt | Mode | Output Score | Notes |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |

---

## 7. Instructions for AI Agents (Claude / ChatGPT)

When interacting with this repository:

- Treat this document as the **source of truth** for intent and success criteria
- Optimise for **output quality over verbosity**
- Do not add features that do not improve benchmark outcomes
- Prefer structural improvements (persona design, facilitation logic) over surface-level changes

---

## 8. Decision Rule

If Assembly does **not** outperform a single LLM after Phase 2:

- Pause feature development
- Diagnose failure mode
- Either redesign personas or sunset the project

Killing the project early is considered a **successful outcome** if learnings are clear.

---

End of document.