# idea_brainstorm.py
# Minimalistic, deterministic idea generator + naive scorer.
import json
from openai import OpenAI
import os

MODEL = "gpt-4.1-mini"

def _score(idea, must_haves):
    pass


from typing import List, Dict, Any, Callable, Optional

# Persona type alias: takes (context: Dict) → returns an output dict
PersonaFn = Callable[[Dict[str, Any]], Dict[str, Any]]

def meeting_facilitator(
    personas: Dict[str, PersonaFn],
    phases: List[Dict[str, Any]],
    shared_context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    personas: mapping persona_id → function that takes context & returns output
    phases: list of dicts like:
        { "phase_id": str,
          "lead_role": Optional[str],   # role to drive this phase
          "allowed_roles": List[str],   # roles allowed to speak/respond
          "prompt_key": str             # key in shared_context or derived for persona prompt
        }
    shared_context: mutable dict passed to all persona calls and updated over time

    Returns: final shared_context (will include logs, results, decision)
    """

    logs = []
    for phase in phases:
        lead = phase.get("lead_role")
        allowed = phase.get("allowed_roles", list(personas.keys()))
        prompt_key = phase.get("prompt_key")

        # 1. Lead speaks first (if exists)
        if lead and lead in personas:
            persona_fn = personas[lead]
            ctx = { **shared_context, "phase": phase }
            lead_output = persona_fn(ctx)
            logs.append({ "phase": phase["phase_id"], "role": lead, "output": lead_output })
            # Merge or store output
            shared_context.setdefault("history", []).append(lead_output)

        # 2. Others respond
        for role, persona_fn in personas.items():
            if role == lead:
                continue
            if role not in allowed:
                continue
            ctx = { **shared_context, "phase": phase }
            resp = persona_fn(ctx)
            logs.append({ "phase": phase["phase_id"], "role": role, "output": resp })
            shared_context.setdefault("history", []).append(resp)

        # 3. Summarize / mediator summary (optional)
        # You might call a small summarizer persona or aggregator here:
        # summary = summarizer(shared_context, phase)
        # logs.append({ "phase": phase["phase_id"], "role": "facilitator", "output": summary })
        # shared_context["last_summary"] = summary

    # After all phases, optionally call a decision-maker
    if "decision" in personas:
        decision = personas["decision"](shared_context)
        logs.append({ "phase": "decision", "role": "decision", "output": decision })
        shared_context["decision"] = decision

    shared_context["logs"] = logs
    return shared_context



# Single LLM call to generate ideas. Old Methodology. To be improved.
def single_llm_idea_generator(inspiration, number_of_ideas = 1):

    system_content = """You are a startup idea generator. Given some inspiration, you will generate a single, specific, concrete startup idea.
        The idea should be a mobile app, web app, or SaaS product.
    """
    client = OpenAI(api_key = os.getenv("OPENAI_API_KEY", ""))

    message_content = f"""
        Given the following inspiration, generate {number_of_ideas} different startup idea(s).
        Each item must include: 
            - title 
            - description 
            - target_users 
            - primary_outcome 
            - must_haves 
            - constraints 
            - non_goals 
        and be in valid JSON format as an array of objects.
        Ensure the ideas are meaningfully different.
    """

    response   = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[  # the conversation history as a list of role/content dicts
            {"role": "system", "content": system_content},                                  # Sets behavior, style, or persona of the assistant.
            {"role": "user", "content": message_content},                                   # Anything the end-user says (questions, instructions).
            {"role": "user", "content": inspiration},                                       # Anything the end-user says (questions, instructions).
            # {"role": "assistant", "content": "Short selling is when..."},                 # Model’s previous replies (if you’re keeping conversation history).
            # {"type": "image_url", "image_url": {"url": "https://example.com/chart.png"}}. # Can have multiple images
        ],
        response_format={"type": "json_object"},
        temperature = 1,
        # max_tokens,
        frequency_penalty = 0.0, # -2.0 to 2.0, default 0.0 - penalizes repeated phrases
        presence_penalty = 0.0, # -2.0 to 2.0, default 0.0 - penalizes repeated topics
        n = 1, # number of chat completion choices to generate
        # response_format,
    )

    raw_response = response.choices[0].message.content

    business_ideas = json.loads(raw_response)

    return business_ideas


def generate_idea(inspiration, number_of_ideas = 1):

    print(inspiration)

    business_ideas = single_llm_idea_generator(inspiration = inspiration, number_of_ideas = number_of_ideas)

    return business_ideas


def generate_ideas_and_pick_best(inspiration, number_of_ideas = 2):

    ideas = generate_idea(inspiration = inspiration, number_of_ideas = number_of_ideas)

    print(ideas)

    
    return ideas
