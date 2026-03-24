# convergence.py
# Final "Decision Owner / Convergence" phase that refines Assembly output
# into a domain-appropriate structured format using iterative self-critique.
#
# Domains:
#   "product"   — startup/product idea → ConvergenceOutput (commercial spec)
#   "technical" — coding/architecture  → TechnicalConvergenceOutput (design spec)
#   "general"   — anything else        → GeneralConvergenceOutput (decision summary)

import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from openai import OpenAI


@dataclass
class ConvergenceOutput:
    """Structured output for product/startup domain."""
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


@dataclass
class TechnicalConvergenceOutput:
    """Structured output for technical/coding domain."""
    solution_name: str
    one_sentence_summary: str
    target_context: str          # e.g. "Node.js backends with >10k req/min"
    architecture_bullets: List[str]  # Max 5 key decisions
    tech_stack: str
    key_differentiator: str      # vs closest alternative approach
    out_of_scope: List[str]
    technical_risks: List[str]   # Top 3
    implementation_plan: List[str]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class GeneralConvergenceOutput:
    """Structured output for general/open-ended domain."""
    title: str
    one_sentence_summary: str
    target_audience: str
    key_points: List[str]       # Max 5 main takeaways
    recommended_approach: str
    key_differentiator: str     # vs doing nothing or obvious alternative
    out_of_scope: List[str]
    risks: List[str]            # Top 3
    action_plan: List[str]

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


# Turn 2: Self-critique — hardened to force competitor naming and pricing specifics
CRITIQUE_PROMPT = """You are a skeptical seed investor reviewing this product spec before a partner meeting.

DRAFT SPEC:
{draft_spec}

Find exactly 3 weaknesses. Be brutal — your partners will ask these questions:

1. **Positioning weakness**: Name the ONE existing product that already does the closest thing to this.
   - What does that product charge and why would a customer switch?
   - Is the differentiator in this spec actually 10x better, or just marginally different?
   - If the ICP is "SMBs" or "developers" or any group larger than 10,000 people, the ICP is too broad — demand a specific sub-segment.

2. **Feasibility weakness**: Is the MVP too big for a 2-person team in 90 days?
   - Name the hardest technical dependency (an API, a model, a dataset, a regulatory approval).
   - What breaks if that dependency fails or prices change?

3. **Commercial weakness** (this is the hardest question — do not soften it):
   - Name a specific type of company or person who would write a cheque for this TODAY.
   - State the most credible price point ($X/month or $X one-time) and explain why that number, not 2x or 0.5x.
   - Identify the go-to-market motion: outbound sales, product-led growth, marketplace listing, or partnership. Pick one and explain why the others won't work.
   - What prevents a well-funded incumbent (name one) from copying this in 6 months?

For each weakness, end with a single sentence: "This spec fails to answer: [specific question]." """


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
    "monetization_model": "Specific model: who pays, exact price point (e.g. '$49/month per seat'), when they pay (upfront/monthly/usage), and the primary GTM motion (PLG/outbound/marketplace)",
    "key_differentiator": "The ONE thing that makes this 10x better than [name the closest competitor]. Explain why that competitor cannot copy this in 6 months.",
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


# ─── Technical domain prompts ────────────────────────────────────────────────

TECHNICAL_SYNTHESIS_PROMPT = """You are a Technical Architect reviewing a multi-persona engineering discussion.

PROBLEM:
{inspiration}

CONVERSATION SUMMARY:
{conversation_summary}

PROPOSALS DISCUSSED:
{ideas_discussed}

Synthesize into a SINGLE, focused technical solution covering:
1. Solution name (descriptive, implementation-ready)
2. One-sentence summary (what it does and what problem it solves)
3. Target context (specific environment, codebase type, or scale this applies to)
4. Core architecture decisions (the 3–5 choices that define the design)
5. Tech stack (primary language, framework, key libraries)
6. Key differentiator vs the most obvious alternative approach
7. Explicit scope: what this design does NOT address

Be concrete about trade-offs. No hand-waving."""


