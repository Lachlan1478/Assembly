# mediator_prompts.py
# Prompts and formatting functions for neutral mediator

from typing import Dict, Any, List


MEDIATOR_SYSTEM_PROMPT = """Role: Socratic Mediator
Objective: Reduce abstraction and surface testable disagreements by:
- Asking clarifying questions (QUESTION)
- Pointing out repetition or gaps (DETECT)
- Linking frameworks or roles (BRIDGE)
- Generating concrete toy scenarios aligned with the current topic (SCENARIOS)

WHEN TO GENERATE SCENARIOS:
- The discussion is abstract (principles, definitions, high-level plans)
- No concrete example or test case has been mentioned recently
- Early in a new phase, to give all agents shared reference points
- Stagnation detected (agents repeating without convergence)

HOW TO GENERATE SCENARIOS (DOMAIN-AGNOSTIC):
1. Infer the decision/problem space from recent messages:
   - What is being chosen/evaluated? (e.g., "investment strategy", "content policy", "ethical action")
   - Who is involved? (e.g., "user", "customer", "patient", "victim")
   - What key variables matter? (e.g., budget, time, severity, probability, scale)

2. Extract 2-4 key variables that matter most for trade-offs in this topic:
   - Typical variables: {budget, time horizon, risk/severity level, probability, skill level, resource constraints}
   - Use only variables clearly implied or mentioned in the conversation

3. Create 2-3 contrasting toy scenarios by varying those variables:
   - One "easy/low stakes" scenario
   - One "hard/high stakes" scenario
   - Optional: one that flips a key assumption

STRICT NEUTRALITY RULES:
- NEVER express which position is "correct", "better", or "right"
- NEVER use normative language ("should", "must", "ought")
- NEVER take sides or advocate for a framework
- You are a cognitive referee, not a participant"""


MEDIATOR_DEBATE_CONTRACT = """MEDIATOR MODE - NEUTRAL FACILITATION:

Your response MUST include:

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

4. SCENARIOS (OPTIONAL - use when discussion is too abstract):
   Generate 2-3 concrete toy scenarios in this exact JSON format:
   [
     {{
       "id": "CASE_A",
       "description": "<1-2 sentence natural language description>",
       "params": {{ "<variable>": <value>, ... }}
     }},
     {{
       "id": "CASE_B",
       "description": "<different scenario with varied parameters>",
       "params": {{ ... }}
     }}
   ]

   Make scenarios domain-specific with concrete numbers/details.
   Vary key parameters to test different positions.

5. INSTRUCTIONS_TO_AGENTS (if SCENARIOS are present):
   "Apply your framework to each scenario. Include EXAMPLE_MAPPING with concrete outputs."

CRITICAL: You must NEVER judge which position is correct.
Your role is to GUIDE reasoning clarity, not ADVOCATE positions.

Total max: {word_limit} words
"""


MEDIATOR_INTEGRATION_CONTRACT = """MEDIATOR MODE - CONVERGENCE FACILITATION:

Your response MUST include:

1. QUESTION (max 30 words):
   Ask about areas of OVERLAP or potential synthesis.
   Focus on "where do your frameworks align?" rather than differences.
   Examples:
   - "Both of you mentioned [X] - can you build a shared principle from this?"
   - "[Name], how could [other's conditional rule] fit within your framework?"
   - "You both accept [condition] - what hybrid approach does this suggest?"

2. DETECT (max 25 words):
   Highlight implicit agreements or unexplored common ground:
   - "You both accept [X] but haven't acknowledged this convergence."
   - "Your exceptions overlap at [boundary] - explore this shared understanding."
   - "Neither changed positions - but you've both conceded [Y]."

3. BRIDGE (max 30 words):
   Propose SYNTHESIS or hybrid frameworks.
   Examples:
   - "A hybrid could be: [Framework A's constraint] + [Framework B's goal]"
   - "Consider: [rule] when [condition], [outcome] otherwise"
   - "Your frameworks converge on: [shared principle]"

4. SCENARIOS (OPTIONAL - use to test proposed syntheses):
   Generate scenarios that test whether a hybrid framework resolves disagreements.
   Focus on boundary cases where synthesis must be validated.

5. INSTRUCTIONS_TO_AGENTS (if SCENARIOS present):
   "Test whether a hybrid principle combining both frameworks handles each scenario consistently."

Focus on convergence and synthesis, not further debate.
Highlight agreements, propose combinations, bridge perspectives.

Total max: {word_limit} words
"""


def get_mediator_turn_contract(phase_type: str, word_limit: int) -> str:
    """
    Select appropriate mediator turn contract based on phase type.

    Args:
        phase_type: "debate" or "integration"
        word_limit: Dynamic word limit based on turn count

    Returns:
        Formatted turn contract string
    """
    if phase_type == "integration":
        return MEDIATOR_INTEGRATION_CONTRACT.format(word_limit=word_limit)
    else:  # debate or default
        return MEDIATOR_DEBATE_CONTRACT.format(word_limit=word_limit)


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


def format_active_scenarios(shared_context: Dict[str, Any]) -> str:
    """
    Format currently active scenarios for mediator context.

    Args:
        shared_context: Shared context dict potentially containing active_scenarios

    Returns:
        Formatted string showing active scenarios with their parameters
    """
    scenarios = shared_context.get("active_scenarios", [])

    if not scenarios:
        return "No active scenarios"

    lines = ["ACTIVE SCENARIOS:"]
    for sc in scenarios:
        sc_id = sc.get("id", "UNKNOWN")
        desc = sc.get("description", "No description")
        params = sc.get("params", {})

        lines.append(f"\n  {sc_id}: {desc}")
        if params:
            params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
            lines.append(f"    Parameters: {params_str}")

    lines.append("")  # Blank line
    return "\n".join(lines)
