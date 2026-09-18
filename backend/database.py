"""
database.py - MongoDB persistence layer.

We use ONE collection, `conversations`, with one document per chat thread:

    {
        "_id": "<uuid string>",
        "title": "First 40 chars of the first prompt",
        "created_at": <datetime>,
        "updated_at": <datetime>,
        "messages": [
            {"prompt": "...", "response": "...", "tone": "casual", "timestamp": <datetime>}
        ]
    }

Messages are embedded inside the conversation because they are always read
together with it. IDs are UUID strings, so the API never has to convert
MongoDB ObjectIds.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from pymongo import DESCENDING, MongoClient

from backend.config import MONGODB_DB, MONGODB_URI

DEFAULT_TITLE = "New chat"
TITLE_LENGTH = 40

# One client for the whole app. PyMongo keeps a connection pool internally.
_client = MongoClient(MONGODB_URI)
_collection = _client[MONGODB_DB]["conversations"]


def _now() -> datetime:
    """Return the current time in UTC (always store timezone-aware timestamps)."""
    return datetime.now(timezone.utc)


def _to_api(doc: dict) -> dict:
    """Rename MongoDB's `_id` field to `id` so the API response is clean."""
    doc["id"] = doc.pop("_id")
    return doc


def create_conversation() -> dict:
    """
    Create a new, empty conversation thread.

    Returns:
        The new conversation as a dict (id, title, timestamps, empty messages).
    """
    now = _now()
    doc = {
        "_id": str(uuid.uuid4()),
        "title": DEFAULT_TITLE,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }
    _collection.insert_one(doc)
    return _to_api(doc)


def list_conversations() -> List[dict]:
    """
    List all conversations for the history sidebar, most recently used first.

    Messages are excluded (projection) to keep the response small.
    """
    cursor = _collection.find({}, {"messages": 0}).sort("updated_at", DESCENDING)
    return [_to_api(doc) for doc in cursor]


def get_conversation(conversation_id: str) -> Optional[dict]:
    """
    Fetch one conversation with all of its messages.

    Returns:
        The conversation dict, or None if no conversation has that id.
    """
    doc = _collection.find_one({"_id": conversation_id})
    return _to_api(doc) if doc else None


def add_message(conversation_id: str, prompt: str, response: str, tone: str) -> None:
    """
    Save one completed exchange (user prompt + AI response) to a conversation.

    Also bumps `updated_at` (so the thread moves to the top of the sidebar)
    and, on the first message, sets the thread title from the prompt.
    """
    now = _now()
    message = {"prompt": prompt, "response": response, "tone": tone, "timestamp": now}

    # $push appends to the messages array; $set updates the timestamp.
    _collection.update_one(
        {"_id": conversation_id},
        {"$push": {"messages": message}, "$set": {"updated_at": now}},
    )

    # Give the thread a readable title the first time the user says something.
    title = prompt[:TITLE_LENGTH] + ("..." if len(prompt) > TITLE_LENGTH else "")
    _collection.update_one(
        {"_id": conversation_id, "title": DEFAULT_TITLE},
        {"$set": {"title": title}},
    )
