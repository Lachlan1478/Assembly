"""
Dynamic Persona and Phase Generation

This module provides LLM-powered generation of personas and phases
tailored to specific problem domains and conversation contexts.
"""

import json
from typing import Dict, List, Any, Optional
from openai import OpenAI


def generate_personas_for_context(
    inspiration: str,
    phase_info: Dict[str, Any],
    existing_personas: List[str],
    count: int = 4,
    model_name: str = "gpt-4o-mini"
) -> List[Dict[str, Any]]:
    """
    Generate domain-specific personas based on problem context.

    Args:
        inspiration: User's problem domain and context
        phase_info: Current phase information (phase_id, goal, desired_outcome)
        existing_personas: List of persona names already generated
        count: Number of personas to generate (default: 4)
        model_name: LLM model to use

    Returns:
        List of persona definition dicts with keys:
        - Name: Persona name and role
        - Archetype: Character archetype and inspiration
        - Purpose: Why this persona exists
        - Deliverables: What they produce
        - Strengths: Core competencies
        - Watch-out: Potential blind spots
        - Conversation_Style: How they interact
    """
    client = OpenAI()

    # Build context about existing personas to avoid duplication
    existing_context = ""
    if existing_personas:
        existing_context = f"\n\nEXISTING PERSONAS (avoid duplicating these roles):\n" + "\n".join([f"- {p}" for p in existing_personas])

    generation_prompt = f"""Generate {count} logic-role agents for this domain.

DOMAIN: {inspiration}
PHASE: {phase_info.get('phase_id', 'N/A')}
GOAL: {phase_info.get('goal', 'N/A')}
{existing_context}

Each agent is a REASONING FUNCTION, not a personality.

Output format:
1. **Role**: Function name (e.g., "Utilitarian Calculator", "Rights Constraint Enforcer")
2. **Objective**: Optimization target or constraint type
3. **Reasoning_Type**: Logic framework (e.g., "Bayesian weighting", "Rule-based exceptions", "Cost-benefit analysis")
4. **Belief_Structure**: How this agent represents knowledge (e.g., "probability distributions over outcomes", "hard constraints + exception list")
5. **Failure_Mode**: What breaks this reasoning pattern

NO personality traits. NO warmth. NO conversational style. NO inspirations.
Pure logical roles.

Respond ONLY with JSON (map new fields to old schema):
{{
  "personas": [
    {{
      "Name": "[Role name]",
      "Archetype": "[Reasoning_Type]",
      "Purpose": "[Objective]",
      "Deliverables": "[Belief_Structure]",
      "Strengths": "[What this reasoning is good at]",
      "Watch-out": "[Failure_Mode]",
      "Conversation_Style": "N/A"
    }}
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You generate logic-role agents. Each agent is a reasoning function with an objective and belief structure. No personality."
                },
                {
                    "role": "user",
                    "content": generation_prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.8
        )

        content = response.choices[0].message.content.strip()

        # Parse JSON - handle both array and object formats
        parsed = json.loads(content)

        if isinstance(parsed, dict):
            # Check if this dict looks like a single persona (has "Name" key)
            if "Name" in parsed or "name" in parsed:
                personas = [parsed]
            else:
                # LLM wrapped array in object - try multiple possible keys
                personas = parsed.get("personas", parsed.get("persona_list", parsed.get("Personas", parsed.get("PersonaList", []))))
        elif isinstance(parsed, list):
            personas = parsed
        else:
            personas = []

        print(f"[OK] Generated {len(personas)} personas for {phase_info.get('phase_id', 'phase')}")
        return personas

    except Exception as e:
        print(f"[!] Failed to generate personas: {e}")
        # Return empty list - caller should handle fallback
        return []


def generate_phases_for_domain(
    inspiration: str,
    number_of_ideas: int = 1,
    model_name: str = "gpt-4o-mini"
) -> List[Dict[str, Any]]:
    """
    Generate custom workflow phases based on problem domain.

    Instead of using generic startup phases (ideation, design, research...),
    this generates phases tailored to the specific problem type.

    Args:
        inspiration: User's problem domain and context
        number_of_ideas: Number of ideas/solutions to generate
        model_name: LLM model to use

    Returns:
        List of phase definition dicts with keys:
        - phase_id: Short ID (lowercase, underscores)
        - goal: What should be accomplished
        - desired_outcome: Specific deliverable
        - max_turns: Recommended turns for this phase
    """
    client = OpenAI()

    generation_prompt = f"""You are a workflow designer creating a custom conversation flow for collaborative problem-solving.

PROBLEM DOMAIN:
{inspiration}

NUMBER OF SOLUTIONS TO GENERATE: {number_of_ideas}

Design a workflow of 5-7 phases that would be most effective for exploring this specific problem domain and generating {number_of_ideas} high-quality solution(s).

PHASE DESIGN PRINCIPLES:
1. Tailor phases to the SPECIFIC domain (e.g., hiring process needs different phases than product development)
2. Start broad (understanding the problem space)
3. Progress through domain-specific stages (not generic "ideation → design → research")
4. End with synthesis and decision-making
5. Each phase should have a clear, measurable outcome

