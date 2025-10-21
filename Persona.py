# persona.py
import json
from typing import Dict, Any, Optional
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

    @classmethod
    def from_file(cls, path: str, model_name: str = "gpt-3.5-turbo"):
        """Initialize persona directly from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            definition = json.load(f)
        return cls(definition, model_name=model_name)

    def response(self, ctx: Dict[str, Any], prompt_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate a persona response given context (ctx).
        You can add custom prompt building here.
        """
        user_prompt = ctx.get("user_prompt") or ctx.get("prompt") or str(ctx)

        # Build a composite system + user message structure
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
                "content": user_prompt
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
