# idea_brainstorm_01.py
# Main entry point: Multi-persona startup idea generator with staged discovery

import json
import logging
import re
import asyncio
from framework import FacilitatorAgent, ConversationLogger, ConversationMonitor

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from framework.helpers import load_personas_from_directory
from framework.persona_manager import PersonaManager
from framework.generators import generate_phases_for_domain
from src.idea_generation.config import MODE_CONFIGS, MODEL
from src.idea_generation.orchestration import meeting_facilitator
from src.idea_generation.extraction import extract_ideas_with_llm
from src.idea_generation.convergence import run_convergence_phase, format_convergence_output


def multiple_llm_idea_generator(inspiration, number_of_ideas=1, mode="medium", monitor=None, logger=None, config_overrides=None):
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
        log.warning("Unknown mode '%s', using 'medium'", mode)
        mode = "medium"

    config = dict(MODE_CONFIGS[mode])
    if config_overrides:
        config.update(config_overrides)
    log.info("Running in %s mode: %s", mode.upper(), config["description"])

    # Initialize PersonaManager for dynamic generation
    log.info("Initializing PersonaManager for dynamic persona generation...")
    persona_manager = PersonaManager(
        cache_dir="dynamic_personas",
        archive_dir="personas_archive",
        model_name=config["model"]
    )

    # Create facilitator agent
    facilitator = FacilitatorAgent(model_name=config["model"])

    # Use provided logger/monitor or create defaults
    if logger is None:
        logger = ConversationLogger(base_dir="conversation_logs")
    if monitor is None:
        monitor = ConversationMonitor()

    # Log session metadata
    logger.log_metadata("inspiration", inspiration)
    logger.log_metadata("number_of_ideas", number_of_ideas)
    logger.log_metadata("mode", mode)
    logger.log_metadata("model", config["model"])
    logger.log_metadata("dynamic_generation", True)

    # Generate domain-specific phases using LLM
    log.info("Generating custom workflow phases for domain...")
    all_phases = generate_phases_for_domain(
        inspiration=inspiration,
        number_of_ideas=number_of_ideas,
        model_name=config["model"]
    )

    # Notify monitor that phases have been generated
    if monitor:
        getattr(monitor, 'on_phases_generated', lambda **kw: None)(phases=all_phases)

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

    log.info("Running %d phases: %s", len(phases), ", ".join(p["phase_id"] for p in phases))
    log.info("Max turns per phase: varies by phase")

    # Log phases to metadata
    logger.log_metadata("phases", phases)

    # Initialize shared context (Pure Dynamic - no prompt template needed)
    # Phases generate their own prompts based on their goals
    shared_context = {
        "inspiration": inspiration,
        "number_of_ideas": number_of_ideas,
        "ideas": [],  # Will be populated during conversation (final structured ideas)
        "ideas_discussed": [],  # Track ideas with full context (title, overview, example, status, rejection_reason)
        "current_focus": None  # Most recently discussed idea title
    }

    # Run the facilitator-directed meeting (async) with dynamic persona generation
    log.info("Starting facilitator-directed meeting with dynamic persona generation...")
    final_context = asyncio.run(meeting_facilitator(
        persona_manager=persona_manager,
        inspiration=inspiration,
        phases=phases,
        shared_context=shared_context,
        facilitator=facilitator,
        logger=logger,
        monitor=monitor,
        enable_summary_updates=config["enable_summary_updates"],
        use_async_updates=True,  # Enable async parallel summary updates
        model_name=config["model"],  # Pass model for idea extraction
        personas_per_phase=config.get("personas_per_phase", 4),  # Configurable persona count
        enable_mediator=config.get("enable_mediator", True),  # Enable mediator based on mode
        memory_mode=config.get("memory_mode", "structured"),
    ))

    # Save basic logs (backwards compatibility)
    logs = final_context.get("logs", [])
    with open("meeting_logs.txt", "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    log.info("Meeting logs saved to meeting_logs.txt (%d exchanges)", len(logs))

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
                log.info("Successfully extracted %d idea(s)", len(business_ideas))
        except Exception as e:
            log.warning("Failed to parse ideas from decision phase: %s", e)

    # Fallback: check if ideas were added to shared_context
    if not business_ideas and final_context.get("ideas"):
        business_ideas = final_context["ideas"]
        log.info("Using ideas from shared context: %d idea(s)", len(business_ideas))

    # LLM extraction fallback: If JSON extraction failed, use LLM to extract ideas
    if not business_ideas:
        log.info("JSON extraction failed, using LLM extraction fallback...")
        business_ideas = extract_ideas_with_llm(
            logs=logs,
            number_of_ideas=number_of_ideas,
            model_name=config["model"]
        )

    # Log final ideas to metadata (Assembly output)
    logger.log_metadata("ideas", business_ideas)

    # === CONVERGENCE PHASE ===
    # Optional final refinement phase that produces commercially sharp output
    convergence_result = None
    if config.get("enable_convergence_phase", False):
        log.info("=" * 60)
        log.info("CONVERGENCE PHASE: Refining into commercial spec...")
        log.info("=" * 60)

        convergence_result = run_convergence_phase(
            inspiration=inspiration,
            logs=logs,
            ideas_discussed=final_context.get("ideas_discussed", []),
            raw_ideas=business_ideas,
            model=config["model"],
            verbose=True
        )

        if convergence_result.get("success"):
            convergence_output = convergence_result.get("convergence_output", {})

            # Log convergence output
            logger.log_metadata("convergence_output", convergence_output)
            logger.log_metadata("convergence_turns", convergence_result.get("turns", []))

            # Display formatted output
            log.info("\n%s", format_convergence_output(convergence_output))
        else:
            log.error("Convergence phase failed: %s", convergence_result.get("error", "Unknown error"))
            logger.log_metadata("convergence_error", convergence_result.get("error"))
    else:
        log.info("Convergence phase disabled (enable with enable_convergence_phase=True)")

    # Save all comprehensive logs
    logger.save_all()

    # Build final return value
    result = {
        "ideas": business_ideas,
        "convergence": convergence_result.get("convergence_output") if convergence_result else None
    }

    # Return ideas (or empty list with warning)
    if not business_ideas:
        log.warning("No ideas could be extracted from conversation")

    # For backwards compatibility, return just ideas if convergence disabled
    if not config.get("enable_convergence_phase", False):
        return business_ideas

    return result
