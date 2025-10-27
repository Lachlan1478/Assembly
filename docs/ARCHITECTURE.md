# Assembly Architecture

## Project Structure

Assembly follows a modular Python package structure with clear separation of concerns:

```
Assembly/
├── main.py                          # Entry point & CLI orchestrator
├── src/                             # Source code (Python package)
│   ├── __init__.py
│   ├── core/                        # Core framework components
│   │   ├── __init__.py
│   │   ├── persona.py              # Persona class with hybrid memory
│   │   ├── facilitator.py          # FacilitatorAgent orchestration
│   │   ├── conversation_logger.py  # Multi-format logging system
│   │   └── utils.py                # Helper functions (persona loading)
│   ├── idea_generation/            # Idea generation pipeline
│   │   ├── __init__.py
│   │   ├── generator.py            # Main entry point (multiple_llm_idea_generator)
│   │   ├── config.py               # Mode configurations
│   │   ├── prompts.py              # Dynamic prompt generation with staging
│   │   ├── orchestration.py       # Meeting facilitation logic
│   │   └── extraction.py           # Idea extraction utilities
│   └── stages/                      # Pipeline stages
│       ├── __init__.py
│       ├── spec_generation.py      # Stage 2: Spec generation
│       └── design_generation.py    # Stage 3: Base44 automation
├── docs/                            # Documentation
│   ├── ARCHITECTURE.md             # This file
│   ├── DOCUMENTATION.md            # User documentation
│   ├── CLAUDE.md                   # Development context
│   └── CONVERSATION_FLOW_ANALYSIS.md
├── personas/                        # Persona definitions (JSON)
│   ├── founder.json
│   ├── product_designer.json
│   ├── market_researcher.json
│   ├── tech_lead.json
│   ├── cfo.json
│   ├── contrarian.json
│   └── facilitator.json
├── tests/                          # Test scripts
│   ├── test_persona_class.py
│   └── test_base_44_automation/
├── outputs/                        # Runtime output files
│   └── .gitkeep
├── conversation_logs/              # Generated conversation logs
├── archive/                        # Legacy/reference code
├── .env                            # Environment configuration
├── .gitignore
└── README.md
```

---

## Script Execution Order

### High-Level Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                          main.py                                 │
│                    (Entry Point & CLI)                           │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Stage 1: Idea Generation                      │
│              src.idea_generation.generator.py                    │
│          multiple_llm_idea_generator(inspiration)                │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Stage 2: Spec Generation                      │
│              src.stages.spec_generation.py                       │
│              make_initial_prompt(idea_json)                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Stage 3: Design Generation                      │
│              src.stages.design_generation.py                     │
│            create_initial_design(spec_prompt)                    │
│                   (Currently stubbed)                            │
└─────────────────────────────────────────────────────────────────┘
```

### Detailed Execution Flow

#### 1. Entry Point: `main.py`

**Purpose**: CLI interface and pipeline orchestration

**Execution Order**:
1. Parse command-line arguments (mode: fast/medium/standard/deep)
2. Load environment variables from `.env`
3. Call Stage 1: `multiple_llm_idea_generator(INSPIRATION, mode=args.mode)`
4. Extract best idea from results
5. Call Stage 2: `make_initial_prompt(best_idea)`
6. (Stage 3 currently commented out)

**Key Imports**:
```python
from src.idea_generation.generator import multiple_llm_idea_generator
from src.idea_generation.config import MODE_CONFIGS
from src.stages.spec_generation import make_initial_prompt
```

---

#### 2. Stage 1: Idea Generation

**Entry Point**: `src/idea_generation/generator.py::multiple_llm_idea_generator()`

**Module Dependencies**:
```
generator.py
    ├── imports config.py (MODE_CONFIGS, MODEL)
    ├── imports orchestration.py (meeting_facilitator)
    ├── imports extraction.py (extract_ideas_with_llm)
    ├── imports src.core.utils (load_all_personas)
    ├── imports src.core.facilitator (FacilitatorAgent)
    └── imports src.core.conversation_logger (ConversationLogger)
