# Assembly Architecture Deep Dive: Shared Context & Meeting Orchestration

## Overview

This document explains how Assembly's multi-phase conversation system works, focusing on the `shared_context` mechanism and the `meeting_facilitator` orchestration engine.

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Shared Context: The Collaborative Whiteboard](#shared-context-the-collaborative-whiteboard)
3. [Meeting Orchestration Flow](#meeting-orchestration-flow)
4. [Dynamic Persona Generation](#dynamic-persona-generation)
5. [Turn-by-Turn Conversation Loop](#turn-by-turn-conversation-loop)
6. [Async Parallelization](#async-parallelization)
7. [Complete Data Flow](#complete-data-flow)
8. [Example: Healthcare Startup Ideas](#example-healthcare-startup-ideas)

---

## Architecture Overview

Assembly uses a **facilitator-directed multi-phase conversation** architecture where:
- Phases are dynamically generated based on the problem domain
- Personas are dynamically generated for each phase
- A shared context acts as collaborative memory across all phases
- Async parallelization enables fast persona memory updates

```
┌─────────────────────────────────────────────────────────────────┐
│                        generator.py                              │
│                     (Entry Point & Config)                       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ├─► Generate dynamic phases (LLM)
                        │
                        ├─► Initialize shared_context = {}
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│                   meeting_facilitator()                          │
│                  (orchestration.py - async)                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  FOR EACH PHASE:                                                 │
│    ┌───────────────────────────────────────────────────────┐   │
│    │ 1. PersonaManager generates 4 expert personas         │   │
│    │    (cached or LLM-generated)                          │   │
│    └───────────────────────────────────────────────────────┘   │
│                        │                                         │
│    ┌───────────────────▼───────────────────────────────────┐   │
│    │ 2. WHILE phase not complete:                          │   │
│    │    ┌──────────────────────────────────────────────┐   │   │
│    │    │ a) Facilitator picks next speaker           │   │   │
│    │    │ b) Generate dynamic prompt (stage-based)     │   │   │
│    │    │ c) Persona responds (uses memory + context)  │   │   │
│    │    │ d) Extract idea titles → UPDATE shared_ctx   │   │   │
│    │    │ e) All personas update memory (PARALLEL)     │   │   │
│    │    └──────────────────────────────────────────────┘   │   │
│    └─────────────────────────────────────────────────────┘   │
│                        │                                         │
│    ┌───────────────────▼───────────────────────────────────┐   │
│    │ 3. Facilitator creates phase summary                  │   │
│    └───────────────────────────────────────────────────────┘   │
│                                                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼ Return mutated shared_context
┌─────────────────────────────────────────────────────────────────┐
│  Extract ideas from final_context["logs"]                       │
│  Save to conversation_logs/                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Shared Context: The Collaborative Whiteboard

### What is `shared_context`?

`shared_context` is a **mutable dictionary** that acts as shared memory across all phases and personas. Think of it as a whiteboard in a real meeting room that everyone can see and update.

```python
# Initialization in generator.py (lines 125-133)
shared_context = {
    "inspiration": inspiration,           # Problem domain (immutable)
    "number_of_ideas": number_of_ideas,   # How many ideas to generate (immutable)
    "ideas": [],                          # MUTABLE: Final structured idea objects
    "ideas_discussed": [],                # MUTABLE: Structured idea concepts with status tracking
    "current_focus": None                 # MUTABLE: Most recently discussed idea title
}
```

### Enhanced `ideas_discussed` Structure (New in v2.0)

Each idea in `ideas_discussed` is now a rich object with status tracking:

```python
{
  "title": "HealthBridge",
  "overview": "A unified patient data API using FHIR standards...",
  "example": "An ER doctor treating an unconscious patient could...",
  "status": "in_play",  # or "rejected"
  "rejection_reason": None,  # Populated if rejected
  "first_mentioned_phase": "problem_space_exploration",
  "first_mentioned_turn": 5,
  "last_updated_turn": 12,
  "refinements": [...]  # Track how idea evolved over turns
}
```

### Why "Pure Dynamic"?

Previously, there was a hardcoded prompt template stored in `shared_context` that was never used. The current architecture is "pure dynamic" because:
- No hardcoded templates
- Prompts are generated on-the-fly based on phase, stage, and conversation state
- `shared_context` only contains actual runtime data that gets mutated

### Mutable vs Immutable Fields

```
┌─────────────────────────────────────────────────────────────┐
│                     shared_context                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  IMMUTABLE (set once, read-only):                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ inspiration: "Domain: Healthcare startup ideas..."    │  │
│  │ number_of_ideas: 3                                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
│  MUTABLE (updated during conversation):                     │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ ideas: []                                             │  │
│  │   → Populated when personas format final ideas       │  │
│  │                                                         │  │
│  │ ideas_discussed: []  (ENHANCED v2.0)                  │  │
│  │   → Updated when detailed proposals are detected     │  │
│  │   → Contains structured objects with:                │  │
│  │       - title, overview, example                      │  │
│  │       - status ("in_play" or "rejected")             │  │
│  │       - rejection_reason (if rejected)                │  │
│  │       - first_mentioned_phase, turn tracking         │  │
│  │       - refinements array (evolution tracking)       │  │
│  │   → Example:                                          │  │
│  │     [{title: "HealthBridge", status: "in_play",...}, │  │
│  │      {title: "MediSync", status: "rejected",...}]    │  │
│  │                                                         │  │
│  │ current_focus: None                                   │  │
│  │   → Updated to most recently discussed idea title    │  │
│  │   → Used in next prompt: "Regarding {current_focus}" │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
│  ADDED BY ORCHESTRATOR (at end):                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ logs: [...]           # Full conversation transcript  │  │
│  │ phase_summaries: [...] # High-level phase summaries  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### How Personas Access Shared Context

When a persona generates a response, it receives `shared_context` in its context:

```python
# orchestration.py lines 144-154
ctx = {
    "user_prompt": dynamic_prompt,      # Stage-appropriate prompt
    "phase": phase,                     # Current phase info
    "shared_context": shared_context,   # ← FULL ACCESS TO SHARED MEMORY
    "recent_exchanges": phase_exchanges, # Recent conversation
    "turn_count": turn_count            # Current turn number
}

response_data = speaker_persona.response(ctx)
```

**What personas can do with `shared_context`:**
- Read `ideas_discussed` to see what's been proposed
- Read `current_focus` to know what idea is being discussed
- Write structured ideas to `ideas` (though this is rare - usually extracted by LLM)

---

## Meeting Orchestration Flow

### Phase Loop Structure

The `meeting_facilitator()` function processes each phase sequentially:

```
PHASE 1: problem_space_exploration
  ├─ Generate 4 personas (LLM)
  ├─ Turn 0: Facilitator → Speaker → Response → Update memories
  ├─ Turn 1: Facilitator → Speaker → Response → Update memories
  ├─ ...
  ├─ Turn N: Facilitator decides phase complete
  └─ Facilitator creates phase summary
           │
           ▼ shared_context passed to next phase
PHASE 2: solution_brainstorming
  ├─ Generate 4 NEW personas (LLM)
  ├─ Turn 0: Can reference Phase 1 via shared_context
  ├─ Turn 1: ...
  └─ Phase summary
           │
           ▼ shared_context passed to next phase
PHASE 3: decision_synthesis
  ├─ Generate 4 NEW personas (LLM)
  ├─ Turn 0: Can reference ALL previous phases
  ├─ Turn 1: ...
  └─ Final phase summary
           │
           ▼ Return final shared_context
```

### Key Orchestration Code

```python
# orchestration.py lines 48-260 (simplified)

async def meeting_facilitator(..., shared_context, ...):
    logs = []
    all_phase_summaries = []

    for phase in phases:
        # 1. Generate personas for this phase
        active_personas = persona_manager.request_personas_for_phase(
            inspiration=inspiration,
            phase_info=phase,
            count=4
        )

        # 2. Turn-by-turn conversation loop
        phase_exchanges = []
        turn_count = 0
        max_turns = phase.get("max_turns", 15)

        while True:
            # 2a. Facilitator decides next speaker
            next_speaker_name = facilitator.decide_next_speaker(
                phase=phase,
                active_personas=active_personas,
                recent_exchanges=phase_exchanges,
                shared_context=shared_context,  # ← Facilitator sees shared memory
                turn_count=turn_count,
                max_turns=max_turns
            )

            if next_speaker_name is None:
                break  # Phase complete

            # 2b. Generate dynamic prompt
            dynamic_prompt = generate_dynamic_prompt(
                phase=phase,
                turn_count=turn_count,
                phase_exchanges=phase_exchanges,
                shared_context=shared_context  # ← Prompt generation sees shared memory
            )

            # 2c. Persona responds
            speaker_persona = active_personas[next_speaker_name]
            ctx = {
                "user_prompt": dynamic_prompt,
                "shared_context": shared_context,  # ← Persona sees shared memory
                "recent_exchanges": phase_exchanges,
                "turn_count": turn_count
            }
            response_data = speaker_persona.response(ctx)

            # 2d. Extract idea titles and UPDATE shared_context
            idea_title = extract_idea_title(response_content)
            if idea_title:
                if idea_title not in shared_context["ideas_discussed"]:
                    shared_context["ideas_discussed"].append(idea_title)  # ← MUTATION
                shared_context["current_focus"] = idea_title  # ← MUTATION

            # 2e. All personas update memory (parallel)
            await asyncio.gather(*[
                persona.update_summary_async(exchange_data)
                for persona in active_personas.values()
            ])

            turn_count += 1

        # 3. Phase summary
        phase_summary = facilitator.summarize_phase(phase, phase_exchanges, shared_context)
        all_phase_summaries.append(phase_summary)

    # 4. Add logs and summaries to shared_context
    shared_context["logs"] = logs
    shared_context["phase_summaries"] = all_phase_summaries

    return shared_context  # Returns mutated version
```

---

## Dynamic Persona Generation

### Three-Tier Persona Caching

PersonaManager uses a three-tier caching strategy to optimize performance:

```
┌─────────────────────────────────────────────────────────────────┐
│                   PERSONA REQUEST FLOW                           │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
         ┌─────────────────────────────────────────────┐
         │ PersonaManager.request_personas_for_phase() │
         └──────────────────┬──────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────┐
│ TIER 1: Memory Cache (self.memory_cache)                      │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ Key: "healthcare_feasibility_analysis"                    │ │
│ │ Value: {                                                   │ │
│ │   "Dr. Sarah Chen": Persona(...),                         │ │
│ │   "John Smith": Persona(...),                             │ │
│ │   ...                                                      │ │
│ │ }                                                          │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ✓ Instant retrieval                                            │
│ ✓ Active for current session only                             │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Cache MISS
                       ▼
┌───────────────────────────────────────────────────────────────┐
│ TIER 2: File Cache (dynamic_personas/)                        │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ File: dynamic_personas/healthcare_feasibility_analysis/   │ │
│ │       healthcare_compliance_officer.json                  │ │
│ │       health_it_architect.json                            │ │
│ │       ...                                                  │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ✓ Persisted across sessions                                   │
│ ✓ Domain + phase specific                                     │
│ ✓ Reusable for similar contexts                               │
└──────────────────────┬──────────────────────────────────────────┘
                       │ Cache MISS
                       ▼
┌───────────────────────────────────────────────────────────────┐
│ TIER 3: LLM Generation + Archive Fallback                     │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ generate_personas_for_context()                           │ │
│ │   ↓                                                        │ │
│ │ LLM generates 4 new personas based on:                    │ │
│ │   - Domain inspiration                                     │ │
│ │   - Phase goal and desired outcome                        │ │
│ │   - Existing personas (to avoid duplicates)               │ │
│ │                                                            │ │
│ │ Fallback: If LLM fails, load from personas_archive/       │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ⚠ Slowest (LLM API call)                                      │
│ ✓ Completely dynamic and domain-specific                      │
│ ✓ Saved to Tier 2 for future reuse                           │
└─────────────────────────────────────────────────────────────────┘
```

### Persona Generation Example

For **domain: "Healthcare startup ideas"** in **phase: "feasibility_analysis"**:

```json
// Generated personas (saved to dynamic_personas/healthcare_startup_ideas_feasibility_analysis/)
[
  {
    "name": "Dr. Sarah Chen",
    "archetype": "Healthcare Compliance Officer",
    "description": "20 years experience in HIPAA compliance and healthcare regulations",
    "expertise": [
      "HIPAA compliance",
      "Healthcare data privacy",
      "FDA medical device regulations"
    ],
    "perspective": "Focuses on regulatory hurdles and compliance requirements for healthcare tech"
  },
  {
    "name": "Marcus Johnson",
    "archetype": "Health IT Architect",
    "description": "Senior architect who has built EHR integration systems for major hospitals",
    "expertise": [
      "HL7 and FHIR standards",
      "Healthcare data interoperability",
      "Cloud infrastructure for healthcare"
    ],
    "perspective": "Emphasizes technical feasibility and integration complexity"
  },
  {
    "name": "Dr. Emily Rodriguez",
    "archetype": "Clinical Workflow Designer",
    "description": "Former ER physician turned healthcare UX consultant",
    "expertise": [
      "Clinical workflows",
      "Physician pain points",
      "Healthcare user experience"
    ],
    "perspective": "Ensures solutions fit into real clinical workflows"
  },
  {
    "name": "Alex Kim",
    "archetype": "Healthcare Data Security Expert",
    "description": "CISO for a major hospital network",
    "expertise": [
      "Healthcare cybersecurity",
      "Data breach prevention",
      "Security compliance"
    ],
    "perspective": "Prioritizes data security and breach prevention"
  }
]
```

---

## Turn-by-Turn Conversation Loop

### Conversation Turn Flow Diagram

```
┌────────────────────────────────────────────────────────────────────┐
│                       TURN N IN PHASE                               │
└────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 1: Facilitator Decides Next Speaker                            │
│                                                                      │
│  facilitator.decide_next_speaker(                                   │
│    phase=phase,                                                      │
│    active_personas={...},                                           │
│    recent_exchanges=[...],                                          │
│    shared_context={ideas_discussed: ["HealthBridge"]},             │
│    turn_count=3,                                                     │
│    max_turns=8                                                       │
│  )                                                                   │
│                                                                      │
│  → LLM decides: "Dr. Sarah Chen" (Compliance Officer)               │
│  → Reasoning: "Need regulatory perspective on HealthBridge"         │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 2: Generate Dynamic Prompt                                     │
│                                                                      │
│  generate_dynamic_prompt(                                           │
│    phase={phase_id: "feasibility_analysis", ...},                   │
│    turn_count=3,                                                     │
│    phase_exchanges=[...],                                           │
│    shared_context={current_focus: "HealthBridge", ...}             │
│  )                                                                   │
│                                                                      │
│  → Stage calculation: turn 3 of 8 → Stage 1 (Technical Assessment) │
│  → Generated prompt:                                                 │
│    "Assess the technical feasibility of HealthBridge:               │
│     1. What technical risks exist?                                  │
│     2. What compliance requirements must be met?                    │
│     3. What would make this hard to build?"                         │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 3: Persona Generates Response                                  │
│                                                                      │
│  ctx = {                                                             │
│    "user_prompt": "Assess the technical feasibility...",           │
│    "shared_context": {ideas_discussed: ["HealthBridge"], ...},     │
│    "recent_exchanges": [prev turns...],                             │
│    "turn_count": 3                                                   │
│  }                                                                   │
│                                                                      │
│  speaker_persona.response(ctx)  # Dr. Sarah Chen                    │
│    ↓                                                                 │
│  Persona uses:                                                       │
│    - Her memory summary (objective facts + subjective notes)        │
│    - shared_context (sees "HealthBridge" was discussed)            │
│    - recent_exchanges (last 3-5 turns)                              │
│    - Her expertise (Healthcare Compliance Officer)                  │
│                                                                      │
│  → Response: "HealthBridge faces significant HIPAA compliance       │
│     challenges. We'd need BAA agreements with all data sources,     │
│     end-to-end encryption, audit logging, and regular security      │
│     assessments. The FHIR API integration is technically sound,     │
│     but we must ensure proper access controls..."                   │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 4: Extract Idea Titles                                         │
│                                                                      │
│  idea_title = extract_idea_title(response_content)                 │
│    → Searches for patterns like:                                    │
│      - "I propose [title]"                                          │
│      - "[title] could solve..."                                     │
│      - Capitalized phrases that sound like product names            │
│                                                                      │
│  → Found: "HealthBridge" (already in ideas_discussed)               │
│  → No update needed this turn                                       │
│                                                                      │
│  shared_context["current_focus"] = "HealthBridge"  # Reaffirm focus│
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│ STEP 5: All Personas Update Memory (ASYNC PARALLEL)                │
│                                                                      │
│  exchange_data = {                                                   │
│    "speaker": "Dr. Sarah Chen",                                     │
│    "content": "HealthBridge faces significant HIPAA...",           │
│    "phase": "feasibility_analysis"                                  │
│  }                                                                   │
│                                                                      │
│  await asyncio.gather(*[                                            │
│    persona.update_summary_async(exchange_data)                     │
│    for persona in active_personas.values()                          │
│  ])                                                                  │
│                                                                      │
│  ┌──────────────────────┐  ┌──────────────────────┐               │
│  │ Dr. Sarah Chen       │  │ Marcus Johnson       │               │
│  │ update_summary()     │  │ update_summary()     │               │
│  │   ↓ LLM call         │  │   ↓ LLM call         │               │
│  │ Add to memory:       │  │ Add to memory:       │               │
│  │ "Noted HIPAA reqs"   │  │ "FHIR mentioned"     │               │
│  └──────────────────────┘  └──────────────────────┘               │
│                                                                      │
│  ┌──────────────────────┐  ┌──────────────────────┐               │
│  │ Dr. Emily Rodriguez  │  │ Alex Kim             │               │
│  │ update_summary()     │  │ update_summary()     │               │
│  │   ↓ LLM call         │  │   ↓ LLM call         │               │
│  │ Add to memory:       │  │ Add to memory:       │               │
│  │ "Compliance focus"   │  │ "Security concerns"  │               │
│  └──────────────────────┘  └──────────────────────┘               │
│                                                                      │
│  All 4 LLM calls happen IN PARALLEL (not sequential!)              │
│  Time: ~0.5s (vs 2s if sequential)                                 │
└───────────────────────────┬──────────────────────────────────────────┘
                            │
                            ▼
                     Turn N+1 begins...
```

---

## Async Parallelization

### Why Async Matters

**Without async (sequential updates):**
```
Turn 1: Persona responds (0.8s)
  → Persona 1 updates memory (0.5s)
  → Persona 2 updates memory (0.5s)
  → Persona 3 updates memory (0.5s)
  → Persona 4 updates memory (0.5s)
  Total: 2.8s per turn

Standard mode: 8 turns × 7 phases = 56 turns
56 turns × 2.8s = 157 seconds = 2.6 minutes
```

**With async (parallel updates):**
```
Turn 1: Persona responds (0.8s)
  → All 4 personas update memory in parallel (0.5s)
  Total: 1.3s per turn

Standard mode: 8 turns × 7 phases = 56 turns
56 turns × 1.3s = 73 seconds = 1.2 minutes
```

**Speedup: 2.15x faster!**

### Async Implementation

```python
# orchestration.py lines 205-213

if use_async_updates:
    # Parallel async updates for speed
    await asyncio.gather(*[
        persona.update_summary_async(exchange_data)
        for persona in active_personas.values()
    ])
else:
    # Sequential updates (backward compatibility)
    for persona_name, persona in active_personas.items():
        persona.update_summary(exchange_data)
```

### Persona Async Method

```python
# framework/persona.py

async def update_summary_async(self, new_exchange: Dict[str, Any]) -> None:
    """
    Asynchronously update persona's summary based on new conversation exchange.

    Uses asyncio to enable parallel summary updates across all personas.
    """
    loop = asyncio.get_event_loop()

    # Run the blocking LLM call in a thread pool
    await loop.run_in_executor(
        None,  # Use default executor
        self.update_summary,  # Existing sync method
        new_exchange
    )
```

### Async vs Sync Comparison

```
┌────────────────────────────────────────────────────────────────────┐
│              SEQUENTIAL (use_async_updates=False)                   │
└────────────────────────────────────────────────────────────────────┘

Time ──────────────────────────────────────────────────────────────►

Persona 1: [────────] (0.5s)
Persona 2:           [────────] (0.5s)
Persona 3:                     [────────] (0.5s)
Persona 4:                               [────────] (0.5s)
           ├─────────┼─────────┼─────────┼─────────┤
           0        0.5s       1s       1.5s       2s

Total: 2 seconds


┌────────────────────────────────────────────────────────────────────┐
│               PARALLEL (use_async_updates=True)                     │
└────────────────────────────────────────────────────────────────────┘

Time ──────────────────────────────────────────────────────────────►

Persona 1: [────────]
Persona 2: [────────]
Persona 3: [────────]
Persona 4: [────────]
           ├─────────┤
           0        0.5s

Total: 0.5 seconds (4x speedup!)
```

---

## Complete Data Flow

### End-to-End Example

```
USER INPUT: "Generate startup ideas for small dev teams with AI tools"
           ↓
┌─────────────────────────────────────────────────────────────────┐
│ generator.py: multiple_llm_idea_generator()                     │
└─────────────────────────────────────────────────────────────────┘
           ↓
    1. Generate dynamic phases using LLM
       → [problem_space_exploration, ai_tool_identification,
          solution_brainstorming, feasibility_analysis,
          monetization_model_design, mvp_definition, decision_synthesis]
           ↓
    2. Select phases based on mode (medium = bookends_plus_middle)
       → [problem_space_exploration, ai_tool_identification,
          solution_brainstorming, decision_synthesis]
           ↓
    3. Initialize shared_context
       shared_context = {
         "inspiration": "...",
         "number_of_ideas": 3,
         "ideas": [],
         "ideas_discussed": [],
         "current_focus": None
       }
           ↓
    4. Call asyncio.run(meeting_facilitator(..., shared_context, ...))
           ↓
┌─────────────────────────────────────────────────────────────────┐
│ orchestration.py: meeting_facilitator()                         │
└─────────────────────────────────────────────────────────────────┘
           ↓
    ┌─────────────────────────────────────────────────────────┐
    │ PHASE 1: problem_space_exploration                       │
    └─────────────────────────────────────────────────────────┘
           ↓
       a) PersonaManager generates 4 personas:
          - Indie Hacker
          - Technical Founder
          - Product Manager
          - Software Architect
           ↓
       b) Turn 0: Facilitator picks "Indie Hacker"
          - Prompt: "What pain points exist for small dev teams?"
          - Response: "Finding product-market fit quickly..."
          - Extract ideas: None yet
          - Update all 4 persona memories (parallel)
           ↓
       c) Turn 1: Facilitator picks "Technical Founder"
          - Prompt: "What competitive solutions exist?"
          - Response: "Tools like GitHub Copilot help but lack domain specificity..."
          - Extract ideas: None yet
          - Update all 4 persona memories (parallel)
           ↓
       d) Turn 2: Facilitator picks "Product Manager"
          - Prompt: "Propose a solution addressing these pain points"
          - Response: "I propose CodeCraft, an AI assistant for rapid prototyping..."
          - Extract ideas: "CodeCraft"
          - shared_context["ideas_discussed"] = ["CodeCraft"]  ← MUTATION
          - shared_context["current_focus"] = "CodeCraft"  ← MUTATION
          - Update all 4 persona memories (parallel)
           ↓
       e) Turn 3-4: More discussion, refining "CodeCraft"
          - shared_context["ideas_discussed"] = ["CodeCraft", "TeamSync"]
           ↓
       f) Facilitator: "Phase complete"
       g) Phase summary created

    ┌─────────────────────────────────────────────────────────┐
    │ PHASE 2: ai_tool_identification                          │
    └─────────────────────────────────────────────────────────┘
           ↓
       a) PersonaManager generates 4 NEW personas:
          - AI/ML Engineer
          - API Integration Specialist
          - DevOps Engineer
          - Data Scientist
           ↓
       b) Turn 0: Facilitator picks "AI/ML Engineer"
          - Prompt references shared_context["current_focus"] = "TeamSync"
          - Prompt: "Identify AI tools that could power TeamSync..."
          - Response: "We could use GPT-4 for code generation, Claude for..."
          - shared_context unchanged (no new ideas)
          - Update all 4 persona memories (parallel)
           ↓
       c) Turns 1-4: Discussion continues...
       d) Phase summary created

    ┌─────────────────────────────────────────────────────────┐
    │ PHASE 3: solution_brainstorming                          │
    └─────────────────────────────────────────────────────────┘
           ↓
       (Similar flow...)

    ┌─────────────────────────────────────────────────────────┐
    │ PHASE 4: decision_synthesis                              │
    └─────────────────────────────────────────────────────────┘
           ↓
       a) PersonaManager generates 4 NEW personas:
          - Product Strategist
          - Business Analyst
          - Technical Architect
          - UX Designer
           ↓
       b) Turn 0: Consolidation stage
          - Prompt: "Review all discussions and synthesize insights"
          - Business Analyst reviews shared_context["ideas_discussed"]
          - Response: "We've discussed CodeCraft, TeamSync, and AIDevKit..."
           ↓
       c) Turn 1-2: Final synthesis
          - Prompt: "Finalize 3 startup ideas with full details"
          - Business Analyst outputs structured JSON:
            [{title: "CodeCraft", description: "...", ...}, {...}, {...}]
          - shared_context["ideas"] = [3 structured ideas]  ← MUTATION
           ↓
       d) Phase complete

    ┌─────────────────────────────────────────────────────────┐
    │ Return final shared_context                              │
    └─────────────────────────────────────────────────────────┘
           ↓
       shared_context now contains:
       {
         "inspiration": "...",
         "number_of_ideas": 3,
         "ideas": [
           {title: "CodeCraft", ...},
           {title: "TeamSync", ...},
           {title: "AIDevKit", ...}
         ],
         "ideas_discussed": ["CodeCraft", "TeamSync", "AIDevKit"],
         "current_focus": "AIDevKit",
         "logs": [56 conversation exchanges],
         "phase_summaries": [4 phase summaries]
       }
           ↓
┌─────────────────────────────────────────────────────────────────┐
│ generator.py: Extract and save ideas                           │
└─────────────────────────────────────────────────────────────────┘
           ↓
    5. Extract ideas from final_context["logs"] or final_context["ideas"]
    6. Save to conversation_logs/session_TIMESTAMP/
       - readable_transcript.md
       - session_metadata.json
       - persona_summaries.json
       - facilitator_decisions.json
    7. Return business_ideas to caller
           ↓
OUTPUT: 3 structured startup ideas
```

---

## Example: Healthcare Startup Ideas

### Real Execution Trace

Let's trace a real example from the logs (`session_20251110_184318`):

#### Phase 1: problem_space_exploration

**Personas Generated:**
- Riley Chen (Startup Strategist)
- Jordan Lee (Software Development Lead)
- Alex Morgan (Market Research Analyst)
- Casey Kim (Product Manager)

**Turn 0:**
- **Speaker**: Riley Chen
- **Prompt**: "What are the core pain points in this domain?"
- **Response**: "Small development teams face unique challenges: limited resources, intense competition, need for rapid MVP development..."
- **shared_context update**: None

**Turn 3:**
- **Speaker**: Casey Kim
- **Prompt**: "Propose a solution addressing these pain points"
- **Response**: "Consider OnboardOptimizer - an AI-driven onboarding tool that customizes learning paths..."
- **shared_context update**:
  ```python
  ideas_discussed = ["OnboardOptimizer"]
  current_focus = "OnboardOptimizer"
  ```

#### Phase 4: feasibility_analysis

**Personas Generated** (new set):
- Taylor Swift (Cost-Benefit Analyst)
- Morgan Lee (Technical Feasibility Expert)
- Jordan Smith (User Experience Researcher)
- Riley Brown (Business Model Strategist)

**Turn 0:**
- **Speaker**: Morgan Lee
- **Prompt**: "Assess the feasibility of **OnboardOptimizer** based on MVP constraints"
  - ← Note: Prompt references `shared_context["current_focus"]`
- **Response**: "OnboardOptimizer is highly feasible. We can build it with existing LLM APIs (OpenAI, Claude), integrate with Slack/GitHub..."
- **shared_context**: Read `current_focus`, no writes

#### Phase 7: decision_synthesis

**Personas Generated** (new set):
- Taylor Jordan (Decision Analyst)
- Morgan Casey (Business Strategist)
- Riley Alex (Product Designer)
- Jordan Kim (Financial Analyst)

**Turn 1:**
- **Speaker**: Morgan Casey
- **Prompt**: "Finalize the startup idea in complete, structured format"
- **Response**: Outputs JSON:
  ```json
  {
    "startup_ideas": [
      {
        "title": "OnboardOptimizer",
        "description": "An AI-driven onboarding tool...",
        "target_users": "Small development teams and new developers",
        "primary_outcome": "Accelerated onboarding with tailored resources",
        "must_haves": ["Interactive task lists", "Mentorship pairing", ...],
        "constraints": ["Must be implemented within 3-6 months", ...],
        "non_goals": ["Will not replace existing PM tools", ...]
      },
      {/* FlowOptimizer */},
      {/* Testim */}
    ]
  }
  ```
- **shared_context update**:
  ```python
  ideas = [{OnboardOptimizer}, {FlowOptimizer}, {Testim}]
  ```

#### Final Output

The `final_context` returned contains:
- `ideas_discussed`: ["OnboardOptimizer", "FlowOptimizer", "Testim"]
- `ideas`: [3 fully structured startup ideas]
- `logs`: 66 conversation exchanges across 7 phases
- `phase_summaries`: 7 high-level summaries

---

## Key Architectural Benefits

### 1. **True Collaboration**
- `shared_context` enables personas to build on each other's contributions
- Ideas from early phases inform discussion in later phases
- No need to manually pass data between phases

### 2. **Dynamic Adaptation**
- Prompts adapt based on conversation state
- Personas generated specifically for each phase's needs
- No hardcoded assumptions about domain or structure

### 3. **Performance Optimization**
- Async parallelization reduces runtime by 2-4x
- Three-tier persona caching avoids redundant LLM calls
- Fast mode can skip summary updates entirely

### 4. **Separation of Concerns**
- Each module has a clear responsibility
- Easy to modify prompt generation without touching orchestration
- Easy to add new phase selection strategies

### 5. **Observability**
- Comprehensive logging at every level
- ConversationMonitor provides real-time progress tracking
- Facilitator decisions logged for debugging

---

## Summary

The `shared_context` + `meeting_facilitator` architecture creates a collaborative multi-agent system where:

1. **Shared memory** (`shared_context`) acts as a mutable whiteboard
2. **Phases** are dynamically generated based on problem domain
3. **Personas** are dynamically generated for each phase's specific needs
4. **Facilitator** intelligently orchestrates speaker selection and flow control
5. **Dynamic prompts** guide personas through staged discovery
6. **Async parallelization** enables 2-4x faster persona memory updates
7. **Three-tier caching** optimizes persona reuse across sessions

The result is a system that can generate high-quality, domain-specific startup ideas through natural multi-agent conversation, with runtime ranging from 1-2 minutes (fast mode) to 60-90 minutes (deep mode).
