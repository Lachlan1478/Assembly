# scoring.py
# Evaluation criteria and scoring functions for Phase 2 benchmark

import json
import re
from dataclasses import dataclass
from typing import Optional, Dict

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI


@dataclass
class IdeaScore:
    """Score for a single idea across all criteria."""
    novelty: int  # 1-5: Is the idea non-obvious?
    feasibility: int  # 1-5: Could this be built and sold?
    specificity: int  # 1-5: Are ICP, problem, solution concrete?
    commercial_clarity: int  # 1-5: Is monetization obvious?
    notes: str = ""  # Optional scorer notes

    @property
    def total(self) -> int:
        """Total score (4-20)."""
        return self.novelty + self.feasibility + self.specificity + self.commercial_clarity

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "novelty": self.novelty,
            "feasibility": self.feasibility,
            "specificity": self.specificity,
            "commercial_clarity": self.commercial_clarity,
            "total": self.total,
            "notes": self.notes,
        }


# Scoring rubric descriptions
SCORING_RUBRIC = {
    "novelty": {
        1: "Completely generic - could find this idea anywhere",
        2: "Slight twist on common idea",
        3: "Decent differentiation from existing solutions",
        4: "Novel angle or combination that's not obvious",
        5: "Highly original, unique insight or approach",
    },
    "feasibility": {
        1: "Impossible or wildly impractical to build",
        2: "Significant technical or market barriers",
        3: "Challenging but achievable with resources",
        4: "Clearly buildable with known technology",
        5: "Straightforward to build and bring to market",
    },
    "specificity": {
        1: "Vague platitudes, no concrete details",
        2: "Some specifics but major gaps",
        3: "Reasonable detail on ICP, problem, or solution",
        4: "Clear and concrete on most dimensions",
        5: "Highly specific ICP, problem, solution, and use case",
    },
    "commercial_clarity": {
        1: "No idea how this makes money",
        2: "Vague monetization concept",
        3: "Reasonable business model outlined",
        4: "Clear revenue model and pricing strategy",
        5: "Obvious path to revenue with validated willingness to pay",
    },
}


def print_scoring_rubric():
    """Print the scoring rubric for reference."""
    print("\n" + "=" * 60)
    print("SCORING RUBRIC")
    print("=" * 60)

    for criterion, levels in SCORING_RUBRIC.items():
        print(f"\n{criterion.upper()}:")
        for score, description in levels.items():
            print(f"  {score}: {description}")


def score_idea_interactive() -> IdeaScore:
    """
    Interactively score an idea using console input.

    Returns:
        IdeaScore with user-provided scores
    """
    print("\nScore the idea (1-5 for each criterion):")
    print_scoring_rubric()
    print()

    def get_score(criterion: str) -> int:
        while True:
            try:
                score = int(input(f"{criterion} (1-5): "))
                if 1 <= score <= 5:
                    return score
                print("Score must be 1-5")
            except ValueError:
                print("Please enter a number 1-5")

    novelty = get_score("Novelty")
    feasibility = get_score("Feasibility")
    specificity = get_score("Specificity")
    commercial_clarity = get_score("Commercial Clarity")
    notes = input("Notes (optional): ").strip()

    return IdeaScore(
        novelty=novelty,
        feasibility=feasibility,
        specificity=specificity,
        commercial_clarity=commercial_clarity,
        notes=notes,
    )


def score_idea(
    novelty: int,
    feasibility: int,
    specificity: int,
    commercial_clarity: int,
    notes: str = "",
) -> IdeaScore:
    """
    Create an IdeaScore from individual scores.

    Args:
        novelty: 1-5 score for novelty
        feasibility: 1-5 score for feasibility
        specificity: 1-5 score for specificity
        commercial_clarity: 1-5 score for commercial clarity
        notes: Optional notes

    Returns:
        IdeaScore instance
    """
    # Validate scores
    for name, score in [
        ("novelty", novelty),
        ("feasibility", feasibility),
        ("specificity", specificity),
        ("commercial_clarity", commercial_clarity),
    ]:
        if not 1 <= score <= 5:
            raise ValueError(f"{name} must be 1-5, got {score}")

    return IdeaScore(
        novelty=novelty,
        feasibility=feasibility,
        specificity=specificity,
        commercial_clarity=commercial_clarity,
        notes=notes,
    )


