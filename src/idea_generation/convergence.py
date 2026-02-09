# convergence.py
# Final "Decision Owner / Convergence" phase that refines Assembly output
# into a commercially sharp, structured format using iterative self-critique.

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from openai import OpenAI


@dataclass
class ConvergenceOutput:
    """Structured output from the convergence phase."""
    product_name: str
    one_sentence_pitch: str
    target_user_icp: str
    mvp_bullets: List[str]  # Max 5
    monetization_model: str
    key_differentiator: str
    what_we_are_not_doing: List[str]
    risks_unknowns: List[str]  # Top 3
    next_7_day_plan: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


# Turn 1: Synthesize conversation into draft product spec
SYNTHESIS_PROMPT = """You are a Decision Owner reviewing a multi-persona brainstorm about a startup idea.

INSPIRATION:
{inspiration}

CONVERSATION SUMMARY:
{conversation_summary}

RAW IDEAS DISCUSSED:
{ideas_discussed}

Your task: Synthesize this conversation into a SINGLE, focused product concept.

Pick the strongest idea thread from the discussion. If multiple ideas were discussed, choose the one with:
- Clearest target user
- Most concrete differentiation
- Most feasible MVP scope

Write a draft product specification covering:
1. Product name (memorable, clear)
2. One-sentence pitch (what it does, for whom, why it matters)
3. Target user (specific ICP - not "everyone")
4. Core MVP features (what ships in v1)
5. How it makes money
6. What makes it different from alternatives
7. What it explicitly WON'T do (scope boundaries)

Be specific and concrete. No hand-waving."""


# Turn 2: Self-critique
CRITIQUE_PROMPT = """You are a skeptical investor reviewing this product spec.

DRAFT SPEC:
{draft_spec}

Find exactly 3 weaknesses:

1. **Positioning weakness**: Is the pitch clear? Is the ICP too broad? Is the differentiator actually different?

2. **Feasibility weakness**: Is the MVP too big? Are there hidden technical risks? Can a small team build this?

3. **Commercial weakness**: Is the monetization model realistic? Will people actually pay? What's the GTM challenge?

For each weakness, be specific about:
- What's wrong
- Why it matters
- What question it leaves unanswered"""


# Turn 3: Address critiques and finalize
REFINEMENT_PROMPT = """You are refining a product spec based on critical feedback.

ORIGINAL SPEC:
{draft_spec}

CRITIQUES:
{critiques}

Address each critique with specific improvements. Then produce the FINAL output in this exact JSON format:

{{
    "product_name": "Clear, memorable name",
    "one_sentence_pitch": "What it does, for whom, why now - max 20 words",
    "target_user_icp": "Specific persona with context (e.g., 'Remote engineering managers at 50-200 person startups who run 3+ standup meetings per week')",
    "mvp_bullets": [
        "Feature 1 - concrete and buildable",
        "Feature 2",
        "Feature 3",
        "Feature 4",
        "Feature 5"
    ],
    "monetization_model": "How it makes money (pricing, who pays, when)",
    "key_differentiator": "The ONE thing that makes this 10x better than alternatives",
    "what_we_are_not_doing": [
        "Explicit scope boundary 1",
        "Explicit scope boundary 2",
        "Explicit scope boundary 3"
    ],
    "risks_unknowns": [
        "Risk 1: description",
        "Risk 2: description",
        "Risk 3: description"
    ],
    "next_7_day_plan": [
        "Day 1-2: Specific action",
        "Day 3-4: Specific action",
        "Day 5-7: Specific action"
    ]
}}

MVP must have exactly 5 bullets or fewer. Be ruthlessly specific."""


def summarize_conversation(logs: List[Dict[str, Any]], max_turns: int = 20) -> str:
    """
    Create a condensed summary of the conversation for the convergence phase.

    Args:
        logs: List of exchange dicts from the conversation
        max_turns: Maximum turns to include

    Returns:
        Formatted conversation summary
    """
    if not logs:
        return "(No conversation logs available)"

    # Take last N turns to focus on the most refined discussion
    recent = logs[-max_turns:]

    lines = []
    for ex in recent:
        speaker = ex.get("speaker", "Unknown")
        phase = ex.get("phase", "")
        content = ex.get("content", "")

        # Truncate long content
        if len(content) > 500:
            content = content[:500] + "..."

        lines.append(f"[{phase}] {speaker}: {content}")

    return "\n\n".join(lines)


def format_ideas_discussed(ideas_discussed: List[Dict[str, Any]]) -> str:
    """Format the ideas_discussed list for the prompt."""
    if not ideas_discussed:
        return "(No structured ideas captured)"

    lines = []
    for idea in ideas_discussed:
        title = idea.get("title", "Untitled")
        overview = idea.get("overview", "")
        status = idea.get("status", "discussed")

        lines.append(f"- {title} [{status}]: {overview[:200]}...")

    return "\n".join(lines)


