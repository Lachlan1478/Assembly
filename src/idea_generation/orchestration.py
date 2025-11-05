# idea_brainstorm_01c_orchestration.py
# Orchestration module: Meeting facilitator and conversation management

import asyncio
import time
from typing import Dict, List, Any, Optional
from framework import Persona, FacilitatorAgent, ConversationLogger
from framework.monitor import ConversationMonitor
from src.idea_generation.prompts import generate_dynamic_prompt
from src.idea_generation.extraction import extract_idea_title


async def meeting_facilitator(
    persona_manager,
    inspiration: str,
    phases: List[Dict[str, Any]],
    shared_context: Dict[str, Any],
    facilitator: FacilitatorAgent,
    logger: ConversationLogger = None,
    monitor: Optional[ConversationMonitor] = None,
    enable_summary_updates: bool = True,
    use_async_updates: bool = True
) -> Dict[str, Any]:
    """
    Facilitator-directed conversation with dynamic persona generation.

    Args:
        persona_manager: PersonaManager for on-demand persona generation
        inspiration: Problem domain context for persona generation
        phases: List of phase dicts with:
            - phase_id: str
            - goal: str (what should be accomplished)
            - desired_outcome: str (specific deliverable)
            - max_turns: int (optional, default 15)
        shared_context: Mutable dict for shared artifacts (ideas, decisions, etc.)
        facilitator: FacilitatorAgent instance
        logger: Optional ConversationLogger for comprehensive logging
        monitor: Optional ConversationMonitor for real-time progress tracking
        enable_summary_updates: If False, skip LLM calls for summary updates (fast mode)
        use_async_updates: If True, use async parallel summary updates for speedup (default: True)

    Returns:
        final shared_context with logs and results
    """
    logs = []
    all_phase_summaries = []

    for phase in phases:
        # Track phase start time for monitor
        phase_start_time = time.time()

        # Monitor: Phase start
        if monitor:
            monitor.on_phase_start(
                phase_id=phase['phase_id'],
                goal=phase.get('goal', 'No goal specified')
            )
        else:
            # Fallback display if no monitor
            print(f"\n{'='*60}")
            print(f"=== Phase: {phase['phase_id'].upper()} ===")
            print(f"Goal: {phase.get('goal')}")
            print(f"{'='*60}\n")

        # Request personas from PersonaManager for this phase
        active_personas = persona_manager.request_personas_for_phase(
            inspiration=inspiration,
            phase_info=phase,
            count=4  # Generate 4 personas per phase
        )

        # Log persona generation
        if logger:
            persona_names = list(active_personas.keys())
            logger.log_facilitator_decision(
                decision_type="persona_generation",
                phase_id=phase["phase_id"],
                decision=persona_names,
                reasoning=f"Generated {len(persona_names)} personas for phase '{phase['phase_id']}'"
            )

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

            # Monitor: Turn start
            if monitor:
                monitor.on_turn_start(
                    speaker=speaker_persona.name,
                    turn_num=turn_count,
                    max_turns=max_turns
                )
            else:
                # Fallback display if no monitor
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
                "recent_exchanges": phase_exchanges,  # Add recent discussion context
                "turn_count": turn_count  # Add turn count for dynamic word limits
            }

            # Persona generates response using their summary
            response_data = speaker_persona.response(ctx)
            response_content = response_data.get("response", "")

            # Display response (only if not using monitor, to avoid clutter)
            if not monitor:
                print(f"\n{speaker_persona.name}: {response_content[:200]}...")

            # Monitor: Turn complete (estimate ~500 tokens per response)
            if monitor:
                monitor.on_turn_complete(
                    speaker=speaker_persona.name,
                    tokens_used=500  # Rough estimate
                )

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
                exchange_data = {
                    "speaker": speaker_persona.name,
                    "content": response_content,
                    "phase": phase["phase_id"]
                }

                if use_async_updates:
                    # Parallel async updates for speed
                    if not monitor:
                        print(f"[i] Updating summaries for all active personas (async parallel)...")

                    await asyncio.gather(*[
                        persona.update_summary_async(exchange_data)
                        for persona in active_personas.values()
                    ])
                else:
                    # Sequential updates (backward compatibility)
                    if not monitor:
                        print(f"[i] Updating summaries for all active personas (sequential)...")

                    for persona_name, persona in active_personas.items():
                        persona.update_summary(exchange_data)
            else:
                if not monitor:
                    print(f"[i] Fast mode: Skipping summary updates")

            turn_count += 1

        # Phase complete - create summary
        phase_elapsed_time = time.time() - phase_start_time

        if not monitor:
            print(f"\n[OK] Phase '{phase['phase_id']}' complete after {turn_count} turns")

        phase_summary = facilitator.summarize_phase(
            phase=phase,
            exchanges=phase_exchanges,
            shared_context=shared_context
        )

        # Monitor: Phase complete
        if monitor:
            monitor.on_phase_complete(
                phase_id=phase['phase_id'],
                summary=phase_summary,
                total_turns=turn_count,
                total_time=phase_elapsed_time
            )
        else:
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

    # Monitor: Display final summary
    if monitor:
        monitor.display_summary()

    return shared_context
