"""
ConversationLogger - Comprehensive logging system for multi-persona conversations.

Saves timestamped session data to enable validation of persona interactions and insights.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class ConversationLogger:
    """
    Logs multi-persona conversations to timestamped session folders.

    Creates a new session folder for each run with multiple output files:
    - full_conversation.json: All exchanges
    - persona_summaries.json: Persona summaries at each phase
    - phase_summaries.txt: Facilitator summaries (human-readable)
    - facilitator_decisions.json: Persona selections and speaker decisions
    - session_metadata.json: Session info, inspiration, phases, results
    - readable_transcript.md: Markdown transcript for easy reading
    """

    def __init__(self, base_dir: str = "conversation_logs"):
        """
        Initialize a new conversation logging session.

        Args:
            base_dir: Base directory for all conversation logs
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)

        # Create timestamped session folder
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_dir = self.base_dir / f"session_{timestamp}"
        self.session_dir.mkdir(exist_ok=True)

        # Initialize data structures
        self.exchanges = []
        self.persona_summaries = {}  # {phase_id: {persona_name: summary}}
        self.phase_summaries = {}    # {phase_id: summary_text}
        self.facilitator_decisions = []
        self.metadata = {
            "timestamp": timestamp,
            "session_start": datetime.now().isoformat()
        }

        print(f"\n[Logger] Session folder: {self.session_dir}")

    def log_metadata(self, key: str, value: Any) -> None:
        """
        Add metadata about the session.

        Args:
            key: Metadata key (e.g., "inspiration", "number_of_ideas")
            value: Metadata value
        """
        self.metadata[key] = value

    def log_exchange(
        self,
        phase_id: str,
        turn: int,
        speaker: str,
        archetype: str,
        content: str
    ) -> None:
        """
        Log a single conversation exchange.

        Args:
            phase_id: Current phase
            turn: Turn number within phase
            speaker: Persona name who spoke
            archetype: Persona archetype
            content: What was said
        """
        exchange = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase_id,
            "turn": turn,
            "speaker": speaker,
            "archetype": archetype,
            "content": content
        }
        self.exchanges.append(exchange)

    def log_persona_summaries(self, phase_id: str, personas: Dict[str, Any]) -> None:
        """
        Log all active persona summaries at a phase boundary.

        Args:
            phase_id: Phase that just completed
            personas: Dict of active Persona instances
        """
        if phase_id not in self.persona_summaries:
            self.persona_summaries[phase_id] = {}

        for persona_name, persona in personas.items():
            self.persona_summaries[phase_id][persona_name] = {
                "objective_facts": persona.summary.get("objective_facts", []),
                "subjective_notes": persona.summary.get("subjective_notes", {})
            }

    def log_phase_summary(self, phase_id: str, summary_text: str) -> None:
        """
        Log the facilitator's summary of a phase.

        Args:
            phase_id: Phase that was summarized
            summary_text: Facilitator's summary
        """
        self.phase_summaries[phase_id] = summary_text

    def log_facilitator_decision(
        self,
        decision_type: str,
        phase_id: str,
        decision: Any,
        reasoning: str = ""
    ) -> None:
        """
        Log a facilitator decision (persona selection or speaker choice).

        Args:
            decision_type: "persona_selection" or "speaker_choice"
            phase_id: Current phase
            decision: The decision made (list of personas or persona name)
            reasoning: Why this decision was made
        """
        self.facilitator_decisions.append({
            "timestamp": datetime.now().isoformat(),
            "type": decision_type,
            "phase": phase_id,
            "decision": decision,
            "reasoning": reasoning
        })

    def save_all(self) -> None:
        """
        Save all logged data to files in the session directory.
        """
        self.metadata["session_end"] = datetime.now().isoformat()

        # Save full conversation
        self._save_json(
            "full_conversation.json",
            self.exchanges,
            description="All conversation exchanges"
        )

        # Save persona summaries
        self._save_json(
            "persona_summaries.json",
            self.persona_summaries,
            description="Persona summaries at each phase boundary"
        )

        # Save phase summaries (text file)
        self._save_phase_summaries()

        # Save facilitator decisions
        self._save_json(
            "facilitator_decisions.json",
            self.facilitator_decisions,
            description="All facilitator decisions"
        )

        # Save metadata
        self._save_json(
            "session_metadata.json",
            self.metadata,
            description="Session metadata"
        )

        # Generate readable transcript
        self._generate_transcript()

        print(f"\n[Logger] All logs saved to: {self.session_dir}")
        print(f"[Logger] Total exchanges: {len(self.exchanges)}")
        print(f"[Logger] Total phases: {len(self.phase_summaries)}")

    def _save_json(self, filename: str, data: Any, description: str = "") -> None:
        """Save data as JSON file."""
        filepath = self.session_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if description:
            print(f"[Logger] Saved {filename}: {description}")

    def _save_phase_summaries(self) -> None:
        """Save phase summaries as readable text file."""
        filepath = self.session_dir / "phase_summaries.txt"
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("="*70 + "\n")
            f.write("PHASE SUMMARIES\n")
            f.write("="*70 + "\n\n")

            for phase_id, summary in self.phase_summaries.items():
                f.write(f"Phase: {phase_id.upper()}\n")
                f.write("-" * 70 + "\n")
                f.write(summary + "\n\n")

        print(f"[Logger] Saved phase_summaries.txt: Human-readable phase summaries")

    def _generate_transcript(self) -> None:
        """Generate a human-friendly markdown transcript."""
        filepath = self.session_dir / "readable_transcript.md"

        with open(filepath, "w", encoding="utf-8") as f:
            # Header
            f.write(f"# Conversation Transcript\n\n")
            f.write(f"**Session**: {self.metadata.get('timestamp')}\n\n")
            if "inspiration" in self.metadata:
                f.write(f"**Inspiration**: {self.metadata['inspiration']}\n\n")
            f.write("---\n\n")

            # Group exchanges by phase
            current_phase = None
            for exchange in self.exchanges:
                phase = exchange["phase"]

                # New phase header
                if phase != current_phase:
                    current_phase = phase
                    f.write(f"\n## Phase: {phase.upper()}\n\n")

                    # Add phase summary if available
                    if phase in self.phase_summaries:
                        f.write(f"*{self.phase_summaries[phase]}*\n\n")

                # Exchange
                speaker = exchange["speaker"]
                archetype = exchange["archetype"]
                content = exchange["content"]
                turn = exchange["turn"]

                f.write(f"### Turn {turn}: {speaker} ({archetype})\n\n")
                f.write(f"{content}\n\n")
                f.write("---\n\n")

            # Final summary
            f.write("\n## Session Summary\n\n")
            f.write(f"- **Total Exchanges**: {len(self.exchanges)}\n")
            f.write(f"- **Total Phases**: {len(self.phase_summaries)}\n")
            f.write(f"- **Duration**: {self.metadata.get('session_start')} to {self.metadata.get('session_end')}\n")

            if "ideas" in self.metadata:
                f.write(f"\n### Generated Ideas\n\n")
                f.write("```json\n")
                f.write(json.dumps(self.metadata["ideas"], indent=2))
                f.write("\n```\n")

        print(f"[Logger] Saved readable_transcript.md: Human-friendly transcript")
