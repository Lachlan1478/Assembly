"""
Basic Example: Design Review Conversation

This example shows a simple 3-persona conversation reviewing a design.
"""

from framework import Persona, FacilitatorAgent, ConversationLogger
from framework import load_personas_from_directory

def run_basic_design_review():
    """
    Run a basic design review with 3 personas.
    """
    print("\n" + "="*60)
    print("BASIC EXAMPLE: Design Review")
    print("="*60 + "\n")

    # 1. Load personas
    print("[1] Loading personas...")
    personas = load_personas_from_directory("personas", model_name="gpt-4o-mini")

    # 2. Create facilitator
    print("[2] Creating facilitator...")
    facilitator = FacilitatorAgent(model_name="gpt-4o-mini")

    # 3. Create logger
    print("[3] Creating logger...")
    logger = ConversationLogger(base_dir="conversation_logs")

    # 4. Define conversation goal
    phase = {
        "phase_id": "design_review",
        "goal": "Review the UX design for a new mobile banking app",
        "desired_outcome": "List of design improvements and concerns",
        "max_turns": 5
    }

    print(f"[4] Phase goal: {phase['goal']}")

    # 5. Select relevant personas
    print("[5] Facilitator selecting personas...")
    selected_names = facilitator.select_personas_for_phase(
        phase=phase,
        available_personas=personas
    )
    print(f"    Selected: {', '.join(selected_names)}")

    active_personas = {name: personas[name] for name in selected_names if name in personas}

    # 6. Run conversation loop
    print(f"[6] Starting conversation (max {phase['max_turns']} turns)...\n")

    exchanges = []
    shared_context = {
        "design_topic": "Mobile banking app - focus on first-time user onboarding"
    }

    for turn in range(phase['max_turns']):
        # Facilitator decides who speaks next
        next_speaker = facilitator.decide_next_speaker(
            phase=phase,
            active_personas=active_personas,
            recent_exchanges=exchanges,
            shared_context=shared_context,
            turn_count=turn,
            max_turns=phase['max_turns']
        )

        if next_speaker is None:
            print(f"[✓] Facilitator ended phase early (turn {turn}/{phase['max_turns']})")
            break

        if next_speaker not in active_personas:
            print(f"[!] Invalid speaker selected: {next_speaker}")
            continue

        persona = active_personas[next_speaker]
        print(f"Turn {turn + 1}: {persona.name} ({persona.archetype})")

        # Generate response
        response_data = persona.response({
            "user_prompt": f"Discuss the {phase['goal']}",
            "phase": phase,
            "shared_context": shared_context,
            "recent_exchanges": exchanges[-3:] if exchanges else []  # Last 3 exchanges
        })

        response_content = response_data.get("response", "")
        print(f"  → {response_content[:150]}...\n")

        # Log exchange
        exchange = {
            "phase": phase["phase_id"],
            "turn": turn,
            "speaker": persona.name,
            "archetype": persona.archetype,
            "content": response_content
        }
        exchanges.append(exchange)

        logger.log_exchange(
            phase_id=phase["phase_id"],
            turn=turn,
            speaker=persona.name,
            archetype=persona.archetype,
            content=response_content
        )

        # Update all persona summaries
        for p in active_personas.values():
            p.update_summary(exchange)

    # 7. Summarize phase
    print(f"[7] Creating phase summary...")
    summary = facilitator.summarize_phase(
        phase=phase,
        exchanges=exchanges,
        shared_context=shared_context
    )
    print(f"    Summary: {summary[:200]}...\n")

    logger.log_phase_summary(phase["phase_id"], summary)
    logger.log_persona_summaries(phase["phase_id"], active_personas)

    # 8. Save all logs
    print(f"[8] Saving logs...")
    logger.save_all()

    print("\n" + "="*60)
    print(f"COMPLETE! Check conversation_logs/ for outputs")
    print("="*60 + "\n")

    return exchanges, summary


if __name__ == "__main__":
    # Run the example
    exchanges, summary = run_basic_design_review()

    print(f"\nTotal exchanges: {len(exchanges)}")
    print(f"\nFinal summary:\n{summary}")
