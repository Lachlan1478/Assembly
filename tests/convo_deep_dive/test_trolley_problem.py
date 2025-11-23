"""
Trolley Problem Ethical Dilemma Test

Tests the conversation framework with 2 personas discussing the classic Trolley Problem.
This test helps analyze:
- How well personas maintain distinct philosophical positions
- Quality of facilitator's discussion management
- Persona memory and argument evolution
- Overall conversation flow and depth

Run:
    python tests/convo_deep_dive/test_trolley_problem.py

Output:
    Logs saved to: tests/convo_deep_dive/logs/session_YYYYMMDD_HHMMSS/
    Review: readable_transcript.md for full conversation
"""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv



# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

load_dotenv(dotenv_path=project_root / ".env")

from framework import FacilitatorAgent, ConversationLogger
from framework.persona_manager import PersonaManager
from src.idea_generation.orchestration import meeting_facilitator


# Test configuration
TEST_DIR = Path(__file__).parent
LOGS_DIR = TEST_DIR / "logs"

# Ensure logs directory exists
LOGS_DIR.mkdir(exist_ok=True)

# Trolley Problem setup
INSPIRATION = """
Domain: Ethical Philosophy - The Trolley Problem

Context: A runaway trolley is barreling down the tracks toward five people
who will be killed if it proceeds on its current path. You are standing next
to a lever that can divert the trolley onto a side track, where it will kill
one person instead of five.

The Dilemma: Is it morally permissible to pull the lever, sacrificing one
person to save five? Does the intent behind the action matter? Does the
difference between action and inaction matter?

Participants should explore these perspectives deeply, engaging with each
other's arguments and considering edge cases and objections.
"""

# Two-phase definition: debate + integration
PHASES = [
    {
        "phase_id": "ethical_analysis",
        "goal": "Analyze the Trolley Problem from multiple ethical frameworks and engage in rigorous philosophical debate",
        "desired_outcome": "Clear articulation of utilitarian and deontological positions with reasoning, objections, and responses",
        "max_turns": 8,
        "phase_type": "debate",
        "domain": "philosophical_debate"
    },
    {
        "phase_id": "ethical_integration",
        "goal": "Find common ground between utilitarian and deontological perspectives on the Trolley Problem",
        "desired_outcome": "Identification of shared principles and clear articulation of genuine remaining disagreements",
        "max_turns": 5,
        "phase_type": "integration",
        "domain": "philosophical_debate"
    }
]


async def run_trolley_problem_test():
    """
    Run the Trolley Problem conversation test.

    Configuration:
    - 2 personas (likely: Utilitarian + Deontologist)
    - 1 facilitator managing the discussion
    - Phase 1 (debate): 8 turns of rigorous philosophical debate
    - Phase 2 (integration): 5 turns of finding common ground
    - Belief state tracking enabled
    - Memory updates enabled for realistic conversation
    """
    print("="*70)
    print("TROLLEY PROBLEM ETHICAL DILEMMA TEST")
    print("="*70)
    print()
    print("Configuration:")
    print("  - Personas: 2 (dynamically generated)")
    print("  - Phase 1 (DEBATE): 8 turns - rigorous philosophical debate")
    print("  - Phase 2 (INTEGRATION): 5 turns - finding common ground")
    print("  - Belief state tracking: ENABLED")
    print("  - Memory updates: ENABLED (realistic conversation)")
    print("  - Model: gpt-4o-mini")
    print()
    print("Estimated runtime: 5-7 minutes")
    print()

    # Initialize components
    print("[1/5] Initializing PersonaManager...")
    persona_manager = PersonaManager(model_name="gpt-4o-mini")

    print("[2/5] Initializing Facilitator...")
    facilitator = FacilitatorAgent(model_name="gpt-4o-mini")

    print("[3/5] Initializing Logger...")
    logger = ConversationLogger(base_dir=str(LOGS_DIR))

    # Shared context for tracking discussion
    shared_context = {
        "dilemma": "Trolley Problem",
        "positions": [],
        "key_arguments": [],
        "objections_raised": []
    }

    print("[4/5] Starting conversation...")
    print()
    print("-" * 70)

    # Run conversation with 2 personas
    result = await meeting_facilitator(
        persona_manager=persona_manager,
        inspiration=INSPIRATION,
        phases=PHASES,
        shared_context=shared_context,
        facilitator=facilitator,
        logger=logger,
        enable_summary_updates=True,  # Enable memory updates
        use_async_updates=True,       # Parallel updates for speed
        model_name="gpt-4o-mini",
        personas_per_phase=2          # KEY: Override to 2 personas
    )

    print("-" * 70)
    print()
    print("[5/5] Saving logs...")
    logger.save_all()  # Save all conversation logs to disk
    print()
    print("Test complete!")
    print()

    # Display results summary
    print("="*70)
    print("RESULTS SUMMARY")
    print("="*70)
    print()
    print(f"Session logs saved to:")
    print(f"  {logger.session_dir}")
    print()
    print("Files generated:")
    print("  readable_transcript.md     - Human-friendly conversation transcript")
    print("  persona_summaries.json      - How personas evolved their understanding")
    print("  facilitator_decisions.json  - Who spoke when and why")
    print("  full_conversation.json      - Complete conversation data")
    print("  phase_summaries.txt         - High-level phase summary")
    print("  session_metadata.json      - Session configuration")
    print()
    print("Next steps:")
    print(f"  1. Review: {logger.session_dir / 'readable_transcript.md'}")
    print("  2. Analyze persona evolution in persona_summaries.json")
    print("  3. Check facilitator decisions in facilitator_decisions.json")
    print()

    # Show conversation statistics
    total_exchanges = len(result.get("logs", []))
    print(f"Statistics:")
    print(f"  Total exchanges: {total_exchanges}")
    print(f"  Phases completed: {len(result.get('phase_summaries', []))}")
    print()

    return result


def main():
    """Main entry point for the test."""
    try:
        result = asyncio.run(run_trolley_problem_test())
        print("[OK] Test completed successfully!")
        return 0
    except KeyboardInterrupt:
        print("\n\n[!] Test interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n[ERROR] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