TECHNICAL_CRITIQUE_PROMPT = """You are a senior engineer doing a design review before this goes to the team.

DRAFT SPEC:
{draft_spec}

Find exactly 3 weaknesses:

1. **Architecture weakness**: Is the design over-engineered for the stated context?
   - Name a specific coupling point or hidden dependency that creates fragility.
   - What breaks at 10x the stated load or data volume?

2. **Implementation weakness**: What is the hardest single piece to build correctly?
   - Name the external dependency (API, model, service, dataset) most likely to fail or change.
   - What happens to the design if that dependency is unavailable or repriced?

3. **Operational weakness**: How does this behave in production?
   - What is the observability story — how would you know it is broken before users complain?
   - How would you debug it at 2am when the logs are unhelpful?

For each weakness, end with: "This spec fails to answer: [specific question]." """


TECHNICAL_REFINEMENT_PROMPT = """You are finalizing a technical design spec based on peer review feedback.

ORIGINAL SPEC:
{draft_spec}

REVIEW FEEDBACK:
{critiques}

Address each point with specific improvements. Then produce the FINAL output in this exact JSON format:

{{
    "solution_name": "Descriptive name for the solution",
    "one_sentence_summary": "What it does and the problem it solves - max 20 words",
    "target_context": "Specific environment (e.g., 'Python async services handling >5k concurrent connections')",
    "architecture_bullets": [
        "Decision 1: specific choice and the trade-off it makes",
        "Decision 2",
        "Decision 3",
        "Decision 4",
        "Decision 5"
    ],
    "tech_stack": "Language + framework + key libraries (e.g., 'Python 3.12, asyncio, Redis 7, PostgreSQL 16')",
    "key_differentiator": "Why this approach vs [name the closest alternative] — name the concrete trade-off that favours this design",
    "out_of_scope": [
        "Explicit boundary 1",
        "Explicit boundary 2",
        "Explicit boundary 3"
    ],
    "technical_risks": [
        "Risk 1: description and mitigation",
        "Risk 2: description and mitigation",
        "Risk 3: description and mitigation"
    ],
    "implementation_plan": [
        "Phase 1 (Day 1-2): Specific deliverable",
        "Phase 2 (Day 3-4): Specific deliverable",
        "Phase 3 (Day 5-7): Specific deliverable"
    ]
}}

Architecture must have exactly 5 bullets or fewer. Be specific about versions and quantities."""


# ─── General domain prompts ───────────────────────────────────────────────────

GENERAL_SYNTHESIS_PROMPT = """You are a Decision Facilitator reviewing a multi-perspective discussion.

TOPIC:
{inspiration}

CONVERSATION SUMMARY:
{conversation_summary}

KEY POSITIONS DISCUSSED:
{ideas_discussed}

Synthesize into a SINGLE, focused recommendation covering:
1. Title (clear name for the recommendation or decision)
2. One-sentence summary (what it recommends and why)
3. Target audience (who this recommendation is for)
4. Key points (the 3–5 most important findings or decisions)
5. Recommended approach (the specific path forward)
6. Key differentiator (vs doing nothing or the most obvious alternative)
7. Explicit scope: what this recommendation does NOT address

Be concrete and actionable."""


GENERAL_CRITIQUE_PROMPT = """You are a critical reviewer examining this recommendation before it is acted on.

DRAFT RECOMMENDATION:
{draft_spec}

Find exactly 3 weaknesses:

1. **Clarity weakness**: Is the recommendation specific enough to act on?
   - What ambiguous term or phrase would two people interpret differently?
   - Who is responsible for each action item?

2. **Evidence weakness**: What assumption is most likely to be wrong?
   - What evidence was cited vs assumed?
   - What would change the recommendation if it turned out to be false?

3. **Completeness weakness**: What important consideration is missing?
   - What stakeholder was not represented in the discussion?
   - What downstream consequence was not addressed?

For each weakness, end with: "This recommendation fails to answer: [specific question]." """


