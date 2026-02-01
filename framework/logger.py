"""
ConversationLogger - Comprehensive logging system for multi-persona conversations.

Saves timestamped session data to enable validation of persona interactions and insights.
"""

import json
import textwrap
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any


class ConversationLogger:
    """
    Logs multi-persona conversations to timestamped session folders.

    Creates a new session folder for each run with multiple output files:
    - readable_transcript.md: Conversation + outcome summary
    - readable_transcript_extended.md: Input prompts shown before each response
    - metadata/full_conversation.json: All exchanges
    - metadata/persona_summaries.json: Persona summaries at each phase
    - metadata/facilitator_decisions.json: Persona selections and speaker decisions
    - metadata/session_metadata.json: Session info, inspiration, phases, results
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

        # Create metadata subdirectory for JSON files
        self.metadata_dir = self.session_dir / "metadata"
        self.metadata_dir.mkdir(exist_ok=True)

        # Initialize data structures
        self.exchanges = []
        self.persona_summaries = {}  # {phase_id: {persona_name: summary}}
        self.phase_summaries = {}    # {phase_id: summary_text}
        self.facilitator_decisions = []
        self.prompt_inputs = []      # Full prompt inputs for each turn
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

    def log_prompt_input(
        self,
        phase_id: str,
        turn: int,
        speaker: str,
        archetype: str,
        prompt_data: Dict[str, Any]
    ) -> None:
        """
        Log the complete input prompt sent to a persona.

        Args:
            phase_id: Current phase
            turn: Turn number within phase
            speaker: Persona name
            archetype: Persona archetype
            prompt_data: Dict containing system_message, enhanced_prompt, and token_count
        """
        prompt_input = {
            "timestamp": datetime.now().isoformat(),
            "phase": phase_id,
            "turn": turn,
            "speaker": speaker,
            "archetype": archetype,
            "system_message": prompt_data.get("system_message", ""),
            "enhanced_prompt": prompt_data.get("enhanced_prompt", ""),
            "token_count": prompt_data.get("token_count", 0)
        }
        self.prompt_inputs.append(prompt_input)

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

        # Generate extended transcript with prompt inputs
        self._generate_extended_transcript()

        print(f"\n[Logger] All logs saved to: {self.session_dir}")
        print(f"[Logger] Total exchanges: {len(self.exchanges)}")

    def _save_json(self, filename: str, data: Any, description: str = "") -> None:
        """Save data as JSON file to metadata directory."""
        filepath = self.metadata_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        if description:
            print(f"[Logger] Saved {filename}: {description}")

    def _wrap_text(self, text: str, width: int = 100) -> str:
        """
        Wrap long text to specified width while preserving paragraphs.

        Args:
            text: Text to wrap
            width: Maximum line width (default 100 for readability)

        Returns:
            Wrapped text with preserved paragraph structure
        """
        # Split into paragraphs
        paragraphs = text.split('\n')
        wrapped_paragraphs = []

        for para in paragraphs:
            if para.strip():
                # Wrap each paragraph
                wrapped = textwrap.fill(
                    para,
                    width=width,
                    break_long_words=False,
                    break_on_hyphens=False
                )
                wrapped_paragraphs.append(wrapped)
            else:
                # Preserve blank lines
                wrapped_paragraphs.append('')

        return '\n'.join(wrapped_paragraphs)

    def _generate_transcript(self) -> None:
        """Generate a human-friendly markdown transcript with wrapped text."""
        filepath = self.session_dir / "readable_transcript.md"

        with open(filepath, "w", encoding="utf-8") as f:
            # Header
            f.write(f"# Conversation Transcript\n\n")
            f.write(f"**Session**: {self.metadata.get('timestamp')}\n\n")

            if "inspiration" in self.metadata:
                f.write(f"**Inspiration**:\n```\n")
                inspiration_text = self._wrap_text(str(self.metadata['inspiration']), width=80)
                f.write(inspiration_text)
                f.write("\n```\n\n")

            f.write("---\n\n")

            # Group exchanges by phase
            current_phase = None
            for exchange in self.exchanges:
                phase = exchange["phase"]

                # New phase header
                if phase != current_phase:
                    current_phase = phase
                    f.write(f"\n## Phase: {phase.upper()}\n\n")

                # Exchange
                speaker = exchange["speaker"]
                archetype = exchange["archetype"]
                content = exchange["content"]
                turn = exchange["turn"]

                f.write(f"### Turn {turn}: {speaker} — {archetype}\n\n")

                # Wrap content for readability
                wrapped_content = self._wrap_text(content, width=100)
                f.write(f"{wrapped_content}\n\n")
                f.write("---\n\n")

            # Final summary
            f.write("\n## Session Summary\n\n")
            f.write(f"- **Total Exchanges**: {len(self.exchanges)}\n")
            f.write(f"- **Duration**: {self.metadata.get('session_start')} to {self.metadata.get('session_end')}\n")

            if "ideas" in self.metadata:
                f.write(f"\n### Generated Ideas\n\n")
                f.write("```json\n")
                f.write(json.dumps(self.metadata["ideas"], indent=2))
                f.write("\n```\n")

        print(f"[Logger] Saved readable_transcript.md: Human-friendly transcript")

    def _generate_extended_transcript(self) -> None:
        """
        Generate extended transcript showing input prompts before each response.

        Pairs each exchange with the corresponding prompt input by matching
        phase, turn, and speaker.
        """
        filepath = self.session_dir / "readable_transcript_extended.md"

        # Build lookup for prompt inputs: (phase, turn, speaker) -> prompt_input
        prompt_lookup = {}
        for prompt_input in self.prompt_inputs:
            key = (prompt_input["phase"], prompt_input["turn"], prompt_input["speaker"])
            prompt_lookup[key] = prompt_input

        with open(filepath, "w", encoding="utf-8") as f:
            # Header
            f.write(f"# Extended Conversation Transcript\n\n")
            f.write(f"**Session**: {self.metadata.get('timestamp')}\n\n")

            if "inspiration" in self.metadata:
                f.write(f"**Inspiration**:\n```\n")
                inspiration_text = self._wrap_text(str(self.metadata['inspiration']), width=80)
                f.write(inspiration_text)
                f.write("\n```\n\n")

            f.write("This transcript shows the complete input prompt before each persona response.\n\n")
            f.write("---\n\n")

            # Group exchanges by phase
            current_phase = None
            for exchange in self.exchanges:
                phase = exchange["phase"]

                # New phase header
                if phase != current_phase:
                    current_phase = phase
                    f.write(f"\n## Phase: {phase.upper()}\n\n")

                # Exchange details
                speaker = exchange["speaker"]
                archetype = exchange["archetype"]
                content = exchange["content"]
                turn = exchange["turn"]

                f.write(f"### Turn {turn}: {speaker} — {archetype}\n\n")

                # Look up corresponding prompt input
                key = (phase, turn, speaker)
                if key in prompt_lookup:
                    prompt_input = prompt_lookup[key]
                    system_message = prompt_input.get("system_message", "")
                    enhanced_prompt = prompt_input.get("enhanced_prompt", "")

                    f.write(f"#### Input Prompt\n\n")
                    f.write(f"**System Message:**\n```\n{system_message}\n```\n\n")
                    f.write(f"**Context Passed:**\n```\n{enhanced_prompt}\n```\n\n")

                # The response
                f.write(f"#### Response\n\n")
                wrapped_content = self._wrap_text(content, width=100)
                f.write(f"{wrapped_content}\n\n")
                f.write("---\n\n")

            # Final summary
            f.write("\n## Session Summary\n\n")
            f.write(f"- **Total Exchanges**: {len(self.exchanges)}\n")
            f.write(f"- **Duration**: {self.metadata.get('session_start')} to {self.metadata.get('session_end')}\n")

            if "ideas" in self.metadata:
                f.write(f"\n### Generated Ideas\n\n")
                f.write("```json\n")
                f.write(json.dumps(self.metadata["ideas"], indent=2))
                f.write("\n```\n")

        print(f"[Logger] Saved readable_transcript_extended.md: Transcript with prompt inputs")
