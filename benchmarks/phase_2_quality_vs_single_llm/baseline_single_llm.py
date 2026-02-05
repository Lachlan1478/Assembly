# baseline_single_llm.py
# Single LLM call generator for fair comparison with Assembly

import json
import os
import sys
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI


# Single comprehensive prompt that combines all Assembly stages
# Updated to use explicit team-of-experts framing for fair comparison
BASELINE_PROMPT = """You are facilitating a brainstorm with a team of experts:

- Market Strategist: Analyzes competitive landscape, market timing, and positioning opportunities
- User Advocate: Champions user pain points, personas, and user experience considerations
- Technical Architect: Evaluates technical feasibility, differentiation, and implementation approach
- Business Developer: Focuses on monetization strategies, go-to-market, and business model

Given the following inspiration, conduct a team discussion where each expert contributes their perspective:

{inspiration}

Have each team member contribute to these stages:

1. PROBLEM DISCOVERY (User Advocate leads): What are the core pain points? Who feels this most acutely? Why is this problem worth solving now?

2. COMPETITIVE LANDSCAPE (Market Strategist leads): What solutions already exist? Where do they fall short? What gaps or whitespace opportunities exist?

3. SOLUTION EXPLORATION (Technical Architect leads): What approach would address these pain points? What would make this 10x better than existing options?

4. BUSINESS VIABILITY (Business Developer leads): How would this make money? What's the go-to-market strategy?

5. SYNTHESIS (All): Consolidate the team's insights into a concrete, actionable startup concept.

After your team discussion, provide the final startup idea in this exact JSON format:

{{
    "title": "Clear, memorable name for the startup",
    "description": "What it does in 2-3 sentences",
    "target_users": "Specific user profile",
    "primary_outcome": "Main value delivered",
    "must_haves": ["Essential feature 1", "Essential feature 2", "..."],
    "constraints": ["Realistic limitation 1", "Realistic limitation 2", "..."],
    "non_goals": ["What it explicitly won't do 1", "What it explicitly won't do 2", "..."]
}}

Provide your analysis first, then the final JSON idea."""


def generate_idea_single_llm(
    inspiration: str,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
) -> dict:
    """
    Generate a startup idea with a single LLM call.

    Uses the same output structure as Assembly for fair comparison.

    Args:
        inspiration: The domain/context for idea generation
        model: Model to use
        temperature: Generation temperature

    Returns:
        Dictionary with the generated idea (same format as Assembly output)
    """
    client = OpenAI()

    prompt = BASELINE_PROMPT.format(inspiration=inspiration)

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert startup consultant. Provide thorough analysis followed by a concrete startup idea in JSON format.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=temperature,
        )

        content = response.choices[0].message.content

        # Extract JSON from response
        idea = extract_json_from_response(content)

        return {
            "idea": idea,
            "raw_response": content,
            "model": model,
            "tokens_used": response.usage.total_tokens if response.usage else None,
        }

    except Exception as e:
        return {
            "idea": None,
            "error": str(e),
            "model": model,
        }


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

    print("Testing single LLM baseline generator...")
    result = generate_idea_single_llm(test_inspiration)

    if result.get("idea"):
        print("\nGenerated idea:")
        print(json.dumps(result["idea"], indent=2))
        print(f"\nTokens used: {result.get('tokens_used', 'N/A')}")
    else:
        print(f"\nError: {result.get('error', 'Unknown error')}")