GENERAL_REFINEMENT_PROMPT = """You are finalizing a recommendation based on critical review feedback.

ORIGINAL RECOMMENDATION:
{draft_spec}

REVIEW FEEDBACK:
{critiques}

Address each point with specific improvements. Then produce the FINAL output in this exact JSON format:

{{
    "title": "Clear title for the recommendation",
    "one_sentence_summary": "What it recommends and why - max 20 words",
    "target_audience": "Specific audience (e.g., 'Engineering leads at 20-100 person startups adopting microservices')",
    "key_points": [
        "Finding or decision 1",
        "Finding or decision 2",
        "Finding or decision 3",
        "Finding or decision 4",
        "Finding or decision 5"
    ],
    "recommended_approach": "The specific path forward with concrete first step",
    "key_differentiator": "Why this vs [name the obvious alternative] — the specific reason to choose this path",
    "out_of_scope": [
        "Explicit boundary 1",
        "Explicit boundary 2",
        "Explicit boundary 3"
    ],
    "risks": [
        "Risk 1: description and what to watch for",
        "Risk 2: description and what to watch for",
        "Risk 3: description and what to watch for"
    ],
    "action_plan": [
        "Step 1 (Day 1-2): Specific action with owner",
        "Step 2 (Day 3-4): Specific action with owner",
        "Step 3 (Day 5-7): Specific action with owner"
    ]
}}

Key points must have exactly 5 bullets or fewer. Be specific and actionable."""


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
    domain: str = "product",
) -> Dict[str, Any]:
    """
    Run the convergence phase: 3-turn iterative refinement to produce
    a domain-appropriate final output.

    Args:
        inspiration: Original inspiration/domain
        logs: Conversation logs from meeting_facilitator
        ideas_discussed: Ideas tracked during conversation
        raw_ideas: Extracted ideas/proposals from Assembly
        model: Model to use
        verbose: Print progress
        domain: "product" | "technical" | "general"

    Returns:
        Dict with convergence_output (domain-specific dataclass as dict),
        intermediate turns, success flag, and error.
    """
    # Select prompts and output builder for this domain
    if domain == "technical":
        synthesis_prompt = TECHNICAL_SYNTHESIS_PROMPT
        critique_prompt = TECHNICAL_CRITIQUE_PROMPT
        refinement_prompt = TECHNICAL_REFINEMENT_PROMPT
        synthesis_system = "You are a Technical Architect synthesizing an engineering discussion into a concrete design spec. Be specific about trade-offs, version numbers, and scale constraints."
        critique_system = "You are a senior engineer doing a design review. Find structural weaknesses, not surface-level style issues."
        refinement_system = "You are finalizing a technical design spec. Output valid JSON only."
        domain_label = "technical design"
    elif domain == "general":
        synthesis_prompt = GENERAL_SYNTHESIS_PROMPT
        critique_prompt = GENERAL_CRITIQUE_PROMPT
        refinement_prompt = GENERAL_REFINEMENT_PROMPT
        synthesis_system = "You are a Decision Facilitator synthesizing a multi-perspective discussion into a clear, actionable recommendation. Be specific about who does what and why."
        critique_system = "You are a critical reviewer. Find gaps in clarity, evidence, and completeness — not tone or style."
        refinement_system = "You are finalizing a recommendation. Output valid JSON only."
        domain_label = "recommendation"
    else:  # "product" (default)
        synthesis_prompt = SYNTHESIS_PROMPT
        critique_prompt = CRITIQUE_PROMPT
        refinement_prompt = REFINEMENT_PROMPT
        synthesis_system = (
            "You are a Decision Owner who synthesizes brainstorms into actionable product specs. "
            "Be specific and concrete. Always identify a specific ICP (not 'developers' or 'SMBs' — "
            "a sub-segment with a named job title and context), a specific monetization model with "
            "a real price point, and name the closest existing competitor."
        )
        critique_system = "You are a skeptical seed investor. Find real weaknesses, not softballs."
        refinement_system = "You are a product strategist finalizing a spec. Output valid JSON only."
        domain_label = "product spec"

    client = OpenAI()

    result = {
        "convergence_output": None,
        "turns": [],
        "success": False,
        "error": None,
        "domain": domain,
    }

    # Prepare context
    conversation_summary = summarize_conversation(logs)
    ideas_summary = format_ideas_discussed(ideas_discussed)

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
            print(f"\n[Convergence 1/3] Synthesizing conversation into draft {domain_label}...")

        turn1_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": synthesis_system},
                {
                    "role": "user",
                    "content": synthesis_prompt.format(
                        inspiration=inspiration,
                        conversation_summary=conversation_summary,
                        ideas_discussed=ideas_summary,
                    ),
                },
            ],
            temperature=0.7,
        )

        draft_spec = turn1_response.choices[0].message.content
        result["turns"].append({
            "turn": 1,
            "type": "synthesis",
            "content": draft_spec,
            "tokens": turn1_response.usage.total_tokens if turn1_response.usage else 0,
        })

        if verbose:
            print(f"    Draft spec generated ({len(draft_spec)} chars)")

        # Turn 2: Critique
        if verbose:
            print("[Convergence 2/3] Running critique...")

        turn2_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": critique_system},
                {"role": "user", "content": critique_prompt.format(draft_spec=draft_spec)},
            ],
            temperature=0.7,
        )

        critiques = turn2_response.choices[0].message.content
        result["turns"].append({
            "turn": 2,
            "type": "critique",
            "content": critiques,
            "tokens": turn2_response.usage.total_tokens if turn2_response.usage else 0,
        })

        if verbose:
            print(f"    Critiques generated ({len(critiques)} chars)")

        # Turn 3: Refinement + JSON output
        if verbose:
            print("[Convergence 3/3] Refining and producing final output...")

        turn3_response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": refinement_system},
                {
                    "role": "user",
                    "content": refinement_prompt.format(
                        draft_spec=draft_spec,
                        critiques=critiques,
                    ),
                },
            ],
            temperature=0.3,
        )

        final_json_str = turn3_response.choices[0].message.content
        result["turns"].append({
            "turn": 3,
            "type": "final_output",
            "content": final_json_str,
            "tokens": turn3_response.usage.total_tokens if turn3_response.usage else 0,
        })

        # Parse JSON and build domain-specific output object
        final_output = extract_json_from_response(final_json_str)

        if final_output:
            convergence = _build_convergence_output(final_output, domain)
            result["convergence_output"] = convergence.to_dict()
            result["success"] = True

            if verbose:
                label = _convergence_display_label(convergence, domain)
                print(f"    Final output: {label}")
        else:
            result["error"] = "Failed to parse JSON from final turn"
            if verbose:
                print("    [!] Failed to parse JSON output")

    except Exception as e:
        result["error"] = str(e)
        if verbose:
            print(f"    [!] Convergence error: {e}")

    return result


