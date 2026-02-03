# test_persona_role_adherence.py
# Phase 1 Benchmark: Measure persona role drift in conversation logs

import json
import os
import re
import sys
from datetime import datetime
from glob import glob
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI


# Role adherence keywords/patterns for common personas
# Note: Dynamic personas may have names like "Need Identifier", "Fear Assessor", etc.
# We use flexible matching based on keywords in persona names
PERSONA_INDICATORS = {
    # Static personas
    "founder": {
        "positive": ["vision", "opportunity", "market", "users", "problem", "solution", "startup", "product"],
        "negative": ["implementation details", "code", "database schema"],
    },
    "designer": {
        "positive": ["user experience", "interface", "usability", "flow", "intuitive", "design", "visual"],
        "negative": ["backend", "infrastructure", "profit margin"],
    },
    "researcher": {
        "positive": ["market", "data", "analysis", "users", "survey", "validate", "evidence", "tam", "sam"],
        "negative": ["let's just build", "implementation"],
    },
    "tech_lead": {
        "positive": ["architecture", "technical", "implementation", "feasible", "scalable", "api", "stack"],
        "negative": ["marketing", "branding"],
    },
    "cfo": {
        "positive": ["revenue", "cost", "profit", "margin", "pricing", "monetization", "business model", "roi"],
        "negative": ["user experience", "visual design"],
    },
    "contrarian": {
        "positive": ["risk", "assumption", "challenge", "what if", "concern", "skeptic", "devil's advocate"],
        "negative": [],
    },
    # Dynamic persona patterns (matched by keywords in name)
    "identifier": {
        "positive": ["identify", "aspects", "examine", "key", "central", "tensions", "factors"],
        "negative": [],
    },
    "evaluator": {
        "positive": ["evaluate", "assess", "analysis", "trade-off", "balance", "consider"],
        "negative": [],
    },
    "analyzer": {
        "positive": ["analyze", "analysis", "examine", "evaluate", "data", "findings"],
        "negative": [],
    },
    "simplifier": {
        "positive": ["simplify", "clarity", "clear", "streamline", "straightforward"],
        "negative": [],
    },
    "assessor": {
        "positive": ["assess", "evaluate", "concerns", "fears", "risks", "challenges"],
        "negative": [],
    },
    "builder": {
        "positive": ["build", "confidence", "support", "guide", "help", "enable"],
        "negative": [],
    },
}


