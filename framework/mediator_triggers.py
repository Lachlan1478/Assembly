# mediator_triggers.py
# Trigger detection system for when mediator should intervene

from typing import Dict, List, Any, Optional


def check_mediator_triggers(
    turn_count: int,
    phase_exchanges: List[Dict[str, Any]],
    active_personas: Dict[str, Any],
    repetition_detected: bool = False,
    phase_type: str = "debate"
) -> bool:
    """
    Main function to determine if mediator should intervene.

    Hybrid trigger model:
    - Regular cadence: Every 3-4 turns in debate phases
    - Event-based: Stagnation, repetition, circular reasoning detected

    Args:
        turn_count: Current turn number in phase
        phase_exchanges: Exchanges so far in this phase
        active_personas: Dict of active personas (to access belief states)
        repetition_detected: Whether facilitator detected repetition
        phase_type: "debate" or "integration" (mediator only in debate)

    Returns:
        True if mediator should speak next, False otherwise
    """
    # Never intervene in integration phases (they already use STEELMAN/SYNTHESIS)
    if phase_type == "integration":
        return False

    # Need at least 2 turns before mediator can analyze patterns
    if turn_count < 2:
        return False

    # Event-based triggers (high priority)
    if repetition_detected:
        return True

    if detect_stagnation(phase_exchanges, active_personas) > 0.7:
        return True

    if count_recent_belief_deltas(phase_exchanges) == 0 and turn_count >= 4:
        # No belief changes in recent turns
        return True

    # Regular cadence: Every 3-4 turns (with some variation)
    # Mediator at turns 3, 7, 11, etc. (not every turn, to let debate flow)
    if turn_count > 0 and turn_count % 4 == 3:
        return True

    return False


def detect_stagnation(
    phase_exchanges: List[Dict[str, Any]],
    active_personas: Dict[str, Any]
) -> float:
    """
    Detect conversation stagnation using multiple signals.

    Stagnation indicators:
    - Multiple "No change because..." updates
    - Repeated arguments (same key phrases)
    - No belief state changes

    Args:
        phase_exchanges: Recent exchanges in phase
        active_personas: Active personas with belief states

    Returns:
        Float score 0.0 (no stagnation) to 1.0 (complete stagnation)
    """
    if len(phase_exchanges) < 3:
        return 0.0

    recent = phase_exchanges[-4:]  # Last 4 turns
    stagnation_score = 0.0

    # Signal 1: Count "No change because" occurrences
    no_change_count = sum(
        1 for ex in recent
        if "no change because" in ex.get("content", "").lower()
    )
    stagnation_score += min(no_change_count / 3.0, 0.4)  # Max 0.4 from this

    # Signal 2: Check for repeated key phrases
    phrase_counts = {}
    for ex in recent:
        content = ex.get("content", "").lower()
        # Extract key phrases (very simple approach)
        words = content.split()
        for i in range(len(words) - 2):
            phrase = " ".join(words[i:i+3])
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1

    max_repetitions = max(phrase_counts.values()) if phrase_counts else 0
    if max_repetitions >= 3:
        stagnation_score += 0.3

    # Signal 3: Check belief state changes
    belief_delta_count = count_recent_belief_deltas(recent)
    if belief_delta_count == 0:
        stagnation_score += 0.3

    return min(stagnation_score, 1.0)


def count_recent_belief_deltas(
    recent_exchanges: List[Dict[str, Any]],
    window: int = 4
) -> int:
    """
    Count how many recent exchanges included actual belief state changes.

    Looks for update indicators:
    - "Certainty: [low/medium/high]" (actual change)
    - "Add condition:", "Add exception:", "Accept critique:"
    - NOT "No change because..."

    Args:
        recent_exchanges: Recent exchanges to analyze
        window: How many recent exchanges to check

    Returns:
        Count of exchanges with belief state changes
    """
    recent = recent_exchanges[-window:]
    delta_count = 0

    for ex in recent:
        content = ex.get("content", "").lower()

        # Exclude "No change because" updates
        if "no change because" in content:
            continue

        # Look for actual change indicators
        if any(indicator in content for indicator in [
            "certainty:",
            "add condition",
            "add exception",
            "accept critique",
            "add conditional rule",
            "shifted my belief",
            "changed my view"
        ]):
            delta_count += 1

    return delta_count


