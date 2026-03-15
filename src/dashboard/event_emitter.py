"""
Dashboard event emitter and logger.

DashboardEventEmitter — ConversationMonitor subclass that pushes structured
JSON events onto a per-session asyncio.Queue (thread-safe via call_soon_threadsafe).

DashboardLogger — ConversationLogger subclass that also pushes `message` and
`prompt_input` events onto the same queue.

Both are instantiated per-session by the FastAPI server and injected into
multiple_llm_idea_generator().
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from framework.monitor import ConversationMonitor
from framework.logger import ConversationLogger


class DashboardEventEmitter(ConversationMonitor):
    """
    Subclass of ConversationMonitor that emits events to the browser via an
    asyncio.Queue shared with the WebSocket handler.

    Because Assembly's generator runs inside asyncio.run() (a separate event
    loop in a ThreadPoolExecutor thread), _emit() uses call_soon_threadsafe to
    cross the thread boundary safely.
    """

    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        super().__init__(enable_display=False)  # silent — no console output
        self.queue = queue
        self.loop = loop

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event: Dict[str, Any]) -> None:
        """Thread-safe push to the asyncio queue living in the FastAPI loop."""
        try:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, event)
        except Exception:
            pass  # Never let emission errors crash the generator

    # ------------------------------------------------------------------
    # Existing ConversationMonitor hooks — emit events + keep base tracking
    # ------------------------------------------------------------------

    def on_phase_start(self, phase_id: str, goal: str) -> None:
        # Call base for internal tracking (tokens, times, etc.)
        # Base reads enable_display=False so produces no console output.
        super().on_phase_start(phase_id, goal)
        self._emit({
            "type": "phase_start",
            "phase_id": phase_id,
            "goal": goal,
            "ts": time.time(),
        })

    def on_turn_start(self, speaker: str, turn_num: int, max_turns: int) -> None:
        super().on_turn_start(speaker, turn_num, max_turns)
        self._emit({
            "type": "turn_start",
            "speaker": speaker,
            "turn_num": turn_num,
            "max_turns": max_turns,
            "ts": time.time(),
        })

    def on_turn_complete(
        self,
        speaker: str,
        tokens_used: Optional[int] = None,
        time_elapsed: Optional[float] = None,
    ) -> None:
        super().on_turn_complete(speaker, tokens_used, time_elapsed)
        self._emit({
            "type": "turn_complete",
            "speaker": speaker,
            "tokens_used": tokens_used,
            "ts": time.time(),
        })

    def on_phase_complete(
        self,
        phase_id: str,
        summary: str,
        total_turns: int,
        total_time: float,
        ideas_in_play: Optional[List[str]] = None,
        ideas_rejected_count: int = 0,
        nuance_count: int = 0,
    ) -> None:
        super().on_phase_complete(phase_id, summary, total_turns, total_time)
        self._emit({
            "type": "phase_complete",
            "phase_id": phase_id,
            "summary": summary,
            "total_turns": total_turns,
            "total_time": total_time,
            "ideas_in_play": ideas_in_play or [],
            "ideas_rejected_count": ideas_rejected_count,
            "nuance_count": nuance_count,
            "ts": time.time(),
        })

    def display_summary(self) -> None:
        # Suppress console output; summary comes through run_complete event
        pass

    # ------------------------------------------------------------------
    # New extension hooks
    # ------------------------------------------------------------------

    def on_phases_generated(self, phases: List[Dict[str, Any]]) -> None:
        self._emit({
            "type": "phases_generated",
            "phases": phases,
            "ts": time.time(),
        })

    def on_personas_generated(self, phase_id: str, personas: List[str]) -> None:
        self._emit({
            "type": "personas_generated",
            "phase_id": phase_id,
            "personas": personas,
            "ts": time.time(),
        })

    def on_mediator_intervention(
        self,
        speaker: str,
        content: str,
        scenarios: List[Any],
    ) -> None:
        self._emit({
            "type": "mediator_intervention",
            "speaker": speaker,
            "content": content,
            "scenarios": scenarios,
            "ts": time.time(),
        })

    def on_memory_update(self, shared_memory: str) -> None:
        self._emit({
            "type": "memory_update",
            "shared_memory": shared_memory,
            "ts": time.time(),
        })

    def on_idea_tracked(
        self,
        title: str,
        status: str,
        overview: str,
        rejection_reason: Optional[str],
        example: str = "",
        why_it_works: Optional[List[Any]] = None,
        why_it_might_fail: Optional[List[Any]] = None,
    ) -> None:
        self._emit({
            "type": "idea_tracked",
            "title": title,
            "status": status,
            "overview": overview,
            "rejection_reason": rejection_reason,
            "example": example,
            "why_it_works": why_it_works or [],
            "why_it_might_fail": why_it_might_fail or [],
            "ts": time.time(),
        })

    def on_gap_nudge(self, content: str) -> None:
        self._emit({
            "type": "gap_nudge",
            "content": content,
            "ts": time.time(),
        })

    def on_persona_states_update(self, phase_id: str, turn: int, personas: List[Dict]) -> None:
        self._emit({
            "type": "persona_states",
            "phase_id": phase_id,
            "turn": turn,
            "personas": personas,
            "ts": time.time(),
        })

    def on_nuances_update(self, nuances: List[str]) -> None:
        self._emit({
            "type": "nuances_update",
            "nuances": nuances,
            "ts": time.time(),
        })

    def on_mediator_log_update(self, mediation_log: Dict, scenario_history: List) -> None:
        self._emit({
            "type": "mediator_log",
            "mediation_log": mediation_log,
            "scenario_history": scenario_history,
            "ts": time.time(),
        })


class DashboardLogger(ConversationLogger):
    """
    Subclass of ConversationLogger that additionally pushes `message` and
    `prompt_input` events onto the same per-session asyncio.Queue.
    """

    def __init__(
        self,
        queue: asyncio.Queue,
        loop: asyncio.AbstractEventLoop,
        base_dir: str = "conversation_logs",
    ):
        super().__init__(base_dir=base_dir)
        self.queue = queue
        self.loop = loop

    def _emit(self, event: Dict[str, Any]) -> None:
        try:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, event)
        except Exception:
            pass

    def log_exchange(
        self,
        phase_id: str,
        turn: int,
        speaker: str,
        archetype: str,
        content: str,
    ) -> None:
        super().log_exchange(phase_id, turn, speaker, archetype, content)
        self._emit({
            "type": "message",
            "phase": phase_id,
            "turn": turn,
            "speaker": speaker,
            "archetype": archetype,
            "content": content,
            "ts": time.time(),
        })

    def log_prompt_input(
        self,
        phase_id: str,
        turn: int,
        speaker: str,
        archetype: str,
        prompt_data: Dict[str, Any],
    ) -> None:
        super().log_prompt_input(phase_id, turn, speaker, archetype, prompt_data)
        self._emit({
            "type": "prompt_input",
            "phase": phase_id,
            "turn": turn,
            "speaker": speaker,
            "archetype": archetype,
            "system_message": prompt_data.get("system_message", ""),
            "enhanced_prompt": prompt_data.get("enhanced_prompt", ""),
            "ts": time.time(),
        })
