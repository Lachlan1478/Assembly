# iterative_single_llm.py
# 4-turn iterative refinement generator for fair comparison with Assembly

import json
import os
import sys
from typing import Optional, List, Dict, Any

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI


# Turn 1: Initial proposal
INITIAL_PROMPT = """You are an expert startup consultant helping to generate a startup idea.

Given the following inspiration, propose an initial startup concept:

{inspiration}

Consider:
- What problem are you solving?
- Who is the target user?
- What is the core solution?
- How would it make money?

Provide a detailed initial proposal covering these aspects. Be specific and concrete."""


# Turn 2: Self-critique
CRITIQUE_PROMPT = """You are a critical evaluator reviewing a startup proposal.

ORIGINAL INSPIRATION:
{inspiration}

INITIAL PROPOSAL:
{initial_proposal}

Identify exactly 3 weaknesses or gaps in this proposal:

1. [First weakness - be specific about what's missing or problematic]
2. [Second weakness - identify a different issue]
3. [Third weakness - find another area for improvement]

For each weakness, explain:
- Why it's a problem
- What questions it leaves unanswered
- How it could undermine the startup's success

Be rigorous and specific in your critique."""


# Turn 3: Address critiques
IMPROVEMENT_PROMPT = """You are refining a startup proposal based on critical feedback.

ORIGINAL INSPIRATION:
{inspiration}

INITIAL PROPOSAL:
{initial_proposal}

CRITIQUES IDENTIFIED:
{critiques}

Address each of the 3 critiques with specific improvements:

For each critique:
- Acknowledge the valid concern
- Propose a concrete solution or refinement
- Explain how this strengthens the overall concept

Provide an improved version of the startup concept that incorporates these refinements."""


# Turn 4: Finalize to JSON
FINALIZE_PROMPT = """You are finalizing a startup concept into a structured format.

ORIGINAL INSPIRATION:
{inspiration}

REFINED PROPOSAL:
{refined_proposal}

Convert this refined proposal into the following exact JSON format:

{{
    "title": "Clear, memorable name for the startup",
    "description": "What it does in 2-3 sentences",
    "target_users": "Specific user profile",
    "primary_outcome": "Main value delivered",
    "must_haves": ["Essential feature 1", "Essential feature 2", "..."],
    "constraints": ["Realistic limitation 1", "Realistic limitation 2", "..."],
    "non_goals": ["What it explicitly won't do 1", "What it explicitly won't do 2", "..."]
}}

Ensure the JSON captures all the key insights from the refinement process.
Respond ONLY with the JSON object, no additional text."""


