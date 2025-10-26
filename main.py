# main.py
from pprint import pprint
import json
import argparse
import os

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from idea_brainstorm_01 import generate_ideas_and_pick_best, MODE_CONFIGS
from spec_generation_02 import make_initial_prompt
# from generate_initial_design_03 import create_initial_design  # Stage 3 not needed for this test

# ---- Hard-coded "user input" / criteria ----

# You can provide as little or as much detail as you like.
    # ChatGPT will fill in the gaps and generate startup/product ideas.

INSPIRATION = """
    Domain: Remote work productivity and team collaboration
    Target users: Remote-first companies and distributed teams (10-500 employees)
    Primary outcome: Help remote teams maintain connection and productivity without Zoom fatigue
    Constraints: Must work asynchronously across time zones, no required synchronous meetings
    UX rules: Lightweight, non-intrusive, integrates with existing tools
"""

# INSPIRATION = """
#     Domain: finance
#     Target users: 
#     Primary outcome:
#     Must haves:
#     Constraints: 
#     Non-goals:
#     UX rules: 
#     Performance: 
# """

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Assembly: AI-powered startup idea generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Available modes:
  fast     - Quick test run (1-2 min, minimal cost)
  standard - Balanced run (5-10 min, moderate cost) [default]
  deep     - Comprehensive run (10-15 min, higher cost)

Examples:
  python main.py                  # Run in standard mode
  python main.py --mode fast      # Run in fast mode
  python main.py --mode deep      # Run in deep mode
        """
    )
    parser.add_argument(
        "--mode",
        type=str,
        default=os.getenv("ASSEMBLY_MODE", "standard"),
        choices=["fast", "standard", "deep"],
        help="Run mode (can also be set via ASSEMBLY_MODE env var)"
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"ASSEMBLY - AI-Powered Startup Idea Generator")
    print(f"Mode: {args.mode.upper()}")
    print(f"{'='*60}\n")

    ideas = generate_ideas_and_pick_best(INSPIRATION, mode=args.mode)

    print("\n--- IDEAS ---")
    pprint(ideas)

    # Check if ideas is a list or needs unpacking
    if isinstance(ideas, list):
        ideas_list = ideas
    elif isinstance(ideas, dict) and "ideas" in ideas:
        ideas_list = ideas["ideas"]
    else:
        print("[!] Unexpected ideas format, using as-is")
        ideas_list = [ideas]

    # Turn each idea dict into a JSON string
    if ideas_list:
        best = json.dumps(ideas_list[0], indent=2)
    else:
        print("[!] No ideas generated")
        return

    print("\n--- BEST IDEA ---")
    pprint(best)
    

    # Stage 2
    prompt = make_initial_prompt(best)

    print("\n--- INITIAL PROMPT ---")
    pprint(prompt)

    # Stage 3
    #app_id, preview_url = create_initial_design(prompt)

    print("\n--- BASE44 BUILD (stub) ---")
    # print("app_id:", app_id)
    # print("preview_url:", preview_url)

   

if __name__ == "__main__":
    main()
