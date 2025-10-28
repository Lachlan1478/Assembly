# Assembly Framework

**Multi-Persona Conversation Orchestration Framework**

A Python framework for creating structured conversations between AI personas with facilitator-directed turn-taking, hybrid memory systems, and comprehensive logging.

## Overview

Assembly Framework enables complex multi-perspective discussions by orchestrating conversations between specialized AI personas. Each persona maintains their own perspective through a hybrid memory system, while a facilitator manages the conversation flow intelligently.

## Key Features

- **Persona Class**: AI agents with role-specific behavior and bounded memory
  - Hybrid memory (objective facts + subjective notes)
  - Incremental summary updates
  - Prevents token explosion in long conversations

- **Facilitator Agent**: Meta-agent that orchestrates conversations
  - Dynamic persona selection based on phase goals
  - Context-aware speaker selection
  - Phase summarization

- **Conversation Logger**: Multi-format comprehensive logging
  - 6 output formats (JSON, Markdown, plain text)
  - Timestamped session folders
  - Human-readable transcripts with text wrapping

- **Persona Loading**: Dynamic persona loading from JSON definitions
  - No code changes needed to add new personas
  - Flexible persona configuration

## Quick Start

```python
from framework import Persona, FacilitatorAgent, ConversationLogger
from framework import load_personas_from_directory

# 1. Load personas from JSON definitions
personas = load_personas_from_directory("personas")

# 2. Create facilitator to manage conversation
facilitator = FacilitatorAgent(model_name="gpt-4o-mini")

# 3. Create logger for comprehensive logging
logger = ConversationLogger(base_dir="conversation_logs")

# 4. Define conversation phase
phase = {
    "phase_id": "design_review",
    "goal": "Review the UX design for our mobile app",
    "desired_outcome": "List of design improvements",
    "max_turns": 5
}

# 5. Select relevant personas
selected_personas = facilitator.select_personas_for_phase(
    phase=phase,
    available_personas=personas
)

# 6. Run conversation loop
# (See examples/ for complete orchestration pattern)
```

## Core Concepts

### Persona

A Persona is an AI agent with specific role, expertise, and memory:

```python
persona = Persona(
    definition={
        "Name": "Product Designer",
        "Archetype": "UX advocate",
        "Purpose": "Ensure user-centric design",
        # ... more fields
    },
    model_name="gpt-4o-mini"
)

# Generate response
response = persona.response({
    "user_prompt": "Review this design...",
    "phase": {"phase_id": "design_review"},
    "shared_context": {}
})

# Update summary after each exchange
persona.update_summary({
    "speaker": "Engineer",
    "content": "The design looks good but...",
    "phase": "design_review"
})
```

### Hybrid Memory System

Personas maintain bounded summaries instead of full conversation history:

```python
persona.summary = {
    "objective_facts": [
        "The app targets mobile users",
        "Primary action is booking appointments"
    ],
    "subjective_notes": {
        "key_concerns": ["Accessibility for elderly users"],
        "priorities": ["Simple navigation"],
        "opinions": ["Current flow is too complex"]
    }
}
```

**Benefits**:
- Constant token usage (no explosion over time)
- Mimics human selective memory
- Enables long multi-phase conversations

### Facilitator Agent

The facilitator orchestrates conversation flow:

```python
facilitator = FacilitatorAgent(model_name="gpt-4o-mini")

# Select personas for a phase
selected = facilitator.select_personas_for_phase(
    phase={"phase_id": "design_review", "goal": "..."},
    available_personas=all_personas
)

# Decide who speaks next
next_speaker = facilitator.decide_next_speaker(
    phase=phase,
    active_personas=selected,
    recent_exchanges=history,
    turn_count=3,
    max_turns=5
)

# Summarize phase
summary = facilitator.summarize_phase(
    phase=phase,
    exchanges=phase_exchanges,
    shared_context=shared_context
)
```

## Use Cases

### 1. Startup Idea Generation
Multiple personas (founder, designer, researcher, engineer, CFO) collaborate to generate and validate startup ideas.

### 2. Design Reviews
Designers, engineers, and product managers review and critique design proposals.

### 3. Technical Decision-Making
Engineers and architects debate technical approaches for complex problems.

### 4. Strategic Planning
Business leaders discuss and decide on strategic initiatives.

### 5. Research Synthesis
Researchers from different disciplines synthesize findings.

### 6. Code Reviews
Developers review code changes from multiple perspectives (security, performance, maintainability).

## Persona Definitions

Personas are defined in JSON files:

```json
{
  "Name": "Product Designer",
  "Archetype": "UX advocate and craft simplifier",
  "Purpose": "Ensure user-centric, intuitive design",
  "Deliverables": "UX flows, design principles, usability feedback",
  "Strengths": "User empathy, visual thinking, simplification",
  "Watch-out": "May over-prioritize aesthetics vs. technical feasibility"
}
```

Place JSON files in `personas/` directory and they load automatically.

## Architecture

### Token Efficiency

The framework is designed for long conversations without token explosion:

- **Bounded Memory**: Personas maintain summaries, not full history
- **Incremental Updates**: Summaries updated after each exchange
- **Constant Token Usage**: Each persona response uses ~same tokens regardless of conversation length

### Conversation Flow

```
1. Facilitator selects relevant personas for phase
2. For each turn:
   a. Facilitator decides next speaker
   b. Speaker generates response using their summary
   c. All personas update summaries
   d. Exchange logged
3. Facilitator summarizes phase
4. Repeat for next phase
```

## Examples

See `framework/examples/` for complete working examples:
- `basic_conversation.py` - Simple 3-persona discussion
- `design_review.py` - Product design review workflow

## API Reference

### Persona
- `__init__(definition, model_name)` - Create persona from definition dict
- `from_file(file_path, model_name)` - Load persona from JSON
- `response(context)` - Generate response given context
- `update_summary(exchange)` - Update memory after exchange

### FacilitatorAgent
- `__init__(model_name)` - Create facilitator
- `select_personas_for_phase(phase, available_personas)` - Select relevant personas
- `decide_next_speaker(...)` - Choose who speaks next
- `summarize_phase(phase, exchanges, shared_context)` - Create phase summary

### ConversationLogger
- `__init__(base_dir)` - Create logger with output directory
- `log_exchange(...)` - Log a conversation exchange
- `log_persona_summaries(phase_id, personas)` - Log persona memory states
- `log_phase_summary(phase_id, summary)` - Log phase summary
- `save_all()` - Write all logs to disk (6 formats)

### Helpers
- `load_personas_from_directory(directory, model_name)` - Load all personas from folder
- `format_summary_for_prompt(summary)` - Format summary for LLM prompts

## License

[Your License Here]

## Contributing

This framework is extracted from the Assembly project. Contributions welcome!

---

**Version**: 0.1.0
