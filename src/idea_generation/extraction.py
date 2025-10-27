# idea_brainstorm_01d_extraction.py
# Extraction module: Extract structured ideas from conversations

import json
import os
import re
from openai import OpenAI
from typing import List, Dict, Any


def extract_idea_title(content: str) -> str:
    """
    Extract idea title from persona response content.

    Looks for common patterns like:
    - **Title:** CodeFlowSync
    - Title: CodeFlowSync
    - **CodeFlowSync**

    Args:
        content: Response content from persona

    Returns:
        Extracted title or empty string if none found
    """
    lines = content.split("\n")

    # Look for explicit title markers
    for line in lines:
        if "title" in line.lower() and (":" in line or "**" in line):
            # Extract text after colon or within bold markers
            title = line.split(":")[-1].strip().strip("*").strip()
            if title and len(title) < 100:  # Sanity check
                return title

    # Fallback: look for first bolded text
    bold_match = re.search(r'\*\*([^*]+)\*\*', content)
    if bold_match:
        title = bold_match.group(1).strip()
        if len(title) < 100:
            return title

    return ""


def extract_ideas_with_llm(logs: List[Dict[str, Any]], number_of_ideas: int, model_name: str = "gpt-4o-mini") -> List[Dict[str, Any]]:
    """
    Extract structured startup ideas from conversation logs using LLM.

    This is a fallback when personas don't format output as JSON naturally.
    The LLM reads the conversation and extracts the structured ideas.

    Args:
        logs: List of conversation exchanges
        number_of_ideas: Expected number of ideas to extract
        model_name: OpenAI model to use for extraction

    Returns:
        List of idea dictionaries with required fields
    """
    # Build conversation summary for extraction
    conversation_text = ""
    for exchange in logs:
        speaker = exchange.get("speaker", "Unknown")
        content = exchange.get("content", "")
        conversation_text += f"\n\n{speaker}:\n{content}"

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

    extraction_prompt = f"""You are extracting startup ideas from a multi-persona conversation.

Read the conversation below and extract {number_of_ideas} startup idea(s) that were discussed.

Each idea must include these fields:
- title: Name of the startup
- description: What it does (2-3 sentences)
- target_users: Who will use it
- primary_outcome: Main value delivered
- must_haves: Essential features (list)
- constraints: Limitations to consider (list)
- non_goals: What it explicitly won't do (list)

Return a JSON array of idea objects. If multiple similar ideas were proposed, consolidate them into the best version.

CONVERSATION:
{conversation_text}

Extract the ideas as a JSON array:"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You extract structured startup ideas from conversations. Always return valid JSON arrays."},
                {"role": "user", "content": extraction_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3  # Lower temperature for more consistent extraction
        )

        raw_response = response.choices[0].message.content
        parsed = json.loads(raw_response)

        # Handle both {"ideas": [...]} and direct array formats
        if isinstance(parsed, dict) and "ideas" in parsed:
            ideas = parsed["ideas"]
        elif isinstance(parsed, list):
            ideas = parsed
        else:
            ideas = [parsed]

        print(f"\n[OK] LLM extraction successful: {len(ideas)} idea(s)")
        return ideas

    except Exception as e:
        print(f"\n[!] LLM extraction failed: {e}")
        return []
