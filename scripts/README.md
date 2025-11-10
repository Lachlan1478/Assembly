# Utility Scripts

This directory contains utility scripts for analyzing and comparing Assembly runs.

## Available Scripts

### compare_modes.py

Compare conversation quality and behavior between different run modes (fast, medium, standard, deep).

**Purpose**: Generates detailed HTML comparison reports showing:
- Turn distribution and engagement metrics
- Persona participation patterns
- Token usage and cost analysis
- Conversation quality indicators
- Side-by-side session analysis

**Usage**:
```bash
python scripts/compare_modes.py
```

**Configuration**:
Edit the script to specify which session directories to compare:
```python
FAST_SESSION = "conversation_logs/session_20251028_200835"
MEDIUM_SESSION = "conversation_logs/session_20251028_201033"
```

**Output**:
- Opens comparison report in default browser
- Generates HTML files in the current directory

**Requirements**:
- ConversationAnalytics from framework module
- Valid session directories with conversation logs
- Web browser for viewing reports

## Adding New Scripts

When adding new utility scripts to this directory:

1. Follow the naming convention: `verb_noun.py` (e.g., `analyze_personas.py`)
2. Add documentation here in this README
3. Include a docstring at the top of the script
4. Update main README.md if the script is important for users

## Notes

- Scripts in this directory are for development and analysis purposes
- They are not part of the main Assembly pipeline
- Keep scripts independent and self-contained when possible
