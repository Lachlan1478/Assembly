# spec_generation.py
# Turns the best idea into a minimal prompt/spec for Base44.

from openai import OpenAI

import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4.1-mini"

def generate_spec(idea):

    system_content = """
        You are an expert at distilling product ideas into clear, concise initial prompts for Base44, a no-code app builder.
        Your task is to take a detailed startup idea and convert it into a minimal yet comprehensive prompt that captures the essence of the app to be built.
        The prompt should focus on the core purpose, key features, target users, and essential data entities, while being as brief and clear as possible.

        You are creative, feel free to drift and invent as needed. Search for ideas that have not been done before.
    
        A good example of an initial prompt for Base44 should be clear, concise, and focus on the "what" and "why" of your app, rather than getting too bogged down in the "how." You should provide enough detail to convey the core idea, purpose, and essential functionalities, but leave room for Base44 to make design and implementation choices.

        Here's a breakdown of what to include and how much detail to go into:

        What Makes a Good Initial Prompt:
        Clear App Name/Concept: A brief, descriptive title or phrase.
        Core Purpose/Problem Solved: What is the main goal of this app? What pain point does it address?
        Target Users: Who will be using this app? (e.g., small business owners, hobbyists, families, students). This helps in tailoring the UI/UX.
        Key Features (MVP - Minimum Viable Product): List the absolute essential functionalities. Don't try to list every single potential feature; focus on what makes the app work for its core purpose.
        Data Needed (Entities): What kind of information will the app need to store or manage? Think about the "things" (entities) your app revolves around.
        Desired Look & Feel (Optional but Recommended): Describe the aesthetic you're aiming for (e.g., "minimalist," "vibrant," "professional," "dark mode"). You can also mention specific color preferences or general "vibe."
        Any Known Integrations (Optional): If you know it needs to interact with an external service (like sending emails, generating images, etc.), mention it.
        How Much Detail?
        Conciseness is key: Get straight to the point. Long, rambling descriptions can be harder to parse.
        Prioritize: Focus on the core functionality. Don't worry about every edge case or advanced feature in the first prompt. You can always iterate and add more later.
        Define "What": Describe what the user should be able to do, and what information needs to be displayed or managed.
        Avoid "How" (initially): Unless you have a very specific technical requirement, try not to dictate how certain features should be implemented (e.g., "use a specific database table named X" or "put this button exactly here"). Let Base44 handle the optimal implementation details based on your needs.
        Example of a Good Prompt:
        "Create a simple Recipe Organizer app."

        Purpose: "This app should help users store, find, and manage their personal recipes easily, focusing on home cooks who want to digitize their handwritten recipes."

        Target Users: "Casual home cooks who prefer a straightforward, uncluttered interface."

        Key Features:

        "Users can add new recipes, including a title, ingredients list, and instructions."
        "Recipes should be searchable by title or ingredients."
        "Users should be able to view a single recipe clearly formatted."
        "Users can mark recipes as 'favorites'."
        Data Needed: "I imagine an entity for Recipe which would need fields like title, ingredients (a list of strings), instructions (a multi-line text field), and isFavorite (a boolean)."

        Desired Look & Feel: "I'd like a clean, modern, and inviting design. Think bright, airy, and easy to read, with perhaps some subtle warm colors like light greens or yellows. It should feel organized but not sterile."

        Integrations: "No specific integrations are needed for the initial version."

        This type of prompt gives Base44 a solid foundation to start building, outlining the core requirements while allowing for efficient design choices.
    """
    client = OpenAI(api_key = OPENAI_API_KEY)

    

    message_content = f"""
        Given the following idea, generate an initial spec: {idea}
    """

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[  # the conversation history as a list of role/content dicts
            {"role": "system", "content": system_content},                                  # Sets behavior, style, or persona of the assistant.
            {"role": "user", "content": message_content},                                   # Anything the end-user says (questions, instructions).
            # {"role": "assistant", "content": "Short selling is when..."},                 # Model’s previous replies (if you’re keeping conversation history).
            # {"type": "image_url", "image_url": {"url": "https://example.com/chart.png"}}. # Can have multiple images
        ],
        temperature = 1,
        # max_tokens,
        frequency_penalty = 0.0, # -2.0 to 2.0, default 0.0 - penalizes repeated phrases
        presence_penalty = 0.0, # -2.0 to 2.0, default 0.0 - penalizes repeated topics
        n = 1, # number of chat completion choices to generate
        # response_format,
    )

    initial_spec = response.choices[0].message.content

    return initial_spec

def make_initial_prompt(best_idea):
    prompt = generate_spec(best_idea)

    return prompt