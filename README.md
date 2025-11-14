# Assembly

**AI-Powered Startup Idea Generator using Multi-Persona Conversations**

Assemble Apps/SaaS from idea in minutes using collaborative AI personas that brainstorm, validate, and refine startup ideas through structured conversations.

## Quick Start

```bash
# Install dependencies
pip install openai python-dotenv

# Set up environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run idea generation
python main.py --mode medium
```

## Features

- **Multi-Persona Architecture**: 7 distinct AI personas (Founder, Designer, Researcher, Tech Lead, CFO, Contrarian, Facilitator) collaborate to generate ideas
- **Staged Discovery Process**: Guides personas from problem exploration → competitive analysis → solution synthesis (mimics real brainstorming)
- **Facilitator-Directed Conversations**: AI facilitator intelligently manages discussion flow and speaker selection
- **Enhanced Idea Tracking**: Rich context tracking with status management (in_play/rejected), rejection reasoning, and evolution tracking prevents redundant discussion
- **Hybrid Memory System**: Personas maintain bounded summaries for efficient long-term conversations
- **4 Run Modes**: Fast (90s), Medium (3-5min), Standard (30-60min), Deep (60-90min)
- **Comprehensive Logging**: Human-readable transcripts + structured JSON outputs

## Run Modes

- **Fast**: Quick test (1-2 min, 2 phases, minimal cost)
- **Medium** ⭐ **Default**: Balanced run (3-5 min, 4 phases, best quality/time ratio)
- **Standard**: Comprehensive (30-60 min, 7 phases, deep validation)
- **Deep**: Maximum exploration (60-90 min, 7 phases, most thorough)

```bash
python main.py --mode medium  # Recommended
python main.py --mode fast    # Quick prototype
python main.py --mode standard # Investor pitch
```

## Documentation

- **[Architecture Deep Dive](docs/architecture_deep_dive.md)** - Comprehensive technical deep dive with diagrams explaining shared context, async orchestration, and idea tracking
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed technical architecture, script execution order, and module overview
- **[DOCUMENTATION.md](docs/DOCUMENTATION.md)** - Complete user guide with examples and troubleshooting
- **[CLAUDE.md](docs/CLAUDE.md)** - Development context for AI assistants

## Project Structure

```
Assembly/
├── main.py                          # Entry point & CLI
├── .env.example                     # Environment template
├── framework/                       # Core conversation framework
│   ├── persona.py                  # Persona with memory system
│   ├── facilitator.py              # AI-powered orchestration
│   ├── conversation_logger.py      # Multi-format logging
│   ├── analytics.py                # Conversation analysis
│   ├── generators.py               # Dynamic persona/phase generation
│   └── utils.py                    # Helper utilities
├── src/                             # Application logic
│   ├── idea_generation/            # Idea generation pipeline
│   │   ├── generator.py            # Main entry point
│   │   ├── config.py               # Mode configurations
│   │   ├── prompts.py              # Staged prompts
│   │   ├── orchestration.py        # Meeting facilitation
│   │   ├── idea_tracker.py         # Enhanced idea tracking & status management
│   │   └── extraction.py           # Idea extraction
│   └── stages/                     # Pipeline stages
│       ├── spec_generation.py      # Stage 2: Specs
│       └── design_generation.py    # Stage 3: Base44
├── dynamic_personas/                # LLM-generated personas (cached)
├── personas/                        # Static persona definitions (JSON)
├── personas_archive/                # Archived persona versions
├── scripts/                         # Utility scripts
│   └── compare_modes.py            # Mode comparison tool
├── tests/                           # Test suite
├── docs/                            # Documentation
└── conversation_logs/               # Generated session logs
```

## How It Works

1. **Load Personas**: Dynamically load 7 AI personas from JSON definitions
2. **Facilitator Orchestration**: AI facilitator selects relevant personas and manages turn-taking
3. **Staged Discovery**: Each phase has 4 stages (Problem → Competitive → Solution → Synthesis)
4. **Multi-Phase Conversation**: Personas discuss through ideation → research → critique → decision phases
5. **Idea Extraction**: Structured ideas extracted from natural conversation
6. **Comprehensive Logging**: All exchanges saved with human-readable transcripts

## Output

Every run creates a timestamped session folder with:
- `readable_transcript.md` - **Start here** - formatted conversation
- `session_metadata.json` - final ideas and run config
- `phase_summaries.txt` - quick phase overview
- `full_conversation.json` - complete structured log
- `persona_summaries.json` - persona memory evolution
- `facilitator_decisions.json` - orchestration reasoning

## Example

```bash
$ python main.py --mode medium

[i] Running in MEDIUM mode: Balanced run (3-5 min, moderate cost)
[i] Loading personas from personas/ directory...
[i] Running 4 phases: ideation, research, critique, decision
[i] Max turns per phase: 5

============================================================
=== Phase: IDEATION ===
Goal: Generate 1 different startup idea(s) based on the inspiration
============================================================

[Speaker] Founder (Visionary Storyteller) speaking...
[i] New idea identified: 'CodeFlowSync'

[OK] Phase 'ideation' complete after 5 turns
[OK] Successfully extracted 1 idea(s)
```

## Requirements

- Python 3.8+
- OpenAI API key
- Dependencies: `openai`, `python-dotenv`

## License

[Your License Here]

---

**Version**: 2.0 (Modular Refactor with Staged Discovery)
**Last Updated**: October 27, 2025
