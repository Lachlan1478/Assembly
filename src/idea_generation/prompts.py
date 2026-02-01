# idea_brainstorm_01b_prompts.py
# Prompt generation module: Staged discovery prompts for all phases

from typing import Dict, Any, List
from textwrap import dedent
from src.idea_generation.idea_tracker import (
    get_ideas_in_play,
    get_rejected_ideas,
    format_ideas_for_prompt,
    format_rejections_for_prompt
)


def get_stage_info(phase_id: str, turn_count: int, max_turns: int) -> Dict[str, Any]:
    """
    Calculate current stage based on phase ID, turn count, and maximum turns.

    Returns dict with stage_number, stage_name, and total_stages.
    """
    # Define stages for each phase
    phase_stages = {
        "ideation": [
            "Problem Discovery",
            "Competitive Landscape",
            "Solution Exploration",
            "Synthesis"
        ],
        "research": [
            "Market Sizing",
            "Competitive Analysis",
            "Validation Strategy"
        ],
        "critique": [
            "Assumption Identification",
            "Risk Analysis",
            "Mitigation Strategies"
        ],
        "decision": [
            "Consolidation",
            "Final Proposal"
        ],
        # Default stages for other phases
        "design": ["User Experience Analysis", "Design Principles", "UX Refinement"],
        "feasibility": ["Technical Assessment", "Architecture Planning", "Implementation Strategy"],
        "financials": ["Business Model", "Cost Structure", "Revenue Projections"]
    }

    stages = phase_stages.get(phase_id, ["Analysis", "Synthesis"])
    total_stages = len(stages)

    # Calculate which stage we're in (equal distribution)
    turns_per_stage = max(1, max_turns / total_stages)
    stage_number = min(int(turn_count / turns_per_stage), total_stages - 1)

    return {
        "stage_number": stage_number,
        "stage_name": stages[stage_number],
        "total_stages": total_stages,
        "stage_progress": f"{stage_number + 1}/{total_stages}"
    }