LLM_JUDGE_PROMPT = """You are an expert startup evaluator scoring a business idea.

SCORING RUBRIC (score each 1-5):

NOVELTY - Is the idea non-obvious or differentiated?
  1: Completely generic - could find this idea anywhere
  2: Slight twist on common idea
  3: Decent differentiation from existing solutions
  4: Novel angle or combination that's not obvious
  5: Highly original, unique insight or approach

FEASIBILITY - Could this realistically be built and sold?
  1: Impossible or wildly impractical to build
  2: Significant technical or market barriers
  3: Challenging but achievable with resources
  4: Clearly buildable with known technology
  5: Straightforward to build and bring to market

SPECIFICITY - Are ICP, problem, and solution concrete?
  1: Vague platitudes, no concrete details
  2: Some specifics but major gaps
  3: Reasonable detail on ICP, problem, or solution
  4: Clear and concrete on most dimensions
  5: Highly specific ICP, problem, solution, and use case

COMMERCIAL_CLARITY - Is monetization obvious and credible?
  1: No idea how this makes money
  2: Vague monetization concept
  3: Reasonable business model outlined
  4: Clear revenue model and pricing strategy
  5: Obvious path to revenue with validated willingness to pay

ORIGINAL DOMAIN/INSPIRATION:
{inspiration}

IDEA TO EVALUATE:
{idea}

Score this idea. Be rigorous and honest. Respond ONLY with valid JSON:
{{
  "novelty": <1-5>,
  "feasibility": <1-5>,
  "specificity": <1-5>,
  "commercial_clarity": <1-5>,
  "notes": "<brief justification for scores>"
}}"""


def score_idea_llm(
    idea: dict,
    inspiration: str,
    model: str = "gpt-5.1",
) -> IdeaScore:
    """
    Score an idea using an LLM as judge.

    Args:
        idea: The idea dictionary to score
        inspiration: Original domain/context for the idea
        model: Model to use for scoring

    Returns:
        IdeaScore with LLM-provided scores
    """
    client = OpenAI()

    idea_text = json.dumps(idea, indent=2) if isinstance(idea, dict) else str(idea)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a rigorous startup evaluator. Score ideas honestly using the provided rubric. Output only valid JSON."
            },
            {
                "role": "user",
                "content": LLM_JUDGE_PROMPT.format(
                    inspiration=inspiration,
                    idea=idea_text
                )
            }
        ],
        temperature=0.3,
    )

    content = response.choices[0].message.content

    # Extract JSON from response
    try:
        start = content.find('{')
        end = content.rfind('}')
        if start != -1 and end != -1:
            scores = json.loads(content[start:end+1])
        else:
            raise ValueError("No JSON found in response")
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[!] Failed to parse LLM judge response: {e}")
        print(f"    Raw response: {content[:200]}")
        # Default to middle scores
        scores = {"novelty": 3, "feasibility": 3, "specificity": 3, "commercial_clarity": 3, "notes": "Parse error - default scores"}

    return IdeaScore(
        novelty=max(1, min(5, scores.get("novelty", 3))),
        feasibility=max(1, min(5, scores.get("feasibility", 3))),
        specificity=max(1, min(5, scores.get("specificity", 3))),
        commercial_clarity=max(1, min(5, scores.get("commercial_clarity", 3))),
        notes=scores.get("notes", ""),
    )


def compare_scores(score_a: IdeaScore, score_b: IdeaScore) -> dict:
    """
    Compare two idea scores.

    Args:
        score_a: Score for idea A (e.g., Assembly)
        score_b: Score for idea B (e.g., Baseline)

    Returns:
        Comparison results dictionary
    """
    return {
        "a_total": score_a.total,
        "b_total": score_b.total,
        "winner": "A" if score_a.total > score_b.total else ("B" if score_b.total > score_a.total else "Tie"),
        "difference": score_a.total - score_b.total,
        "percent_difference": ((score_a.total - score_b.total) / score_b.total * 100) if score_b.total > 0 else 0,
        "criteria_comparison": {
            "novelty": {"a": score_a.novelty, "b": score_b.novelty},
            "feasibility": {"a": score_a.feasibility, "b": score_b.feasibility},
            "specificity": {"a": score_a.specificity, "b": score_b.specificity},
            "commercial_clarity": {"a": score_a.commercial_clarity, "b": score_b.commercial_clarity},
        },
    }


