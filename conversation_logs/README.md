# Conversation Logs

This directory contains timestamped session logs for all multi-persona conversations.

## Purpose

These logs let you validate whether valuable insights are gained from persona interactions. Each session is saved in a timestamped folder with multiple file formats for different analysis needs.

## Session Structure

Each session creates a folder named `session_YYYYMMDD_HHMMSS/` containing:

### Files Generated

1. **`readable_transcript.md`** - **START HERE**
   - Human-friendly markdown format
   - Organized by phase
   - Includes phase summaries
   - Shows each persona's contributions with turn numbers
   - **Best for**: Quick review and understanding the conversation flow

2. **`full_conversation.json`**
   - Complete conversation data
   - Every exchange with timestamp, speaker, archetype, content
   - **Best for**: Programmatic analysis, searching specific quotes

3. **`persona_summaries.json`**
   - Each persona's summary at each phase boundary
   - Shows how personas' understanding evolved
   - Includes objective facts and subjective notes
   - **Best for**: Tracking how personas build context over time

4. **`phase_summaries.txt`**
   - Facilitator's summary of each phase
   - Human-readable text format
   - **Best for**: High-level understanding of what was accomplished

5. **`facilitator_decisions.json`**
   - All facilitator decisions logged
   - Persona selections for each phase
   - Speaker choices for each turn
   - **Best for**: Understanding why certain personas were chosen

6. **`session_metadata.json`**
   - Session configuration and results
   - Inspiration, phases, final ideas
   - Timestamp and duration
   - **Best for**: Quick overview of session parameters

## How to Review a Session

### Quick Review (5 minutes)
1. Open `readable_transcript.md` in any markdown viewer
2. Read the phase summaries and skim conversations
3. Check the final ideas in the session summary

### Detailed Analysis (20+ minutes)
1. Start with `readable_transcript.md` for context
2. Review `persona_summaries.json` to see how understanding evolved
3. Check `facilitator_decisions.json` to understand orchestration
4. Deep dive into `full_conversation.json` for specific exchanges

### Validating Persona Value

To assess if personas are adding value, look for:

**Good Signs:**
- Personas build on each other's points (check summaries)
- Different archetypes surface unique concerns (Designer vs CFO vs Tech Lead)
- Conversations become more refined across phases
- Final ideas show evidence of multi-perspective thinking

**Warning Signs:**
- Personas repeat similar points
- Summaries don't accumulate meaningful insights
- Facilitator selects same personas repeatedly
- No evolution in thinking across phases

## Example Session

```
conversation_logs/
  session_20251026_143022/
    ├── readable_transcript.md        # Read this first
    ├── full_conversation.json         # All data
    ├── persona_summaries.json         # How personas evolved
    ├── phase_summaries.txt            # Phase outcomes
    ├── facilitator_decisions.json     # Why personas were selected
    └── session_metadata.json          # Session config
```

## Tips

- **Compare sessions**: Review multiple sessions to see patterns
- **Track specific personas**: Use `full_conversation.json` to filter by speaker
- **Analyze phase effectiveness**: Check if certain phases consistently produce valuable insights
- **Facilitator tuning**: Use decision logs to see if selection logic is working well

## Backing Up Logs

Each session is independent. To backup:
```bash
# Backup a specific session
cp -r session_YYYYMMDD_HHMMSS /path/to/backup/

# Backup all sessions
cp -r conversation_logs /path/to/backup/
```

## Integration with Main Pipeline

Logs are automatically created when running:
```bash
python main.py
```

The logger creates a new session folder on each run and saves all files at the end of the conversation.