def detect_circular_arguments(
    phase_exchanges: List[Dict[str, Any]],
    speaker_name: str
) -> Optional[str]:
    """
    Detect if a speaker is repeating the same argument.

    Args:
        phase_exchanges: All exchanges in phase
        speaker_name: Name of speaker to check

    Returns:
        String description of circular argument, or None if not detected
    """
    # Get all exchanges from this speaker
    speaker_exchanges = [
        ex for ex in phase_exchanges
        if ex.get("speaker") == speaker_name
    ]

    if len(speaker_exchanges) < 2:
        return None

    # Check last 2 exchanges for similar content
    if len(speaker_exchanges) >= 2:
        recent_1 = speaker_exchanges[-1].get("content", "").lower()
        recent_2 = speaker_exchanges[-2].get("content", "").lower()

        # Extract key phrases (3-grams)
        def extract_3grams(text):
            words = text.split()
            return {" ".join(words[i:i+3]) for i in range(len(words) - 2)}

        phrases_1 = extract_3grams(recent_1)
        phrases_2 = extract_3grams(recent_2)

        # Calculate overlap
        if phrases_1 and phrases_2:
            overlap = len(phrases_1 & phrases_2) / len(phrases_1 | phrases_2)

            if overlap > 0.4:  # 40% overlap = likely repetition
                return f"{speaker_name} repeating similar argument structure"

    return None


def detect_abstraction_overload(
    phase_exchanges: List[Dict[str, Any]]
) -> List[str]:
    """
    Detect undefined abstract terms that need operational definitions.

    Common philosophical abstractions that need grounding:
    - "justice", "fairness", "rights", "duty", "good", "harm"
    - "rational", "valid", "moral", "ethical"

    Args:
        phase_exchanges: Recent exchanges in phase

    Returns:
        List of abstract terms that appear frequently but lack definitions
    """
    abstract_terms = [
        "justice", "fairness", "rights", "duty", "good", "harm",
        "rational", "valid", "moral", "ethical", "value", "virtue",
        "ought", "should", "must", "obligated", "responsible"
    ]

    # Count usage in recent exchanges
    recent = phase_exchanges[-5:]
    term_counts = {term: 0 for term in abstract_terms}

    for ex in recent:
        content = ex.get("content", "").lower()
        for term in abstract_terms:
            # Count whole-word occurrences
            if f" {term} " in f" {content} ":
                term_counts[term] += 1

    # Return terms used 3+ times (likely central to debate but undefined)
    overused_terms = [
        term for term, count in term_counts.items()
        if count >= 3
    ]

    return overused_terms


def detect_implicit_agreement(
    phase_exchanges: List[Dict[str, Any]],
    active_personas: Dict[str, Any]
) -> Optional[str]:
    """
    Detect when advocates have converged on a point but haven't acknowledged it.

    Looks for:
    - Both added same conditional rule
    - Both added same exception
    - Both acknowledged same critique

    Args:
        phase_exchanges: Recent exchanges
        active_personas: Active personas with belief states

    Returns:
        String describing convergence point, or None if not detected
    """
    # Need at least 2 personas
    if len(active_personas) < 2:
        return None

    # Extract belief states
    belief_states = {}
    for name, persona in active_personas.items():
        if hasattr(persona, 'belief_state') and persona.belief_state:
            belief_states[name] = persona.belief_state

    if len(belief_states) < 2:
        return None

    # Check for overlapping conditional rules
    all_conditional_rules = []
    for name, state in belief_states.items():
        rules = state.get("conditional_rules", [])
        for rule in rules:
            all_conditional_rules.append((name, rule.lower()))

    # Find duplicates (same rule from different speakers)
    for i, (name1, rule1) in enumerate(all_conditional_rules):
        for name2, rule2 in all_conditional_rules[i+1:]:
            if name1 != name2:
                # Simple similarity check
                if rule1 == rule2 or rule1 in rule2 or rule2 in rule1:
                    return f"{name1} and {name2} both added condition: '{rule1[:50]}...'"

    # Check for overlapping exceptions
    all_exceptions = []
    for name, state in belief_states.items():
        exceptions = state.get("exceptions", [])
        for exc in exceptions:
            all_exceptions.append((name, exc.lower()))

    for i, (name1, exc1) in enumerate(all_exceptions):
        for name2, exc2 in all_exceptions[i+1:]:
            if name1 != name2:
                if exc1 == exc2 or exc1 in exc2 or exc2 in exc1:
                    return f"{name1} and {name2} both added exception: '{exc1[:50]}...'"

    return None


def should_force_definition(
    turn_count: int,
    phase_exchanges: List[Dict[str, Any]]
) -> Optional[str]:
    """
    Determine if mediator should force operational definition of abstract term.

    Args:
        turn_count: Current turn in phase
        phase_exchanges: Recent exchanges

    Returns:
        Term that needs definition, or None
    """
    # Only after turn 4 (let debate establish first)
    if turn_count < 4:
        return None

    overused = detect_abstraction_overload(phase_exchanges)

    if overused:
        # Return most overused term
        return overused[0]

    return None
