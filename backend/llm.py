"""
llm.py - Everything that talks to the OpenAI API.

Two responsibilities:
  1. Build the message list for the model, including the TONE as a system
     instruction (this is the "Tone Toggle" / Vibe Check requirement).
  2. Call OpenAI with streaming enabled and yield the reply piece by piece.
"""

from typing import Iterator, List

from openai import OpenAI

from backend.config import MAX_HISTORY_TURNS, OPENAI_API_KEY, OPENAI_MODEL

# One OpenAI client for the whole app (reads the key from .env via config).
_client = OpenAI(api_key=OPENAI_API_KEY)

BASE_INSTRUCTION = "You are a helpful AI chat assistant."

# The Tone Toggle: each tone maps to an extra system instruction.
# Changing the tone changes this text, which changes the style of the next reply.
TONE_INSTRUCTIONS = {
    "professional": (
        "Respond in a professional, formal tone. Be clear, precise and well-structured, "
        "like a knowledgeable consultant."
    ),
    "casual": (
        "Respond in a casual, friendly tone, like chatting with a friend. "
        "Keep it relaxed and conversational; light humour and emojis are fine."
    ),
    "concise": (
        "Respond as concisely as possible. Use the fewest words needed - "
        "short sentences or bullet points, no filler."
    ),
}


def build_messages(tone: str, history: List[dict], prompt: str) -> List[dict]:
    """
    Build the list of messages sent to OpenAI.

    Order matters:
      1. system  -> base instruction + the selected tone modifier
      2. history -> previous user/assistant turns (last MAX_HISTORY_TURNS only) for context
      3. user    -> the new prompt

    Args:
        tone: One of "professional", "casual", "concise" (already validated).
        history: Saved messages of this conversation ({"prompt", "response", ...}).
        prompt: The new user message.

    Returns:
        A list of {"role": ..., "content": ...} dicts in OpenAI chat format.
    """
    system_prompt = f"{BASE_INSTRUCTION} {TONE_INSTRUCTIONS[tone]}"
    messages = [{"role": "system", "content": system_prompt}]

    # Replay recent history so the model remembers the conversation.
    for past in history[-MAX_HISTORY_TURNS:]:
        messages.append({"role": "user", "content": past["prompt"]})
        messages.append({"role": "assistant", "content": past["response"]})

    messages.append({"role": "user", "content": prompt})
    return messages


def stream_completion(messages: List[dict]) -> Iterator[str]:
    """
    Call OpenAI with stream=True and yield text chunks as soon as they arrive.

    Args:
        messages: Output of build_messages().

    Yields:
        Small pieces of the AI reply (a few characters/words at a time).
    """
    stream = _client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=messages,
        stream=True,
    )
    for chunk in stream:
        # Each chunk carries a small "delta" of new text (can be None/empty).
        if chunk.choices and chunk.choices[0].delta.content:
            yield chunk.choices[0].delta.content