def aggregate_results(comparisons: list[dict]) -> dict:
    """
    Aggregate multiple comparison results.

    Args:
        comparisons: List of comparison result dictionaries

    Returns:
        Aggregated results
    """
    total = len(comparisons)
    a_wins = sum(1 for c in comparisons if c["winner"] == "A")
    b_wins = sum(1 for c in comparisons if c["winner"] == "B")
    ties = sum(1 for c in comparisons if c["winner"] == "Tie")

    a_total_score = sum(c["a_total"] for c in comparisons)
    b_total_score = sum(c["b_total"] for c in comparisons)

    return {
        "total_comparisons": total,
        "a_wins": a_wins,
        "b_wins": b_wins,
        "ties": ties,
        "a_win_rate": a_wins / total * 100 if total > 0 else 0,
        "a_avg_score": a_total_score / total if total > 0 else 0,
        "b_avg_score": b_total_score / total if total > 0 else 0,
        "avg_score_difference": (a_total_score - b_total_score) / total if total > 0 else 0,
        "percent_improvement": ((a_total_score - b_total_score) / b_total_score * 100) if b_total_score > 0 else 0,
    }


def check_phase2_gate(results: dict) -> dict:
    """
    Check if Phase 2 gate is passed.

    Targets:
    - Assembly wins >= 70% of comparisons
    - Assembly scores >= 20% higher on average

    Args:
        results: Aggregated results from aggregate_results()

    Returns:
        Gate check results
    """
    win_rate = results.get("a_win_rate", 0)
    improvement = results.get("percent_improvement", 0)

    win_rate_passed = win_rate >= 70
    improvement_passed = improvement >= 20

    return {
        "win_rate_target": 70,
        "win_rate_actual": win_rate,
        "win_rate_passed": win_rate_passed,
        "improvement_target": 20,
        "improvement_actual": improvement,
        "improvement_passed": improvement_passed,
        "gate_passed": win_rate_passed and improvement_passed,
        "recommendation": (
            "PROCEED to Phase 3"
            if win_rate_passed and improvement_passed
            else "REVISIT persona design or facilitator logic"
        ),
    }


def compare_n_scores(scores: Dict[str, IdeaScore]) -> dict:
    """
    Compare N idea scores (supports 2-way, 3-way, or more comparisons).

    Args:
        scores: Dictionary mapping labels (e.g., "A", "B", "C") to IdeaScore objects

    Returns:
        Comparison results dictionary with winner, rankings, and per-criteria breakdown
    """
    if not scores:
        return {"error": "No scores provided"}

    labels = list(scores.keys())
    totals = {label: score.total for label, score in scores.items()}

    # Find winner(s)
    max_total = max(totals.values())
    winners = [label for label, total in totals.items() if total == max_total]

    # Rank all entries
    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)
    rankings = {label: rank + 1 for rank, (label, _) in enumerate(ranked)}

    # Per-criteria comparison
    criteria = ["novelty", "feasibility", "specificity", "commercial_clarity"]
    criteria_comparison = {}
    for criterion in criteria:
        criterion_scores = {label: getattr(score, criterion) for label, score in scores.items()}
        max_criterion = max(criterion_scores.values())
        criterion_winners = [label for label, val in criterion_scores.items() if val == max_criterion]
        criteria_comparison[criterion] = {
            "scores": criterion_scores,
            "winner": criterion_winners[0] if len(criterion_winners) == 1 else "Tie",
            "winners": criterion_winners,
        }

    return {
        "totals": totals,
        "winner": winners[0] if len(winners) == 1 else "Tie",
        "winners": winners,
        "rankings": rankings,
        "criteria_comparison": criteria_comparison,
        "score_details": {label: score.to_dict() for label, score in scores.items()},
    }