def run_convergence_phase(
    inspiration: str,
    logs: List[Dict[str, Any]],
    ideas_discussed: List[Dict[str, Any]],
    raw_ideas: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Run the convergence phase: 3-turn iterative refinement to produce
    a commercially sharp final output.

    Args:
        inspiration: Original inspiration/domain
        logs: Conversation logs from meeting_facilitator
        ideas_discussed: Ideas tracked during conversation
        raw_ideas: Extracted business ideas from Assembly
        model: Model to use
        verbose: Print progress

    Returns:
        Dict with convergence_output and intermediate turns
    """
    client = OpenAI()

    result = {
        "convergence_output": None,
        "turns": [],
        "success": False,
        "error": None,
    }

    # Prepare context
    conversation_summary = summarize_conversation(logs)
    ideas_summary = format_ideas_discussed(ideas_discussed)

    # Also include raw extracted ideas if available
    if raw_ideas:
        ideas_summary += "\n\nEXTRACTED IDEAS:\n"
        for idea in raw_ideas:
            if isinstance(idea, dict):
                title = idea.get("title", "Untitled")
                desc = idea.get("description", "")[:200]
                ideas_summary += f"- {title}: {desc}...\n"

    try:
        # Turn 1: Synthesis
        if verbose:
            print("\n[Convergence 1/3] Synthesizing conversation into draft spec...")

        turn1_response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a Decision Owner who synthesizes brainstorms into actionable product specs. Be specific and concrete."
                },
                {
                    "role": "user",
                    "content": SYNTHESIS_PROMPT.format(
                        inspiration=inspiration,
                        conversation_summary=conversation_summary,
                        ideas_discussed=ideas_summary
                    )
                }
            ],
            temperature=0.7,
        )

        draft_spec = turn1_response.choices[0].message.content
        result["turns"].append({
            "turn": 1,
            "type": "synthesis",
            "content": draft_spec,
            "tokens": turn1_response.usage.total_tokens if turn1_response.usage else 0
        })

        if verbose:
            print(f"    Draft spec generated ({len(draft_spec)} chars)")

        # Turn 2: Self-critique
        if verbose:
            print("[Convergence 2/3] Running self-critique...")

        turn2_response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a skeptical investor. Find real weaknesses, not softballs."
                },
                {
                    "role": "user",
                    "content": CRITIQUE_PROMPT.format(draft_spec=draft_spec)
                }
            ],
            temperature=0.7,
        )

        critiques = turn2_response.choices[0].message.content
        result["turns"].append({
            "turn": 2,
            "type": "critique",
            "content": critiques,
            "tokens": turn2_response.usage.total_tokens if turn2_response.usage else 0
        })

        if verbose:
            print(f"    Critiques generated ({len(critiques)} chars)")

        # Turn 3: Refinement + JSON output
        if verbose:
            print("[Convergence 3/3] Refining and producing final output...")

        turn3_response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a product strategist finalizing a spec. Output valid JSON only."
                },
                {
                    "role": "user",
                    "content": REFINEMENT_PROMPT.format(
                        draft_spec=draft_spec,
                        critiques=critiques
                    )
                }
            ],
            temperature=0.3,  # Lower for consistent JSON
        )

        final_json_str = turn3_response.choices[0].message.content
        result["turns"].append({
            "turn": 3,
            "type": "final_output",
            "content": final_json_str,
            "tokens": turn3_response.usage.total_tokens if turn3_response.usage else 0
        })

        # Parse JSON output
        final_output = extract_json_from_response(final_json_str)

        if final_output:
            # Validate and create ConvergenceOutput
            convergence = ConvergenceOutput(
                product_name=final_output.get("product_name", "Unnamed"),
                one_sentence_pitch=final_output.get("one_sentence_pitch", ""),
                target_user_icp=final_output.get("target_user_icp", ""),
                mvp_bullets=final_output.get("mvp_bullets", [])[:5],  # Max 5
                monetization_model=final_output.get("monetization_model", ""),
                key_differentiator=final_output.get("key_differentiator", ""),
                what_we_are_not_doing=final_output.get("what_we_are_not_doing", []),
                risks_unknowns=final_output.get("risks_unknowns", [])[:3],  # Top 3
                next_7_day_plan=final_output.get("next_7_day_plan", []),
            )

            result["convergence_output"] = convergence.to_dict()
            result["success"] = True

            if verbose:
                print(f"    Final output: {convergence.product_name}")
                print(f"    Pitch: {convergence.one_sentence_pitch[:80]}...")
        else:
            result["error"] = "Failed to parse JSON from final turn"
            if verbose:
                print("    [!] Failed to parse JSON output")

    except Exception as e:
        result["error"] = str(e)
        if verbose:
            print(f"    [!] Convergence error: {e}")

    return result


def extract_json_from_response(content: str) -> Optional[dict]:
    """Extract JSON from LLM response."""
    import re

    # Try to find JSON block
    json_match = re.search(r'\{[^{}]*"product_name"[^{}]*\}', content, re.DOTALL)

    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    # Try more aggressive extraction
    try:
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            json_str = content[start:end+1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        pass

    return None


def format_convergence_output(output: Dict[str, Any]) -> str:
    """Format convergence output for display/logging."""
    if not output:
        return "(No convergence output)"

    lines = [
        "=" * 60,
        "CONVERGENCE OUTPUT",
        "=" * 60,
        "",
        f"PRODUCT: {output.get('product_name', 'Unnamed')}",
        "",
        f"PITCH: {output.get('one_sentence_pitch', '')}",
        "",
        f"TARGET USER (ICP): {output.get('target_user_icp', '')}",
        "",
        "MVP (v1 Features):",
    ]

    for bullet in output.get("mvp_bullets", []):
        lines.append(f"  - {bullet}")

    lines.extend([
        "",
        f"MONETIZATION: {output.get('monetization_model', '')}",
        "",
        f"KEY DIFFERENTIATOR: {output.get('key_differentiator', '')}",
        "",
        "WHAT WE'RE NOT DOING:",
    ])

    for item in output.get("what_we_are_not_doing", []):
        lines.append(f"  - {item}")

    lines.extend([
        "",
        "RISKS / UNKNOWNS:",
    ])

    for risk in output.get("risks_unknowns", []):
        lines.append(f"  - {risk}")

    lines.extend([
        "",
        "NEXT 7-DAY PLAN:",
    ])

    for step in output.get("next_7_day_plan", []):
        lines.append(f"  - {step}")

    lines.append("=" * 60)

    return "\n".join(lines)
