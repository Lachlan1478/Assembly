# idea_brainstorm_01a_config.py
# Configuration module: Mode definitions for different run speeds

#MODEL = "gpt-4.1-mini"
MODEL = "gpt-4o-mini"

# Mode configurations for different run speeds
# phase_selection strategies:
#   - "bookends": First and last phase only (fast exploration → decision)
#   - "bookends_plus_middle": First phase + last phase + (n-2) middle phases
#   - "first_n": First N phases (partial workflow, set via num_phases)
#   - "all": All dynamically generated phases (full workflow)
MODE_CONFIGS = {
    "fast": {
        "phase_selection": "bookends",
        "max_turns_per_phase": 3,
        "model": "gpt-3.5-turbo",
        "enable_summary_updates": False,
        "description": "Quick test (1-2 min) - exploration → decision only"
    },
    "medium": {
        "phase_selection": "bookends_plus_middle",
        "num_phases": 4,
        "max_turns_per_phase": 5,
        "model": "gpt-4o-mini",
        "enable_summary_updates": True,
        "description": "Balanced (3-5 min) - first + middle + decision phases"
    },
    "standard": {
        "phase_selection": "all",
        "max_turns_per_phase": 8,
        "model": "gpt-4o-mini",
        "enable_summary_updates": True,
        "description": "Comprehensive (30-60 min) - full workflow"
    },
    "deep": {
        "phase_selection": "all",
        "max_turns_per_phase": 15,
        "model": "gpt-4o-mini",
        "enable_summary_updates": True,
        "description": "Deep exploration (60-90 min) - maximum depth"
    }
}