def aggregate_n_way_results(comparisons: list[dict], approach_mapping: Dict[str, str] = None) -> dict:
    """
    Aggregate multiple N-way comparison results.

    Args:
        comparisons: List of comparison result dictionaries from compare_n_scores
        approach_mapping: Optional mapping from labels to approach names
                         (e.g., {"A": "assembly", "B": "iterative", "C": "single_shot"})

    Returns:
        Aggregated results with win rates per approach
    """
    if not comparisons:
        return {"error": "No comparisons provided"}

    # Collect all labels across comparisons
    all_labels = set()
    for comp in comparisons:
        all_labels.update(comp.get("totals", {}).keys())

    # Initialize counters
    win_counts = {label: 0 for label in all_labels}
    total_scores = {label: 0 for label in all_labels}
    appearance_counts = {label: 0 for label in all_labels}

    # Aggregate
    for comp in comparisons:
        totals = comp.get("totals", {})
        winners = comp.get("winners", [])

        for label, total in totals.items():
            total_scores[label] += total
            appearance_counts[label] += 1

        for winner in winners:
            win_counts[winner] += 1 / len(winners)  # Split wins for ties

    # Calculate rates and averages
    results = {
        "total_comparisons": len(comparisons),
        "by_label": {},
        "by_approach": {},
    }

    for label in all_labels:
        count = appearance_counts[label]
        if count > 0:
            results["by_label"][label] = {
                "wins": win_counts[label],
                "win_rate": win_counts[label] / count * 100,
                "avg_score": total_scores[label] / count,
                "appearances": count,
            }

    # If approach mapping provided, also aggregate by approach name
    if approach_mapping:
        approach_wins = {}
        approach_scores = {}
        approach_counts = {}

        for comp in comparisons:
            # Get this comparison's mapping (may vary if anonymized)
            comp_mapping = comp.get("mapping", approach_mapping)
            totals = comp.get("totals", {})
            winners = comp.get("winners", [])

            for label, approach in comp_mapping.items():
                if approach not in approach_wins:
                    approach_wins[approach] = 0
                    approach_scores[approach] = 0
                    approach_counts[approach] = 0

                if label in totals:
                    approach_scores[approach] += totals[label]
                    approach_counts[approach] += 1

                if label in winners:
                    approach_wins[approach] += 1 / len(winners)

        for approach in approach_wins:
            count = approach_counts[approach]
            if count > 0:
                results["by_approach"][approach] = {
                    "wins": approach_wins[approach],
                    "win_rate": approach_wins[approach] / count * 100,
                    "avg_score": approach_scores[approach] / count,
                    "appearances": count,
                }

    return results


def load_and_score_results(results_file: str) -> None:
    """
    Load comparison results and interactively score them.

    Args:
        results_file: Path to comparison results JSON file
    """
    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    comparisons = data.get("comparisons", [])
    scored_comparisons = []

    for i, comparison in enumerate(comparisons):
        print(f"\n{'='*60}")
        print(f"COMPARISON {i+1}/{len(comparisons)}: {comparison.get('prompt_id', 'Unknown')}")
        print(f"{'='*60}")

        # Show both ideas (anonymized as A and B)
        print("\n--- IDEA A ---")
        idea_a = comparison.get("idea_a")
        if idea_a:
            print(json.dumps(idea_a, indent=2))
        else:
            print("(No idea generated)")

        print("\n--- IDEA B ---")
        idea_b = comparison.get("idea_b")
        if idea_b:
            print(json.dumps(idea_b, indent=2))
        else:
            print("(No idea generated)")

        # Score both
        print("\n--- SCORE IDEA A ---")
        score_a = score_idea_interactive()

        print("\n--- SCORE IDEA B ---")
        score_b = score_idea_interactive()

        # Compare
        result = compare_scores(score_a, score_b)
        result["prompt_id"] = comparison.get("prompt_id")
        result["score_a_details"] = score_a.to_dict()
        result["score_b_details"] = score_b.to_dict()

        scored_comparisons.append(result)

        print(f"\nWinner: {result['winner']} (difference: {result['difference']})")

    # Aggregate and show final results
    aggregated = aggregate_results(scored_comparisons)
    gate_check = check_phase2_gate(aggregated)

    print(f"\n{'='*60}")
    print("FINAL RESULTS")
    print(f"{'='*60}")
    print(f"A wins: {aggregated['a_wins']}/{aggregated['total_comparisons']} ({aggregated['a_win_rate']:.1f}%)")
    print(f"B wins: {aggregated['b_wins']}/{aggregated['total_comparisons']}")
    print(f"A avg score: {aggregated['a_avg_score']:.2f}")
    print(f"B avg score: {aggregated['b_avg_score']:.2f}")
    print(f"Improvement: {aggregated['percent_improvement']:.1f}%")
    print(f"\nGate: {'PASSED' if gate_check['gate_passed'] else 'FAILED'}")
    print(f"Recommendation: {gate_check['recommendation']}")

    # Save scored results
    output_file = results_file.replace(".json", "_scored.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "comparisons": scored_comparisons,
            "aggregated": aggregated,
            "gate_check": gate_check,
        }, f, indent=2)
    print(f"\nScored results saved to: {output_file}")


