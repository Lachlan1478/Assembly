# idea_brainstorm_01a_config.py
# Configuration module: Mode definitions for different run speeds

#MODEL = "gpt-4.1-mini"
MODEL = "gpt-5-mini"

# Mode configurations for different run speeds
MODE_CONFIGS = {
    "fast": {
        "phases": ["ideation", "decision"],
        "max_turns_per_phase": 3,
        "model": "gpt-3.5-turbo",
        "enable_summary_updates": False,
        "description": "Quick test run (1-2 min, minimal cost)"
    },
    "medium": {
        "phases": ["ideation", "research", "critique", "decision"],
        "max_turns_per_phase": 5,
        "model": "gpt-4o-mini",
        "enable_summary_updates": True,
        "description": "Balanced run (3-5 min, moderate cost)"
    },
    "standard": {
        "phases": ["ideation", "design", "research", "feasibility", "financials", "critique", "decision"],
        "max_turns_per_phase": 8,
        "model": "gpt-4o-mini",
        "enable_summary_updates": True,
        "description": "Comprehensive run (30-60 min, higher cost)"
    },
    "deep": {
        "phases": ["ideation", "design", "research", "feasibility", "financials", "critique", "decision"],
        "max_turns_per_phase": 15,
        "model": "gpt-5-mini",
        "enable_summary_updates": True,
        "description": "Deep exploration (60-90 min, highest cost)"
    }
}
