# Conversation Framework Deep Dive Tests

This directory contains minimal test scripts for analyzing the Assembly conversation framework's behavior with simplified configurations.

## Purpose

These tests help you:
- **Understand conversation dynamics** with fewer personas (easier to analyze)
- **Review conversation quality** through detailed logs
- **Test framework modifications** without running full idea generation
- **Analyze persona behavior** and facilitator decision-making
- **Experiment with different configurations** quickly

## Tests Available

### `test_trolley_problem.py`

**What it tests:**
- 2 personas discussing the classic Trolley Problem ethical dilemma
- Facilitator managing a focused philosophical debate
- Persona memory evolution over 10 turns
- Quality of argument engagement and counter-arguments

**Configuration:**
- **Personas**: 2 (dynamically generated, likely Utilitarian + Deontologist)
- **Phases**: 1 ("ethical_analysis")
- **Turns**: 10
- **Memory updates**: Enabled (realistic conversation)
- **Runtime**: ~3-5 minutes
- **Cost**: ~$0.10-0.15 (gpt-4o-mini)

**Run:**
```bash
python tests/convo_deep_dive/test_trolley_problem.py
```

**Output:**
```
tests/convo_deep_dive/logs/session_20251114_HHMMSS/
├── readable_transcript.md          ← START HERE
├── persona_summaries.json          ← See how personas evolved
├── facilitator_decisions.json      ← See speaker selection reasoning
├── full_conversation.json
├── phase_summaries.txt
└── session_metadata.json
```

## How to Analyze the Logs

### 1. Read the Transcript First

**File:** `logs/session_*/readable_transcript.md`

Look for:
- ✅ **Distinct positions**: Do personas maintain different philosophical stances?
- ✅ **Argument engagement**: Do they respond to each other's points?
- ✅ **Depth**: Do arguments go beyond surface-level observations?
- ✅ **Examples**: Do they provide concrete scenarios?
- ❌ **Repetition**: Are personas repeating themselves without adding new insights?
- ❌ **Agreement too fast**: Do they concede too easily?

**Example of good engagement:**
```
Turn 3: Utilitarian Philosopher
"From a utilitarian perspective, the moral calculus is clear: five lives
outweigh one. The greatest good for the greatest number demands pulling the lever..."

Turn 4: Deontological Ethicist
"I must respectfully disagree with this consequentialist framing. Using
someone merely as a means to an end—even to save others—violates the
Kantian categorical imperative. We cannot treat that one person as expendable..."

Turn 5: Utilitarian Philosopher
"But consider this objection to your position: inaction is also a choice!
If you don't pull the lever, you're still causally responsible for the outcome..."
```

### 2. Check Persona Evolution

**File:** `logs/session_*/persona_summaries.json`

Each persona's summary shows what they learned/remembered from the discussion:

```json
{
  "ethical_analysis": {
    "Dr. Sarah Chen (Utilitarian Philosopher)": {
      "summary": {
        "objective_facts": [
          "Deontologist argued pulling lever violates categorical imperative",
          "Five people on main track, one on side track",
          "Discussed action vs inaction distinction"
        ],
        "subjective_notes": {
          "key_concerns": [
            "Need to address the action/inaction objection more thoroughly"
          ],
          "priorities": [
            "Demonstrate consequentialist reasoning is more consistent"
          ],
          "opinions": [
            "Deontologist's position leads to counterintuitive outcomes"
          ]
        }
      }
    }
  }
}
```

**Look for:**
- ✅ Summaries capture opponent's arguments (shows listening)
- ✅ Personas update their concerns/priorities (shows adaptation)
- ✅ New objections appear in later turns
- ❌ Summaries don't reference other personas (isolation)
- ❌ No evolution across turns (static positions)

### 3. Analyze Facilitator Decisions

**File:** `logs/session_*/facilitator_decisions.json`

Shows WHO the facilitator picked and WHY:

```json
{
  "decisions": [
    {
      "type": "speaker_choice",
      "phase_id": "ethical_analysis",
      "decision": "Dr. Sarah Chen",
      "reasoning": "Turn 3 in phase 'ethical_analysis'",
      "timestamp": "2025-11-14T15:23:45.123Z"
    }
  ]
}
```

**Look for:**
- ✅ Turn-taking is balanced (not one persona dominating)
- ✅ Speaker switches happen when topics shift
- ✅ Both personas get multiple consecutive turns when deep in argument
- ❌ Same persona speaks 5+ times in a row (imbalanced)

### 4. Review Full Data (Advanced)

**File:** `logs/session_*/full_conversation.json`

