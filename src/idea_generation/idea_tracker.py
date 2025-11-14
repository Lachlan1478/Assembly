# idea_tracker.py
# Enhanced idea tracking system with status management and rejection reasoning

import re
import asyncio
from typing import Dict, List, Any, Optional
from openai import OpenAI
from difflib import SequenceMatcher


def is_detailed_proposal(response: str) -> bool:
    """
    Detect if a response contains a detailed proposal/solution.

    Looks for keywords and patterns that indicate a persona is proposing
    or describing a concrete solution, not just mentioning it in passing.

    Args:
        response: Persona's response text

    Returns:
        True if response contains a detailed proposal
    """
    # Keywords that indicate detailed proposals
    proposal_patterns = [
        r'\bI propose\b',
        r'\bI suggest\b',
        r'\bwhat if we built\b',
        r'\bwhat if we created\b',
        r'\bconsider [\w\s]+ that\b',
        r'\b(?:solution|approach|concept|idea):\s*[\w\s]+(?:would|could|will)',
        r'\bthis would work by\b',
        r'\bhere\'s how it would work\b',
        r'\bthe solution would\b',
        r'\bour product would\b',
    ]

    # Check for proposal keywords
    for pattern in proposal_patterns:
        if re.search(pattern, response, re.IGNORECASE):
            # Additional check: must be reasonably detailed (>150 chars after keyword)
            match = re.search(pattern, response, re.IGNORECASE)
            if match and len(response[match.start():]) > 150:
                return True

    return False


def similarity_ratio(str1: str, str2: str) -> float:
    """Calculate similarity ratio between two strings (0-1)."""
    return SequenceMatcher(None, str1.lower(), str2.lower()).ratio()


