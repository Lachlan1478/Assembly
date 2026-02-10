# idea_brainstorm_01a_config.py
# Configuration module: Mode definitions for different run speeds

MODEL = "gpt-5.1"

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
        "personas_per_phase": 3,  # Fewer personas for faster testing
        "model": "gpt-5.1",
        "enable_summary_updates": False,
        "enable_mediator": False,  # Disable mediator for speed
        "enable_convergence_phase": False,  # Skip convergence for speed
        "description": "Quick test (1-2 min) - exploration -> decision only"
    },
    "medium": {
        "phase_selection": "bookends_plus_middle",
        "num_phases": 4,
        "max_turns_per_phase": 5,
        "personas_per_phase": 4,  # Standard persona count
        "model": "gpt-5.1",
        "enable_summary_updates": True,
        "enable_mediator": True,  # Enable mediator for quality discussions
        "enable_convergence_phase": True,  # Enable convergence for commercial refinement
        "description": "Balanced (3-5 min) - first + middle + decision phases + convergence"
    },
    "standard": {
        "phase_selection": "all",
        "max_turns_per_phase": 8,
        "personas_per_phase": 4,  # Standard persona count
        "model": "gpt-5.1",
        "enable_summary_updates": True,
        "enable_mediator": True,  # Enable mediator for quality discussions
        "enable_convergence_phase": True,  # Enable convergence for commercial refinement
        "description": "Comprehensive (30-60 min) - full workflow + convergence"
    },
    "deep": {
        "phase_selection": "all",
        "max_turns_per_phase": 15,
        "personas_per_phase": 5,  # More personas for deeper exploration
        "model": "gpt-5.1",
        "enable_summary_updates": True,
        "enable_mediator": True,  # Enable mediator for deepest exploration
        "enable_convergence_phase": True,  # Enable convergence for commercial refinement
        "description": "Deep exploration (60-90 min) - maximum depth + convergence"
    }
}
