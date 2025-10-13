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
        self.name = definition.get("name", "Unknown Persona")
        self.role = definition.get("role", "")
        self.purpose = definition.get("purpose", "")
        self.delivers = definition.get("delivers", "")
        self.watchouts = definition.get("watchouts", "")
        self.system_prompt = definition.get("system_prompt", "")
        self.temperature = 1.0  # Default temperature
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
                "content": f"You are {self.name}, the {self.role}. "
                           f"Purpose: {self.purpose}. Deliverables: {self.delivers}. "
                           f"Be mindful of: {self.watchouts}. {self.system_prompt}"
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ]

        # Call LLM
        completion = self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=self.temperature
        )

        content = completion.choices[0].message.content.strip()
        return {
            "persona": self.name,
            "role": self.role,
            "response": content
        }
