"""
chat_service.py - Business logic for a chat turn.

Sits between the API routes (main.py) and the lower layers:
  - database.py  (load history / save the finished exchange)
  - llm.py       (build tone-aware messages / stream the AI reply)

Keeping this logic here means the routes stay thin and the frontend
only has to display what the server sends.
"""

from typing import Iterator

from fastapi import HTTPException

from backend import database, llm
from backend.schemas import ChatRequest


def get_conversation_or_404(conversation_id: str) -> dict:
    """
    Load a conversation, or raise HTTP 404 if it doesn't exist.

    Called BEFORE streaming starts, because once a streaming response has
    begun we can no longer change its HTTP status code.
    """
    conversation = database.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


def stream_chat(conversation: dict, request: ChatRequest) -> Iterator[str]:
    """
    Stream the AI reply for one user prompt, then save the exchange to MongoDB.

    Steps:
      1. Build messages = tone system instruction + recent history + new prompt.
      2. Forward each chunk from OpenAI to the client as soon as it arrives.
      3. After the stream ends, save {prompt, response, tone, timestamp}.

    Args:
        conversation: The conversation document (with its past messages).
        request: The validated chat request (conversation_id, prompt, tone).

    Yields:
        Pieces of the AI reply text.
    """
    messages = llm.build_messages(request.tone, conversation["messages"], request.prompt)

    reply_parts = []  # collect the full reply so we can store it at the end
    try:
        for chunk in llm.stream_completion(messages):
            reply_parts.append(chunk)
            yield chunk
    except Exception as exc:  # e.g. invalid API key, rate limit, network error
        # Show a readable error in the chat instead of crashing; don't save a broken reply.
        yield f"\n\n⚠️ AI service error: {exc}"
        return

    # Only reached when the stream completed successfully.
    database.add_message(
        conversation_id=request.conversation_id,
        prompt=request.prompt,
        response="".join(reply_parts),
        tone=request.tone,
    )
