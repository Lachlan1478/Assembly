# persona.py
import json
from typing import Dict, Any, Optional, List
from openai import OpenAI

class Persona:
    def __init__(self, definition: Dict[str, Any], model_name: str = "gpt-3.5-turbo"):
        """
        definition: dict loaded from JSON defining this persona
        model_name: default model used for responses
        """
        self.name = definition.get("Name", "Unknown Persona")
        self.archetype = definition.get("Archetype", "")
        self.purpose = definition.get("Purpose", "")
        self.deliverables = definition.get("Deliverables", "")
        self.strengths = definition.get("Strengths", "")
        self.watchouts = definition.get("Watch-out", "")
        self.model_name = model_name
        self.client = OpenAI()  # your LLM client

        # Initialize hybrid summary (objective facts + subjective notes)
        self.summary = {
            "objective_facts": [],
            "subjective_notes": {
                "key_concerns": [],
                "priorities": [],
                "opinions": []
            }
        }

    @classmethod
    def from_file(cls, path: str, model_name: str = "gpt-3.5-turbo"):
        """Initialize persona directly from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            definition = json.load(f)
        return cls(definition, model_name=model_name)

    def response(self, ctx: Dict[str, Any], prompt_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a persona response given context (ctx).
        Uses the persona's summary instead of full conversation history.

        Args:
            ctx: Context dictionary containing:
                - user_prompt or prompt: The current question/topic
                - phase: Current phase information (optional)
                - shared_context: Any shared artifacts (optional)

        Returns:
            Dict with persona, archetype, and response
        """
        user_prompt = ctx.get("user_prompt") or ctx.get("prompt") or ""
        phase = ctx.get("phase", {})
        shared_context = ctx.get("shared_context", {})
        recent_exchanges = ctx.get("recent_exchanges", [])

        # Format summary for inclusion in prompt
        summary_text = self._format_summary()

        # Format recent discussion
        recent_discussion = self._format_recent_exchanges(recent_exchanges)

        # Build enhanced user prompt with summary and context
        enhanced_prompt = f"""CURRENT TOPIC/QUESTION:
{user_prompt}

{recent_discussion}

YOUR MEETING SUMMARY SO FAR:
{summary_text}

SHARED CONTEXT:
{json.dumps(shared_context, indent=2) if shared_context else 'None'}

CURRENT PHASE:
{json.dumps(phase, indent=2) if phase else 'Not specified'}

Based on the recent discussion, your summary, the shared context, and your role as {self.archetype}, provide your perspective. Build on previous ideas when appropriate, or challenge them if you see issues."""

        # Build messages with persona identity in system prompt
        messages = [
            {
                "role": "system",
                "content": f"You are {self.name}, the {self.archetype}. "
                           f"Purpose: {self.purpose}. Deliverables: {self.deliverables}. "
                           f"Strengths: {self.strengths}. "
                           f"Be mindful of: {self.watchouts}."
            },
            {
                "role": "user",
                "content": enhanced_prompt
            }
        ]

        # Call LLM
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages
        )

        content = completion.choices[0].message.content.strip()
        return {
            "persona": self.name,
            "archetype": self.archetype,
            "response": content
        }

    def _format_summary(self) -> str:
        """Format the persona's summary for inclusion in prompts."""
        if not self.summary.get("objective_facts") and not any(self.summary.get("subjective_notes", {}).values()):
            return "No summary yet - this is the start of the conversation."

        lines = []

        # Objective facts
        obj_facts = self.summary.get("objective_facts", [])
        if obj_facts:
            lines.append("OBJECTIVE FACTS (shared understanding):")
            for fact in obj_facts:
                lines.append(f"  • {fact}")

        # Subjective notes
        subj_notes = self.summary.get("subjective_notes", {})
        if subj_notes:
            lines.append("\nYOUR SUBJECTIVE NOTES:")
            for key, value in subj_notes.items():
                if isinstance(value, list) and value:
                    lines.append(f"  {key.replace('_', ' ').title()}:")
                    for item in value:
                        lines.append(f"    - {item}")
                elif value and not isinstance(value, list):
                    lines.append(f"  {key.replace('_', ' ').title()}: {value}")

        return "\n".join(lines) if lines else "No summary yet."

    def _format_recent_exchanges(self, exchanges: List[Dict[str, Any]]) -> str:
        """
        Format recent exchanges for inclusion in prompts.

        Args:
            exchanges: List of recent exchange dicts with speaker, content, etc.

        Returns:
            Formatted string showing recent discussion
        """
        if not exchanges:
            return "RECENT DISCUSSION:\n(No recent exchanges - this is the start of the phase)"

        lines = ["RECENT DISCUSSION:"]

        # Show last 3-5 exchanges (most recent conversation context)
        recent = exchanges[-5:] if len(exchanges) > 5 else exchanges

        for ex in recent:
            speaker = ex.get("speaker", "Unknown")
            content = ex.get("content", "")

            # Truncate very long responses to ~500 chars
            if len(content) > 500:
                content = content[:500] + "..."

            lines.append(f"\n[{speaker}]:")
            lines.append(content)
            lines.append("")  # Blank line between exchanges

        return "\n".join(lines)

    def update_summary(self, new_exchange: Dict[str, Any]) -> None:
        """
        Update the persona's summary based on a new conversation exchange.

        Uses LLM to extract:
        1. Objective facts that should be added to shared understanding
        2. Subjective observations relevant to this persona's role

        Args:
            new_exchange: Dict containing:
                - speaker: Who spoke
                - content: What was said
                - phase: Current phase info (optional)
        """
        speaker = new_exchange.get("speaker", "Unknown")
        content = new_exchange.get("content", "")
        phase = new_exchange.get("phase", "")

        # Build prompt for summary update
        update_prompt = f"""You are {self.name}, the {self.archetype}.

CURRENT SUMMARY:
{self._format_summary()}

NEW EXCHANGE:
{speaker}: {content}

CURRENT PHASE: {phase}

Update your summary by:
1. Extracting any new OBJECTIVE FACTS (concrete information that everyone should know)
2. Adding your SUBJECTIVE NOTES as {self.archetype} (concerns, priorities, opinions)

Respond ONLY with a JSON object in this format:
{{
  "new_objective_facts": ["fact1", "fact2"],
  "new_subjective_notes": {{
    "key_concerns": ["concern1"],
    "priorities": ["priority1"],
    "opinions": ["opinion1"]
  }}
}}

Only include fields that have new information. Empty lists/objects are fine if nothing new."""

        messages = [
            {
                "role": "system",
                "content": f"You are a summary updater for {self.name}, the {self.archetype}. "
                           f"Extract objective facts and subjective notes from conversations."
            },
            {
                "role": "user",
                "content": update_prompt
            }
        ]

        # Call LLM to update summary
        try:
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )

            response_content = completion.choices[0].message.content.strip()
            updates = json.loads(response_content)

            # Merge new facts (avoid duplicates)
            new_facts = updates.get("new_objective_facts", [])
            for fact in new_facts:
                if fact and fact not in self.summary["objective_facts"]:
                    self.summary["objective_facts"].append(fact)

            # Merge subjective notes
            new_subj = updates.get("new_subjective_notes", {})
            for key, values in new_subj.items():
                if key in self.summary["subjective_notes"]:
                    if isinstance(values, list):
                        for val in values:
                            if val and val not in self.summary["subjective_notes"][key]:
                                self.summary["subjective_notes"][key].append(val)
                    else:
                        self.summary["subjective_notes"][key] = values
                else:
                    self.summary["subjective_notes"][key] = values

        except Exception as e:
            print(f"[!] Failed to update summary for {self.name}: {e}")
            # Continue without updating - non-critical failure
