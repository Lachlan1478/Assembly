"""
FacilitatorAgent - Orchestrates multi-persona conversations.

The facilitator is responsible for:
1. Selecting relevant personas for each phase
2. Deciding who should speak next
3. Determining when phase objectives are met
"""

import json
from typing import Dict, List, Optional, Any
from openai import OpenAI


def safe_print(text: str) -> None:
    """Print text with unicode handling for Windows console."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace problematic unicode characters with ASCII equivalents
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text)


class FacilitatorAgent:
    """
    Orchestrates conversations between personas.
    Uses LLM to make intelligent decisions about conversation flow.
    """

    def __init__(self, model_name: str = "gpt-4o-mini"):
        """
        Initialize the facilitator.

        Args:
            model_name: LLM model to use for facilitation decisions
        """
        self.model_name = model_name
        self.client = OpenAI()

    def select_personas_for_phase(
        self,
        phase: Dict[str, Any],
        available_personas: Dict[str, Any]
    ) -> List[str]:
        """
        Select which personas should participate in a given phase.

        Args:
            phase: Dict with phase_id, goal, desired_outcome
            available_personas: Dict mapping persona names to Persona instances

        Returns:
            List of persona names (keys from available_personas) to include
        """
        # Build persona descriptions
        persona_descriptions = []
        for name, persona in available_personas.items():
            persona_descriptions.append({
                "name": name,
                "archetype": persona.archetype,
                "purpose": persona.purpose,
                "strengths": persona.strengths
            })

        selection_prompt = f"""You are a meeting facilitator selecting participants for a phase.

PHASE INFORMATION:
- Phase ID: {phase.get('phase_id')}
- Goal: {phase.get('goal')}
- Desired Outcome: {phase.get('desired_outcome')}

AVAILABLE PERSONAS:
{json.dumps(persona_descriptions, indent=2)}

Select the 3-6 most relevant personas for this phase based on:
1. Their archetype and purpose alignment with phase goal
2. Their strengths matching the desired outcome
3. Diversity of perspectives needed

Respond ONLY with a JSON object:
{{
  "selected_personas": ["persona1", "persona2", ...],
  "reasoning": "Brief explanation of why these personas were chosen"
}}

Use the exact "name" values from the available personas list."""

        messages = [
            {
                "role": "system",
                "content": "You are an expert meeting facilitator. Select participants wisely based on phase objectives."
            },
            {
                "role": "user",
                "content": selection_prompt
            }
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )

            response_content = completion.choices[0].message.content.strip()
            result = json.loads(response_content)

            selected = result.get("selected_personas", [])
            reasoning = result.get("reasoning", "No reasoning provided")

            safe_print(f"\n[Facilitator] Selected personas for '{phase.get('phase_id')}': {', '.join(selected)}")
            safe_print(f"[Facilitator] Reasoning: {reasoning}\n")

            return selected

        except Exception as e:
            print(f"[!] Facilitator failed to select personas: {e}")
            # Fallback: return all personas
            return list(available_personas.keys())

    def decide_next_speaker(
        self,
        phase: Dict[str, Any],
        active_personas: Dict[str, Any],
        recent_exchanges: List[Dict[str, str]],
        shared_context: Dict[str, Any],
        turn_count: int,
        max_turns: int = 15
    ) -> Optional[str]:
        """
        Decide who should speak next in the conversation.

        Args:
            phase: Current phase information
            active_personas: Dict of personas participating in this phase
            recent_exchanges: List of recent speaker/content dicts
            shared_context: Current shared context
            turn_count: How many turns have occurred in this phase
            max_turns: Maximum allowed turns for this phase

        Returns:
            Name of persona who should speak next, or None if phase is complete
        """
        # Check if we've hit max turns
        if turn_count >= max_turns:
            print(f"[Facilitator] Max turns ({max_turns}) reached for phase '{phase.get('phase_id')}'")
            return None

        # Build persona list
        persona_list = []
        for name, persona in active_personas.items():
            persona_list.append({
                "name": name,
                "archetype": persona.archetype,
                "purpose": persona.purpose
            })

        # Format recent exchanges (last 5)
        recent_formatted = []
        for exchange in recent_exchanges[-5:]:
            recent_formatted.append(f"{exchange.get('speaker')}: {exchange.get('content')[:200]}...")

        decision_prompt = f"""You are a meeting facilitator managing conversation flow.

