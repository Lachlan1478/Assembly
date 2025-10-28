"""
Assembly Framework - Multi-Persona Conversation Orchestration

A framework for creating structured conversations between AI personas,
with facilitator-directed turn-taking and comprehensive logging.

Key Features:
- Persona class with hybrid memory system (objective facts + subjective notes)
- FacilitatorAgent for intelligent conversation orchestration
- ConversationLogger with 6 output formats (JSON, Markdown, plain text)
- Dynamic persona loading from JSON definitions
- Bounded memory design prevents token explosion in long conversations

Example Usage:
    >>> from framework import Persona, FacilitatorAgent, ConversationLogger
    >>> from framework import load_personas_from_directory
    >>>
    >>> # Load personas
    >>> personas = load_personas_from_directory("personas")
    >>>
    >>> # Create facilitator
    >>> facilitator = FacilitatorAgent(model_name="gpt-4o-mini")
    >>>
    >>> # Create logger
    >>> logger = ConversationLogger(base_dir="conversation_logs")
    >>>
    >>> # Define conversation goal
    >>> phase = {
    ...     "phase_id": "design_review",
    ...     "goal": "Review the UX design for our mobile app",
    ...     "max_turns": 5
    ... }
    >>>
    >>> # Let facilitator select relevant personas
    >>> selected = facilitator.select_personas_for_phase(phase, personas)

Use Cases:
- Startup idea generation and validation
- Design reviews and critiques
- Technical decision-making
- Strategic planning discussions
- Research synthesis
- Code reviews
- Any task requiring multiple perspectives

See framework/examples/ for complete usage examples.
"""

__version__ = "0.1.0"
__author__ = "Assembly Team"

from .persona import Persona
from .facilitator import FacilitatorAgent
from .logger import ConversationLogger
from .monitor import ConversationMonitor
from .helpers import load_personas_from_directory, format_summary_for_prompt

__all__ = [
    "Persona",
    "FacilitatorAgent",
    "ConversationLogger",
    "ConversationMonitor",
    "load_personas_from_directory",
    "format_summary_for_prompt",
]
