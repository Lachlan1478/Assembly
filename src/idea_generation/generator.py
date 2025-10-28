# idea_brainstorm_01.py
# Main entry point: Multi-persona startup idea generator with staged discovery

import json
import re
from framework import FacilitatorAgent, ConversationLogger
from framework.helpers import load_personas_from_directory
from src.idea_generation.config import MODE_CONFIGS, MODEL
from src.idea_generation.orchestration import meeting_facilitator
from src.idea_generation.extraction import extract_ideas_with_llm


def multiple_llm_idea_generator(inspiration, number_of_ideas=1, mode="medium"):
    """
    Generate startup ideas using dynamic persona loading and facilitator-directed conversation.

    This function orchestrates a multi-persona conversation across multiple phases,
    using staged prompts that guide personas from problem discovery to solution synthesis.

    Args:
        inspiration: User-provided inspiration for ideas
        number_of_ideas: How many ideas to generate
        mode: Run mode - "fast", "medium", "standard", or "deep" (default: "medium")

    Returns:
        List of business idea dictionaries with structured fields
    """
    # Get mode configuration
    if mode not in MODE_CONFIGS:
        print(f"[!] Unknown mode '{mode}', using 'medium'")
        mode = "medium"

    config = MODE_CONFIGS[mode]
    print(f"\n[i] Running in {mode.upper()} mode: {config['description']}")

    # Load personas dynamically from personas/ directory
    print("\n[i] Loading personas from personas/ directory...")
    all_personas = load_personas_from_directory(directory="personas", model_name=config["model"])

    # Create facilitator agent
    facilitator = FacilitatorAgent(model_name=config["model"])

    # Create conversation logger
    logger = ConversationLogger(base_dir="conversation_logs")

    # Log session metadata
    logger.log_metadata("inspiration", inspiration)
    logger.log_metadata("number_of_ideas", number_of_ideas)
    logger.log_metadata("mode", mode)
    logger.log_metadata("model", config["model"])
    logger.log_metadata("personas_loaded", list(all_personas.keys()))

    # Define all possible phases with goals and desired outcomes
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

    # Create initial prompt template (will be replaced by dynamic prompts)
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

    # Initialize shared context
    shared_context = {
        "user_prompt": prompt,
        "original_prompt": prompt,  # Store original for dynamic prompt generation
        "inspiration": inspiration,
        "number_of_ideas": number_of_ideas,
        "ideas": [],  # Will be populated during conversation
        "ideas_discussed": [],  # Track idea titles discussed during conversation
        "current_focus": None  # Most recently discussed idea
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