EXAMPLE FOR HIRING PROCESS:
- Phase 1: candidate_needs → Understand what makes great candidates for this role
- Phase 2: screening_design → Design effective screening criteria and process
- Phase 3: interview_framework → Create structured interview questions and rubrics
- Phase 4: evaluation_system → Build fair, unbiased evaluation framework
- Phase 5: decision_synthesis → Consolidate feedback and make hiring decision

EXAMPLE FOR HEALTHCARE PRODUCT:
- Phase 1: patient_journey → Map the end-to-end patient experience
- Phase 2: pain_point_analysis → Identify critical unmet needs
- Phase 3: solution_exploration → Brainstorm intervention approaches
- Phase 4: clinical_validation → Assess medical/regulatory feasibility
- Phase 5: implementation_design → Define how solution fits into care workflow
- Phase 6: business_model → Determine sustainable revenue model
- Phase 7: decision_synthesis → Choose best solution and define MVP

For each phase, provide:
- **phase_id**: Short identifier (lowercase, underscores, e.g., "patient_journey")
- **goal**: Clear objective for this phase
- **desired_outcome**: Specific deliverable (be concrete about what artifact should exist after)
- **max_turns**: Recommended number of conversation turns (typically 8-12)
- **phase_type**: Either "debate" (default) or "integration"
  - Use "debate" for divergent thinking phases (exploration, analysis, critique)
  - Use "integration" for convergent thinking phases (synthesis, consensus, decision)
  - Typically the last 1-2 phases should be "integration" to converge on solutions

Respond ONLY with a JSON object:
{{
  "phases": [
    {{
      "phase_id": "...",
      "goal": "...",
      "desired_outcome": "...",
      "max_turns": 8,
      "phase_type": "debate"
    }},
    ...
  ]
}}"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert at designing effective problem-solving workflows tailored to specific domains."
                },
                {
                    "role": "user",
                    "content": generation_prompt
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.7  # Moderate creativity for structured workflow
        )

        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)

        phases = parsed.get("phases", [])

        # Add defaults for backward compatibility
        for phase in phases:
            # Default phase_type to "debate" if not specified
            if "phase_type" not in phase:
                phase["phase_type"] = "debate"
            # Validate phase_type
            if phase["phase_type"] not in ["debate", "integration"]:
                print(f"[!] Warning: Invalid phase_type '{phase['phase_type']}' for {phase.get('phase_id')}, defaulting to 'debate'")
                phase["phase_type"] = "debate"

        print(f"[OK] Generated {len(phases)} custom phases for domain")
        for phase in phases:
            phase_type_label = f"[{phase.get('phase_type', 'debate').upper()}]"
            print(f"     - {phase_type_label} {phase.get('phase_id')}: {phase.get('goal')}")

        return phases

    except Exception as e:
        print(f"[!] Failed to generate phases: {e}")
        # Return empty list - caller should use default phases as fallback
        return []


def refine_persona_for_phase(
    base_persona: Dict[str, Any],
    phase_info: Dict[str, Any],
    model_name: str = "gpt-4o-mini"
) -> Dict[str, Any]:
    """
    Refine a persona's conversation style for a specific phase.

    Takes a general persona and adapts their conversation approach
    for the current phase's specific goals.

    Args:
        base_persona: Base persona definition
        phase_info: Current phase information
        model_name: LLM model to use

    Returns:
        Refined persona dict with updated Conversation_Style
    """
    client = OpenAI()

    refinement_prompt = f"""Given this persona and current phase, refine how they should participate in this specific conversation.

PERSONA:
Name: {base_persona.get('Name')}
Archetype: {base_persona.get('Archetype')}
Purpose: {base_persona.get('Purpose')}
Current Conversation Style: {base_persona.get('Conversation_Style', 'Not specified')}

CURRENT PHASE:
- Phase: {phase_info.get('phase_id')}
- Goal: {phase_info.get('goal')}
- Desired Outcome: {phase_info.get('desired_outcome')}

Update the Conversation_Style to be specifically relevant for THIS phase while maintaining the persona's core character. Include:
- What questions they should ask given the phase goal
- Which other personas they should particularly engage with
- What artifacts/deliverables they should push for
- When to be brief vs detailed based on phase objectives

Respond ONLY with a JSON object:
{{
  "Conversation_Style": "refined conversation style text here"
}}"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "system",
                    "content": "You are refining how a persona participates in a specific conversation phase."
                },
                {
                    "role": "user",
                    "content": refinement_prompt
                }
            ],
            response_format={"type": "json_object"}
        )

        content = response.choices[0].message.content.strip()
        parsed = json.loads(content)

        # Create refined persona with updated conversation style
        refined_persona = base_persona.copy()
        refined_persona["Conversation_Style"] = parsed.get("Conversation_Style")

        return refined_persona

    except Exception as e:
        print(f"[!] Failed to refine persona: {e}")
        # Return original persona as fallback
        return base_persona
