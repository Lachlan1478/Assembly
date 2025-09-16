# idea_brainstorm.py
# Minimalistic, deterministic idea generator + naive scorer.
import json
from openai import OpenAI
import os

MODEL = "gpt-4.1-mini"

def _score(idea, must_haves):
    pass

def generate_idea(inspiration, number_of_ideas = 1):

    system_content = """You are a startup idea generator. Given some inspiration, you will generate a single, specific, concrete startup idea.
    The idea should be a mobile app, web app, or SaaS product.
    """
    client = OpenAI(api_key = os.getenv("OPENAI_API_KEY", ""))

    print(inspiration)

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


def generate_ideas_and_pick_best(inspiration, number_of_ideas = 2):

    ideas = generate_idea(inspiration = inspiration, number_of_ideas = number_of_ideas)

    print(ideas)

    
    return ideas
