"""
ConversationReplayer - Navigate and inspect past conversations

Provides read-only navigation through completed conversations, allowing
inspection of:
- Individual exchanges and turns
- Persona states and summaries at any point
- Facilitator decisions and reasoning
- Shared context evolution
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class ConversationReplayer:
    """
    Navigate and inspect past conversations (read-only).

    Example:
        >>> replayer = ConversationReplayer.from_session("conversation_logs/session_xyz")
        >>> replayer.goto_phase("ideation")
        >>> replayer.goto_turn(5)
        >>> replayer.current_exchange()
        >>> replayer.view_persona_summary("founder")
    """

    def __init__(self, session_path: str):
        """
        Initialize replayer from a session log directory.

        Args:
            session_path: Path to session folder (e.g., "conversation_logs/session_20251028")
        """
        self.session_path = Path(session_path)
        if not self.session_path.exists():
            raise FileNotFoundError(f"Session path not found: {session_path}")

        # Load all log files
        self.metadata = self._load_json("session_metadata.json")
        self.exchanges = self._load_json("full_conversation.json")
        self.facilitator_decisions = self._load_json("facilitator_decisions.json")
        self.persona_summaries = self._load_json("persona_summaries.json")

        # Current position
        self.current_turn_index = 0
        self.current_phase = None

        # Extract session info
        self.session_id = self.session_path.name
        self.phases = self.metadata.get("phases", [])
        self.total_turns = len(self.exchanges)

        # Update current phase from first exchange
        if self.exchanges:
            self.current_phase = self.exchanges[0].get("phase")

    @classmethod
    def from_session(cls, session_path: str) -> 'ConversationReplayer':
        """
        Create replayer instance from session path.

        Args:
            session_path: Path to session folder

        Returns:
            ConversationReplayer instance
        """
        return cls(session_path)

    def _load_json(self, filename: str) -> Any:
        """Load JSON file from session directory."""
        file_path = self.session_path / filename
        if not file_path.exists():
            return {} if filename.endswith('.json') else []

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # =========================================================================
    # Navigation Methods
    # =========================================================================

    def goto_phase(self, phase_id: str) -> bool:
        """
        Jump to the first turn of a specific phase.

        Args:
            phase_id: Phase identifier (e.g., "ideation", "research")

        Returns:
            True if phase found, False otherwise
        """
        for i, exchange in enumerate(self.exchanges):
            if exchange.get("phase") == phase_id:
                self.current_turn_index = i
                self.current_phase = phase_id
                print(f"[OK] Jumped to phase '{phase_id}' at turn {i}")
                return True

        print(f"[!] Phase '{phase_id}' not found")
        return False

    def goto_turn(self, turn_index: int) -> bool:
        """
        Jump to a specific turn number.

        Args:
            turn_index: Turn index (0-based)

        Returns:
            True if turn exists, False otherwise
        """
        if 0 <= turn_index < self.total_turns:
            self.current_turn_index = turn_index
            self.current_phase = self.exchanges[turn_index].get("phase")
            print(f"[OK] Jumped to turn {turn_index} (phase: {self.current_phase})")
            return True
        else:
            print(f"[!] Turn {turn_index} out of range (0-{self.total_turns-1})")
            return False

    def next_turn(self) -> bool:
        """
        Move to the next turn.

        Returns:
            True if moved, False if already at end
        """
        if self.current_turn_index < self.total_turns - 1:
            self.current_turn_index += 1
            self.current_phase = self.exchanges[self.current_turn_index].get("phase")
            print(f"[OK] Advanced to turn {self.current_turn_index}")
            return True
        else:
            print(f"[!] Already at final turn ({self.total_turns-1})")
            return False

    def prev_turn(self) -> bool:
        """
        Move to the previous turn.

        Returns:
            True if moved, False if already at start
        """
        if self.current_turn_index > 0:
            self.current_turn_index -= 1
            self.current_phase = self.exchanges[self.current_turn_index].get("phase")
            print(f"[OK] Moved back to turn {self.current_turn_index}")
            return True
        else:
            print(f"[!] Already at first turn (0)")
            return False

    def goto_start(self) -> None:
        """Jump to the start of the conversation."""
        self.current_turn_index = 0
        if self.exchanges:
            self.current_phase = self.exchanges[0].get("phase")
        print(f"[OK] Jumped to start (turn 0)")

    def goto_end(self) -> None:
        """Jump to the end of the conversation."""
        self.current_turn_index = self.total_turns - 1
        if self.exchanges:
            self.current_phase = self.exchanges[-1].get("phase")
        print(f"[OK] Jumped to end (turn {self.current_turn_index})")

    # =========================================================================
    # Inspection Methods
    # =========================================================================

    def current_exchange(self) -> Dict[str, Any]:
        """
        Get the current exchange.

        Returns:
            Dict with exchange data (speaker, content, phase, etc.)
        """
        if 0 <= self.current_turn_index < self.total_turns:
            return self.exchanges[self.current_turn_index]
        return {}

    def view_exchange(self, formatted: bool = True) -> None:
        """
        Display the current exchange.

        Args:
            formatted: If True, pretty-print the exchange
        """
        exchange = self.current_exchange()

        if not exchange:
            print("[!] No exchange at current position")
            return

        turn = exchange.get("turn", self.current_turn_index)
        phase = exchange.get("phase", "unknown")
        speaker = exchange.get("speaker", "Unknown")
        archetype = exchange.get("archetype", "")
        content = exchange.get("content", "")

        if formatted:
            print(f"\n{'='*70}")
            print(f"Turn {turn} | Phase: {phase}")
            print(f"Speaker: {speaker} ({archetype})")
            print(f"{'='*70}")
            print(content[:500] + ("..." if len(content) > 500 else ""))
            print(f"{'='*70}\n")
        else:
            print(json.dumps(exchange, indent=2))

    def view_persona_summary(self, persona_name: str) -> Optional[Dict[str, Any]]:
        """
        View a persona's summary at the current phase.

        Args:
            persona_name: Name of persona to inspect

        Returns:
            Persona summary dict if available, None otherwise
        """
        if not self.persona_summaries:
            print("[!] No persona summaries available")
            return None

        # Find summary for current phase
        phase_summaries = self.persona_summaries.get(self.current_phase, {})

        if persona_name in phase_summaries:
            summary = phase_summaries[persona_name]
            print(f"\n[Persona Summary: {persona_name} at phase '{self.current_phase}']")
            print(json.dumps(summary, indent=2))
            return summary
        else:
            print(f"[!] No summary found for '{persona_name}' in phase '{self.current_phase}'")
            return None

    def view_facilitator_decision(self, turn_index: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        View the facilitator's decision at a specific turn.

        Args:
            turn_index: Turn to inspect (defaults to current turn)

        Returns:
            Decision dict if found, None otherwise
        """
        if turn_index is None:
            turn_index = self.current_turn_index

        # Find decisions around this turn
        relevant_decisions = []

        for decision in self.facilitator_decisions:
            # Match by phase and approximate timing
            phase = decision.get("phase")
            if phase == self.current_phase:
                relevant_decisions.append(decision)

        if relevant_decisions:
            print(f"\n[Facilitator Decisions for phase '{self.current_phase}']:")
            for i, decision in enumerate(relevant_decisions):
                decision_type = decision.get("type", "unknown")
                decision_value = decision.get("decision", "")
                reasoning = decision.get("reasoning", "No reasoning provided")

                print(f"\n{i+1}. {decision_type}")
                print(f"   Decision: {decision_value}")
                print(f"   Reasoning: {reasoning}")

            return relevant_decisions[0]
        else:
            print(f"[!] No facilitator decisions found for phase '{self.current_phase}'")
            return None

    def view_shared_context(self) -> Dict[str, Any]:
        """
        View the shared context (from metadata).

        Returns:
            Dict with shared context data
        """
        # Shared context evolves during conversation but we only have final state
        print(f"\n[Shared Context - Final State]:")

        context = {
            "inspiration": self.metadata.get("inspiration", ""),
            "number_of_ideas": self.metadata.get("number_of_ideas", 0),
            "ideas": self.metadata.get("ideas", []),
            "mode": self.metadata.get("mode", ""),
            "model": self.metadata.get("model", "")
        }

        print(json.dumps(context, indent=2))
        return context

    def list_phases(self) -> List[str]:
        """
        List all phases in the conversation.

        Returns:
            List of phase IDs
        """
        phases = list(set(ex.get("phase") for ex in self.exchanges))
        print(f"\n[Phases]: {', '.join(phases)}")
        return phases

    def list_personas(self) -> List[str]:
        """
        List all personas that participated.

        Returns:
            List of persona names
        """
        personas = list(set(ex.get("speaker") for ex in self.exchanges))
        print(f"\n[Personas]: {', '.join(personas)}")
        return personas

    # =========================================================================
    # Export Methods
    # =========================================================================

    def export_snapshot(self, output_path: str) -> None:
        """
        Export current state as JSON snapshot.

        Args:
            output_path: Path to save snapshot
        """
        current_exchange = self.current_exchange()

        snapshot = {
            "session_id": self.session_id,
            "current_position": {
                "turn_index": self.current_turn_index,
                "phase": self.current_phase,
                "total_turns": self.total_turns
            },
            "current_exchange": current_exchange,
            "metadata": self.metadata
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2)

        print(f"[OK] Snapshot saved to: {output_path}")

    def get_phase_exchanges(self, phase_id: str) -> List[Dict[str, Any]]:
        """
        Get all exchanges for a specific phase.

        Args:
            phase_id: Phase identifier

        Returns:
            List of exchanges in that phase
        """
        return [
            ex for ex in self.exchanges
            if ex.get("phase") == phase_id
        ]

    def search_content(self, query: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """
        Search for exchanges containing specific text.

        Args:
            query: Text to search for
            case_sensitive: Whether search is case-sensitive

        Returns:
            List of matching exchanges with turn index
        """
        results = []

        for i, exchange in enumerate(self.exchanges):
            content = exchange.get("content", "")

            if case_sensitive:
                match = query in content
            else:
                match = query.lower() in content.lower()

            if match:
                results.append({
                    "turn_index": i,
                    "phase": exchange.get("phase"),
                    "speaker": exchange.get("speaker"),
                    "content_preview": content[:200] + "..." if len(content) > 200 else content
                })

        if results:
            print(f"\n[Found {len(results)} matches for '{query}']:")
            for result in results:
                print(f"  Turn {result['turn_index']} ({result['phase']}) - {result['speaker']}")
        else:
            print(f"[!] No matches found for '{query}'")

        return results

    # =========================================================================
    # Summary Methods
    # =========================================================================

    def display_summary(self) -> None:
        """Display a summary of the conversation."""
        print(f"\n{'='*70}")
        print(f"CONVERSATION REPLAY SUMMARY")
        print(f"{'='*70}")
        print(f"Session ID: {self.session_id}")
        print(f"Mode: {self.metadata.get('mode', 'unknown')}")
        print(f"Model: {self.metadata.get('model', 'unknown')}")
        print(f"Total Turns: {self.total_turns}")
        print(f"Total Phases: {len(set(ex.get('phase') for ex in self.exchanges))}")
        print(f"\nCurrent Position:")
        print(f"  Turn: {self.current_turn_index}/{self.total_turns-1}")
        print(f"  Phase: {self.current_phase}")
        print(f"{'='*70}\n")
