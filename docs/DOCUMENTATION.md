# Assembly Documentation

**AI-Powered Startup Idea Generator using Multi-Persona Conversations**

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [Architecture](#architecture)
4. [Run Modes](#run-modes)
5. [How It Works](#how-it-works)
6. [Output Files](#output-files)
7. [Configuration](#configuration)
8. [Development Guide](#development-guide)
9. [Performance & Cost](#performance--cost)
10. [Troubleshooting](#troubleshooting)

---

## Overview

Assembly is an AI-powered system that generates validated startup ideas through simulated multi-persona conversations. Instead of a single LLM call, Assembly orchestrates a team of AI personas (founder, designer, market researcher, etc.) who discuss, challenge, and refine ideas through structured phases.

### Key Features

- **Multi-Persona Architecture**: 7 distinct personas with specialized roles
- **Facilitator-Directed Conversations**: AI facilitator manages discussion flow
- **Hybrid Memory System**: Personas maintain summaries instead of full conversation history
- **4 Run Modes**: Fast/Medium/Standard/Deep for different use cases
- **Comprehensive Logging**: Human-readable transcripts and structured JSON outputs
- **LLM Extraction Fallback**: Robust idea capture regardless of format

---

## Quick Start

### Installation

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd Assembly

# 2. Install dependencies
pip install openai python-dotenv

# 3. Set up environment
cp .env.example .env
# Edit .env and add your OpenAI API key

# 4. Run your first idea generation
python main.py --mode medium
```

### Your First Idea

```bash
# Generate a startup idea (default: medium mode, ~3-5 min)
python main.py

# Quick test (90 seconds)
python main.py --mode fast

# Deep validation (30-60 min)
python main.py --mode standard
```

---

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                              │
│                    (Entry Point & CLI)                       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│              idea_brainstorm_01.py                           │
│         (Multi-Persona Idea Generator)                       │
│  • MODE_CONFIGS (fast/medium/standard/deep)                  │
│  • meeting_facilitator() - Core orchestration                │
│  • extract_ideas_with_llm() - Fallback extraction            │
└───────┬─────────────────────────────┬───────────────────────┘
        │                             │
        ▼                             ▼
┌──────────────────┐         ┌──────────────────────┐
│  facilitator.py  │         │     persona.py       │
│                  │         │                      │
│ FacilitatorAgent │         │  Persona class       │
│ • select_personas│         │  • response()        │
│ • decide_speaker │         │  • update_summary()  │
│ • summarize()    │         │  • hybrid memory     │
└──────────────────┘         └──────────────────────┘
        │                             │
        └──────────────┬──────────────┘
                       │
                       ▼
            ┌─────────────────────┐
            │ conversation_logger  │
            │                      │
            │ ConversationLogger   │
            │ • Text wrapping      │
            │ • 6 output formats   │
            │ • Timestamped logs   │
            └─────────────────────┘
```

### Core Classes

#### `Persona` (persona.py)
Represents a single AI persona with:
- **Role & Archetype**: Defines expertise and thinking style
- **Hybrid Summary**: Maintains `objective_facts` + `subjective_notes`
- **Response Generation**: Creates contextual responses
- **Summary Updates**: Incrementally updates understanding

#### `FacilitatorAgent` (facilitator.py)
Meta-agent that orchestrates the conversation:
- **Persona Selection**: Chooses 3-6 relevant personas per phase
- **Speaker Selection**: Decides who speaks next based on context
- **Phase Summarization**: Creates summaries at phase boundaries

#### `ConversationLogger` (conversation_logger.py)
Comprehensive logging system:
- **6 Output Formats**: JSON, markdown, text
- **Text Wrapping**: 100-char line wrapping for readability
- **Timestamped Sessions**: Each run gets unique folder

---

## Run Modes

Assembly offers 4 run modes optimized for different scenarios:

### Fast Mode
**Best for**: Quick prototyping, throwaway ideas

```bash
python main.py --mode fast
```

- **Duration**: 1-2 minutes
- **Phases**: 2 (ideation, decision)
- **Turns per phase**: 3
- **Model**: gpt-3.5-turbo
- **Summary updates**: Disabled (speed optimization)
- **Output**: 1 basic idea

**Use when**: You need rough ideas quickly, exploring a domain

---

### Medium Mode ⭐ (Default)
**Best for**: Daily ideation work, real product development

```bash
python main.py --mode medium
# or just
python main.py
```

- **Duration**: 3-5 minutes
- **Phases**: 4 (ideation, research, critique, decision)
- **Turns per phase**: 5
- **Model**: gpt-4o-mini
- **Summary updates**: Enabled
- **Output**: 1 well-validated idea

**Use when**: Building real products, need market validation + risk assessment

**Why it's the default**:
- Adds critical research & critique phases
- 5x longer than fast, but 7x faster than standard
- Produces noticeably better ideas than fast mode
- Perfect balance of quality and speed

---

### Standard Mode
**Best for**: Investor pitches, comprehensive validation

```bash
python main.py --mode standard
```

- **Duration**: 30-60 minutes
- **Phases**: 7 (ideation, design, research, feasibility, financials, critique, decision)
- **Turns per phase**: 8
- **Model**: gpt-4o-mini
- **Summary updates**: Enabled
- **Output**: 5 thoroughly vetted ideas

**Use when**: Need multiple options, preparing investor presentations, deep market analysis

**Trade-offs**:
- 7x more time than medium mode
- Explores 30-40 concept variations
- Marginal quality improvement over medium for single ideas

---

### Deep Mode
**Best for**: Academic research, novel domains

```bash
python main.py --mode deep
```

- **Duration**: 60-90 minutes
- **Phases**: 7 (all phases)
- **Turns per phase**: 15
- **Model**: gpt-5-mini (most capable)
- **Summary updates**: Enabled
- **Output**: 5+ deeply explored ideas

**Use when**: Researching novel spaces, need extreme thoroughness, cost is not a concern

---

## How It Works

### The Multi-Persona Process

#### Phase 1: Persona Selection
```python
# Facilitator analyzes phase goal and selects relevant personas
selected = facilitator.select_personas_for_phase(
    phase={"phase_id": "ideation", "goal": "Generate startup ideas"},
    available_personas=all_personas
)
# Returns: ["founder_visionary", "product_designer", "market_researcher"]
```

#### Phase 2: Conversation Loop
```
For each turn (up to max_turns_per_phase):
  1. Facilitator decides next speaker
  2. Speaker generates response using their summary
  3. All personas update their summaries
  4. Repeat until phase complete or max turns reached
```

#### Phase 3: Idea Extraction
```python
# Try direct JSON parsing first
business_ideas = extract_json_from_text(conversation)

# Fallback: LLM extraction if parsing fails
if not business_ideas:
    business_ideas = extract_ideas_with_llm(
        logs=conversation_logs,
        number_of_ideas=1
    )
```

### Available Personas

Located in `personas/` directory:

| Persona | Role | Key Contribution |
|---------|------|------------------|
| **Founder - Visionary** | Bold dreamer | Big vision, inspiring narratives |
| **Product Designer - UX** | Craft simplifier | User experience, clarity |
| **Market Researcher - Growth PM** | Analytical connector | TAM/SAM, competitive analysis |
| **Tech Lead - Architect** | Pragmatic builder | Feasibility, architecture |
| **CFO - Business Strategist** | Financial rationalist | Unit economics, sustainability |
| **Contrarian - Devil's Advocate** | Skeptical challenger | Risk identification, stress-testing |
| **Facilitator - Orchestrator** | Process manager | Synthesis, balanced participation |

### Conversation Phases

| Phase | Goal | Key Questions Answered |
|-------|------|----------------------|
| **Ideation** | Generate concepts | What problems can we solve? |
| **Design** | Refine UX | How will users interact? |
| **Research** | Validate market | Is there demand? Who are competitors? |
| **Feasibility** | Assess technical | Can we build this? What are risks? |
| **Financials** | Model business | How do we make money? What's the cost? |
| **Critique** | Stress-test | What can go wrong? What are we missing? |
| **Decision** | Consolidate | Which idea(s) should we pursue? |

---

## Output Files

Every run creates a timestamped session folder in `conversation_logs/`:

```
conversation_logs/
└── session_20251026_193136/
    ├── full_conversation.json      # All exchanges with metadata
    ├── persona_summaries.json      # Persona memories at each phase
    ├── phase_summaries.txt         # Human-readable phase summaries
    ├── facilitator_decisions.json  # Speaker selections & reasoning
    ├── session_metadata.json       # Run config, timing, final ideas
    └── readable_transcript.md      # **START HERE** - Formatted conversation
```

### Recommended Reading Order

1. **readable_transcript.md** - Human-friendly overview with wrapped text
2. **session_metadata.json** - Check final ideas and metadata
3. **phase_summaries.txt** - Quick summary of each phase
4. **facilitator_decisions.json** - Understand facilitator's reasoning
5. **persona_summaries.json** - See how personas' understanding evolved
6. **full_conversation.json** - Complete detailed record

### Example: readable_transcript.md

```markdown
# Conversation Transcript

**Session**: 20251026_193136

**Inspiration**:
```
Domain: Software development workflows and code review
Target users: Engineering teams at startups and scale-ups (5-50 engineers)
...
```

---

## Phase: IDEATION

*During the ideation phase, five distinct startup ideas were generated...*

### Turn 0: Founder — Visionary — Bold dreamer and storyteller

I am excited to dive into this challenge of generating a unique startup idea
in the realm of software development workflows and code review for engineering
teams at startups and scale-ups. Let's think outside the box and come up with
an idea that truly disrupts the existing landscape...

---
```

---

## Configuration

### Environment Variables

Create a `.env` file (copy from `.env.example`):

```bash
# Required: OpenAI API Key
OPENAI_API_KEY=sk-proj-your-key-here

# Optional: Default run mode
ASSEMBLY_MODE=medium

# Stage 3 (Base44) - Not currently used
BASE44_URL=https://app.base44.com
BASE44_BROWSER_CHANNEL=msedge
BASE44_USER_DATA_DIR=C:\Users\User\EdgePW
BASE44_PROFILE_DIR=Default
```

### Customizing Inspiration

Edit `main.py` to change the inspiration prompt:

```python
INSPIRATION = """
    Domain: Your domain here
    Target users: Who will use this?
    Primary outcome: What value does it deliver?
    Constraints: What limitations exist?
    UX rules: How should it feel?
"""
```

### Adding New Personas

1. Create `personas/new_persona.json`:

```json
{
  "name": "Your Persona Name",
  "archetype": "Short description of thinking style",
  "system_prompt": "You are a [role]...",
  "context_instructions": "When responding...",
  "summary_instructions": "When updating summaries...",
  "lead_role": "ideation",
  "allowed_phases": ["ideation", "research"]
}
```

2. Run Assembly - new persona loads automatically!

---

## Development Guide

### Project Structure

```
Assembly/
├── main.py                          # Entry point & CLI
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
│   │   ├── generator.py            # Main entry point
│   │   ├── config.py               # Mode configurations
│   │   ├── prompts.py              # Dynamic prompt generation with staging
│   │   ├── orchestration.py       # Meeting facilitation logic
│   │   └── extraction.py           # Idea extraction utilities
│   └── stages/                      # Pipeline stages
│       ├── __init__.py
│       ├── spec_generation.py      # Stage 2: Spec generation
│       └── design_generation.py    # Stage 3: Base44 automation
├── docs/                            # Documentation
│   ├── ARCHITECTURE.md             # Technical architecture & execution order
│   ├── DOCUMENTATION.md            # This file - user guide
│   ├── CLAUDE.md                   # Development context for AI assistants
│   └── CONVERSATION_FLOW_ANALYSIS.md
├── personas/                        # Persona definitions (JSON)
│   ├── founder.json
│   ├── product_designer.json
│   └── ...
├── tests/                          # Test scripts
│   ├── test_persona_class.py
│   └── test_base_44_automation/
├── outputs/                        # Runtime output files
│   └── .gitkeep
├── conversation_logs/              # Generated conversation logs
├── archive/                        # Legacy/reference code
├── .env                            # Your API keys (gitignored)
├── .env.example                   # Template
└── README.md                      # Project overview
```

For detailed technical architecture and script execution order, see [ARCHITECTURE.md](ARCHITECTURE.md).

### Key Design Patterns

#### 1. Hybrid Summary System
Instead of passing full conversation history:

```python
# Persona maintains bounded summary
self.summary = {
    "objective_facts": [
        "CodeSync focuses on real-time collaboration",
        "Target users are 5-50 engineer teams"
    ],
    "subjective_notes": {
        "key_concerns": ["Data privacy with code access"],
        "priorities": ["Seamless GitHub integration"],
        "opinions": ["AI should augment, not replace humans"]
    }
}

# Updates incrementally
persona.update_summary(new_exchange)
```

**Benefits**:
- Constant token usage per response
- Mimics human memory (selective, biased)
- Prevents token explosion

#### 2. Facilitator Orchestration
Meta-agent decides who speaks when:

```python
# Select relevant personas per phase
personas = facilitator.select_personas_for_phase(phase, all_personas)

# Decide next speaker based on context
next_speaker = facilitator.decide_next_speaker(
    phase=phase,
    active_personas=personas,
    recent_exchanges=history,
    turn_count=current_turn
)
```

**Benefits**:
- Dynamic participation (not hardcoded)
- Context-aware speaker selection
- Natural conversation flow

#### 3. LLM Extraction Fallback
Separate conversation from extraction:

```python
# Personas talk naturally
conversation_logs = meeting_facilitator(...)

# Extract structure afterward
try:
    ideas = parse_json(conversation_logs)
except:
    ideas = extract_ideas_with_llm(conversation_logs)
```

**Benefits**:
- No format constraints during ideation
- Robust to persona variations
- Single extraction call vs forcing JSON every turn

### Adding a New Phase

1. Edit `MODE_CONFIGS` in `idea_brainstorm_01.py`:

```python
"custom": {
    "phases": ["ideation", "your_new_phase", "decision"],
    "max_turns_per_phase": 5,
    ...
}
```

2. Define phase in `multiple_llm_idea_generator()`:

```python
all_phases = [
    ...
    {
        "phase_id": "your_new_phase",
        "goal": "What should this phase accomplish?",
        "desired_outcome": "Specific deliverable"
    }
]
```

3. Run with custom mode!

---

## Performance & Cost

### Actual Performance Data

Based on real runs with developer tools inspiration:

| Mode | Duration | Exchanges | API Calls* | Est. Cost** |
|------|----------|-----------|------------|-------------|
| Fast | 90 sec | 6 | ~10 | $0.01 |
| Medium | 7.5 min | 20 | ~100 | $0.10 |
| Standard | 52 min | 56 | ~400 | $0.50 |
| Deep | ~90 min | ~100 | ~700 | $1.00 |

\* Includes persona responses + summary updates + facilitator decisions
\** Estimated using gpt-4o-mini pricing ($0.150/1M input, $0.600/1M output tokens)

### Cost Optimization Tips

1. **Use medium mode by default** - best quality/cost ratio
2. **Disable summary updates for testing** - set `enable_summary_updates: False`
3. **Reduce turns per phase** - adjust `max_turns_per_phase`
4. **Use faster models** - switch to gpt-3.5-turbo for prototyping

### Performance Bottlenecks

**Summary Updates** are the main bottleneck:
- 5 personas × 5 turns × 4 phases = 100 LLM calls just for summaries
- Each call takes 2-5 seconds

**Why we keep them**:
- Maintains context across long conversations
- Enables personas to remember key insights
- Prevents token explosion
- Worth it for medium+ modes

---

## Troubleshooting

### Common Issues

#### "No ideas could be extracted from conversation"

**Cause**: Personas didn't format output as JSON, and extraction fallback failed.

**Fix**: This should be rare now with LLM extraction fallback. If it happens:
1. Check `conversation_logs/*/readable_transcript.md` - were ideas discussed?
2. Try running again (LLMs have variance)
3. Increase `max_turns_per_phase` for more refinement time

#### "Unicode encoding error"

**Cause**: Windows console can't display certain characters.

**Fix**: Already fixed in current code - we use ASCII-safe characters. If you see this, you're running old code.

#### Standard mode takes too long

**Solution**: Use medium mode! It's the recommended default for 95% of use cases.

#### Personas generating too many similar ideas

**Observation**: Standard mode explored 40+ concept variations, many redundant.

**Why**: More turns = more exploration, but diminishing returns.

**Solution**:
- Use medium mode for single best idea
- Use standard mode when you want multiple options to choose from
- Consider adding convergence detection (future feature)

### Debug Tips

1. **Check facilitator decisions**:
```bash
cat conversation_logs/session_*/facilitator_decisions.json
```

2. **Review persona summaries**:
```bash
cat conversation_logs/session_*/persona_summaries.json
```

3. **Read full conversation**:
```bash
code conversation_logs/session_*/readable_transcript.md
```

4. **Test with fast mode first**:
```bash
python main.py --mode fast
```

---

## Roadmap & Future Enhancements

### Planned Features

- [ ] **Convergence Detection**: Stop early when ideas stabilize
- [ ] **Cost Tracking**: Real-time token usage and cost display
- [ ] **Batch Summary Updates**: Update summaries in batch vs per-turn
- [ ] **Custom Phase Templates**: Predefined phase combinations
- [ ] **Idea Scoring**: Automatic ranking of generated ideas
- [ ] **Web Interface**: Browser-based UI for Assembly
- [ ] **Streaming Responses**: Real-time conversation display
- [ ] **Multi-Domain Presets**: Quick starts for common domains

### Framework Extraction (Potential Pivot)

The core multi-persona framework could be extracted for general use:

```python
from assembly_framework import MultiPersonaConversation

conversation = MultiPersonaConversation(
    personas=["expert_a", "expert_b", "critic"],
    phases=["brainstorm", "critique", "decide"],
    goal="Solve problem X"
)

result = conversation.run()
```

This would enable:
- Design reviews
- Technical decision-making
- Strategic planning
- Research synthesis
- Any domain requiring multiple perspectives

---

## Credits & Acknowledgments

### Inspiration for Personas

- **Founder - Visionary**: Brian Chesky (Airbnb), Reid Hoffman (LinkedIn)
- **Product Designer**: Dylan Field (Figma), Julie Zhuo, Airbnb design team
- **Market Researcher**: Growth PM best practices, investor-level rigor
- **Tech Lead**: Patrick Collison (Stripe), pragmatic builders
- **CFO**: Sequoia-backed CFOs, early-stage finance operators
- **Contrarian**: Paul Graham's essays, Ben Horowitz's pragmatism
- **Facilitator**: Sheryl Sandberg, design sprint moderators

### Technologies

- **OpenAI GPT Models**: gpt-3.5-turbo, gpt-4o-mini, gpt-5-mini
- **Python Libraries**: openai, python-dotenv, textwrap
- **Logging**: Custom ConversationLogger with JSON/Markdown output

---

## Contributing

### How to Contribute

1. **Add Personas**: Create new persona definitions in `personas/`
2. **Optimize Performance**: Improve summary update efficiency
3. **Add Features**: Implement items from the roadmap
4. **Report Issues**: Document bugs or unexpected behavior
5. **Share Results**: Post interesting ideas generated by Assembly

### Coding Standards

- Use type hints for new functions
- Add docstrings to all classes and public methods
- Follow existing code structure
- Test with fast mode before submitting

---

## License

[Your License Here]

---

## Contact & Support

- **Issues**: [GitHub Issues URL]
- **Discussions**: [GitHub Discussions URL]
- **Email**: [Your Email]

---

**Last Updated**: October 26, 2025
**Version**: 1.0 (Medium Mode Release)
