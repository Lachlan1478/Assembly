# gap_detection.py
# Gap signal detection for nudge-based conversation steering

from typing import Dict, List, Any, Optional
from collections import Counter


def compute_coverage_gaps(
    phase_exchanges: List[Dict[str, Any]],
    active_personas: Dict[str, Any],
    phase: Dict[str, Any],
    turn_count: int,
) -> Optional[str]:
    """
    Compute coverage gaps and return a single nudge string (or None).

    This function checks for:
    1. Participation imbalance (someone hasn't spoken in a while)
    2. Topic coverage (expected topics not discussed)
    3. Stagnation (no new ideas in last 3 turns)

    Design principle: Nudge, not rule. Personas can ignore it.

    Args:
        phase_exchanges: List of exchanges in current phase
        active_personas: Dict of persona_name -> Persona objects
        phase: Current phase configuration
        turn_count: Current turn number in phase

    Returns:
        Single nudge string or None if no gap detected
    """
    # Check participation imbalance first (most actionable)
    participation_nudge = _check_participation_imbalance(phase_exchanges, active_personas)
    if participation_nudge:
        return participation_nudge

    # Check for stagnation
    stagnation_nudge = _check_stagnation(phase_exchanges)
    if stagnation_nudge:
        return stagnation_nudge

    # Check topic coverage last (phase-specific)
    coverage_nudge = _check_topic_coverage(phase_exchanges, phase)
    if coverage_nudge:
        return coverage_nudge

    return None


def _check_participation_imbalance(
    phase_exchanges: List[Dict[str, Any]],
    active_personas: Dict[str, Any],
) -> Optional[str]:
    """
    Check if any persona hasn't spoken in a while.

    Returns nudge suggesting the quiet persona might have something to add.
    """
    if len(phase_exchanges) < 4:
        return None

    # Count recent speakers (last 6 turns)
    recent_speakers = [ex.get("speaker") for ex in phase_exchanges[-6:]]
    speaker_counts = Counter(recent_speakers)

    # Find personas who haven't spoken recently
    silent_personas = []
    for name in active_personas.keys():
        if speaker_counts.get(name, 0) == 0:
            silent_personas.append(name)

    if silent_personas:
        # Pick the first silent persona
        silent_name = silent_personas[0]
        persona = active_personas.get(silent_name)
        if persona:
            archetype = getattr(persona, 'archetype', 'participant')
            return f"{silent_name} ({archetype}) hasn't weighed in recently - their perspective might add something here."

    return None


def _check_stagnation(
    phase_exchanges: List[Dict[str, Any]],
    lookback: int = 3,
) -> Optional[str]:
    """
    Check if conversation seems stuck (no new substantive points).

    Uses simple heuristics:
    - Short responses
    - Repetitive language patterns
    - Agreement without extension
    """
    if len(phase_exchanges) < lookback:
        return None

    recent = phase_exchanges[-lookback:]

    # Heuristic 1: All recent responses are short (<100 chars)
    all_short = all(len(ex.get("content", "")) < 100 for ex in recent)

    # Heuristic 2: High repetition of agreement phrases
    agreement_phrases = ["agree", "good point", "exactly", "right", "yes", "that makes sense"]
    agreement_count = 0
    for ex in recent:
        content_lower = ex.get("content", "").lower()
        for phrase in agreement_phrases:
            if phrase in content_lower:
                agreement_count += 1
                break

    high_agreement = agreement_count >= lookback - 1  # Almost all turns have agreement

    # Heuristic 3: Same speakers back-to-back (ping-pong without others)
    speakers = [ex.get("speaker") for ex in recent]
    unique_speakers = len(set(speakers))
    low_diversity = unique_speakers <= 2

    if (all_short and high_agreement) or (high_agreement and low_diversity):
        return "The discussion might benefit from a new angle or specific example to move forward."

    return None


def _check_topic_coverage(
    phase_exchanges: List[Dict[str, Any]],
    phase: Dict[str, Any],
) -> Optional[str]:
    """
    Check if expected topics for the phase have been discussed.

    Uses phase goal and desired_outcome to infer expected topics.
    """
    if len(phase_exchanges) < 5:
        return None

    phase_id = phase.get("phase_id", "").lower()
    goal = phase.get("goal", "").lower()
    desired_outcome = phase.get("desired_outcome", "").lower()

    # Combine all exchange content for topic checking
    all_content = " ".join([ex.get("content", "").lower() for ex in phase_exchanges])

    # Phase-specific topic checks
    missing_topics = []

    if "discovery" in phase_id or "problem" in phase_id:
        # Problem discovery phase should mention users and pain points
        if "user" not in all_content and "customer" not in all_content:
            missing_topics.append("specific user segments")
        if "pain" not in all_content and "frustrat" not in all_content and "problem" not in all_content:
            missing_topics.append("concrete pain points")

    elif "solution" in phase_id or "ideation" in phase_id:
        # Solution phase should mention how and what
        if "how" not in all_content and "approach" not in all_content:
            missing_topics.append("implementation approach")
        if "differen" not in all_content and "unique" not in all_content and "better" not in all_content:
            missing_topics.append("differentiation from existing solutions")

    elif "synthesis" in phase_id or "final" in phase_id:
        # Synthesis should mention tradeoffs and decisions
        if "tradeoff" not in all_content and "trade-off" not in all_content and "versus" not in all_content:
            missing_topics.append("key tradeoffs")
        if "decision" not in all_content and "chose" not in all_content and "pick" not in all_content:
            missing_topics.append("concrete decisions")

    elif "competitive" in phase_id or "landscape" in phase_id:
        # Competitive analysis should mention competitors and gaps
        if "competitor" not in all_content and "existing" not in all_content and "current" not in all_content:
            missing_topics.append("existing solutions in the market")
        if "gap" not in all_content and "missing" not in all_content and "opportunity" not in all_content:
            missing_topics.append("market gaps or opportunities")

    if missing_topics:
        topic = missing_topics[0]  # Just nudge about one topic
        return f"The discussion hasn't touched on {topic} yet."

    return None


def get_gap_nudge_text(nudge: str) -> str:
    """
    Format a nudge string for injection into persona context.

    Framed as optional consideration - persona can ignore it.

    Args:
        nudge: The raw nudge string

    Returns:
        Formatted nudge text ready for injection
    """
    return f"\n[Optional consideration: {nudge}]\n"
