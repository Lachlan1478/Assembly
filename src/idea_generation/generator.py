# idea_brainstorm_01.py
# Main entry point: Multi-persona startup idea generator with staged discovery

import json
import re
import asyncio
from framework import FacilitatorAgent, ConversationLogger, ConversationMonitor
from framework.helpers import load_personas_from_directory
from framework.persona_manager import PersonaManager
from framework.generators import generate_phases_for_domain
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

    # Initialize PersonaManager for dynamic generation
    print("\n[i] Initializing PersonaManager for dynamic persona generation...")
    persona_manager = PersonaManager(
        cache_dir="dynamic_personas",
        archive_dir="personas_archive",
        model_name=config["model"]
    )

    # Create facilitator agent
    facilitator = FacilitatorAgent(model_name=config["model"])

    # Create conversation logger
    logger = ConversationLogger(base_dir="conversation_logs")

    # Create conversation monitor for real-time progress tracking
    monitor = ConversationMonitor()

    # Log session metadata
    logger.log_metadata("inspiration", inspiration)
    logger.log_metadata("number_of_ideas", number_of_ideas)
    logger.log_metadata("mode", mode)
    logger.log_metadata("model", config["model"])
    logger.log_metadata("dynamic_generation", True)

    # Generate domain-specific phases using LLM
    print("\n[i] Generating custom workflow phases for domain...")
    all_phases = generate_phases_for_domain(
        inspiration=inspiration,
        number_of_ideas=number_of_ideas,
        model_name=config["model"]
    )

    # Validate that phases were generated successfully
    if not all_phases or len(all_phases) == 0:
        raise RuntimeError(
            "[ERROR] Failed to generate phases dynamically. "
            "This could be due to:\n"
            "  - OpenAI API error or connectivity issue\n"
            "  - Malformed inspiration text\n"
            "  - Model response parsing failure\n"
            "Please check your API key and try again."
        )

    # Select phases based on mode configuration strategy
    # Dynamically generated phases can have any names, so we use positional selection
    selection_strategy = config.get("phase_selection", "all")

    if selection_strategy == "bookends":
        # Fast mode: Take first and last phase (exploring and deciding)
        if len(all_phases) >= 2:
            phases = [all_phases[0], all_phases[-1]]
        else:
            phases = all_phases
    elif selection_strategy == "bookends_plus_middle":
        # Medium mode: First + (n-2) middle + last (ensures decision phase is included)
        n = config.get("num_phases", 4)
        if len(all_phases) <= n:
            # If we have fewer phases than requested, take all
            phases = all_phases
        elif n <= 2:
            # If n is 2 or less, just do bookends
            phases = [all_phases[0], all_phases[-1]] if len(all_phases) >= 2 else all_phases
        else:
            # Take first, (n-2) from middle, and last
            middle_count = n - 2
            middle_phases = all_phases[1:1+middle_count]  # Take first (n-2) after first phase
            phases = [all_phases[0]] + middle_phases + [all_phases[-1]]
    elif selection_strategy == "first_n":
        # Take first N phases (partial workflow)
        n = config.get("num_phases", 3)
        phases = all_phases[:n] if len(all_phases) >= n else all_phases
    else:  # "all"
        # Standard/deep mode: Use all generated phases (full workflow)
        phases = all_phases

    # Ensure max_turns is set (use from config if not in phase)
    for phase in phases:
        if "max_turns" not in phase:
            phase["max_turns"] = config["max_turns_per_phase"]

    print(f"[i] Running {len(phases)} phases: {', '.join([p['phase_id'] for p in phases])}")
    print(f"[i] Max turns per phase: varies by phase\n")

    # Log phases to metadata
    logger.log_metadata("phases", phases)

    # Initialize shared context (Pure Dynamic - no prompt template needed)
    # Phases generate their own prompts based on their goals
    shared_context = {
        "inspiration": inspiration,
        "number_of_ideas": number_of_ideas,
        "ideas": [],  # Will be populated during conversation
        "ideas_discussed": [],  # Track idea titles discussed during conversation
        "current_focus": None  # Most recently discussed idea
    }

    # Run the facilitator-directed meeting (async) with dynamic persona generation
    print("\n[i] Starting facilitator-directed meeting with dynamic persona generation...\n")
    final_context = asyncio.run(meeting_facilitator(
        persona_manager=persona_manager,
        inspiration=inspiration,
        phases=phases,
        shared_context=shared_context,
        facilitator=facilitator,
        logger=logger,
        monitor=monitor,
        enable_summary_updates=config["enable_summary_updates"],
        use_async_updates=True  # Enable async parallel summary updates
    ))

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