```

**Execution Order**:

1. **Load Configuration** (`config.py`)
   - Get mode settings (phases, max_turns, model, etc.)

2. **Load Personas** (`src.core.utils.py::load_all_personas()`)
   - Dynamically load all JSON files from `personas/` directory
   - Create `Persona` instances for each definition
   - Returns: `Dict[str, Persona]`

3. **Initialize Components**
   - Create `FacilitatorAgent` instance
   - Create `ConversationLogger` instance
   - Log session metadata (inspiration, mode, personas)

4. **Define Phases**
   - Filter phases based on mode configuration
   - Apply max_turns_per_phase from config
   - Each phase has: `phase_id`, `goal`, `desired_outcome`, `max_turns`

5. **Call Orchestrator** (`orchestration.py::meeting_facilitator()`)
   - Pass: personas, phases, shared_context, facilitator, logger
   - Returns: final_context with logs and ideas

6. **Extract Ideas** (`extraction.py`)
   - Try direct JSON parsing from decision phase
   - Fallback to `extract_ideas_with_llm()` if parsing fails
   - Returns: List of structured idea dictionaries

7. **Save Logs**
   - Save to `meeting_logs.txt` (backwards compatibility)
   - Logger automatically saves comprehensive logs to `conversation_logs/`

---

#### 3. Orchestration: `src/idea_generation/orchestration.py`

**Function**: `meeting_facilitator()`

**Purpose**: Core conversation loop with facilitator-directed turn-taking

**Module Dependencies**:
```
orchestration.py
    ├── imports prompts.py (generate_dynamic_prompt)
    ├── imports extraction.py (extract_idea_title)
    ├── imports src.core.persona (Persona)
    ├── imports src.core.facilitator (FacilitatorAgent)
    └── imports src.core.conversation_logger (ConversationLogger)
