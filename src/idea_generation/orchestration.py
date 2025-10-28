# idea_brainstorm_01c_orchestration.py
# Orchestration module: Meeting facilitator and conversation management

from typing import Dict, List, Any
from framework import Persona, FacilitatorAgent, ConversationLogger
from src.idea_generation.prompts import generate_dynamic_prompt
from src.idea_generation.extraction import extract_idea_title


def meeting_facilitator(
    all_personas: Dict[str, Persona],
    phases: List[Dict[str, Any]],
    shared_context: Dict[str, Any],
    facilitator: FacilitatorAgent,
    logger: ConversationLogger = None,
    enable_summary_updates: bool = True
) -> Dict[str, Any]:
    """
    Facilitator-directed conversation architecture with staged prompts.

    Args:
        all_personas: Dict mapping persona names to Persona instances
        phases: List of phase dicts with:
            - phase_id: str
            - goal: str (what should be accomplished)
            - desired_outcome: str (specific deliverable)
            - max_turns: int (optional, default 15)
        shared_context: Mutable dict for shared artifacts (ideas, decisions, etc.)
        facilitator: FacilitatorAgent instance
        logger: Optional ConversationLogger for comprehensive logging
        enable_summary_updates: If False, skip LLM calls for summary updates (fast mode)

    Returns:
        final shared_context with logs and results
    """
    logs = []
    all_phase_summaries = []

    for phase in phases:
        print(f"\n{'='*60}")
        print(f"=== Phase: {phase['phase_id'].upper()} ===")
        print(f"Goal: {phase.get('goal')}")
        print(f"{'='*60}\n")

        # Facilitator selects relevant personas for this phase
        selected_persona_names = facilitator.select_personas_for_phase(
            phase=phase,
            available_personas=all_personas
        )

        # Log persona selection
        if logger:
            logger.log_facilitator_decision(
                decision_type="persona_selection",
                phase_id=phase["phase_id"],
                decision=selected_persona_names,
                reasoning=f"Selected {len(selected_persona_names)} personas for phase '{phase['phase_id']}'"
            )

        # Get the actual Persona instances
        active_personas = {
            name: all_personas[name]
            for name in selected_persona_names
            if name in all_personas
        }

        if not active_personas:
            print(f"[!] No personas selected for phase '{phase['phase_id']}', skipping")
            continue

        # Phase-specific tracking
        phase_exchanges = []
        turn_count = 0
        max_turns = phase.get("max_turns", 15)

        # Conversation loop for this phase
        while True:
            # Facilitator decides who should speak next
            next_speaker_name = facilitator.decide_next_speaker(
                phase=phase,
                active_personas=active_personas,
                recent_exchanges=phase_exchanges,
                shared_context=shared_context,
                turn_count=turn_count,
                max_turns=max_turns
            )

            # Log speaker decision
            if logger:
                logger.log_facilitator_decision(
                    decision_type="speaker_choice",
                    phase_id=phase["phase_id"],
                    decision=next_speaker_name or "PHASE_COMPLETE",
                    reasoning=f"Turn {turn_count} in phase '{phase['phase_id']}'"
                )

            # If facilitator says phase is complete, exit loop
            if next_speaker_name is None:
                break

            # Validate speaker
            if next_speaker_name not in active_personas:
                print(f"[!] Facilitator selected invalid persona '{next_speaker_name}', skipping")
                turn_count += 1
                continue

            # Get the persona and have them respond
            speaker_persona = active_personas[next_speaker_name]

            print(f"\n[Speaker] {speaker_persona.name} ({speaker_persona.archetype}) speaking...")

            # Generate dynamic prompt based on conversation state
            dynamic_prompt = generate_dynamic_prompt(
                phase=phase,
                turn_count=turn_count,
                phase_exchanges=phase_exchanges,
                shared_context=shared_context
            )

            # Build context for this persona's response
            ctx = {
                "user_prompt": dynamic_prompt,  # Use dynamic prompt instead of static
                "phase": phase,
                "shared_context": shared_context,
                "recent_exchanges": phase_exchanges  # Add recent discussion context
            }

            # Persona generates response using their summary
            response_data = speaker_persona.response(ctx)
            response_content = response_data.get("response", "")

            print(f"\n{speaker_persona.name}: {response_content[:200]}...")

            # Log this exchange
            exchange = {
                "phase": phase["phase_id"],
                "turn": turn_count,
                "speaker": speaker_persona.name,
                "archetype": speaker_persona.archetype,
                "content": response_content
            }
            phase_exchanges.append(exchange)
            logs.append(exchange)

            # Log to conversation logger
            if logger:
                logger.log_exchange(
                    phase_id=phase["phase_id"],
                    turn=turn_count,
                    speaker=speaker_persona.name,
                    archetype=speaker_persona.archetype,
                    content=response_content
                )

            # Extract and track discussed ideas (Fix #3)
            idea_title = extract_idea_title(response_content)
            if idea_title:
                if idea_title not in shared_context["ideas_discussed"]:
                    shared_context["ideas_discussed"].append(idea_title)
                    print(f"[i] New idea identified: '{idea_title}'")
                shared_context["current_focus"] = idea_title

            # All active personas update their summaries based on this exchange
            if enable_summary_updates:
                print(f"[i] Updating summaries for all active personas...")
                for persona_name, persona in active_personas.items():
                    persona.update_summary({
                        "speaker": speaker_persona.name,
                        "content": response_content,
                        "phase": phase["phase_id"]
                    })
            else:
                print(f"[i] Fast mode: Skipping summary updates")

            turn_count += 1

        # Phase complete - create summary
        print(f"\n[OK] Phase '{phase['phase_id']}' complete after {turn_count} turns")
        phase_summary = facilitator.summarize_phase(
            phase=phase,
            exchanges=phase_exchanges,
            shared_context=shared_context
        )
        print(f"[Summary] {phase_summary}\n")

        all_phase_summaries.append({
            "phase_id": phase["phase_id"],
            "summary": phase_summary,
            "turns": turn_count
        })

        # Log persona summaries and phase summary
        if logger:
            logger.log_persona_summaries(phase["phase_id"], active_personas)
            logger.log_phase_summary(phase["phase_id"], phase_summary)

    # Store logs and summaries in shared context
    shared_context["logs"] = logs
    shared_context["phase_summaries"] = all_phase_summaries

    return shared_context