def load_and_score_three_way_results(results_file: str) -> None:
    """
    Load 3-way comparison results and interactively score them.

    Args:
        results_file: Path to three_way_comparison results JSON file
    """
    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    comparisons = data.get("comparisons", [])
    scored_comparisons = []

    for i, comparison in enumerate(comparisons):
        print(f"\n{'='*60}")
        print(f"COMPARISON {i+1}/{len(comparisons)}: {comparison.get('prompt_id', 'Unknown')}")
        print(f"{'='*60}")

        # Show all three ideas (anonymized as A, B, C)
        for label in ["A", "B", "C"]:
            idea_key = f"idea_{label.lower()}"
            print(f"\n--- IDEA {label} ---")
            idea = comparison.get(idea_key)
            if idea:
                print(json.dumps(idea, indent=2))
            else:
                print("(No idea generated)")

        # Score all three
        scores = {}
        for label in ["A", "B", "C"]:
            if comparison.get(f"idea_{label.lower()}"):
                print(f"\n--- SCORE IDEA {label} ---")
                scores[label] = score_idea_interactive()

        # Compare
        if len(scores) >= 2:
            result = compare_n_scores(scores)
            result["prompt_id"] = comparison.get("prompt_id")
            result["mapping"] = comparison.get("mapping", {})

            scored_comparisons.append(result)

            print(f"\nWinner: {result['winner']}")
            print(f"Rankings: {result['rankings']}")
            print(f"Totals: {result['totals']}")

    # Aggregate and show final results
    if scored_comparisons:
        # Get approach mapping from first comparison
        sample_mapping = scored_comparisons[0].get("mapping", {})
        aggregated = aggregate_n_way_results(scored_comparisons, sample_mapping)

        print(f"\n{'='*60}")
        print("FINAL 3-WAY RESULTS")
        print(f"{'='*60}")

        print("\nBy Approach:")
        for approach, stats in aggregated.get("by_approach", {}).items():
            print(f"  {approach}:")
            print(f"    Wins: {stats['wins']:.1f}")
            print(f"    Win rate: {stats['win_rate']:.1f}%")
            print(f"    Avg score: {stats['avg_score']:.2f}")

        # Save scored results
        output_file = results_file.replace(".json", "_scored.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump({
                "comparisons": scored_comparisons,
                "aggregated": aggregated,
            }, f, indent=2)
        print(f"\nScored results saved to: {output_file}")
    else:
        print("\nNo valid comparisons to aggregate.")


if __name__ == "__main__":
    import sys
    import argparse

    parser = argparse.ArgumentParser(description="Score benchmark comparison results")
    parser.add_argument("results_file", nargs="?", help="Path to results JSON file")
    parser.add_argument(
        "--mode",
        choices=["two_way", "three_way"],
        default="two_way",
        help="Scoring mode: two_way or three_way (default: two_way)"
    )
    args = parser.parse_args()

    if args.results_file:
        if args.mode == "three_way":
            load_and_score_three_way_results(args.results_file)
        else:
            load_and_score_results(args.results_file)
    else:
        # Print rubric for reference
        print_scoring_rubric()
        print("\nUsage: python scoring.py <results_file.json> [--mode two_way|three_way]")
