"""
schemas.py - Request/response shapes for the API (Pydantic models).

Pydantic validates every incoming request automatically. If the client sends
an unknown tone or an empty prompt, FastAPI rejects it with HTTP 422 before
any of our code runs, so validation stays on the server.
"""

from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel, Field, field_validator

from backend.config import MAX_PROMPT_LENGTH

# The only tones the backend accepts. Literal = "must be exactly one of these".
Tone = Literal["professional", "casual", "concise"]


class ChatRequest(BaseModel):
    """Body of POST /api/chat: which thread, what the user typed, and the chosen tone."""

    conversation_id: str
    prompt: str = Field(..., max_length=MAX_PROMPT_LENGTH)
    tone: Tone = "professional"

    @field_validator("prompt")
    @classmethod
    def prompt_not_blank(cls, value: str) -> str:
        """Strip surrounding whitespace and reject prompts that are empty after stripping."""
        value = value.strip()
        if not value:
            raise ValueError("Prompt cannot be empty")
        return value


class Message(BaseModel):
    """One exchange in a conversation: user prompt, AI response, tone used, and when it happened."""

    prompt: str
    response: str
    tone: Tone
    timestamp: datetime


class ConversationSummary(BaseModel):
    """Lightweight conversation info for the history sidebar (no messages)."""

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class Conversation(ConversationSummary):
    """A full conversation thread including all of its messages."""

    messages: List[Message] = []