Contains:
- Complete exchanges with exact timestamps
- Token counts (for cost analysis)
- Model responses
- Raw LLM outputs

Use this for:
- Debugging extraction failures
- Analyzing exact phrasing
- Calculating costs
- Finding edge cases

## What Makes a "Good" Conversation?

Based on reviewing the logs, a high-quality conversation should have:

### ✅ Good Signs
1. **Distinct Perspectives**: Personas represent genuinely different viewpoints
2. **Active Engagement**: Personas respond to each other's specific points
3. **Argument Depth**: Goes beyond surface-level ("but what about...?")
4. **Concrete Examples**: Real scenarios, not just abstract principles
5. **Objections Raised**: Personas challenge each other's reasoning
6. **Evolution**: Arguments refine over time based on objections
7. **Balanced Participation**: Both personas contribute roughly equally

### ❌ Warning Signs
1. **Rapid Agreement**: Personas concede too easily
2. **Repetition**: Same arguments repeated without development
3. **Talking Past Each Other**: Not engaging with specific points
4. **Shallow Arguments**: "I think X because Y" without deeper justification
5. **Imbalanced Turns**: One persona dominates
6. **Generic Responses**: Could apply to any topic

## Creating Your Own Tests

### Basic Template

```python
import asyncio
from pathlib import Path
from framework import FacilitatorAgent, ConversationLogger
from framework.persona_manager import PersonaManager
from src.idea_generation.orchestration import meeting_facilitator

# Define your topic
INSPIRATION = """
Domain: [Your domain]

Context: [Your context]

Question: [Your question]
"""

# Define phases
PHASES = [{
    "phase_id": "your_phase",
    "goal": "What you want to accomplish",
    "desired_outcome": "Specific deliverable",
    "max_turns": 10
}]

async def run_test():
    persona_manager = PersonaManager(model_name="gpt-4o-mini")
    facilitator = FacilitatorAgent(model_name="gpt-4o-mini")
    logger = ConversationLogger(base_dir="logs")

    shared_context = {"topic": "Your topic"}

    result = await meeting_facilitator(
        persona_manager=persona_manager,
        inspiration=INSPIRATION,
        phases=PHASES,
        shared_context=shared_context,
        facilitator=facilitator,
        logger=logger,
        enable_summary_updates=True,
        personas_per_phase=2  # Adjust as needed
    )

    return result

asyncio.run(run_test())
```

### Tips for Custom Tests

1. **Start small**: 2-3 personas, 5-10 turns
2. **Single phase**: Easier to analyze than multi-phase
3. **Clear topic**: Avoid overly broad or vague domains
4. **Disable summaries for speed**: Set `enable_summary_updates=False` for quick tests
5. **Vary persona count**: Try 2, 3, 4, 5 to see how dynamics change

## Performance Benchmarks

Based on `test_trolley_problem.py`:

| Config | Runtime | Cost (est.) | Quality |
|--------|---------|-------------|---------|
| 2 personas, 10 turns, updates ON | 3-5 min | $0.10-0.15 | High |
| 2 personas, 10 turns, updates OFF | 1-2 min | $0.05-0.08 | Medium |
| 4 personas, 10 turns, updates ON | 5-8 min | $0.20-0.30 | High |
| 2 personas, 20 turns, updates ON | 6-10 min | $0.20-0.30 | Very High |

**Cost breakdown** (gpt-4o-mini rates: $0.15/1M input, $0.60/1M output):
- Persona generation: ~$0.02 per persona
- Each turn: ~$0.01-0.02
- Memory updates: ~$0.005 per persona per turn
- Facilitator decisions: ~$0.01 per turn

## Troubleshooting

### Test fails with "No personas generated"
- Check OpenAI API key is set in `.env`
- Verify internet connection
- Check API quota/billing

### Personas are too similar
- Make inspiration more specific about desired perspectives
- Example: "Participants should include a utilitarian and a deontologist"

### Conversation is shallow
- Increase turns (10 → 20)
- Enable memory updates
- Make inspiration more specific about depth expected

### Runtime is too long
- Reduce turns (10 → 5)
- Disable memory updates: `enable_summary_updates=False`
- Use fewer personas (4 → 2)

## Next Steps

After analyzing the Trolley Problem test:
1. Try modifying the ethical dilemma
2. Test with 3-4 personas
3. Experiment with multi-phase discussions
4. Compare memory ON vs OFF
5. Try different philosophical topics

## Questions?

Review the main Assembly documentation:
- `docs/architecture_deep_dive.md` - Detailed framework explanation
- `docs/ARCHITECTURE.md` - Technical architecture
- `README.md` - Quick start guide
