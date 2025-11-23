# idea_brainstorm_01c_orchestration.py
# Orchestration module: Meeting facilitator and conversation management

import asyncio
import time
from typing import Dict, List, Any, Optional
from framework import Persona, FacilitatorAgent, ConversationLogger
from framework.monitor import ConversationMonitor
from src.idea_generation.prompts import generate_dynamic_prompt
from src.idea_generation.extraction import extract_idea_title
from src.idea_generation.idea_tracker import (
    is_detailed_proposal,
    extract_idea_concept_async,
    detect_rejections_async
)


async def meeting_facilitator(
    persona_manager,
    inspiration: str,
    phases: List[Dict[str, Any]],
    shared_context: Dict[str, Any],
    facilitator: FacilitatorAgent,
    logger: ConversationLogger = None,
    monitor: Optional[ConversationMonitor] = None,
    enable_summary_updates: bool = True,
    use_async_updates: bool = True,
    model_name: str = "gpt-4o-mini",
    personas_per_phase: int = 4
) -> Dict[str, Any]:
    """
    Facilitator-directed conversation with dynamic persona generation and novelty tracking.

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
        model_name: LLM model to use for idea extraction (default: "gpt-4o-mini")
        personas_per_phase: Number of personas to generate per phase (default: 4)

    Returns:
        final shared_context with logs and results
    """
    logs = []
    all_phase_summaries = []

    # Initialize novelty tracking in shared_context
    if "mentioned_nuances" not in shared_context:
        shared_context["mentioned_nuances"] = set()

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
            count=personas_per_phase  # Configurable persona count (default: 4)
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

        # Track pending async extractions for this phase
        pending_extractions = []

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

            # Check for repetition
            repetition_warning = facilitator.check_for_repetition(
                speaker_name=speaker_persona.name,
                response_content=response_content
            )

            if repetition_warning:
                print(repetition_warning)
                # Note: In a full implementation, we could request a revision here
                # For now, we just warn and continue

            # Track novelty: extract key phrases from response and add to mentioned_nuances
            from framework.facilitator import extract_key_phrases
            new_phrases = extract_key_phrases(response_content, max_phrases=3)
            shared_context["mentioned_nuances"].update(new_phrases)

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

            # Enhanced idea tracking: Extract detailed concepts and detect rejections (async)
            # Check if this is a detailed proposal (not just passing mention)
            if is_detailed_proposal(response_content):
                # Kick off async extraction (non-blocking)
                extraction_task = asyncio.create_task(
                    extract_idea_concept_async(
                        response=response_content,
                        shared_context=shared_context,
                        turn_count=turn_count,
                        phase_id=phase["phase_id"],
                        model_name=model_name
                    )
                )
                pending_extractions.append(extraction_task)

            # Also detect rejections asynchronously (always check, not just on proposals)
            rejection_task = asyncio.create_task(
                detect_rejections_async(
                    response=response_content,
                    shared_context=shared_context,
                    turn_count=turn_count,
                    phase_id=phase["phase_id"],
                    model_name=model_name
                )
            )
            pending_extractions.append(rejection_task)

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
                        print(f"[i] Updating summaries and belief states for all active personas (async parallel)...")

                    # Update both summaries and belief states in parallel
                    update_tasks = []
                    for persona in active_personas.values():
                        update_tasks.append(persona.update_summary_async(exchange_data))
                        # Also update belief state if initialized
                        if persona.belief_state is not None:
                            update_tasks.append(persona.update_belief_state_async(exchange_data, turn_count))

                    await asyncio.gather(*update_tasks)
                else:
                    # Sequential updates (backward compatibility)
                    if not monitor:
                        print(f"[i] Updating summaries and belief states for all active personas (sequential)...")

                    for persona_name, persona in active_personas.items():
                        persona.update_summary(exchange_data)
                        # Also update belief state if initialized
                        if persona.belief_state is not None:
                            persona.update_belief_state(exchange_data, turn_count)
            else:
                if not monitor:
                    print(f"[i] Fast mode: Skipping summary updates")

            turn_count += 1

        # Phase complete - ensure all pending extractions are complete before moving to summary
        if pending_extractions:
            if not monitor:
                print(f"[i] Waiting for {len(pending_extractions)} pending idea extractions/rejection detections...")
            await asyncio.gather(*pending_extractions, return_exceptions=True)

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