def _build_convergence_output(data: dict, domain: str):
    """Construct the domain-appropriate output dataclass from parsed JSON."""
    if domain == "technical":
        return TechnicalConvergenceOutput(
            solution_name=data.get("solution_name", "Unnamed"),
            one_sentence_summary=data.get("one_sentence_summary", ""),
            target_context=data.get("target_context", ""),
            architecture_bullets=data.get("architecture_bullets", [])[:5],
            tech_stack=data.get("tech_stack", ""),
            key_differentiator=data.get("key_differentiator", ""),
            out_of_scope=data.get("out_of_scope", []),
            technical_risks=data.get("technical_risks", [])[:3],
            implementation_plan=data.get("implementation_plan", []),
        )
    elif domain == "general":
        return GeneralConvergenceOutput(
            title=data.get("title", "Unnamed"),
            one_sentence_summary=data.get("one_sentence_summary", ""),
            target_audience=data.get("target_audience", ""),
            key_points=data.get("key_points", [])[:5],
            recommended_approach=data.get("recommended_approach", ""),
            key_differentiator=data.get("key_differentiator", ""),
            out_of_scope=data.get("out_of_scope", []),
            risks=data.get("risks", [])[:3],
            action_plan=data.get("action_plan", []),
        )
    else:  # "product"
        return ConvergenceOutput(
            product_name=data.get("product_name", "Unnamed"),
            one_sentence_pitch=data.get("one_sentence_pitch", ""),
            target_user_icp=data.get("target_user_icp", ""),
            mvp_bullets=data.get("mvp_bullets", [])[:5],
            monetization_model=data.get("monetization_model", ""),
            key_differentiator=data.get("key_differentiator", ""),
            what_we_are_not_doing=data.get("what_we_are_not_doing", []),
            risks_unknowns=data.get("risks_unknowns", [])[:3],
            next_7_day_plan=data.get("next_7_day_plan", []),
        )