def generate_dynamic_prompt(
    phase: Dict[str, Any],
    turn_count: int,
    phase_exchanges: List[Dict[str, Any]],
    shared_context: Dict[str, Any]
) -> str:
    """
    Generate staged, discovery-oriented prompts that mimic real brainstorming.

    Each phase progresses through multiple stages that guide personas from problem
    discovery to solution synthesis, rather than jumping straight to solutions.

    Args:
        phase: Current phase dict with phase_id and goal
        turn_count: Current turn number in phase
        phase_exchanges: Exchanges so far in this phase
        shared_context: Shared context including inspiration, ideas, and focus

    Returns:
        Stage-appropriate prompt that guides natural discovery process
    """
    phase_id = phase.get("phase_id", "")
    phase_type = phase.get("phase_type", "debate")  # Available but not used for format enforcement
    max_turns = phase.get("max_turns", 15)
    inspiration = shared_context.get("inspiration", "")
    ideas_discussed = shared_context.get("ideas_discussed", [])

    # All phases use natural discussion format
    # Phase type controls mediator behavior, not persona response format

    # Get current stage info
    stage_info = get_stage_info(phase_id, turn_count, max_turns)
    stage_num = stage_info["stage_number"]

    # =======================
    # IDEATION PHASE (4 stages)
    # =======================
    if phase_id == "ideation":
        # Stage 1: Problem Discovery
        if stage_num == 0:
            return dedent(f"""\
                Based on the following inspiration, let's start by deeply understanding
                the problem space BEFORE jumping to solutions:

                {inspiration}

                Discuss:
                1. What are the core pain points in this domain? Share specific examples
                   you've encountered or heard about.
                2. Why is this problem worth solving now? What's changed recently that
                   makes this timely?
                3. Who feels this pain most acutely? Be specific about the user profile.

                Focus on problem discovery, not solutions yet.""").strip()

        # Stage 2: Competitive Landscape
        elif stage_num == 1:
            return dedent(f"""\
                Now let's analyze the existing competitive landscape:

                1. What tools, products, or approaches already exist in this space?
                   Name specific competitors if you know them.
                2. Where do current solutions fall short? What complaints do users have?
                3. What gaps or whitespace opportunities do you see that aren't being
                   addressed?

                Continue exploring - still no specific solutions yet.""").strip()

        # Stage 3: Solution Exploration
        elif stage_num == 2:
            pain_points = "the pain points and gaps we've identified"
            return dedent(f"""\
                Based on our discussion of {pain_points}, let's start exploring
                potential solutions:

                1. Propose an approach that addresses the core pain points we identified.
                2. Describe a concrete scenario: "Imagine a [user type] who [specific
                   situation]... with our solution, they would [specific outcome]..."
                3. What would make this solution 10x better than existing options?

                Focus on how your solution uniquely addresses the problems discussed.""").strip()

        # Stage 4: Synthesis & Refinement
        else:
            if ideas_discussed:
                # Get ideas currently in play and rejected ideas
                in_play = get_ideas_in_play(ideas_discussed)
                rejected = get_rejected_ideas(ideas_discussed)

                # Build prompt with structured context
                ideas_context = format_ideas_for_prompt(in_play, max_count=3)
                rejection_context = format_rejections_for_prompt(rejected)

                prompt_parts = [f"Ideas being considered:\n{ideas_context}"]

                if rejection_context:
                    prompt_parts.append(f"\nNote - these were rejected:\n{rejection_context}")

                prompt_parts.append("""
Either:
1. Build on the in-play ideas with specific improvements or refinements
2. Identify potential issues or edge cases we haven't considered
3. Merge the best aspects into a stronger unified concept
4. Describe how this would work in a specific real-world scenario

Focus on making ideas concrete and actionable. Do not re-propose rejected ideas.""")

                return dedent("\n".join(prompt_parts)).strip()
            else:
                return dedent(f"""\
                    Let's consolidate our discussion into concrete startup concepts:

                    Based on everything discussed, propose or refine a solution that:
                    - Addresses the pain points we identified
                    - Fills gaps in the competitive landscape
                    - Has a clear, compelling use case

                    Include a real-world example of how it would be used.""").strip()

    # =======================
    # RESEARCH PHASE (3 stages)
    # =======================
    elif phase_id == "research":
        # Format in-play ideas with their full context
        in_play = get_ideas_in_play(ideas_discussed)
        if in_play:
            concept_titles = [idea["title"] for idea in in_play[-3:]]
            concepts = ", ".join(f'"{title}"' for title in concept_titles)
            concepts_detail = format_ideas_for_prompt(in_play[-3:], max_count=3)
        else:
            concepts = "the concepts discussed"
            concepts_detail = "the ideas we've been discussing"

        # Stage 1: Market Sizing
        if stage_num == 0:
            return dedent(f"""\
                Let's validate market demand for {concepts}:

                1. What is the Total Addressable Market (TAM)? Estimate the number of
                   potential users/customers.
                2. What is the Serviceable Available Market (SAM)? Who specifically would
                   adopt this?
                3. What evidence suggests people would pay for this solution? Reference
                   similar products or user research.

                Ground your analysis in data and realistic market dynamics.""").strip()

        # Stage 2: Competitive Analysis
        elif stage_num == 1:
            return dedent(f"""\
                Now let's deeply analyze the competitive landscape:

                1. Create a feature comparison: How do existing solutions compare on key
                   dimensions?
                2. What pain points do competitors fail to address? Where do users
                   complain?
                3. What is our unique differentiation? Why would users switch to us?

                Be specific about named competitors and their strengths/weaknesses.""").strip()

        # Stage 3: Validation Strategy
        else:
            return dedent(f"""\
                How would we validate demand before building?

                1. What user research or interviews should we conduct? With whom?
                2. What pilot program or MVP could test our core assumptions?
                3. What metrics would indicate product-market fit?

                Propose concrete validation steps, not abstract concepts.""").strip()

    # =======================
    # CRITIQUE PHASE (3 stages)
    # =======================
    elif phase_id == "critique":
        # Format in-play ideas with their full context
        in_play = get_ideas_in_play(ideas_discussed)
        if in_play:
            concept_titles = [idea["title"] for idea in in_play[-3:]]
            concepts = ", ".join(f'"{title}"' for title in concept_titles)
            concepts_detail = format_ideas_for_prompt(in_play[-3:], max_count=3)
        else:
            concepts = "the proposed solution"
            concepts_detail = "the ideas we've been discussing"

        # Stage 1: Assumption Identification
        if stage_num == 0:
            return dedent(f"""\
                Let's identify and stress-test our core assumptions about {concepts}:

                1. What assumptions are we making about users, market, or technology?
                2. Which assumptions, if wrong, would invalidate the entire concept?
                3. What evidence supports or contradicts each assumption?

                Be critical and thorough - identify blind spots we might have.""").strip()

        # Stage 2: Risk Analysis
        elif stage_num == 1:
            return dedent(f"""\
                Now let's analyze key risks:

                1. Technical risks: What could make this hard or impossible to build?
                2. Market risks: Why might users NOT adopt this?
                3. Competitive risks: How might competitors respond?

                Focus on realistic risks with potential high impact.""").strip()

        # Stage 3: Mitigation Strategies
        else:
            return dedent(f"""\
                For the risks and assumptions identified, propose mitigation strategies:

                1. How can we reduce or eliminate each major risk?
                2. What early warning signs would indicate a risk is materializing?
                3. What contingency plans should we have?

                Provide actionable mitigation tactics, not generic advice.""").strip()

    # =======================
    # DECISION PHASE (2 stages)
    # =======================
    elif phase_id == "decision":
        # Stage 1: Consolidation
        if stage_num == 0:
            return dedent(f"""\
                Review all discussions across phases and synthesize key insights:

                1. What are the strongest ideas that emerged?
                2. What critical feedback and risks were identified?
                3. How should we incorporate this feedback into the final proposal?

                Focus on synthesis - combine the best elements into a coherent concept.""").strip()

        # Stage 2: Final Proposal
        else:
            return dedent(f"""\
                Finalize the startup idea in complete, structured format:

                Include ALL required fields:
                - title: Clear, memorable name
                - description: What it does (2-3 sentences)
                - target_users: Specific user profile
                - primary_outcome: Main value delivered
                - must_haves: Essential features (list)
                - constraints: Realistic limitations (list)
                - non_goals: What it explicitly won't do (list)

                Make it concrete, actionable, and grounded in our discussions.""").strip()

    # =======================
    # OTHER PHASES (Default staging)
    # =======================
    else:
        phase_goal = phase.get("goal", "the phase objective")

        if stage_num == 0:
            return dedent(f"""\
                Let's begin by analyzing {phase_goal}:

                1. What aspects should we examine based on our previous discussions?
                2. What questions need answering to achieve this phase's goal?

                Build on the conversation so far.""").strip()
        else:
            return dedent(f"""\
                Continue discussing {phase_goal}:

                1. What insights can you add based on what others have shared?
                2. How does this relate to the problems and solutions we've identified?

                Synthesize and build on previous contributions.""").strip()


# Integration prompt function removed - all phases now use natural discussion format
# Phase type controls mediator behavior only, not persona response format
