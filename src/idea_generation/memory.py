# memory.py
# Shared memory update logic for structured memory system

import logging
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


SHARED_MEMORY_UPDATE_PROMPT = """
You are maintaining a shared memory for a group brainstorm.

CURRENT SHARED MEMORY:
{current_memory}

NEW EXCHANGE:
{speaker}: {content}

Update the shared memory. Keep it under 200 words. Capture:
- Consensus points (ideas multiple people agreed on)
- Dead ends (ideas proposed then dismissed — critical to prevent repetition)
- Key constraints or facts established

Return only the updated shared memory text. No preamble.
"""


async def update_shared_memory_async(
    current_memory: str,
    new_exchange: dict,
    model: str = "gpt-5.1"
) -> str:
    """
    Async version of update_shared_memory for parallel execution.

    Args:
        current_memory: Current shared memory text
        new_exchange: Dict with 'speaker' and 'content' keys
        model: LLM model to use

    Returns:
        Updated shared memory string
    """
    async_client = AsyncOpenAI()

    speaker = new_exchange.get("speaker", "Unknown")
    content = new_exchange.get("content", "")

    prompt = SHARED_MEMORY_UPDATE_PROMPT.format(
        current_memory=current_memory or "(empty — first turn)",
        speaker=speaker,
        content=content
    )

    try:
        completion = await async_client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a concise memory keeper for a group brainstorm. Update shared memory faithfully."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Failed to async update shared memory: %s", e)
        return current_memory


def format_shared_memory_block(shared_memory: str) -> str:
    """
    Format shared memory for injection into a persona prompt.

    Args:
        shared_memory: Current shared memory text

    Returns:
        Formatted block string
    """
    return f"=== SHARED MEMORY (what the group has established) ===\n{shared_memory}\n"
