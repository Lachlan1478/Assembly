# idea_brainstorm.py
# Minimalistic, deterministic idea generator + naive scorer.
import json
from openai import OpenAI
import os
from persona import Persona

#MODEL = "gpt-4.1-mini"
MODEL = "gpt-5-mini"

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

        print(f"\n=== Starting Phase: {phase['phase_id']} ===")
        
        # 1. Lead speaks first (if exists)
        if lead and lead in personas:
            print(f"\n👤 Lead {lead} is speaking...")
            persona_fn = personas[lead]
            ctx = { **shared_context, "phase": phase }
            lead_output = persona_fn(ctx)
            log_entry = { "phase": phase["phase_id"], "role": lead, "output": lead_output }
            logs.append(log_entry)
            print(f"Output from {lead}:")
            print(json.dumps(log_entry["output"], indent=2))
            # Merge or store output
            shared_context.setdefault("history", []).append(lead_output)

        # 2. Others respond
        print("\n👥 Other participants responding...")
        for role, persona_fn in personas.items():
            if role == lead:
                continue
            if role not in allowed:
                continue
            ctx = { **shared_context, "phase": phase }
            print(f"\nℹ️ {role} is responding...")
            resp = persona_fn(ctx)
            log_entry = { "phase": phase["phase_id"], "role": role, "output": resp }
            logs.append(log_entry)
            print(f"Output from {role}:")
            print(json.dumps(log_entry["output"], indent=2))
            shared_context.setdefault("history", []).append(resp)

        # 3. Summarize / mediator summary (optional)
        # You might call a small summarizer persona or aggregator here:
        # summary = summarizer(shared_context, phase)
        # logs.append({ "phase": phase["phase_id"], "role": "facilitator", "output": summary })
        # shared_context["last_summary"] = summary

    # After all phases, optionally call a decision-maker
    if "decision" in personas:
        print("\n🎯 Making final decision...")
        decision = personas["decision"](shared_context)
        log_entry = { "phase": "decision", "role": "decision", "output": decision }
        logs.append(log_entry)
        print("Final Decision:")
        print(json.dumps(log_entry["output"], indent=2))
        shared_context["decision"] = decision

    shared_context["logs"] = logs
    return shared_context

# Multi-persona LLM call to generate ideas. New Methodology.
def multiple_llm_idea_generator(inspiration, number_of_ideas = 1):

    founder = Persona.from_file("personas/founder.json", model_name=MODEL)
    designer = Persona.from_file("personas/designer.json", model_name=MODEL)
    researcher = Persona.from_file("personas/researcher.json", model_name=MODEL)
    tech_lead = Persona.from_file("personas/tech_lead.json", model_name=MODEL)
    cfo = Persona.from_file("personas/cfo.json", model_name=MODEL)
    contrarian = Persona.from_file("personas/contrarian.json", model_name=MODEL)

    personas = {
        "founder": founder.response,
        "designer": designer.response,
        "researcher": researcher.response,
        "tech_lead": tech_lead.response,
        "cfo": cfo.response,
        "contrarian": contrarian.response
    }    

    phases = [
        { "phase_id": "ideation", "lead_role": "founder", "allowed_roles": ["founder", "designer", "researcher", "tech_lead", "cfo", "contrarian"], "prompt_key": "user_prompt" },
        { "phase_id": "design", "lead_role": "designer", "allowed_roles": ["designer", "tech_lead", "researcher"], "prompt_key": "user_prompt" },
        { "phase_id": "research", "lead_role": "researcher", "allowed_roles": ["researcher", "contrarian"], "prompt_key": "user_prompt" },
        { "phase_id": "feasibility", "lead_role": "tech_lead", "allowed_roles": ["tech_lead", "designer", "cfo"], "prompt_key": "user_prompt" },
        { "phase_id": "financials", "lead_role": "cfo", "allowed_roles": ["cfo", "contrarian"], "prompt_key": "user_prompt" },
        { "phase_id": "critique", "lead_role": "contrarian", "allowed_roles": ["contrarian", "founder"], "prompt_key": "user_prompt" },
        { "phase_id": "decision", "lead_role": "founder", "allowed_roles": ["founder"], "prompt_key": "user_prompt" }
    ]

    intial_prompt = f"""


        Inspiration: {inspiration}

    """

    prompt = f"""
        Given the following inspiration, generate {number_of_ideas} different startup idea(s).
        Ensure the ideas are meaningfully different.
        
        Inspiration: {inspiration}
    """

    shared_context = {
        "user_prompt": prompt,
        "inspiration": inspiration,
        "number_of_ideas": number_of_ideas,
    }

    final_context = meeting_facilitator(personas, phases, shared_context)
    logs = final_context.get("logs", [])
    with open("meeting_logs.txt", "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2)
    raw_ideas = final_context.get("decision", {}).get("response", "[]")

    business_ideas = json.loads(raw_ideas)
    
    return business_ideas


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

    new_ideas = multiple_llm_idea_generator(inspiration = inspiration, number_of_ideas = number_of_ideas)
    print(new_ideas)
    return new_ideas