```

**Execution Order** (per phase):

1. **Persona Selection**
   - Facilitator analyzes phase goal
   - Selects 3-6 relevant personas via `facilitator.select_personas_for_phase()`
   - Logs selection decision

2. **Conversation Loop** (until max_turns reached or facilitator signals complete):

   a. **Speaker Selection**
      - Facilitator decides next speaker via `facilitator.decide_next_speaker()`
      - Returns persona name or `None` (phase complete)

   b. **Dynamic Prompt Generation** (`prompts.py::generate_dynamic_prompt()`)
      - Calculate current stage (Problem Discovery → Competitive Landscape → Solution Exploration → Synthesis)
      - Generate stage-specific prompt
      - Returns: Dynamic prompt string

   c. **Persona Response** (`src.core.persona.py::response()`)
      - Persona generates response using their summary + dynamic prompt
      - Returns: `{"response": "...", "tokens_used": ...}`

   d. **Idea Tracking** (`extraction.py::extract_idea_title()`)
      - Extract idea title from response (if present)
      - Add to `shared_context["ideas_discussed"]`
      - Update `shared_context["current_focus"]`

   e. **Summary Updates** (if enabled)
      - All active personas call `persona.update_summary(exchange)`
      - Maintains bounded memory across conversation

   f. **Logging**
      - Log exchange to conversation_logger
      - Add to phase_exchanges and global logs

3. **Phase Completion**
   - Facilitator generates phase summary via `facilitator.summarize_phase()`
   - Log persona summaries and phase summary
   - Repeat for next phase

4. **Return Final Context**
   - Contains: all logs, phase summaries, ideas discussed

---

#### 4. Dynamic Prompt Generation: `src/idea_generation/prompts.py`

**Function**: `generate_dynamic_prompt()`

**Purpose**: Generate stage-specific prompts that guide natural discovery process

**Key Functions**:

1. **`get_stage_info(phase_id, turn_count, max_turns)`**
   - Calculates current stage within phase
   - Maps phase_id to stage names (e.g., ideation → ["Problem Discovery", "Competitive Landscape", ...])
   - Returns: `{"stage_number": 0, "stage_name": "Problem Discovery", "total_stages": 4, "stage_progress": "1/4"}`

2. **`generate_dynamic_prompt(phase, turn_count, phase_exchanges, shared_context)`**
   - Gets stage info
   - Generates prompt based on phase_id and stage_number
   - Includes context from shared_context (inspiration, ideas discussed, current focus)
   - Returns: Formatted prompt string with stage-specific guidance

**Staged Discovery** (Ideation Phase Example):
- **Stage 1** (turns 0-3): Problem Discovery - "Discuss pain points, don't jump to solutions yet"
- **Stage 2** (turns 4-6): Competitive Landscape - "What tools exist? Where are the gaps?"
- **Stage 3** (turns 7-9): Solution Exploration - "Now propose solutions with real-world examples"
- **Stage 4** (turns 10-12): Synthesis - "Consolidate and refine the best ideas"

This prevents personas from rushing to solutions and mimics real brainstorming sessions.

---

#### 5. Core Components

##### `src/core/persona.py`

**Class**: `Persona`

**Purpose**: Individual AI agent with role-specific behavior and hybrid memory

**Key Methods**:
- `__init__(definition, model_name)`: Initialize from JSON definition
- `response(context)`: Generate response using summary + context
- `update_summary(exchange)`: Incrementally update hybrid summary
- `_format_recent_exchanges(exchanges)`: Format recent discussion for context

**Hybrid Memory System**:
```python
self.summary = {
    "objective_facts": [
        "Fact 1",
        "Fact 2"
    ],
    "subjective_notes": {
        "key_concerns": ["Concern 1"],
        "priorities": ["Priority 1"],
        "opinions": ["Opinion 1"]
    }
}
```

**Benefits**:
- Constant token usage (bounded memory)
- Mimics human memory (selective, biased)
- Enables long conversations without token explosion

##### `src/core/facilitator.py`

**Class**: `FacilitatorAgent`

**Purpose**: Meta-agent that orchestrates conversation flow

**Key Methods**:
- `select_personas_for_phase(phase, available_personas)`: Choose relevant personas for phase
- `decide_next_speaker(phase, active_personas, recent_exchanges, shared_context, turn_count, max_turns)`: Select next speaker
- `summarize_phase(phase, exchanges, shared_context)`: Create phase summary

**Intelligence**:
- Considers phase goals when selecting personas
- Analyzes recent exchanges to decide who should speak next
- Creates concise summaries at phase boundaries

##### `src/core/conversation_logger.py`

**Class**: `ConversationLogger`

**Purpose**: Comprehensive multi-format logging system

**Output Files** (per session in `conversation_logs/session_YYYYMMDD_HHMMSS/`):
1. `full_conversation.json` - Complete structured log
2. `persona_summaries.json` - Persona memories at each phase
3. `phase_summaries.txt` - Human-readable phase summaries
4. `facilitator_decisions.json` - All facilitator decisions
5. `session_metadata.json` - Run configuration and results
6. `readable_transcript.md` - **Most readable** - Markdown transcript with 100-char line wrapping

**Key Methods**:
- `log_exchange(phase_id, turn, speaker, archetype, content)`
- `log_persona_summaries(phase_id, personas)`
- `log_phase_summary(phase_id, summary)`
- `log_facilitator_decision(decision_type, phase_id, decision, reasoning)`
- `log_metadata(key, value)`
- `save_all()` - Write all logs to disk

##### `src/core/utils.py`

**Function**: `load_all_personas(directory, model_name)`

**Purpose**: Dynamic persona loading from JSON files

**Process**:
1. Scan `personas/` directory for `*.json` files
2. Load each JSON file
3. Create `Persona` instance from definition
4. Return dictionary mapping persona names to instances

**Benefits**:
- Add new personas without code changes
- Easy to customize persona behavior via JSON
- Consistent loading mechanism

---

#### 6. Configuration: `src/idea_generation/config.py`

**Purpose**: Centralized mode configurations

**Key Exports**:
- `MODEL`: Default model (e.g., "gpt-5-mini")
- `MODE_CONFIGS`: Dictionary of mode settings

**Mode Structure**:
```python
{
    "phases": ["ideation", "research", "critique", "decision"],
    "max_turns_per_phase": 5,
    "model": "gpt-4o-mini",
    "enable_summary_updates": True,
    "description": "Balanced run (3-5 min, moderate cost)"
}
```

**Available Modes**:
- `fast`: Quick test (1-2 min, 2 phases, 3 turns, gpt-3.5-turbo)
- `medium`: **Default** (3-5 min, 4 phases, 5 turns, gpt-4o-mini)
- `standard`: Comprehensive (30-60 min, 7 phases, 8 turns, gpt-4o-mini)
- `deep`: Deep exploration (60-90 min, 7 phases, 15 turns, gpt-5-mini)

---

#### 7. Extraction: `src/idea_generation/extraction.py`

**Purpose**: Extract structured ideas from conversation

**Key Functions**:

1. **`extract_idea_title(content)`**
   - Extracts idea title from persona response
   - Looks for patterns like `**Title:** ...` or `Title: ...`
   - Used for real-time idea tracking during conversation
   - Returns: Title string or empty string

2. **`extract_ideas_with_llm(logs, number_of_ideas, model_name)`**
   - Fallback when JSON parsing fails
   - Uses LLM to read conversation and extract structured ideas
   - Enforces JSON output format via `response_format={"type": "json_object"}`
   - Returns: List of idea dictionaries with all required fields

**Extraction Strategy**:
1. **Try direct JSON parsing** from decision phase
2. **Check shared_context** for ideas added during conversation
3. **Fallback to LLM extraction** if above fail
4. **Warn user** if all methods fail

---

## Module Overview

### Core Modules (`src/core/`)

| Module | Purpose | Key Classes/Functions | Dependencies |
|--------|---------|----------------------|--------------|
| `persona.py` | AI persona with memory | `Persona` class | OpenAI API |
| `facilitator.py` | Conversation orchestration | `FacilitatorAgent` class | OpenAI API |
| `conversation_logger.py` | Multi-format logging | `ConversationLogger` class | pathlib, datetime |
| `utils.py` | Helper functions | `load_all_personas()` | persona.py |

### Idea Generation Modules (`src/idea_generation/`)

| Module | Purpose | Key Functions | Dependencies |
|--------|---------|---------------|--------------|
| `generator.py` | Main entry point | `multiple_llm_idea_generator()` | All other modules |
| `config.py` | Mode configurations | `MODE_CONFIGS` dict | None |
| `prompts.py` | Dynamic prompt generation | `generate_dynamic_prompt()`, `get_stage_info()` | None |
| `orchestration.py` | Meeting facilitation | `meeting_facilitator()` | prompts, extraction, core modules |
| `extraction.py` | Idea extraction | `extract_idea_title()`, `extract_ideas_with_llm()` | OpenAI API |

### Stage Modules (`src/stages/`)

| Module | Purpose | Key Functions | Dependencies |
|--------|---------|---------------|--------------|
| `spec_generation.py` | Generate Base44 spec | `make_initial_prompt()` | OpenAI API |
| `design_generation.py` | Base44 automation | `create_initial_design()` | Playwright |

---

## Data Flow

### Stage 1: Idea Generation

```
User Input (INSPIRATION)
    ↓
