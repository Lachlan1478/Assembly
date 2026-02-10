# value_accumulation.py
# Per-turn value scoring and accumulation metrics for Assembly vs baseline comparison

import json
import os
import sys
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI


@dataclass
class TurnValueScore:
    """Value signals extracted from a single conversation turn."""
    turn: int
    speaker: str
    new_concept: bool  # New idea/mechanism introduced?
    builds_on_prior: bool  # References/extends prior idea?
    concrete_artifact: bool  # Specific feature, metric, example?
    challenges_assumption: bool  # Questions prior claim?
    raw_extraction: Dict[str, Any] = field(default_factory=dict)  # Full LLM output

    @property
    def value_count(self) -> int:
        """Count of value flags that are True (0-4)."""
        return sum([
            self.new_concept,
            self.builds_on_prior,
            self.concrete_artifact,
            self.challenges_assumption
        ])

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "turn": self.turn,
            "speaker": self.speaker,
            "new_concept": self.new_concept,
            "builds_on_prior": self.builds_on_prior,
            "concrete_artifact": self.concrete_artifact,
            "challenges_assumption": self.challenges_assumption,
            "value_count": self.value_count,
        }


@dataclass
class SessionValueMetrics:
    """Aggregated value metrics for an entire conversation session."""
    session_id: str
    turn_scores: List[TurnValueScore]
    total_turns: int = 0
    total_new_concepts: int = 0
    total_builds_on_prior: int = 0
    total_concrete_artifacts: int = 0
    total_challenges: int = 0
    cumulative_concepts: List[int] = field(default_factory=list)  # Cumulative curve

    def compute_aggregates(self):
        """Compute aggregate metrics from turn scores."""
        self.total_turns = len(self.turn_scores)
        self.total_new_concepts = sum(1 for t in self.turn_scores if t.new_concept)
        self.total_builds_on_prior = sum(1 for t in self.turn_scores if t.builds_on_prior)
        self.total_concrete_artifacts = sum(1 for t in self.turn_scores if t.concrete_artifact)
        self.total_challenges = sum(1 for t in self.turn_scores if t.challenges_assumption)

        # Build cumulative curve for new concepts
        cumulative = 0
        self.cumulative_concepts = []
        for t in self.turn_scores:
            if t.new_concept:
                cumulative += 1
            self.cumulative_concepts.append(cumulative)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "total_turns": self.total_turns,
            "total_new_concepts": self.total_new_concepts,
            "total_builds_on_prior": self.total_builds_on_prior,
            "total_concrete_artifacts": self.total_concrete_artifacts,
            "total_challenges": self.total_challenges,
            "cumulative_concepts": self.cumulative_concepts,
            "turn_scores": [t.to_dict() for t in self.turn_scores],
        }


# Prompt for extracting value signals from a turn
VALUE_EXTRACTION_PROMPT = """Analyze this conversation turn for value signals.

PRIOR TURNS (for context):
{prior_turns}

EXISTING CONCEPTS INTRODUCED SO FAR:
{existing_concepts}

CURRENT TURN TO ANALYZE:
Speaker: {speaker}
Content: {content}

Extract value signals by answering these questions:

1. NEW_CONCEPT: Does this turn introduce a genuinely new idea, mechanism, or approach that wasn't mentioned before?
   - Must be substantively different from existing concepts
   - Not just rephrasing or minor variation

2. BUILDS_ON_PRIOR: Does this turn explicitly reference, extend, or build upon something said in a prior turn?
   - Look for: "building on X's point", "that reminds me", "to extend that idea"
   - Must reference specific prior content, not just general agreement

3. CONCRETE_ARTIFACT: Does this turn provide a specific, actionable artifact?
   - Examples: specific feature name, concrete metric, detailed example, user scenario, pricing point
   - Not just abstract concepts or general statements

4. CHALLENGES_ASSUMPTION: Does this turn question, critique, or push back on a prior claim or assumption?
   - Must actively challenge, not just offer alternative
   - Look for: "but have we considered", "I'm not sure that", "the risk with that is"

Respond with a JSON object:
{{
    "new_concept": true/false,
    "new_concept_description": "brief description if true, else null",
    "builds_on_prior": true/false,
    "builds_on_prior_reference": "what it builds on if true, else null",
    "concrete_artifact": true/false,
    "concrete_artifact_description": "the artifact if true, else null",
    "challenges_assumption": true/false,
    "challenges_assumption_target": "what it challenges if true, else null"
}}"""


