# mediator_prompts.py
# Prompts and formatting functions for neutral mediator

from typing import Dict, Any, List


MEDIATOR_SYSTEM_PROMPT = """You are a NEUTRAL mediator guiding philosophical debate.

STRICT RULES - NEVER VIOLATE:
1. NEVER express which position is "correct", "better", or "right"
2. NEVER use normative language ("should", "must", "ought")
3. NEVER take sides or advocate for a framework
4. NEVER generate solutions - only guide advocates to find them

YOUR ONLY ROLE:
- Ask probing questions that reveal hidden assumptions
- Detect and call out circular reasoning explicitly
- Bridge ideas by translating between frameworks
- Track concessions and belief state changes
- Force operational definitions of abstract terms
- Introduce conceptual tools when frameworks deadlock

You are a cognitive referee, not a participant."""


MEDIATOR_TURN_CONTRACT = """MEDIATOR MODE - NEUTRAL FACILITATION:

Your response MUST follow this EXACT structure:

1. QUESTION (max 30 words):
   Ask ONE targeted question to a specific advocate by name.
   Reference their specific belief state (certainty, conditional rules, exceptions).
   Examples:
   - "[Name], is there ANY circumstance where [X] matters to your framework?"
   - "You added exception '[Y]' at turn 3. How do you define when [Y] applies?"
   - "Both of you acknowledge [Z] - can you analyze that together?"

2. DETECT (max 25 words):
   Call out ONE of:
   - Circular reasoning: "You've repeated [argument] - what's NEW?"
   - Stagnation: "Neither of you changed belief states. Move to boundary cases."
   - Implicit agreement: "You both added condition [X] - acknowledge this convergence."

3. BRIDGE (max 30 words):
   Translate between frameworks OR introduce one conceptual tool.
   Examples:
   - "[Advocate A]'s '[term1]' = [Advocate B]'s '[term2]' in different terminology"
   - "Consider rule-utilitarianism: outcome-maximization under rights-based constraints"
   - "This is a threshold problem - at what point does [X] override [Y]?"

CRITICAL: You must NEVER judge which position is correct.
Your role is to GUIDE reasoning clarity, not ADVOCATE positions.

Total max: {word_limit} words
"""


def format_advocate_states(advocate_states: Dict[str, Any]) -> str:
    """
    Format advocate belief states for mediator context.

    Args:
        advocate_states: Dict mapping advocate name to their belief_state

    Returns:
        Formatted string showing current positions, certainty, conditionals, exceptions
    """
    if not advocate_states:
        return "No advocate belief states available"

    lines = []
    for advocate_name, belief_state in advocate_states.items():
        if not belief_state:
            lines.append(f"{advocate_name}: No belief state yet")
            continue

        lines.append(f"### {advocate_name}:")

        # Position
        position = belief_state.get("position")
        if position:
            position_preview = position[:80] + "..." if len(position) > 80 else position
            lines.append(f"  Position: {position_preview}")

        # Certainty
        certainty = belief_state.get("certainty", "medium")
        lines.append(f"  Certainty: {certainty}")

        # Conditional rules
        conditional_rules = belief_state.get("conditional_rules", [])
        if conditional_rules:
            lines.append(f"  Conditional rules ({len(conditional_rules)}):")
            for rule in conditional_rules[-2:]:  # Last 2
                rule_preview = rule[:60] + "..." if len(rule) > 60 else rule
                lines.append(f"    - {rule_preview}")

        # Exceptions
        exceptions = belief_state.get("exceptions", [])
        if exceptions:
            lines.append(f"  Exceptions ({len(exceptions)}):")
            for exc in exceptions[-2:]:  # Last 2
                exc_preview = exc[:60] + "..." if len(exc) > 60 else exc
                lines.append(f"    - {exc_preview}")

        # Accepted critiques
        accepted_critiques = belief_state.get("accepted_critiques", [])
        if accepted_critiques:
            lines.append(f"  Accepted critiques ({len(accepted_critiques)}):")
            for critique in accepted_critiques[-2:]:  # Last 2
                critique_preview = critique[:60] + "..." if len(critique) > 60 else critique
                lines.append(f"    - {critique_preview}")

        # Concessions (from other advocates)
        concessions = belief_state.get("concessions", [])
        if concessions:
            recent_concessions = concessions[-2:]
            lines.append(f"  Recent concessions ({len(concessions)} total):")
            for conc in recent_concessions:
                from_speaker = conc.get("from_speaker", "Unknown")
                point = conc.get("point", "")[:50]
                lines.append(f"    - From {from_speaker}: {point}")

        lines.append("")  # Blank line between advocates

    return "\n".join(lines)


def format_mediation_log(mediation_log: Dict[str, List]) -> str:
    """
    Format mediator's prior interventions to prevent redundancy.

    Args:
        mediation_log: Mediator's log of prior interventions

    Returns:
        Formatted string showing recent questions, detections, bridges
    """
    if not mediation_log or not any(mediation_log.values()):
        return "No prior interventions yet (first mediation turn)"

    lines = []

    # Questions asked (last 2)
    questions = mediation_log.get("questions_asked", [])
    if questions:
        lines.append(f"Questions asked ({len(questions)} total):")
        for q in questions[-2:]:
            turn = q.get("turn", "?")
            to = q.get("to", "?")
            question_preview = q.get("question", "")[:60] + "..."
            lines.append(f"  Turn {turn} to {to}: {question_preview}")

    # Circular arguments detected (last 2)
    circular = mediation_log.get("circular_arguments_detected", [])
    if circular:
        lines.append(f"Circular arguments detected ({len(circular)} total):")
        for c in circular[-2:]:
            turn = c.get("turn", "?")
            detection_preview = c.get("detection", "")[:60] + "..."
            lines.append(f"  Turn {turn}: {detection_preview}")

    # Conceptual tools introduced (all)
    tools = mediation_log.get("conceptual_tools_introduced", [])
    if tools:
        tool_names = [t.get("tool", "?") for t in tools]
        lines.append(f"Conceptual tools introduced: {', '.join(tool_names)}")

    # Definitions forced (last 2)
    definitions = mediation_log.get("definitions_forced", [])
    if definitions:
        lines.append(f"Definitions requested ({len(definitions)} total):")
        for d in definitions[-2:]:
            turn = d.get("turn", "?")
            request_preview = d.get("request", "")[:50] + "..."
            lines.append(f"  Turn {turn}: {request_preview}")

    return "\n".join(lines) if lines else "No prior interventions"


def format_recent_exchanges(exchanges: List[Dict[str, Any]]) -> str:
    """
    Format recent exchanges for mediator context.

    Args:
        exchanges: List of exchange dicts (last 3-5)

    Returns:
        Formatted string showing recent discussion
    """
    if not exchanges:
        return "No recent exchanges yet"

    # Take last 3-5 exchanges
    recent = exchanges[-5:]

    lines = []
    for ex in recent:
        turn = ex.get("turn", "?")
        speaker = ex.get("speaker", "Unknown")
        content = ex.get("content", "")

        # Truncate to 150 chars
        content_preview = content[:150] + "..." if len(content) > 150 else content

        lines.append(f"Turn {turn} - {speaker}:")
        lines.append(f"  {content_preview}")
        lines.append("")  # Blank line

    return "\n".join(lines)
