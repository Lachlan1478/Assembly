import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables before importing Persona
load_dotenv()

# Add the parent directory to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from persona import Persona

persona_json_path = "personas/test.json"

# Create persona from JSON file
founder = Persona.from_file(persona_json_path)

# Context example
ctx = {
    "user_prompt": "Generate 3 SaaS ideas for AI in personal finance.",
    "phase": "ideation",
    "desired_outcome": "Identify bold MVPs"
}

# Get founder's response
founders_response = founder.response(ctx)
print(founders_response["response"])