def extract_turn_value(
    turn: Dict[str, Any],
    prior_turns: List[Dict[str, Any]],
    existing_concepts: List[str],
    model: str = "gpt-4o-mini",
) -> TurnValueScore:
    """
    LLM-based extraction of value signals from a single turn.

    Args:
        turn: Current turn dict with 'speaker', 'content', 'turn' keys
        prior_turns: List of previous turn dicts
        existing_concepts: List of concepts already introduced
        model: LLM model to use

    Returns:
        TurnValueScore with extracted value signals
    """
    client = OpenAI()

    # Format prior turns
    prior_formatted = "\n".join([
        f"Turn {t.get('turn', '?')} - {t.get('speaker', 'Unknown')}: {t.get('content', '')[:300]}..."
        for t in prior_turns[-5:]  # Last 5 turns for context
    ]) if prior_turns else "(First turn - no prior context)"

    # Format existing concepts
    concepts_formatted = "\n".join([
        f"- {concept}" for concept in existing_concepts[-10:]  # Last 10 concepts
    ]) if existing_concepts else "(None yet)"

    prompt = VALUE_EXTRACTION_PROMPT.format(
        prior_turns=prior_formatted,
        existing_concepts=concepts_formatted,
        speaker=turn.get("speaker", "Unknown"),
        content=turn.get("content", ""),
    )

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a conversation analyst extracting value signals. Be strict - only mark True when clearly evident."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1,  # Low temperature for consistent extraction
        )

        result = json.loads(response.choices[0].message.content)

        return TurnValueScore(
            turn=turn.get("turn", 0),
            speaker=turn.get("speaker", "Unknown"),
            new_concept=result.get("new_concept", False),
            builds_on_prior=result.get("builds_on_prior", False),
            concrete_artifact=result.get("concrete_artifact", False),
            challenges_assumption=result.get("challenges_assumption", False),
            raw_extraction=result,
        )

    except Exception as e:
        print(f"[!] Error extracting value from turn {turn.get('turn', '?')}: {e}")
        return TurnValueScore(
            turn=turn.get("turn", 0),
            speaker=turn.get("speaker", "Unknown"),
            new_concept=False,
            builds_on_prior=False,
            concrete_artifact=False,
            challenges_assumption=False,
            raw_extraction={"error": str(e)},
        )


