# idea_brainstorm.py
# Multi-persona idea generator using facilitator-directed conversations
import json
from openai import OpenAI
import os
from persona import Persona
from facilitator import FacilitatorAgent
from utils import load_all_personas
from conversation_logger import ConversationLogger

#MODEL = "gpt-4.1-mini"
MODEL = "gpt-5-mini"

# Mode configurations for different run speeds
MODE_CONFIGS = {
    "fast": {
        "phases": ["ideation", "decision"],
        "max_turns_per_phase": 3,
        "model": "gpt-3.5-turbo",
        "enable_summary_updates": False,
        "description": "Quick test run (1-2 min, minimal cost)"
    },
    "standard": {
        "phases": ["ideation", "design", "research", "feasibility", "financials", "critique", "decision"],
        "max_turns_per_phase": 8,
        "model": "gpt-4o-mini",
        "enable_summary_updates": True,
        "description": "Balanced run (5-10 min, moderate cost)"
    },
    "deep": {
        "phases": ["ideation", "design", "research", "feasibility", "financials", "critique", "decision"],
        "max_turns_per_phase": 15,
        "model": "gpt-5-mini",
        "enable_summary_updates": True,
        "description": "Comprehensive run (10-15 min, higher cost)"
    }
}

def _score(idea, must_haves):
    pass


from typing import List, Dict, Any

def meeting_facilitator(
    all_personas: Dict[str, Persona],
    phases: List[Dict[str, Any]],
    shared_context: Dict[str, Any],
    facilitator: FacilitatorAgent,
    logger: ConversationLogger = None,
    enable_summary_updates: bool = True
) -> Dict[str, Any]:
    """
    New facilitator-directed conversation architecture.

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

            # Build context for this persona's response
            ctx = {
                "user_prompt": shared_context.get("user_prompt", ""),
                "phase": phase,
                "shared_context": shared_context
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

def extract_ideas_with_llm(logs: list, number_of_ideas: int, model_name: str = "gpt-4o-mini") -> list:
    """
    Extract structured startup ideas from conversation logs using LLM.

    This is a fallback when personas don't format output as JSON naturally.
    The LLM reads the conversation and extracts the structured ideas.

    Args:
        logs: List of conversation exchanges
        number_of_ideas: Expected number of ideas to extract
        model_name: OpenAI model to use for extraction

    Returns:
        List of idea dictionaries with required fields
    """
    # Build conversation summary for extraction
    conversation_text = ""
    for exchange in logs:
        speaker = exchange.get("speaker", "Unknown")
        content = exchange.get("content", "")
        conversation_text += f"\n\n{speaker}:\n{content}"

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    extraction_prompt = f"""You are extracting startup ideas from a multi-persona conversation.

Read the conversation below and extract {number_of_ideas} startup idea(s) that were discussed.

Each idea must include these fields:
- title: Name of the startup
- description: What it does (2-3 sentences)
- target_users: Who will use it
- primary_outcome: Main value delivered
- must_haves: Essential features (list)
- constraints: Limitations to consider (list)
- non_goals: What it explicitly won't do (list)

Return a JSON array of idea objects. If multiple similar ideas were proposed, consolidate them into the best version.

CONVERSATION:
{conversation_text}

Extract the ideas as a JSON array:"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You extract structured startup ideas from conversations. Always return valid JSON arrays."},
                {"role": "user", "content": extraction_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3  # Lower temperature for more consistent extraction
        )

        raw_response = response.choices[0].message.content
        parsed = json.loads(raw_response)

        # Handle both {"ideas": [...]} and direct array formats
        if isinstance(parsed, dict) and "ideas" in parsed:
            ideas = parsed["ideas"]
        elif isinstance(parsed, list):
            ideas = parsed
        else:
            ideas = [parsed]

        print(f"\n[OK] LLM extraction successful: {len(ideas)} idea(s)")
        return ideas

    except Exception as e:
        print(f"\n[!] LLM extraction failed: {e}")
        return []


