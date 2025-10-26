"""
Utility functions for the Assembly application.
"""

import json
from pathlib import Path
from typing import Dict
from persona import Persona


def load_all_personas(directory: str = "personas", model_name: str = "gpt-4o-mini") -> Dict[str, Persona]:
    """
    Dynamically load all persona definitions from the specified directory.

    Args:
        directory: Path to directory containing persona JSON files
        model_name: LLM model to use for all personas

    Returns:
        Dictionary mapping persona names to Persona instances
        Example: {"founder": Persona(...), "designer": Persona(...)}
    """
    personas = {}
    personas_path = Path(directory)

    if not personas_path.exists():
        raise FileNotFoundError(f"Personas directory not found: {directory}")

    # Find all .json files in the directory
    json_files = list(personas_path.glob("*.json"))

    if not json_files:
        raise ValueError(f"No persona JSON files found in {directory}")

    # Load each persona
    for json_file in json_files:
        try:
            persona = Persona.from_file(str(json_file), model_name=model_name)
            # Use the persona's name (lowercase) as the key
            # Normalize by replacing em-dashes, hyphens, and spaces with underscores
            persona_key = (persona.name.lower()
                          .replace("—", "_")  # Em-dash
                          .replace("–", "_")  # En-dash
                          .replace("-", "_")  # Hyphen
                          .replace(" ", "_")  # Space
                          .replace("/", "_")) # Slash
            # Clean up multiple consecutive underscores
            while "__" in persona_key:
                persona_key = persona_key.replace("__", "_")
            personas[persona_key] = persona
            print(f"[OK] Loaded persona: {persona.name} ({persona.archetype})")
        except Exception as e:
            print(f"[!] Failed to load {json_file.name}: {e}")
            continue

    if not personas:
        raise ValueError(f"Failed to load any personas from {directory}")

    print(f"\n[i] Total personas loaded: {len(personas)}")
    return personas


def format_summary_for_prompt(summary: Dict) -> str:
    """
    Convert a persona's summary dictionary into readable text for LLM prompts.

    Args:
        summary: Dict with "objective_facts" (list) and "subjective_notes" (dict)

    Returns:
        Formatted string suitable for inclusion in prompts
    """
    if not summary:
        return "No summary yet - this is the start of the conversation."

    lines = []

    # Objective facts section
    obj_facts = summary.get("objective_facts", [])
    if obj_facts:
        lines.append("OBJECTIVE FACTS (shared understanding):")
        for fact in obj_facts:
            lines.append(f"  • {fact}")

    # Subjective notes section
    subj_notes = summary.get("subjective_notes", {})
    if subj_notes:
        lines.append("\nYOUR SUBJECTIVE NOTES:")
        for key, value in subj_notes.items():
            if isinstance(value, list):
                lines.append(f"  {key.replace('_', ' ').title()}:")
                for item in value:
                    lines.append(f"    - {item}")
            else:
                lines.append(f"  {key.replace('_', ' ').title()}: {value}")

    return "\n".join(lines) if lines else "No summary yet."
