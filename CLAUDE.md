# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Assembly** is an AI-powered application builder framework that rapidly generates full-stack applications from initial ideas. The system leverages multi-persona AI conversations to ideate, design, and build apps through integration with the Base44 no-code platform.

**Core Mission**: "Assemble Apps/SaaS from idea in minutes"

## Architecture

Assembly uses a **three-stage pipeline architecture with persona-based orchestration**:

### Stage 1: Idea Generation (`idea_brainstorm_01.py`)
- **Input**: User-provided inspiration (domain + desired outcome)
- **Process**: Multi-persona facilitated conversation with 7 structured phases
- **Personas**: Founder, Designer, Researcher, Tech Lead, CFO, Contrarian (6 personas)
- **Output**: Multiple validated startup ideas (JSON format)
- **Logging**: Complete conversation history saved to `meeting_logs.txt`

### Stage 2: Spec Generation (`spec_generation_02.py`)
- **Input**: Best idea selected from Stage 1
- **Process**: LLM transforms idea into detailed Base44 application specification
- **Output**: Structured prompt/specification for Base44 platform

### Stage 3: Design Generation (`generate_initial_design_03.py`)
- **Input**: Specification from Stage 2
- **Process**: Playwright-based browser automation to interact with Base44
- **Integration**: Submits spec to https://app.base44.com and waits for build
- **Output**: App ID and preview URL
- **Status**: Currently stubbed in main.py (lines 54-55)

### Orchestration (`main.py`)
Coordinates all three stages sequentially, passing outputs between stages.

## Key Components

### Persona System (`persona.py`)

The `Persona` class wraps LLM calls with specific personality profiles:

```python
# Load persona from JSON definition
persona = Persona.from_file("personas/founder.json", model_name="gpt-4o-mini")

# Generate response with context
response = persona.response({
    "user_prompt": "...",
    "phase": "ideation",
    "shared_context": {...}
})
```

**Persona Definition Structure** (JSON files in `personas/`):
- `Name`: Persona identifier
- `Archetype`: Role description
- `Purpose`: Primary responsibility
- `Deliverables`: Expected outputs
- `Strengths`: Key capabilities
- `Watch-out`: Potential pitfalls to avoid

**Available Personas**:
- `founder.json` - Visionary storyteller, drives product ideas
- `designer.json` - UX/design advocate, creates lovable experiences
- `researcher.json` - Market analyst, validates demand
- `tech_lead.json` - Technical architect, assesses feasibility
- `cfo.json` - Business strategist, ensures economic viability
- `contrarian.json` - Devil's advocate, stress-tests assumptions
- `facilitator.json` - Meeting orchestrator (optional)
- `test.json` - Test persona for development

### Meeting Facilitator Pattern

The `meeting_facilitator()` function orchestrates structured multi-persona conversations:

**Phase Structure**:
1. `ideation` (Lead: Founder) - Generate initial ideas
2. `design` (Lead: Designer) - Define user experience
3. `research` (Lead: Researcher) - Validate market demand
4. `feasibility` (Lead: Tech Lead) - Assess technical viability
5. `financials` (Lead: CFO) - Evaluate business model
6. `critique` (Lead: Contrarian) - Challenge assumptions
7. `decision` (Lead: Founder) - Consolidate and finalize

Each phase:
- Has a **lead role** (speaks first with priority)
- Defines **allowed roles** (who can participate)
- Accumulates insights in **shared context**
- Appends all responses to conversation history

### Browser Automation (Stage 3)

Uses Playwright with persistent browser context to maintain authentication state:

**Critical Configuration**:
- Persistent Edge profile (`BASE44_USER_DATA_DIR`) must be pre-seeded with Base44 login
- Browser launches in non-headless mode for visibility
- Intelligent input detection handles textarea, input, or contenteditable elements
- Preview URL polling with 180-second timeout

**Key Functions**:
- `_find_builder_input()` - Locates spec input field
- `_wait_for_preview_url()` - Polls for build completion
- `_extract_app_id()` - Parses app identifier from preview URL

## Development Commands

### Running the Full Pipeline

```bash
# Ensure .env is configured with OPENAI_API_KEY
python main.py
```

**Note**: Stage 3 (browser automation) is currently commented out. Uncomment lines 54-55 in `main.py` to enable.

### Running Individual Stages

```bash
# Stage 1: Generate ideas
python idea_brainstorm_01.py

# Stage 2: Generate spec from idea
python spec_generation_02.py

# Stage 3: Build app in Base44 (requires pre-seeded browser profile)
python generate_initial_design_03.py
```

### Testing

```bash
# Test Persona class
cd Testing
python test_persona_class.py

# Validate Base44 browser session
cd Testing/test_base_44_automation
python seed_base44_session.py
```

The `seed_base44_session.py` script:
- Launches persistent Edge browser with saved profile
- Checks if logged into Base44
- Takes screenshot (saved to `artifacts/`)
- Provides manual setup instructions if not logged in

### Testing Single Personas

```python
# Test any persona interactively
from persona import Persona

persona = Persona.from_file("personas/designer.json")
response = persona.response({
    "user_prompt": "Design a user dashboard",
    "phase": "design"
})
print(response["response"])
```

## Environment Configuration

Required `.env` file:

```
OPENAI_API_KEY=sk-proj-...                    # Required for all LLM calls
BASE44_URL=https://app.base44.com             # Optional (has default)
BASE44_BROWSER_CHANNEL=msedge                 # "msedge" or "chrome"
BASE44_USER_DATA_DIR=C:\Users\User\EdgePW     # Persistent browser profile
BASE44_PROFILE_DIR=Default                    # Browser profile name
```