def analyze_session_value(
    conversation_log_path: str,
    model: str = "gpt-4o-mini",
    verbose: bool = False,
) -> SessionValueMetrics:
    """
    Process full conversation log and extract per-turn value metrics.

    Args:
        conversation_log_path: Path to conversation log JSON file or directory
        model: LLM model to use for extraction
        verbose: If True, print progress

    Returns:
        SessionValueMetrics with all turn scores and aggregates
    """
    # Load conversation log
    if os.path.isdir(conversation_log_path):
        # Find the conversation file in the directory
        for filename in os.listdir(conversation_log_path):
            if filename.endswith("_conversation.json"):
                conversation_log_path = os.path.join(conversation_log_path, filename)
                break

    with open(conversation_log_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract session ID from path
    session_id = os.path.basename(os.path.dirname(conversation_log_path))
    if not session_id or session_id == ".":
        session_id = os.path.basename(conversation_log_path).replace("_conversation.json", "")

    # Get exchanges from the conversation log
    exchanges = data.get("exchanges", [])
    if not exchanges:
        # Try alternative structure
        exchanges = data.get("logs", [])

    if verbose:
        print(f"Analyzing {len(exchanges)} turns from session {session_id}...")

    # Process each turn
    turn_scores = []
    existing_concepts = []
    prior_turns = []

    for i, exchange in enumerate(exchanges):
        if verbose:
            print(f"  Turn {i+1}/{len(exchanges)}: {exchange.get('speaker', 'Unknown')}")

        score = extract_turn_value(
            turn=exchange,
            prior_turns=prior_turns,
            existing_concepts=existing_concepts,
            model=model,
        )

        turn_scores.append(score)

        # Track new concepts for future turns
        if score.new_concept:
            concept_desc = score.raw_extraction.get("new_concept_description", f"Concept from turn {i}")
            if concept_desc:
                existing_concepts.append(concept_desc)

        prior_turns.append(exchange)

    # Build metrics
    metrics = SessionValueMetrics(
        session_id=session_id,
        turn_scores=turn_scores,
    )
    metrics.compute_aggregates()

    return metrics


def compare_value_accumulation(
    assembly_metrics: SessionValueMetrics,
    baseline_metrics: SessionValueMetrics,
) -> dict:
    """
    Compare value accumulation between Assembly and baseline sessions.

    Args:
        assembly_metrics: SessionValueMetrics from Assembly session
        baseline_metrics: SessionValueMetrics from baseline session

    Returns:
        Comparison dict with ratios and headline
    """
    # Avoid division by zero
    baseline_concepts = max(baseline_metrics.total_new_concepts, 1)
    baseline_artifacts = max(baseline_metrics.total_concrete_artifacts, 1)
    baseline_builds = max(baseline_metrics.total_builds_on_prior, 1)
    baseline_challenges = max(baseline_metrics.total_challenges, 1)

    concept_ratio = assembly_metrics.total_new_concepts / baseline_concepts
    artifact_ratio = assembly_metrics.total_concrete_artifacts / baseline_artifacts
    builds_ratio = assembly_metrics.total_builds_on_prior / baseline_builds
    challenge_ratio = assembly_metrics.total_challenges / baseline_challenges

    # Generate headline based on most impressive ratio
    ratios = {
        "novel mechanisms": concept_ratio,
        "concrete artifacts": artifact_ratio,
        "iterative builds": builds_ratio,
        "critical challenges": challenge_ratio,
    }
    best_metric, best_ratio = max(ratios.items(), key=lambda x: x[1])

    if best_ratio >= 1.5:
        headline = f"{best_ratio:.1f}x more cumulative {best_metric}"
    elif best_ratio >= 1.0:
        headline = f"Comparable value accumulation ({best_ratio:.1f}x {best_metric})"
    else:
        headline = f"Baseline shows {1/best_ratio:.1f}x more {best_metric}"

    return {
        "concept_ratio": round(concept_ratio, 2),
        "artifact_ratio": round(artifact_ratio, 2),
        "builds_ratio": round(builds_ratio, 2),
        "challenge_ratio": round(challenge_ratio, 2),
        "headline": headline,
        "cumulative_curves": {
            "assembly": assembly_metrics.cumulative_concepts,
            "baseline": baseline_metrics.cumulative_concepts,
        },
        "totals": {
            "assembly": {
                "new_concepts": assembly_metrics.total_new_concepts,
                "concrete_artifacts": assembly_metrics.total_concrete_artifacts,
                "builds_on_prior": assembly_metrics.total_builds_on_prior,
                "challenges": assembly_metrics.total_challenges,
                "turns": assembly_metrics.total_turns,
            },
            "baseline": {
                "new_concepts": baseline_metrics.total_new_concepts,
                "concrete_artifacts": baseline_metrics.total_concrete_artifacts,
                "builds_on_prior": baseline_metrics.total_builds_on_prior,
                "challenges": baseline_metrics.total_challenges,
                "turns": baseline_metrics.total_turns,
            },
        },
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze value accumulation in conversation logs")
    parser.add_argument(
        "conversation_log",
        nargs="?",
        help="Path to conversation log file or session directory"
    )
    parser.add_argument(
        "--compare",
        help="Path to baseline conversation log for comparison"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress during analysis"
    )
    args = parser.parse_args()

    if args.conversation_log:
        print(f"Analyzing: {args.conversation_log}")
        metrics = analyze_session_value(args.conversation_log, verbose=args.verbose)

        print(f"\n{'='*60}")
        print("VALUE ACCUMULATION METRICS")
        print(f"{'='*60}")
        print(f"Session: {metrics.session_id}")
        print(f"Total turns: {metrics.total_turns}")
        print(f"New concepts: {metrics.total_new_concepts}")
        print(f"Builds on prior: {metrics.total_builds_on_prior}")
        print(f"Concrete artifacts: {metrics.total_concrete_artifacts}")
        print(f"Challenges assumptions: {metrics.total_challenges}")
        print(f"\nCumulative concept curve: {metrics.cumulative_concepts}")

        if args.compare:
            print(f"\nComparing with baseline: {args.compare}")
            baseline_metrics = analyze_session_value(args.compare, verbose=args.verbose)

            comparison = compare_value_accumulation(metrics, baseline_metrics)

            print(f"\n{'='*60}")
            print("COMPARISON RESULTS")
            print(f"{'='*60}")
            print(f"Headline: {comparison['headline']}")
            print(f"Concept ratio: {comparison['concept_ratio']}x")
            print(f"Artifact ratio: {comparison['artifact_ratio']}x")
            print(f"Builds ratio: {comparison['builds_ratio']}x")
            print(f"Challenge ratio: {comparison['challenge_ratio']}x")

        # Save results
        output_file = f"value_metrics_{metrics.session_id}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            output = metrics.to_dict()
            if args.compare:
                output["comparison"] = comparison
            json.dump(output, f, indent=2)
        print(f"\nResults saved to: {output_file}")

    else:
        print("Usage: python value_accumulation.py <conversation_log> [--compare <baseline_log>] [-v]")
        print("\nExample:")
        print("  python value_accumulation.py conversation_logs/session_20260201_213400")
        print("  python value_accumulation.py assembly_log.json --compare baseline_log.json -v")
