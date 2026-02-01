# mediator_persona.py
# Neutral meta-level facilitator for guiding philosophical debates

import json
from typing import Dict, Any, List, Optional
from openai import OpenAI, AsyncOpenAI
from framework.persona import Persona


class MediatorPersona(Persona):
    """
    Meta-level neutral facilitator that guides reasoning without taking positions.

    Key Differences from Standard Persona:
    - No belief_state (remains neutral)
    - Access to all advocate belief_states
    - Special turn contract (QUESTION/DETECT/BRIDGE)
    - Maintains mediation_log (interventions, not conversation memory)
    """

    def __init__(self, definition: Dict[str, Any], model_name: str = "gpt-4o-mini"):
        super().__init__(definition, model_name)

        # Explicitly disable belief state - mediator must remain neutral
        self.belief_state = None

        # Mediation log tracks interventions, not conversation content
        self.mediation_log = {
            "questions_asked": [],  # {turn, to, question, answered}
            "circular_arguments_detected": [],  # {turn, speaker, argument}
            "synthesis_points": [],  # {turn, bridge}
            "conceptual_tools_introduced": [],  # {turn, tool, context}
            "definitions_forced": [],  # {turn, term, for_speaker}
            "scenarios_presented": []  # {turn, scenarios, instructions}
        }

    @classmethod
    def from_definition(cls, definition: Dict[str, Any], model_name: str = "gpt-4o-mini"):
        """Create mediator from definition dict."""
        return cls(definition, model_name=model_name)

    @classmethod
    def get_default_mediator(cls, model_name: str = "gpt-4o-mini"):
        """
        Get default neutral mediator persona.

        Returns:
            MediatorPersona with standard neutral referee configuration
        """
        definition = {
            "Name": "Socratic Mediator",
            "Archetype": "Neutral referee who guides philosophical debates through probing questions",
            "Purpose": "Detect circular reasoning, force precision, bridge frameworks, track concessions",
            "Deliverables": "Targeted questions, synthesis summaries, conceptual reframings",
            "Strengths": "Meta-level pattern detection, philosophical translation, progress tracking",
            "Watch-out": "Must never take sides or express normative positions",
            "Conversation_Style": "Address advocates by name with specific questions. Call out repetition explicitly. Bridge ideas by translating terminology. Track progress."
        }
        return cls(definition, model_name=model_name)

    def mediate(self, ctx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate mediator intervention (QUESTION/DETECT/BRIDGE).

        Different from response() - has access to ALL advocate belief states.

        Args:
            ctx: Context dictionary containing:
                - advocate_belief_states: Dict of {name: belief_state}
                - recent_exchanges: Last 5 turns
                - shared_context: Topic, current focus
                - turn_count: Current turn number
                - stagnation_detected: bool

        Returns:
            Dict with persona, archetype, and response (QUESTION/DETECT/BRIDGE format)
        """
        from src.idea_generation.mediator_prompts import (
            MEDIATOR_SYSTEM_PROMPT,
            get_mediator_turn_contract,
            format_advocate_states,
            format_mediation_log,
            format_recent_exchanges,
            format_active_scenarios
        )

        advocate_states = ctx.get("advocate_belief_states", {})
        recent_exchanges = ctx.get("recent_exchanges", [])
        shared_context = ctx.get("shared_context", {})
        turn_count = ctx.get("turn_count", 0)
        stagnation_detected = ctx.get("stagnation_detected", False)
        phase_type = ctx.get("phase_type", "debate")

        # Calculate dynamic word limit (consistent with debate mode)
        if turn_count == 0:
            word_limit = 300
        elif turn_count <= 2:
            word_limit = 200
        else:
            word_limit = 150

        # Build mediator-specific prompt
        prompt = f"""RECENT DISCUSSION (Last 3-5 turns):
{format_recent_exchanges(recent_exchanges)}

---

ADVOCATE BELIEF STATES:
{format_advocate_states(advocate_states)}

---

{format_active_scenarios(shared_context)}

---

YOUR PRIOR INTERVENTIONS:
{format_mediation_log(self.mediation_log)}

---

CONTEXT:
Turn: {turn_count}
Phase type: {phase_type}
Stagnation detected: {stagnation_detected}

---

{get_mediator_turn_contract(phase_type, word_limit)}"""

        # Build system message emphasizing neutrality
        system_message = f"""{MEDIATOR_SYSTEM_PROMPT}

Your archetype: {self.archetype}
Your purpose: {self.purpose}
Your strengths: {self.strengths}
CRITICAL: {self.watchouts}"""

        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ]

        # Call LLM
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages
        )

        content = completion.choices[0].message.content.strip()

        # Log intervention
        self._log_intervention(content, ctx)

        # Check if scenarios were just presented (extract from latest log entry)
        scenarios = None
        if self.mediation_log["scenarios_presented"]:
            latest_scenario_entry = self.mediation_log["scenarios_presented"][-1]
            if latest_scenario_entry["turn"] == turn_count:
                scenarios = latest_scenario_entry["scenarios"]

        return {
            "persona": self.name,
            "archetype": self.archetype,
            "response": content,
            "scenarios": scenarios  # None if no scenarios presented, else list of scenario dicts
        }

    def _log_intervention(self, content: str, ctx: Dict[str, Any]) -> None:
        """
        Parse mediator response and log intervention details.

        Args:
            content: Mediator's response text
            ctx: Context with turn_count, advocate names
        """
        turn = ctx.get("turn_count", 0)

        # Extract QUESTION section (rough parsing)
        if "QUESTION:" in content or "1." in content:
            # Log that a question was asked (detailed parsing would be more complex)
            advocate_names = list(ctx.get("advocate_belief_states", {}).keys())
            for name in advocate_names:
                if name in content:
                    self.mediation_log["questions_asked"].append({
                        "turn": turn,
                        "to": name,
                        "question": content[:100],  # First 100 chars as preview
                        "answered": False  # Will be updated on next turn
                    })
                    break

        # Extract DETECT section (circular arguments, stagnation calls)
        if any(keyword in content.lower() for keyword in ["repeated", "circular", "stagnation", "axiom"]):
            self.mediation_log["circular_arguments_detected"].append({
                "turn": turn,
                "detection": content[:150]  # Preview
            })

        # Extract BRIDGE section (synthesis, translation, tools)
        if any(keyword in content.lower() for keyword in ["synthesis", "translate", "consider", "framework", "rule-"]):
            self.mediation_log["synthesis_points"].append({
                "turn": turn,
                "bridge": content[:150]  # Preview
            })

        # Detect conceptual tool introductions
        conceptual_tools = ["rule-utilitarian", "threshold", "side-constraint", "categorical imperative", "veil of ignorance"]
        for tool in conceptual_tools:
            if tool in content.lower():
                self.mediation_log["conceptual_tools_introduced"].append({
                    "turn": turn,
                    "tool": tool,
                    "context": "Introduced in mediation"
                })

        # Detect definition requests
        if "define" in content.lower() or "operational" in content.lower():
            self.mediation_log["definitions_forced"].append({
                "turn": turn,
                "request": content[:100]
            })

        # Detect scenario presentations (look for SCENARIOS: or JSON array with "id" fields)
        if "SCENARIOS:" in content or ('"id":' in content and "CASE_" in content):
            import re
            import json

            # Try to extract JSON scenarios
            scenarios = []
            instructions = None

            # Look for SCENARIOS: followed by JSON array
            match = re.search(r'SCENARIOS:\s*(\[.*?\])', content, re.DOTALL)
            if match:
                try:
                    scenarios = json.loads(match.group(1))
                except json.JSONDecodeError:
                    # Fallback: try to find JSON array anywhere
                    match = re.search(r'(\[\s*\{[^}]*"id"[^}]*\}.*?\])', content, re.DOTALL)
                    if match:
                        try:
                            scenarios = json.loads(match.group(1))
                        except json.JSONDecodeError:
                            pass

            # Extract instructions to agents
            if "INSTRUCTIONS_TO_AGENTS:" in content:
                inst_match = re.search(r'INSTRUCTIONS_TO_AGENTS:\s*"([^"]+)"', content)
                if inst_match:
                    instructions = inst_match.group(1)
                else:
                    # Look for instructions after the section marker
                    inst_match = re.search(r'INSTRUCTIONS_TO_AGENTS:\s*([^\n]+)', content)
                    if inst_match:
                        instructions = inst_match.group(1).strip()

            if scenarios:
                self.mediation_log["scenarios_presented"].append({
                    "turn": turn,
                    "scenarios": scenarios,
                    "instructions": instructions or "Apply your framework to each scenario"
                })

    def update_summary(self, new_exchange: Dict[str, Any]) -> None:
        """
        Override: Mediator doesn't update summary (has no evolving memory).

        Mediator operates at meta-level and doesn't accumulate conversation knowledge.
        """
        pass  # No-op for mediator

    async def update_summary_async(self, new_exchange: Dict[str, Any]) -> None:
        """
        Override: Mediator doesn't update summary (async version).
        """
        pass  # No-op for mediator

    def update_belief_state(self, new_exchange: Dict[str, Any], turn_count: int) -> None:
        """
        Override: Mediator has no belief state to update.

        Mediator must remain neutral and cannot take positions.
        """
        pass  # No-op for mediator

    async def update_belief_state_async(self, new_exchange: Dict[str, Any], turn_count: int) -> None:
        """
        Override: Mediator has no belief state to update (async version).
        """
        pass  # No-op for mediator