def find_existing_idea(title: str, ideas_discussed: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Find if an idea with similar title already exists.

    Uses fuzzy matching to catch similar ideas:
    - "HealthBridge" vs "Health Bridge"
    - "MediSync" vs "Medi-Sync"

    Args:
        title: Idea title to search for
        ideas_discussed: List of existing ideas

    Returns:
        Existing idea dict if found, None otherwise
    """
    for idea in ideas_discussed:
        # Exact match
        if idea["title"].lower() == title.lower():
            return idea

        # Fuzzy match (>0.85 similarity)
        if similarity_ratio(idea["title"], title) > 0.85:
            return idea

    return None


async def extract_idea_concept_async(
    response: str,
    shared_context: Dict[str, Any],
    turn_count: int,
    phase_id: str,
    model_name: str = "gpt-4o-mini"
) -> Optional[Dict[str, Any]]:
    """
    Asynchronously extract idea concept from a detailed proposal.

    Extracts:
    - Title: Name of the solution/product
    - Overview: 1-2 sentence description of what it is
    - Example: Concrete use case showing how it would be used

    Args:
        response: Persona's response containing proposal
        shared_context: Shared context dict (will be mutated)
        turn_count: Current turn number
        phase_id: Current phase ID
        model_name: LLM model to use for extraction

    Returns:
        Extracted idea dict if successful, None otherwise
    """
    client = OpenAI()

    extraction_prompt = f"""Extract the startup idea/solution from this response.

Response:
{response}

Extract the following:
1. **Title**: The name of the solution/product (e.g., "HealthBridge", "MediSync")
2. **Overview**: 1-2 sentences describing what it is and how it works
3. **Example**: A concrete real-world use case showing how someone would use it

Return as JSON:
{{
  "title": "...",
  "overview": "...",
  "example": "..."
}}

If no clear solution is proposed, return: {{"title": null}}
"""

    try:
        # Run in thread pool to not block async event loop
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": extraction_prompt}],
                temperature=0.0,
                max_tokens=500
            )
        )

        result_text = completion.choices[0].message.content.strip()

        # Parse JSON
        import json
        # Extract JSON from markdown code blocks if present
        json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(1)
        elif result_text.startswith('```') and result_text.endswith('```'):
            result_text = result_text[3:-3].strip()

        extracted = json.loads(result_text)

        # Check if extraction was successful
        if not extracted.get("title"):
            return None

        title = extracted["title"]
        overview = extracted.get("overview", "")
        example = extracted.get("example", "")

        # Check if similar idea already exists
        existing = find_existing_idea(title, shared_context["ideas_discussed"])

        if existing:
            # Update existing idea with refinement
            if len(overview) > len(existing.get("overview", "")):
                # New description is more detailed, add as refinement
                existing["refinements"].append({
                    "turn": turn_count,
                    "phase": phase_id,
                    "overview": overview,
                    "example": example
                })
                existing["overview"] = overview
                existing["example"] = example
                existing["last_updated_turn"] = turn_count
                print(f"[i] Refined existing idea: '{title}' (turn {turn_count})")
            return existing
        else:
            # Create new idea entry
            new_idea = {
                "title": title,
                "overview": overview,
                "example": example,
                "status": "in_play",
                "rejection_reason": None,
                "first_mentioned_phase": phase_id,
                "first_mentioned_turn": turn_count,
                "last_updated_turn": turn_count,
                "refinements": [{
                    "turn": turn_count,
                    "phase": phase_id,
                    "overview": overview,
                    "example": example
                }]
            }

            # Add to shared context
            shared_context["ideas_discussed"].append(new_idea)
            shared_context["current_focus"] = title

            print(f"[i] New idea extracted: '{title}' (turn {turn_count})")
            return new_idea

    except Exception as e:
        print(f"[!] Error extracting idea concept: {e}")
        return None


async def detect_rejections_async(
    response: str,
    shared_context: Dict[str, Any],
    turn_count: int,
    phase_id: str,
    model_name: str = "gpt-4o-mini"
) -> Optional[Dict[str, Any]]:
    """
    Asynchronously detect if response contains rejection of an idea.

    Looks for patterns like:
    - "I don't think [idea] will work because..."
    - "[Idea] has a fatal flaw: ..."
    - "We should abandon [idea] since..."

    Args:
        response: Persona's response to analyze
        shared_context: Shared context dict (will be mutated if rejection found)
        turn_count: Current turn number
        phase_id: Current phase ID
        model_name: LLM model to use

    Returns:
        Rejection info dict if found, None otherwise
    """
    # Quick heuristic check first (avoid unnecessary LLM calls)
    rejection_keywords = [
        "won't work", "will not work", "doesn't work", "fatal flaw",
        "major problem", "abandon", "reject", "not feasible", "too risky",
        "deal-breaker", "show-stopper", "infeasible", "impractical"
    ]

    has_rejection_signal = any(keyword in response.lower() for keyword in rejection_keywords)
    if not has_rejection_signal:
        return None

    client = OpenAI()

    # Get list of current ideas for context
    current_ideas = [idea["title"] for idea in shared_context["ideas_discussed"]
                     if idea["status"] == "in_play"]

    detection_prompt = f"""Analyze if this response rejects or argues against any of the current ideas being discussed.

Current ideas: {', '.join(current_ideas) if current_ideas else 'None'}

Response:
{response}

Is the speaker rejecting one of the ideas? If yes, extract:
1. **idea_title**: Which idea is being rejected (exact match from current ideas)
2. **rejection_reason**: Brief summary of why (1-2 sentences)

Return as JSON:
{{
  "rejected": true,
  "idea_title": "...",
  "rejection_reason": "..."
}}

If NO clear rejection, return: {{"rejected": false}}
"""

    try:
        loop = asyncio.get_event_loop()
        completion = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": detection_prompt}],
                temperature=0.0,
                max_tokens=300
            )
        )

        result_text = completion.choices[0].message.content.strip()

        # Parse JSON
        import json
        json_match = re.search(r'```json\s*(.*?)\s*```', result_text, re.DOTALL)
        if json_match:
            result_text = json_match.group(1)
        elif result_text.startswith('```') and result_text.endswith('```'):
            result_text = result_text[3:-3].strip()

        detected = json.loads(result_text)

        if detected.get("rejected"):
            idea_title = detected.get("idea_title")
            rejection_reason = detected.get("rejection_reason")

            # Find and update the idea
            existing = find_existing_idea(idea_title, shared_context["ideas_discussed"])
            if existing and existing["status"] == "in_play":
                mark_idea_rejected(
                    shared_context=shared_context,
                    idea_title=idea_title,
                    reason=rejection_reason,
                    turn=turn_count,
                    phase=phase_id
                )
                return {
                    "idea_title": idea_title,
                    "rejection_reason": rejection_reason,
                    "turn": turn_count
                }

        return None

    except Exception as e:
        print(f"[!] Error detecting rejections: {e}")
        return None


def mark_idea_rejected(
    shared_context: Dict[str, Any],
    idea_title: str,
    reason: str,
    turn: int,
    phase: str
) -> None:
    """
    Mark an idea as rejected with reasoning.

    Args:
        shared_context: Shared context dict to mutate
        idea_title: Title of idea to reject
        reason: Why it was rejected
        turn: Turn number when rejected
        phase: Phase ID when rejected
    """
    existing = find_existing_idea(idea_title, shared_context["ideas_discussed"])

    if existing:
        existing["status"] = "rejected"
        existing["rejection_reason"] = reason
        existing["rejected_turn"] = turn
        existing["rejected_phase"] = phase
        existing["last_updated_turn"] = turn

        print(f"[!] Idea rejected: '{idea_title}' - {reason}")

        # Update current_focus if this was the focus
        if shared_context.get("current_focus") == idea_title:
            # Find next in-play idea to focus on
            in_play = [i for i in shared_context["ideas_discussed"] if i["status"] == "in_play"]
            shared_context["current_focus"] = in_play[-1]["title"] if in_play else None


def get_ideas_in_play(ideas_discussed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all ideas with status='in_play'."""
    return [idea for idea in ideas_discussed if idea["status"] == "in_play"]


def get_rejected_ideas(ideas_discussed: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Get all ideas with status='rejected'."""
    return [idea for idea in ideas_discussed if idea["status"] == "rejected"]


def format_ideas_for_prompt(ideas: List[Dict[str, Any]], max_count: int = 3) -> str:
    """
    Format ideas for inclusion in prompts.

    Args:
        ideas: List of idea dicts
        max_count: Maximum number of ideas to include (most recent)

    Returns:
        Formatted string for prompt inclusion
    """
    if not ideas:
        return "None yet."

    recent_ideas = ideas[-max_count:]  # Take most recent

    formatted = []
    for idea in recent_ideas:
        formatted.append(
            f"**{idea['title']}**: {idea['overview']}\n"
            f"   Example: {idea['example']}"
        )

    return "\n\n".join(formatted)


def format_rejections_for_prompt(rejected_ideas: List[Dict[str, Any]]) -> str:
    """
    Format rejected ideas for prompt inclusion.

    Args:
        rejected_ideas: List of rejected idea dicts

    Returns:
        Formatted string warning about rejected ideas
    """
    if not rejected_ideas:
        return ""

    formatted = []
    for idea in rejected_ideas:
        formatted.append(
            f"- **{idea['title']}**: Rejected in {idea.get('rejected_phase', 'earlier phase')} "
            f"because {idea['rejection_reason']}"
        )

    return "\n".join(formatted)


def get_idea_summary_stats(ideas_discussed: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    Get summary statistics about ideas.

    Returns:
        Dict with counts: total, in_play, rejected
    """
    return {
        "total": len(ideas_discussed),
        "in_play": len([i for i in ideas_discussed if i["status"] == "in_play"]),
        "rejected": len([i for i in ideas_discussed if i["status"] == "rejected"])
    }
