# main.py
from pprint import pprint
import json

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from idea_brainstorm_01 import generate_ideas_and_pick_best
from spec_generation_02 import make_initial_prompt
from generate_initial_design_03 import create_initial_design

# ---- Hard-coded "user input" / criteria ----

# You can provide as little or as much detail as you like.
    # ChatGPT will fill in the gaps and generate startup/product ideas.

INSPIRATION = """
    Domain: Cooking
    Target users: Home cooks, food enthusiasts, and culinary beginners
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
    ideas = generate_ideas_and_pick_best(INSPIRATION)

    print("\n--- IDEAS ---")
    pprint(ideas)
    # Turn each idea dict into a JSON string
    best = [json.dumps(idea, indent=2) for idea in ideas["ideas"]][0]
    
    print("\n--- BEST IDEA ---")
    pprint(best)
    

    # Stage 2
    prompt = make_initial_prompt(best)

    print("\n--- INITIAL PROMPT ---")
    pprint(prompt)

    # Stage 3
    app_id, preview_url = create_initial_design(prompt)

    print("\n--- BASE44 BUILD (stub) ---")
    print("app_id:", app_id)
    print("preview_url:", preview_url)

   

if __name__ == "__main__":
    main()