[Load Personas] → Dict[str, Persona]
    ↓
[Initialize Facilitator & Logger]
    ↓
[Define Phases] → List[Phase]
    ↓
[Meeting Facilitator Loop]
    ├── For each phase:
    │   ├── Select personas → List[Persona]
    │   ├── For each turn:
    │   │   ├── Generate dynamic prompt → str
    │   │   ├── Facilitator selects speaker → Persona
    │   │   ├── Persona generates response → str
    │   │   ├── Extract idea title (if present)
    │   │   ├── Update all persona summaries
    │   │   └── Log exchange
    │   └── Generate phase summary
    └── Return final_context
    ↓
[Extract Ideas]
    ├── Try JSON parsing
    ├── Check shared_context
    └── Fallback: LLM extraction
    ↓
[Save Logs]
    ├── meeting_logs.txt
    └── conversation_logs/session_*/
    ↓
Return: List[Dict] (ideas)
```

### Shared Context Evolution

```python
# Initial
shared_context = {
    "user_prompt": "...",
    "original_prompt": "...",
    "inspiration": "...",
    "number_of_ideas": 1,
    "ideas": [],
    "ideas_discussed": [],
    "current_focus": None
}

# During conversation
shared_context["ideas_discussed"] = ["Idea A", "Idea B", "Idea C"]
shared_context["current_focus"] = "Idea B"

