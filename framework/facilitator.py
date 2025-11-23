"""
FacilitatorAgent - Orchestrates multi-persona conversations.

The facilitator is responsible for:
1. Selecting relevant personas for each phase
2. Deciding who should speak next
3. Determining when phase objectives are met
4. Detecting repetition and enforcing novelty
"""

import json
from typing import Dict, List, Optional, Any, Set
from openai import OpenAI


def safe_print(text: str) -> None:
    """Print text with unicode handling for Windows console."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Replace problematic unicode characters with ASCII equivalents
        safe_text = text.encode('ascii', 'replace').decode('ascii')
        print(safe_text)


def extract_key_phrases(text: str, max_phrases: int = 5) -> Set[str]:
    """
    Extract key phrases (3-5 word sequences) from text for repetition detection.

    Args:
        text: Input text to extract phrases from
        max_phrases: Maximum number of phrases to extract

    Returns:
        Set of key phrases (lowercase, normalized)
    """
    # Simple extraction: get 3-5 word sequences
    words = text.lower().split()
    phrases = set()

    # Extract 3-word sequences
    for i in range(len(words) - 2):
        phrase = " ".join(words[i:i+3])
        phrases.add(phrase)
        if len(phrases) >= max_phrases:
            break

    return phrases


def detect_repetition(current_text: str, previous_texts: List[str], threshold: float = 0.3) -> bool:
    """
    Detect if current text repeats content from previous texts.

    Args:
        current_text: Current speaker's text
        previous_texts: List of previous texts from same speaker
        threshold: Similarity threshold (0.0-1.0) to consider repetition

    Returns:
        True if repetition detected, False otherwise
    """
    if not previous_texts:
        return False

    current_phrases = extract_key_phrases(current_text, max_phrases=10)

    for prev_text in previous_texts[-3:]:  # Check last 3 turns only
        prev_phrases = extract_key_phrases(prev_text, max_phrases=10)

        # Calculate overlap
        if current_phrases and prev_phrases:
            overlap = len(current_phrases & prev_phrases)
            similarity = overlap / len(current_phrases)

            if similarity >= threshold:
                return True

    return False


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
        # Track speaker history for repetition detection
        self.speaker_history: Dict[str, List[str]] = {}  # {speaker_name: [previous_responses]}

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

        decision_prompt = f"""You are a meeting facilitator creating NATURAL, ENGAGING conversation flow.

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

Decide who should speak next to create NATURAL conversation flow:

PRIORITIZE NATURAL DIALOGUE:
1. If someone was directly ASKED or ADDRESSED, give them the floor to respond
2. If a claim was made, let the CONTRARIAN or relevant expert challenge it
3. If someone DISAGREED or PUSHED BACK, allow that person to respond/defend
4. Allow 2-3 turn EXCHANGES between same speakers when they're actively debating
5. Route to domain experts when technical/financial/design questions arise

ALSO CONSIDER:
- Balance of participation (but natural back-and-forth beats forced rotation)
- Phase goal progress
- Avoiding the same person speaking 4+ times in a row (unless in active debate)
- Mix quick reactions with deeper analysis

PHASE COMPLETION:
Mark phase_complete=true ONLY if the desired outcome is clearly achieved in the exchanges.

Respond ONLY with a JSON object:
{{
  "phase_complete": true/false,
  "next_speaker": "persona_name" or null,
  "reasoning": "Why this creates natural flow (e.g., 'Designer asked Market Researcher a question' or 'Contrarian challenged Founder's assumption')"
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

    def check_for_repetition(
        self,
        speaker_name: str,
        response_content: str
    ) -> Optional[str]:
        """
        Check if speaker is repeating previous arguments.

        Args:
            speaker_name: Name of the speaker
            response_content: Current response content

        Returns:
            Warning message if repetition detected, None otherwise
        """
        # Get speaker's history
        previous_responses = self.speaker_history.get(speaker_name, [])

        # Detect repetition
        if detect_repetition(response_content, previous_responses):
            warning = (
                f"[Facilitator] {speaker_name}, you repeated a previous point. "
                "Please revise by adding a novel nuance or modifying your belief_state."
            )
            return warning

        # Update history
        if speaker_name not in self.speaker_history:
            self.speaker_history[speaker_name] = []
        self.speaker_history[speaker_name].append(response_content)

        # Keep only last 5 responses per speaker
        if len(self.speaker_history[speaker_name]) > 5:
            self.speaker_history[speaker_name] = self.speaker_history[speaker_name][-5:]

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
