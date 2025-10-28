# Test run: Education domain
from pprint import pprint
import json
from dotenv import load_dotenv

load_dotenv()

from src.idea_generation.generator import multiple_llm_idea_generator
from src.stages.spec_generation import make_initial_prompt

INSPIRATION = """
    Domain: Education technology

    Context: Making online learning more engaging for high school students
"""

print(f"\n{'='*60}")
print(f"TEST RUN: Education Domain")
print(f"Mode: MEDIUM")
print(f"{'='*60}\n")

ideas = multiple_llm_idea_generator(INSPIRATION, number_of_ideas=1, mode="medium")

print("\n--- IDEAS ---")
pprint(ideas)

if isinstance(ideas, list) and ideas:
    best = json.dumps(ideas[0], indent=2)
    print("\n--- BEST IDEA ---")
    pprint(best)

    prompt = make_initial_prompt(best)
    print("\n--- SPEC GENERATED ---")
    print(f"Spec length: {len(prompt)} characters")