PHASE INFORMATION:
- Phase ID: {phase.get('phase_id')}
- Goal: {phase.get('goal')}
- Desired Outcome: {phase.get('desired_outcome')}
- Turns so far: {turn_count}/{max_turns}

ACTIVE PERSONAS:
{json.dumps(persona_list, indent=2)}

RECENT EXCHANGES:
{chr(10).join(recent_formatted) if recent_formatted else 'No exchanges yet'}

SHARED CONTEXT:
{json.dumps(shared_context, indent=2)}

Decide:
1. Is the phase goal achieved? (Check if desired outcome is met)
2. If not, who should speak next to move toward the goal?

Consider:
- Balance of participation (don't let one persona dominate)
- Phase goal progress
- Natural conversation flow
- Avoiding repetition

Respond ONLY with a JSON object:
{{
  "phase_complete": true/false,
  "next_speaker": "persona_name" or null,
  "reasoning": "Brief explanation"
}}

If phase_complete is true, set next_speaker to null.
Otherwise, choose from: {', '.join([p['name'] for p in persona_list]) if persona_list else 'none'}"""

        messages = [
            {
                "role": "system",
                "content": "You are an expert meeting facilitator managing conversation flow and ensuring objectives are met."
            },
            {
                "role": "user",
                "content": decision_prompt
            }
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )

            response_content = completion.choices[0].message.content.strip()
            result = json.loads(response_content)

            phase_complete = result.get("phase_complete", False)
            next_speaker = result.get("next_speaker")
            reasoning = result.get("reasoning", "No reasoning provided")

            if phase_complete:
                safe_print(f"[Facilitator] Phase '{phase.get('phase_id')}' complete: {reasoning}")
                return None
            else:
                safe_print(f"[Facilitator] Next speaker: {next_speaker} - {reasoning}")
                return next_speaker

        except Exception as e:
            print(f"[!] Facilitator failed to decide next speaker: {e}")
            # Fallback: if we have room, pick a random active persona
            if turn_count < max_turns and active_personas:
                fallback = list(active_personas.keys())[turn_count % len(active_personas)]
                print(f"[Facilitator] Fallback: selecting {fallback}")
                return fallback
            return None

    def summarize_phase(
        self,
        phase: Dict[str, Any],
        exchanges: List[Dict[str, str]],
        shared_context: Dict[str, Any]
    ) -> str:
        """
        Create a summary of what was accomplished in a phase.

        Args:
            phase: Phase information
            exchanges: All exchanges from this phase
            shared_context: Final shared context

        Returns:
            Summary text
        """
        exchanges_text = "\n".join([
            f"{ex.get('speaker')}: {ex.get('content')[:300]}"
            for ex in exchanges
        ])

        summary_prompt = f"""Summarize the outcomes of this meeting phase.

PHASE: {phase.get('phase_id')}
GOAL: {phase.get('goal')}

CONVERSATION:
{exchanges_text}

FINAL SHARED CONTEXT:
{json.dumps(shared_context, indent=2)}

Create a concise summary (2-3 sentences) of what was accomplished and key decisions made."""

        messages = [
            {
                "role": "system",
                "content": "You are a meeting facilitator creating phase summaries."
            },
            {
                "role": "user",
                "content": summary_prompt
            }
        ]

        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages
            )

            return completion.choices[0].message.content.strip()

        except Exception as e:
            print(f"[!] Failed to create phase summary: {e}")
            return f"Phase '{phase.get('phase_id')}' completed with {len(exchanges)} exchanges."