# After extraction
shared_context["ideas"] = [
    {
        "title": "Idea B",
        "description": "...",
        "target_users": "...",
        # ... full structure
    }
]
```

---

## Key Design Patterns

### 1. Staged Discovery Pattern

**Problem**: Personas rush to solutions without exploring problem space

**Solution**: Multi-stage prompts that guide natural progression
- Stage 1: Problem Discovery
- Stage 2: Competitive Landscape
- Stage 3: Solution Exploration
- Stage 4: Synthesis

**Implementation**: `prompts.py::get_stage_info()` + `generate_dynamic_prompt()`

### 2. Hybrid Memory Pattern

**Problem**: Full conversation history causes token explosion

**Solution**: Bounded summary with objective facts + subjective notes
- Personas maintain summaries instead of full history
- Constant token usage regardless of conversation length
- Mimics human memory (selective, biased)

**Implementation**: `persona.py::summary` + `update_summary()`

### 3. Facilitator Orchestration Pattern

**Problem**: Hardcoded turn-taking doesn't adapt to conversation needs

**Solution**: Meta-agent decides who speaks based on context
- Analyzes phase goals
- Considers recent exchanges
- Ensures balanced participation

**Implementation**: `facilitator.py::FacilitatorAgent`

### 4. LLM Extraction Fallback Pattern

**Problem**: Forcing JSON output constrains natural conversation

**Solution**: Let personas talk naturally, extract structure afterward
- Personas focus on discussion quality
- Single extraction call at end
- Robust to format variations

**Implementation**: `extraction.py::extract_ideas_with_llm()`

### 5. Modular Configuration Pattern

**Problem**: Hard to experiment with different conversation settings

**Solution**: Centralized mode configurations
- Easy to add new modes
- Clear trade-offs (time vs quality vs cost)
- Mode can be selected at runtime

**Implementation**: `config.py::MODE_CONFIGS`

---

## Extension Points

### Adding New Personas

1. Create `personas/new_persona.json`
2. Define: Name, Archetype, Purpose, Deliverables, Strengths, Watch-out
3. Personas load automatically on next run

### Adding New Phases

1. Edit `generator.py::all_phases`
2. Add phase definition with: phase_id, goal, desired_outcome
3. Update `MODE_CONFIGS` to include new phase
4. Optionally add phase-specific prompts in `prompts.py`

### Adding New Stages (to phases)

1. Edit `prompts.py::get_stage_info()` phase_stages mapping
2. Add stage names for new phase
3. Add stage-specific prompts in `generate_dynamic_prompt()`

### Customizing Logging

1. Extend `ConversationLogger` class
2. Add new output format method
3. Call in `save_all()`

---

## Performance Characteristics

### Token Usage

**Per Turn** (approximate):
- Persona response: 1,000-2,000 tokens
- Summary update: 500-1,000 tokens per persona
- Facilitator decisions: 200-500 tokens

**Total** (medium mode, 4 phases, 5 turns/phase):
- 20 persona responses: ~30,000 tokens
- 100 summary updates (5 personas × 5 turns × 4 phases): ~75,000 tokens
- 20 facilitator decisions: ~8,000 tokens
- **Total**: ~115,000 tokens (~$0.10 at gpt-4o-mini pricing)

### Time Complexity

**Bottleneck**: Summary updates
- 5 personas × 5 turns × 4 phases = 100 LLM calls
- Each call: 2-5 seconds
- **Total**: 200-500 seconds (3-8 minutes)

**Optimization**: Disable summary updates in fast mode
- `enable_summary_updates: False`
- Reduces time from 7.5 min → 90 sec (5x speedup)
- Trade-off: Personas lose long-term memory

---

## Testing Strategy

### Unit Tests

- `tests/test_persona_class.py` - Test Persona class in isolation
- Test individual modules with mocked dependencies

### Integration Tests

- Run full pipeline with fast mode
- Verify logs are created correctly
- Check idea extraction works

### Manual Testing

```bash
# Test fast mode (90 seconds)
python main.py --mode fast

# Inspect logs
cat conversation_logs/session_*/readable_transcript.md

# Verify ideas extracted
cat conversation_logs/session_*/session_metadata.json
```

---

**Last Updated**: October 27, 2025
**Version**: 2.0 (Modular Refactor)
