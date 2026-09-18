"""
main.py - FastAPI application and HTTP routes.

Routes are intentionally thin: they validate input (via Pydantic schemas),
call the service/database layer, and return the result.

Run with:  uvicorn backend.main:app --reload
Docs at:   http://localhost:8000/docs
"""

from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend import chat_service, database
from backend.llm import TONE_INSTRUCTIONS
from backend.schemas import ChatRequest, Conversation, ConversationSummary

app = FastAPI(title="AI Chat Assistant API")

# Allow the frontend (running on another port) to call this API during local development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    """Simple liveness check."""
    return {"status": "ok"}


@app.get("/api/tones")
def list_tones() -> List[str]:
    """Return the supported tones, so the UI never hardcodes them."""
    return list(TONE_INSTRUCTIONS.keys())


@app.post("/api/conversations", response_model=Conversation)
def create_conversation() -> dict:
    """Start a new, empty conversation thread."""
    return database.create_conversation()


@app.get("/api/conversations", response_model=List[ConversationSummary])
def list_conversations() -> List[dict]:
    """List past conversation threads for the history sidebar (newest first)."""
    return database.list_conversations()


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
def get_conversation(conversation_id: str) -> dict:
    """Return one conversation with all its messages (404 if it doesn't exist)."""
    return chat_service.get_conversation_or_404(conversation_id)


@app.post("/api/chat")
def chat(request: ChatRequest) -> StreamingResponse:
    """
    Send a prompt and stream back the AI reply as plain text.

    The response body arrives in small chunks while the model is generating;
    the exchange is saved to MongoDB once the reply is complete.
    """
    # Check the conversation exists first, so we can still return a proper 404.
    conversation = chat_service.get_conversation_or_404(request.conversation_id)
    return StreamingResponse(
        chat_service.stream_chat(conversation, request),
        media_type="text/plain; charset=utf-8",
    )