def _convergence_display_label(convergence, domain: str) -> str:
    """Return a short display string for the verbose completion log."""
    if domain == "technical":
        return convergence.solution_name
    elif domain == "general":
        return convergence.title
    else:
        return f"{convergence.product_name} — {convergence.one_sentence_pitch[:60]}..."


def extract_json_from_response(content: str) -> Optional[dict]:
    """Extract JSON from LLM response."""
    # Use start/rfind extraction — more reliable than regex for nested JSON
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
    """Format convergence output for display/logging.

    Detects domain from which keys are present in the output dict.
    """
    if not output:
        return "(No convergence output)"

    sep = "=" * 60

    # Technical domain
    if "solution_name" in output:
        lines = [sep, "CONVERGENCE OUTPUT (TECHNICAL)", sep, "",
                 f"SOLUTION: {output.get('solution_name', 'Unnamed')}", "",
                 f"SUMMARY: {output.get('one_sentence_summary', '')}", "",
                 f"TARGET CONTEXT: {output.get('target_context', '')}", "",
                 "ARCHITECTURE DECISIONS:"]
        for b in output.get("architecture_bullets", []):
            lines.append(f"  - {b}")
        lines += ["", f"TECH STACK: {output.get('tech_stack', '')}", "",
                  f"KEY DIFFERENTIATOR: {output.get('key_differentiator', '')}", "",
                  "OUT OF SCOPE:"]
        for item in output.get("out_of_scope", []):
            lines.append(f"  - {item}")
        lines += ["", "TECHNICAL RISKS:"]
        for risk in output.get("technical_risks", []):
            lines.append(f"  - {risk}")
        lines += ["", "IMPLEMENTATION PLAN:"]
        for step in output.get("implementation_plan", []):
            lines.append(f"  - {step}")

    # General domain
    elif "recommended_approach" in output:
        lines = [sep, "CONVERGENCE OUTPUT (GENERAL)", sep, "",
                 f"TITLE: {output.get('title', 'Unnamed')}", "",
                 f"SUMMARY: {output.get('one_sentence_summary', '')}", "",
                 f"TARGET AUDIENCE: {output.get('target_audience', '')}", "",
                 "KEY POINTS:"]
        for pt in output.get("key_points", []):
            lines.append(f"  - {pt}")
        lines += ["", f"RECOMMENDED APPROACH: {output.get('recommended_approach', '')}", "",
                  f"KEY DIFFERENTIATOR: {output.get('key_differentiator', '')}", "",
                  "OUT OF SCOPE:"]
        for item in output.get("out_of_scope", []):
            lines.append(f"  - {item}")
        lines += ["", "RISKS:"]
        for risk in output.get("risks", []):
            lines.append(f"  - {risk}")
        lines += ["", "ACTION PLAN:"]
        for step in output.get("action_plan", []):
            lines.append(f"  - {step}")

    # Product domain (default)
    else:
        lines = [sep, "CONVERGENCE OUTPUT (PRODUCT)", sep, "",
                 f"PRODUCT: {output.get('product_name', 'Unnamed')}", "",
                 f"PITCH: {output.get('one_sentence_pitch', '')}", "",
                 f"TARGET USER (ICP): {output.get('target_user_icp', '')}", "",
                 "MVP (v1 Features):"]
        for b in output.get("mvp_bullets", []):
            lines.append(f"  - {b}")
        lines += ["", f"MONETIZATION: {output.get('monetization_model', '')}", "",
                  f"KEY DIFFERENTIATOR: {output.get('key_differentiator', '')}", "",
                  "WHAT WE'RE NOT DOING:"]
        for item in output.get("what_we_are_not_doing", []):
            lines.append(f"  - {item}")
        lines += ["", "RISKS / UNKNOWNS:"]
        for risk in output.get("risks_unknowns", []):
            lines.append(f"  - {risk}")
        lines += ["", "NEXT 7-DAY PLAN:"]
        for step in output.get("next_7_day_plan", []):
            lines.append(f"  - {step}")

    lines.append(sep)
    return "\n".join(lines)