## Dependencies

Install required packages:

```bash
pip install openai python-dotenv playwright
playwright install chromium  # For browser automation
```

**Key Dependencies**:
- `openai` - LLM API client (GPT-3.5/4)
- `python-dotenv` - Environment variable management
- `playwright` - Browser automation for Base44 integration

## Project Structure

```
Assembly/
├── main.py                          # Pipeline orchestrator (entry point)
├── persona.py                       # Persona class framework
├── idea_brainstorm_01.py           # Stage 1: Multi-persona ideation
├── spec_generation_02.py           # Stage 2: Spec generation
├── generate_initial_design_03.py   # Stage 3: Base44 automation
├── .env                             # Environment configuration (git-ignored)
├── .venv/                           # Python virtual environment
├── personas/                        # Persona JSON definitions
│   ├── founder.json
│   ├── designer.json
│   ├── researcher.json
│   ├── tech_lead.json
│   ├── cfo.json
│   ├── contrarian.json
│   ├── facilitator.json
│   └── test.json
├── Testing/
│   ├── test_persona_class.py                     # Unit test for Persona
│   └── test_base_44_automation/
│       ├── seed_base44_session.py                # Browser session validator
│       └── artifacts/                            # Screenshots from tests
├── Archive/                                      # Legacy/reference code
│   ├── explore_app.py                           # App crawler
│   └── publish_app.py                           # App publishing
└── meeting_logs.txt                             # Output from Stage 1
```

## Design Patterns

### Persona System Prompt Construction

Each persona's response is generated using a dynamically constructed system prompt:

```python
system_prompt = f"""You are {name}, the {archetype}.
Purpose: {purpose}
Deliverables: {deliverables}
Strengths: {strengths}
Be mindful of: {watchouts}
"""
```

This ensures consistent persona behavior across all interactions.

### Shared Context Pattern

All personas receive and contribute to a shared context dictionary:

```python
shared_context = {
    "user_prompt": "...",           # Initial inspiration
    "phase": "ideation",            # Current phase
    "history": [],                  # Accumulated responses
    "ideas": [],                    # Generated ideas
    # ... custom fields added by personas
}
```

This enables:
- Cross-persona knowledge sharing
- Progressive refinement of ideas
- Complete auditability of decision-making

### JSON Logging

All Stage 1 conversations are logged to `meeting_logs.txt` in JSON format:

```json
{
  "phase": "ideation",
  "lead_role": "founder",
  "responses": [
    {
      "persona": "Founder",
      "archetype": "Visionary Storyteller",
      "response": "..."
    }
  ]
}
```

Review logs to understand persona interactions and debug unexpected outputs.

## Base44 Integration

### Prerequisites for Stage 3

1. **Manual Browser Profile Setup**:
   ```bash
   # Launch Edge with persistent profile
   & "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --user-data-dir="C:\Users\User\EdgePW" --profile-directory="Default"
   ```

2. **Log into Base44**: Navigate to https://app.base44.com and complete authentication

3. **Close Browser**: Profile is now seeded with login session

4. **Validate Setup**:
   ```bash
   cd Testing/test_base_44_automation
   python seed_base44_session.py
   ```

### How Stage 3 Works

1. Launches persistent context (reuses seeded profile)
2. Navigates to Base44 builder
3. Locates spec input field (handles multiple input types)
4. Fills in specification text
5. Submits build (via button click or Ctrl+Enter)
6. Polls for preview URL (180-second timeout)
7. Extracts app ID from URL
8. Returns `(app_id, preview_url)` tuple

## Common Development Patterns

### Modifying Personas

1. Edit JSON file in `personas/` directory
2. Adjust `Purpose`, `Deliverables`, `Strengths`, or `Watch-out` fields
3. Test with `test_persona_class.py` or direct instantiation
4. No code changes required—personas are loaded dynamically

### Adding New Phases

Edit `idea_brainstorm_01.py`:

```python
phases = [
    # ... existing phases
    {
        "phase_id": "new_phase",
        "lead_role": "designer",
        "allowed_roles": ["founder", "designer", "tech_lead"],
        "description": "Purpose of this phase..."
    }
]
```

### Changing LLM Models

Default model: `gpt-3.5-turbo` (defined in `persona.py`)

To use different model:

```python
persona = Persona.from_file("personas/founder.json", model_name="gpt-4o-mini")
```

Or modify default in `Persona.__init__()`.

### Debugging LLM Responses

1. Check `meeting_logs.txt` for complete conversation history
2. Verify persona JSON definitions match intended behavior
3. Ensure shared context includes necessary information
4. Test individual personas in isolation (see "Testing Single Personas")

## Current Limitations

- **Stage 3 is stubbed**: Browser automation code exists but is commented out in `main.py`
- **Windows-specific paths**: Browser profile paths are hardcoded for Windows
- **Single Base44 account**: Assumes single user with pre-authenticated session
- **No error recovery**: Pipeline stops on first error (no retry logic)
- **High token usage**: Multi-persona conversations can be expensive
- **No parallel execution**: Stages run sequentially (could be optimized)

## Important Notes

- **API Costs**: Multiple personas × multiple phases = significant OpenAI API usage
- **Browser Automation Fragility**: Stage 3 depends on Base44 UI remaining stable
- **Persistent State**: Browser profile must maintain valid session (may expire)
- **Platform-Specific**: Designed for Windows with Edge; adapt for Mac/Linux
- **Meeting Logs**: `meeting_logs.txt` is overwritten on each Stage 1 run—archive if needed