def analyze_role_adherence_with_llm(
    exchange: dict,
    model_name: str = "gpt-4o-mini",
) -> dict:
    """
    Use LLM to analyze whether a persona stayed in role.

    Args:
        exchange: Single conversation exchange with persona and content
        model_name: Model to use for analysis

    Returns:
        Dictionary with analysis results
    """
    client = OpenAI()

    # Support both "persona" and "speaker" field names
    persona = exchange.get("persona") or exchange.get("speaker", "Unknown")
    archetype = exchange.get("archetype", "")
    content = exchange.get("content", "")
    phase = exchange.get("phase", "unknown")

    analysis_prompt = f"""Analyze whether this persona stayed in their assigned role.

Persona: {persona}
Role/Archetype: {archetype}
Phase: {phase}

Response:
{content[:2000]}  # Truncate for cost efficiency

Evaluate on a scale of 1-5:
1 = Completely out of character (talking about unrelated topics)
2 = Mostly out of character (occasional role-appropriate content)
3 = Mixed (some in-role, some drift)
4 = Mostly in character (minor drift)
5 = Fully in character (consistent with role throughout)

Respond in JSON format:
{{
    "score": <1-5>,
    "in_role": <true if score >= 4, false otherwise>,
    "reasoning": "<brief explanation>"
}}
"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You analyze AI persona role adherence. Return valid JSON only."},
                {"role": "user", "content": analysis_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
        )

        result = json.loads(response.choices[0].message.content)
        return {
            "persona": persona,
            "phase": phase,
            "score": result.get("score", 0),
            "in_role": result.get("in_role", False),
            "reasoning": result.get("reasoning", ""),
        }

    except Exception as e:
        return {
            "persona": persona,
            "phase": phase,
            "score": 0,
            "in_role": False,
            "reasoning": f"Analysis failed: {e}",
            "error": str(e),
        }


def analyze_role_adherence_heuristic(exchange: dict) -> dict:
    """
    Simple heuristic-based role adherence check (no LLM cost).

    Args:
        exchange: Single conversation exchange

    Returns:
        Dictionary with analysis results
    """
    # Support both "persona" and "speaker" field names
    persona = exchange.get("persona") or exchange.get("speaker", "Unknown")
    persona = persona.lower()
    content = exchange.get("content", "").lower()
    phase = exchange.get("phase", "unknown")

    # Find matching persona indicators
    indicators = None
    for key in PERSONA_INDICATORS:
        if key in persona:
            indicators = PERSONA_INDICATORS[key]
            break

    if not indicators:
        return {
            "persona": persona,
            "phase": phase,
            "score": 3,  # Neutral if unknown persona
            "in_role": True,
            "reasoning": "Unknown persona type - assuming in-role",
        }

    # Count positive and negative indicators
    positive_count = sum(1 for word in indicators["positive"] if word in content)
    negative_count = sum(1 for word in indicators["negative"] if word in content)

    # Calculate score
    if positive_count >= 3 and negative_count == 0:
        score = 5
    elif positive_count >= 2 and negative_count <= 1:
        score = 4
    elif positive_count >= 1:
        score = 3
    elif negative_count >= 2:
        score = 2
    else:
        score = 3  # Neutral

    return {
        "persona": persona,
        "phase": phase,
        "score": score,
        "in_role": score >= 4,
        "reasoning": f"Positive indicators: {positive_count}, Negative: {negative_count}",
    }


def run_role_adherence_test(
    logs_path: Optional[str] = None,
    use_llm: bool = False,
    model_name: str = "gpt-4o-mini",
    output_dir: Optional[str] = None,
) -> dict:
    """
    Analyze conversation logs for persona role adherence.

    Args:
        logs_path: Path to meeting_logs.txt or conversation log JSON
        use_llm: Whether to use LLM for analysis (more accurate but costly)
        model_name: Model to use if use_llm=True
        output_dir: Directory to save results

    Returns:
        Dictionary with test results
    """
    print(f"\n{'='*60}")
    print("PHASE 1: Persona Role Adherence Test")
    print(f"{'='*60}")
    print(f"Analysis method: {'LLM-based' if use_llm else 'Heuristic-based'}")
    print(f"{'='*60}\n")

    # Find logs file
    if logs_path is None:
        # Look for most recent conversation log
        project_root = os.path.join(os.path.dirname(__file__), "..", "..")
        logs_path = os.path.join(project_root, "meeting_logs.txt")

        if not os.path.exists(logs_path):
            # Try conversation_logs directory
            log_dir = os.path.join(project_root, "conversation_logs")
            if os.path.exists(log_dir):
                log_files = sorted(glob(os.path.join(log_dir, "*.json")))
                if log_files:
                    logs_path = log_files[-1]  # Most recent

    if not os.path.exists(logs_path):
        print(f"[ERROR] No logs found at: {logs_path}")
        print("Run a generation first to create logs.")
        return {"error": "No logs found"}

    print(f"Analyzing logs: {logs_path}")

    # Load logs
    with open(logs_path, "r", encoding="utf-8") as f:
        logs = json.load(f)

    # Handle different log formats
    if isinstance(logs, dict) and "exchanges" in logs:
        exchanges = logs["exchanges"]
    elif isinstance(logs, list):
        exchanges = logs
    else:
        print("[ERROR] Unknown log format")
        return {"error": "Unknown log format"}

    print(f"Found {len(exchanges)} exchanges to analyze\n")

    results = {
        "test_name": "persona_role_adherence",
        "timestamp": datetime.now().isoformat(),
        "config": {
            "logs_path": logs_path,
            "use_llm": use_llm,
            "model_name": model_name if use_llm else "heuristic",
        },
        "exchanges": [],
        "summary": {
            "total_exchanges": len(exchanges),
            "in_role": 0,
            "out_of_role": 0,
            "average_score": 0,
        },
    }

    total_score = 0
    analyze_func = analyze_role_adherence_with_llm if use_llm else analyze_role_adherence_heuristic

    for i, exchange in enumerate(exchanges):
        # Skip non-persona exchanges (facilitator messages, mediator, etc.)
        # Support both "persona" and "speaker" field names
        speaker = exchange.get("persona") or exchange.get("speaker", "")
        if not speaker:
            continue
        if speaker.lower() in ["facilitator", "socratic mediator", "mediator"]:
            continue

        print(f"Analyzing exchange {i+1}: {speaker} ({exchange.get('phase', 'unknown')})")

        if use_llm:
            analysis = analyze_func(exchange, model_name=model_name)
        else:
            analysis = analyze_func(exchange)

        results["exchanges"].append(analysis)
        total_score += analysis["score"]

        if analysis["in_role"]:
            results["summary"]["in_role"] += 1
        else:
            results["summary"]["out_of_role"] += 1

    # Calculate summary
    num_analyzed = len(results["exchanges"])
    if num_analyzed > 0:
        results["summary"]["average_score"] = total_score / num_analyzed
        adherence_rate = results["summary"]["in_role"] / num_analyzed * 100
    else:
        adherence_rate = 0

    results["summary"]["adherence_rate_percent"] = adherence_rate

    # Print summary
    print(f"\n{'='*60}")
    print("ROLE ADHERENCE TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Exchanges analyzed: {num_analyzed}")
    print(f"In-role: {results['summary']['in_role']} ({adherence_rate:.1f}%)")
    print(f"Out-of-role: {results['summary']['out_of_role']}")
    print(f"Average score: {results['summary']['average_score']:.2f}/5")

    # Check gate (target: >=90% in-role)
    gate_passed = adherence_rate >= 90
    results["summary"]["gate_passed"] = gate_passed

    if gate_passed:
        print(f"\n[PASS] Gate passed: {adherence_rate:.1f}% >= 90% in-role")
    else:
        print(f"\n[FAIL] Gate failed: {adherence_rate:.1f}% < 90% in-role")

        # Show worst offenders
        out_of_role = [ex for ex in results["exchanges"] if not ex["in_role"]]
        if out_of_role:
            print("\nLowest scoring exchanges:")
            for ex in sorted(out_of_role, key=lambda x: x["score"])[:3]:
                print(f"  - {ex['persona']} ({ex['phase']}): {ex['score']}/5 - {ex['reasoning'][:50]}...")

    # Save results if output directory specified
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(
            output_dir,
            f"role_adherence_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to: {output_file}")

    return results


if __name__ == "__main__":
    run_role_adherence_test(
        use_llm=False,  # Use heuristic by default (free)
        output_dir="results",
    )