# Multi-persona LLM call to generate ideas. New Methodology.
def multiple_llm_idea_generator(inspiration, number_of_ideas = 1, mode="standard"):
    """
    Generate startup ideas using dynamic persona loading and facilitator-directed conversation.

    Args:
        inspiration: User-provided inspiration for ideas
        number_of_ideas: How many ideas to generate
        mode: Run mode - "fast", "standard", or "deep" (default: "standard")

    Returns:
        List of business idea dictionaries
    """
    # Get mode configuration
    if mode not in MODE_CONFIGS:
        print(f"[!] Unknown mode '{mode}', using 'standard'")
        mode = "standard"

    config = MODE_CONFIGS[mode]
    print(f"\n[i] Running in {mode.upper()} mode: {config['description']}")

    print("\n[i] Loading personas from personas/ directory...")
    all_personas = load_all_personas(directory="personas", model_name=config["model"])

    # Create facilitator
    facilitator = FacilitatorAgent(model_name=config["model"])

    # Create conversation logger
    logger = ConversationLogger(base_dir="conversation_logs")

    # Log session metadata
    logger.log_metadata("inspiration", inspiration)
    logger.log_metadata("number_of_ideas", number_of_ideas)
    logger.log_metadata("mode", mode)
    logger.log_metadata("model", config["model"])
    logger.log_metadata("personas_loaded", list(all_personas.keys()))

    # Define ALL phases with goals and desired outcomes
    all_phases = [
        {
            "phase_id": "ideation",
            "goal": f"Generate {number_of_ideas} different startup idea(s) based on the inspiration",
            "desired_outcome": "List of concrete startup ideas with clear value propositions"
        },
        {
            "phase_id": "design",
            "goal": "Refine the user experience and design aspects of the proposed ideas",
            "desired_outcome": "Enhanced ideas with UX considerations and design principles"
        },
        {
            "phase_id": "research",
            "goal": "Validate market demand and identify whitespace for the ideas",
            "desired_outcome": "Market validation and competitive analysis for each idea"
        },
        {
            "phase_id": "feasibility",
            "goal": "Assess technical feasibility and implementation approach",
            "desired_outcome": "Technical assessment and architecture considerations"
        },
        {
            "phase_id": "financials",
            "goal": "Evaluate business model and economic viability",
            "desired_outcome": "Revenue model and cost structure for each idea"
        },
        {
            "phase_id": "critique",
            "goal": "Stress-test assumptions and identify potential risks",
            "desired_outcome": "List of key risks and mitigation strategies"
        },
        {
            "phase_id": "decision",
            "goal": "Consolidate all feedback and output final startup ideas in JSON format",
            "desired_outcome": f"JSON array of {number_of_ideas} startup idea(s) with all required fields"
        }
    ]

    # Filter phases based on mode configuration and apply max_turns
    enabled_phase_ids = config["phases"]
    phases = [
        {**phase, "max_turns": config["max_turns_per_phase"]}
        for phase in all_phases
        if phase["phase_id"] in enabled_phase_ids
    ]

    print(f"[i] Running {len(phases)} phases: {', '.join([p['phase_id'] for p in phases])}")
    print(f"[i] Max turns per phase: {config['max_turns_per_phase']}\n")

    prompt = f"""
Given the following inspiration, generate {number_of_ideas} different startup idea(s).
Ensure the ideas are meaningfully different.

Each idea should include:
- title: Name of the startup
- description: What it does
- target_users: Who will use it
- primary_outcome: Main value delivered
- must_haves: Essential features
- constraints: Limitations to consider
- non_goals: What it explicitly won't do

Inspiration: {inspiration}
"""

    # Log phases to metadata
    logger.log_metadata("phases", phases)

    shared_context = {
        "user_prompt": prompt,
        "inspiration": inspiration,
        "number_of_ideas": number_of_ideas,
        "ideas": []  # Will be populated during conversation
    }

    # Run the facilitator-directed meeting
    print("\n[i] Starting facilitator-directed meeting...\n")
    final_context = meeting_facilitator(
        all_personas=all_personas,
        phases=phases,
        shared_context=shared_context,
        facilitator=facilitator,
        logger=logger,
        enable_summary_updates=config["enable_summary_updates"]
    )

    # Save basic logs (backwards compatibility)
    logs = final_context.get("logs", [])
    with open("meeting_logs.txt", "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    print(f"\n[OK] Meeting logs saved to meeting_logs.txt ({len(logs)} exchanges)")

    # Extract ideas from the final conversation
    business_ideas = []

    # The last exchange in the decision phase should contain the JSON ideas
    decision_exchanges = [
        ex for ex in logs
        if ex.get("phase") == "decision"
    ]

    if decision_exchanges:
        # Try to extract JSON from the last decision exchange
        last_decision = decision_exchanges[-1].get("content", "")

        # Try to parse as JSON
        try:
            # Look for JSON array in the response
            import re
            json_match = re.search(r'\[.*\]', last_decision, re.DOTALL)
            if json_match:
                raw_ideas = json_match.group(0)
                business_ideas = json.loads(raw_ideas)
                print(f"\n[OK] Successfully extracted {len(business_ideas)} idea(s)")
        except Exception as e:
            print(f"[!] Failed to parse ideas from decision phase: {e}")

    # Fallback: check if ideas were added to shared_context
    if not business_ideas and final_context.get("ideas"):
        business_ideas = final_context["ideas"]
        print(f"\n[OK] Using ideas from shared context: {len(business_ideas)} idea(s)")

    # LLM extraction fallback: If JSON extraction failed, use LLM to extract ideas
    if not business_ideas:
        print("\n[i] JSON extraction failed, using LLM extraction fallback...")
        business_ideas = extract_ideas_with_llm(
            logs=logs,
            number_of_ideas=number_of_ideas,
            model_name=config["model"]
        )

    # Log final ideas to metadata
    logger.log_metadata("ideas", business_ideas)

    # Save all comprehensive logs
    logger.save_all()

    # Return ideas (or empty list with warning)
    if not business_ideas:
        print("[!] Warning: No ideas could be extracted from conversation")

    return business_ideas


# Single LLM call to generate ideas. Old Methodology. To be improved.
def single_llm_idea_generator(inspiration, number_of_ideas = 1):

    system_content = """You are a startup idea generator. Given some inspiration, you will generate a single, specific, concrete startup idea.
        The idea should be a mobile app, web app, or SaaS product.
    """
    client = OpenAI(api_key = os.getenv("OPENAI_API_KEY", ""))

    message_content = f"""
        Given the following inspiration, generate {number_of_ideas} different startup idea(s).
        Each item must include: 
            - title 
            - description 
            - target_users 
            - primary_outcome 
            - must_haves 
            - constraints 
            - non_goals 
        and be in valid JSON format as an array of objects.
        Ensure the ideas are meaningfully different.
    """

    response   = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[  # the conversation history as a list of role/content dicts
            {"role": "system", "content": system_content},                                  # Sets behavior, style, or persona of the assistant.
            {"role": "user", "content": message_content},                                   # Anything the end-user says (questions, instructions).
            {"role": "user", "content": inspiration},                                       # Anything the end-user says (questions, instructions).
            # {"role": "assistant", "content": "Short selling is when..."},                 # Model’s previous replies (if you’re keeping conversation history).
            # {"type": "image_url", "image_url": {"url": "https://example.com/chart.png"}}. # Can have multiple images
        ],
        response_format={"type": "json_object"},
        # max_tokens,
        frequency_penalty = 0.0, # -2.0 to 2.0, default 0.0 - penalizes repeated phrases
        presence_penalty = 0.0, # -2.0 to 2.0, default 0.0 - penalizes repeated topics
        n = 1, # number of chat completion choices to generate
        # response_format,
    )

    raw_response = response.choices[0].message.content

    business_ideas = json.loads(raw_response)

    return business_ideas


def generate_idea(inspiration, number_of_ideas = 1):

    print(inspiration)

    business_ideas = single_llm_idea_generator(inspiration = inspiration, number_of_ideas = number_of_ideas)

    return business_ideas


def generate_ideas_and_pick_best(inspiration, number_of_ideas = 1, mode="standard"):

    new_ideas = multiple_llm_idea_generator(inspiration = inspiration, number_of_ideas = number_of_ideas, mode=mode)
    print(new_ideas)
    return new_ideas