def generate_idea_iterative(
    inspiration: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Generate a startup idea with 4-turn iterative refinement.

    Turn 1: Initial proposal
    Turn 2: Self-critique (find 3 weaknesses)
    Turn 3: Address critiques
    Turn 4: Finalize to JSON

    Args:
        inspiration: The domain/context for idea generation
        model: Model to use
        temperature: Generation temperature
        verbose: If True, print intermediate steps

    Returns:
        Dictionary with the generated idea and intermediate steps
    """
    client = OpenAI()

    result = {
        "idea": None,
        "model": model,
        "turns": [],
        "total_tokens": 0,
        "error": None,
    }

    try:
        # Turn 1: Initial proposal
        if verbose:
            print("[Turn 1/4] Generating initial proposal...")

        turn1_response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert startup consultant. Generate detailed, concrete startup proposals."
                },
                {
                    "role": "user",
                    "content": INITIAL_PROMPT.format(inspiration=inspiration)
                }
            ],
            temperature=temperature,
        )

        initial_proposal = turn1_response.choices[0].message.content
        result["turns"].append({
            "turn": 1,
            "type": "initial_proposal",
            "content": initial_proposal,
            "tokens": turn1_response.usage.total_tokens if turn1_response.usage else 0
        })
        result["total_tokens"] += turn1_response.usage.total_tokens if turn1_response.usage else 0

        if verbose:
            print(f"    Initial proposal: {initial_proposal[:200]}...")

        # Turn 2: Self-critique
        if verbose:
            print("[Turn 2/4] Generating self-critique...")

        turn2_response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a rigorous critical evaluator. Find genuine weaknesses in proposals."
                },
                {
                    "role": "user",
                    "content": CRITIQUE_PROMPT.format(
                        inspiration=inspiration,
                        initial_proposal=initial_proposal
                    )
                }
            ],
            temperature=temperature,
        )

        critiques = turn2_response.choices[0].message.content
        result["turns"].append({
            "turn": 2,
            "type": "critiques",
            "content": critiques,
            "tokens": turn2_response.usage.total_tokens if turn2_response.usage else 0
        })
        result["total_tokens"] += turn2_response.usage.total_tokens if turn2_response.usage else 0

        if verbose:
            print(f"    Critiques: {critiques[:200]}...")

        # Turn 3: Address critiques
        if verbose:
            print("[Turn 3/4] Addressing critiques...")

        turn3_response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a startup consultant refining a proposal based on feedback."
                },
                {
                    "role": "user",
                    "content": IMPROVEMENT_PROMPT.format(
                        inspiration=inspiration,
                        initial_proposal=initial_proposal,
                        critiques=critiques
                    )
                }
            ],
            temperature=temperature,
        )

        refined_proposal = turn3_response.choices[0].message.content
        result["turns"].append({
            "turn": 3,
            "type": "refined_proposal",
            "content": refined_proposal,
            "tokens": turn3_response.usage.total_tokens if turn3_response.usage else 0
        })
        result["total_tokens"] += turn3_response.usage.total_tokens if turn3_response.usage else 0

        if verbose:
            print(f"    Refined proposal: {refined_proposal[:200]}...")

        # Turn 4: Finalize to JSON
        if verbose:
            print("[Turn 4/4] Finalizing to JSON...")

        turn4_response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a technical writer converting proposals to structured JSON format. Output ONLY valid JSON."
                },
                {
                    "role": "user",
                    "content": FINALIZE_PROMPT.format(
                        inspiration=inspiration,
                        refined_proposal=refined_proposal
                    )
                }
            ],
            temperature=0.3,  # Lower temperature for more consistent JSON output
        )

        final_json = turn4_response.choices[0].message.content
        result["turns"].append({
            "turn": 4,
            "type": "final_json",
            "content": final_json,
            "tokens": turn4_response.usage.total_tokens if turn4_response.usage else 0
        })
        result["total_tokens"] += turn4_response.usage.total_tokens if turn4_response.usage else 0

        # Extract JSON from response
        idea = extract_json_from_response(final_json)
        result["idea"] = idea

        if verbose:
            if idea:
                print(f"    Final idea: {idea.get('title', 'Untitled')}")
            else:
                print("    Failed to extract JSON from response")

    except Exception as e:
        result["error"] = str(e)
        if verbose:
            print(f"    Error: {e}")

    return result


def extract_json_from_response(content: str) -> Optional[dict]:
    """
    Extract JSON idea from LLM response.

    Args:
        content: Raw LLM response text

    Returns:
        Parsed idea dictionary or None if extraction fails
    """
    import re

    # Try to find JSON block
    json_match = re.search(r'\{[^{}]*"title"[^{}]*\}', content, re.DOTALL)

    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Try more aggressive extraction
    try:
        # Find content between first { and last }
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            json_str = content[start:end+1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    return None


if __name__ == "__main__":
    # Quick test
    test_inspiration = """
    Domain: Personal finance
    Target users: Young professionals new to investing
    Primary outcome: Build confidence in investment decisions
    """

    print("Testing 4-turn iterative refinement generator...")
    print("=" * 60)

    result = generate_idea_iterative(test_inspiration, verbose=True)

    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)

    if result.get("idea"):
        print("\nGenerated idea:")
        print(json.dumps(result["idea"], indent=2))
    else:
        print(f"\nError: {result.get('error', 'No idea extracted')}")

    print(f"\nTotal tokens used: {result.get('total_tokens', 'N/A')}")
    print(f"Number of turns: {len(result.get('turns', []))}")
