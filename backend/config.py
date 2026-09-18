"""
config.py - Central place for all settings.

Values are read from the `.env` file (via python-dotenv) so secrets like the
OpenAI API key never live in the source code. Every other backend module
imports its settings from here.
"""

import os

from dotenv import load_dotenv

# Load key=value pairs from .env into environment variables.
load_dotenv()

# --- OpenAI ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# --- MongoDB ---
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
MONGODB_DB = os.getenv("MONGODB_DB", "ai_chat_assistant")

# --- Chat behaviour ---
# How many previous prompt/response pairs we send back to the model as context.
# Keeps token usage (and cost) bounded for long conversations.
MAX_HISTORY_TURNS = 10

# Maximum characters allowed in a single user prompt (validated server-side).
MAX_PROMPT_LENGTH = 4000
