"""
ConversationMonitor - Real-time visibility for multi-persona conversations

Provides progress tracking, token usage monitoring, and time estimation
for long-running conversations.
"""

import time
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class ConversationMonitor:
    """
    Monitor and display real-time progress during multi-persona conversations.

    Tracks:
    - Phase progress (which phase, how many complete)
    - Turn progress (current turn / max turns per phase)
    - Token usage and estimated cost
    - Time elapsed and estimated remaining
    - Recent exchanges for context

    Example:
        >>> monitor = ConversationMonitor()
        >>> monitor.on_phase_start("ideation", "Generate startup ideas")
        >>> monitor.on_turn_start("Product Designer", 1, 10)
        >>> monitor.on_turn_complete("Product Designer", tokens_used=250, time_elapsed=2.3)
        >>> monitor.on_phase_complete("ideation", "3 ideas generated", 8, 45.2)
        >>> monitor.display_summary()
    """

    def __init__(
        self,
        cost_per_1k_tokens: float = 0.002,  # Rough estimate for GPT-4o-mini
        enable_display: bool = True
    ):
        """
        Initialize conversation monitor.

        Args:
            cost_per_1k_tokens: Estimated cost per 1000 tokens (for cost estimation)
            enable_display: If False, disable all output (silent mode)
        """
        self.cost_per_1k_tokens = cost_per_1k_tokens
        self.enable_display = enable_display

        # Session tracking
        self.session_start_time = time.time()
        self.total_tokens = 0
        self.total_turns = 0
        self.phases_completed = 0

        # Current phase tracking
        self.current_phase_id: Optional[str] = None
        self.current_phase_start_time: Optional[float] = None
        self.current_phase_tokens = 0
        self.current_phase_turns = 0

        # Phase history
        self.phase_history: List[Dict[str, Any]] = []

        # Recent exchanges (for context)
        self.recent_exchanges: List[Dict[str, str]] = []
        self.max_recent_exchanges = 3

    def on_phase_start(self, phase_id: str, goal: str) -> None:
        """
        Called when a new phase begins.

        Args:
            phase_id: Identifier for the phase (e.g., "ideation", "design")
            goal: What this phase is trying to accomplish
        """
        if not self.enable_display:
            return

        self.current_phase_id = phase_id
        self.current_phase_start_time = time.time()
        self.current_phase_tokens = 0
        self.current_phase_turns = 0

        # Display phase banner
        print(f"\n{'='*70}")
        print(f"{'='*70}")
        print(f"  PHASE: {phase_id.upper()}")
        print(f"  Goal: {goal}")
        print(f"{'='*70}")
        print(f"{'='*70}\n")

    def on_turn_start(self, speaker: str, turn_num: int, max_turns: int) -> None:
        """
        Called when a persona starts speaking.

        Args:
            speaker: Name of the persona speaking
            turn_num: Current turn number (0-indexed)
            max_turns: Maximum turns for this phase
        """
        if not self.enable_display:
            return

        # Progress indicator
        progress_pct = (turn_num / max_turns) * 100 if max_turns > 0 else 0
        bar_length = 30
        filled = int(bar_length * turn_num / max_turns) if max_turns > 0 else 0
        bar = '#' * filled + '-' * (bar_length - filled)

        elapsed = self._format_duration(time.time() - self.session_start_time)

        print(f"\n+-- Turn {turn_num + 1}/{max_turns} [{bar}] {progress_pct:.0f}%")
        print(f"|   Speaker: {speaker}")
        print(f"|   Phase: {self.current_phase_id} | Elapsed: {elapsed}")
        print(f"+-- Tokens: {self.total_tokens:,} | Cost: ${self._estimate_cost():.4f}\n")

    def on_turn_complete(
        self,
        speaker: str,
        tokens_used: Optional[int] = None,
        time_elapsed: Optional[float] = None
    ) -> None:
        """
        Called when a persona finishes speaking.

        Args:
            speaker: Name of the persona that spoke
            tokens_used: Approximate tokens used in this turn (if known)
            time_elapsed: Time taken for this turn in seconds (if known)
        """
        self.total_turns += 1
        self.current_phase_turns += 1

        if tokens_used:
            self.total_tokens += tokens_used
            self.current_phase_tokens += tokens_used

        # Track recent exchange
        self.recent_exchanges.append({
            "speaker": speaker,
            "phase": self.current_phase_id or "unknown",
            "tokens": tokens_used or 0
        })

        # Keep only recent exchanges
        if len(self.recent_exchanges) > self.max_recent_exchanges:
            self.recent_exchanges.pop(0)

    def on_phase_complete(
        self,
        phase_id: str,
        summary: str,
        total_turns: int,
        total_time: float
    ) -> None:
        """
        Called when a phase completes.

        Args:
            phase_id: Identifier for the completed phase
            summary: Summary of what was accomplished
            total_turns: Total turns in this phase
            total_time: Total time for this phase in seconds
        """
        if not self.enable_display:
            return

        self.phases_completed += 1

        # Store phase history
        self.phase_history.append({
            "phase_id": phase_id,
            "turns": total_turns,
            "time": total_time,
            "tokens": self.current_phase_tokens,
            "summary": summary
        })

        # Display phase summary
        print(f"\n{'-'*70}")
        print(f"[OK] PHASE COMPLETE: {phase_id.upper()}")
        print(f"{'-'*70}")
        print(f"Turns: {total_turns}")
        print(f"Time: {self._format_duration(total_time)}")
        print(f"Tokens: {self.current_phase_tokens:,}")
        print(f"\nSummary: {summary[:200]}{'...' if len(summary) > 200 else ''}")
        print(f"{'-'*70}\n")

        # Reset phase tracking
        self.current_phase_id = None
        self.current_phase_start_time = None
        self.current_phase_tokens = 0
        self.current_phase_turns = 0

    def display_summary(self) -> None:
        """
        Display final session summary with all statistics.
        """
        if not self.enable_display:
            return

        total_time = time.time() - self.session_start_time
        avg_time_per_turn = total_time / self.total_turns if self.total_turns > 0 else 0

        print(f"\n{'='*70}")
        print(f"{'='*70}")
        print(f"  SESSION COMPLETE")
        print(f"{'='*70}")
        print(f"{'='*70}\n")

        print(f"[STATISTICS]")
        print(f"{'-'*70}")
        print(f"Phases completed:      {self.phases_completed}")
        print(f"Total turns:           {self.total_turns}")
        print(f"Total tokens:          {self.total_tokens:,}")
        print(f"Estimated cost:        ${self._estimate_cost():.4f}")
        print(f"Total time:            {self._format_duration(total_time)}")
        print(f"Avg time per turn:     {self._format_duration(avg_time_per_turn)}")
        print(f"{'-'*70}\n")

        # Phase breakdown
        if self.phase_history:
            print(f"[PHASE BREAKDOWN]")
            print(f"{'-'*70}")
            for phase in self.phase_history:
                print(f"\n{phase['phase_id'].upper()}")
                print(f"  Turns: {phase['turns']}")
                print(f"  Time: {self._format_duration(phase['time'])}")
                print(f"  Tokens: {phase['tokens']:,}")
            print(f"\n{'-'*70}\n")

    def _estimate_cost(self) -> float:
        """Estimate total cost based on tokens used."""
        return (self.total_tokens / 1000.0) * self.cost_per_1k_tokens

    def _format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format."""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            return f"{hours}h {minutes}m"

    def get_stats(self) -> Dict[str, Any]:
        """
        Get current session statistics as a dictionary.

        Returns:
            Dictionary with tokens, turns, time, cost, phases
        """
        total_time = time.time() - self.session_start_time

        return {
            "total_tokens": self.total_tokens,
            "total_turns": self.total_turns,
            "phases_completed": self.phases_completed,
            "total_time_seconds": total_time,
            "estimated_cost": self._estimate_cost(),
            "phase_history": self.phase_history
        }
