"""
app.py - Streamlit frontend for the AI Chat Assistant.

Presentation only: this file draws the UI and calls the FastAPI backend.
All business logic (tone -> system instruction, validation, saving to
MongoDB) lives on the server.

Layout:
  - Sidebar: "New chat" button, Tone Toggle, history of past threads.
  - Main:    scrollable chat view with user/AI bubbles + input box.

Run with:  streamlit run frontend/app.py
"""

import os
import time

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

TYPING_DELAY_SECONDS = 0.005  # delay per character -> typewriter effect
ERROR_MARKER = "⚠️"  # prefix used for error text shown inside the chat

st.set_page_config(page_title="AI Chat Assistant", page_icon="💬")

# st.session_state survives Streamlit's re-runs (the script re-runs on every click).
# We only need to remember which conversation is open.
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None


# ---------------------------------------------------------------- API helpers


def api_get(path: str):
    """GET a backend endpoint and return the parsed JSON (stops the app if the backend is down)."""
    try:
        response = requests.get(f"{BACKEND_URL}{path}", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        st.error(f"Could not reach the backend at {BACKEND_URL}: {exc}")
        st.stop()


def api_post(path: str):
    """POST to a backend endpoint (no body) and return the parsed JSON."""
    response = requests.post(f"{BACKEND_URL}{path}", timeout=10)
    response.raise_for_status()
    return response.json()


def stream_reply(conversation_id: str, prompt: str, tone: str):
    """
    Send the prompt to /api/chat and yield the reply ONE CHARACTER at a time.

    The backend streams chunks from OpenAI; we split each chunk into single
    characters with a tiny delay so the text "types itself" in the bubble.
    """
    payload = {"conversation_id": conversation_id, "prompt": prompt, "tone": tone}
    try:
        with requests.post(f"{BACKEND_URL}/api/chat", json=payload, stream=True, timeout=120) as response:
            if response.status_code != 200:
                yield f"{ERROR_MARKER} Request rejected ({response.status_code}): {response.text}"
                return
            for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
                for char in chunk:
                    yield char
                    time.sleep(TYPING_DELAY_SECONDS)
    except requests.RequestException as exc:
        yield f"{ERROR_MARKER} Could not reach the backend: {exc}"


# ------------------------------------------------------------------ UI parts


def render_sidebar() -> str:
    """
    Draw the sidebar: New chat button, Tone Toggle and conversation history.

    Returns:
        The tone currently selected by the user.
    """
    with st.sidebar:
        if st.button("➕ New chat", use_container_width=True):
            st.session_state.conversation_id = None
            st.rerun()

        # Tone Toggle - options come from the backend, not hardcoded here.
        tone = st.radio("Tone", api_get("/api/tones"), format_func=str.title, horizontal=True)

        st.subheader("History")
        conversations = api_get("/api/conversations")
        if not conversations:
            st.caption("No conversations yet.")
        for conv in conversations:
            is_active = conv["id"] == st.session_state.conversation_id
            if st.button(
                conv["title"],
                key=conv["id"],
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                # Clicking a past thread opens it in the main chat view.
                st.session_state.conversation_id = conv["id"]
                st.rerun()
    return tone


def render_chat(chat_box) -> None:
    """Draw all saved messages of the open conversation as user/AI chat bubbles."""
    if st.session_state.conversation_id is None:
        chat_box.info("Start a new conversation by typing a message below.")
        return

    conversation = api_get(f"/api/conversations/{st.session_state.conversation_id}")
    for message in conversation["messages"]:
        with chat_box.chat_message("user", avatar="🧑"):
            st.markdown(message["prompt"])
        with chat_box.chat_message("assistant", avatar="🤖"):
            st.markdown(message["response"])
            st.caption(f"Tone: {message['tone'].title()}")


# ---------------------------------------------------------------- Main page

st.title("💬 AI Chat Assistant")

tone = render_sidebar()

# Fixed-height container = scrollable conversation view.
chat_box = st.container(height=560)
render_chat(chat_box)

prompt = st.chat_input("Type your message...")
if prompt:
    # First message of a new chat: ask the backend to create the thread.
    if st.session_state.conversation_id is None:
        st.session_state.conversation_id = api_post("/api/conversations")["id"]

    with chat_box.chat_message("user", avatar="🧑"):
        st.markdown(prompt)
    with chat_box.chat_message("assistant", avatar="🤖"):
        # write_stream renders the generator's output live and returns the full text.
        reply = st.write_stream(stream_reply(st.session_state.conversation_id, prompt, tone))

    # Re-run to refresh the sidebar (new title / ordering). Skip it on errors
    # so the user can still read the error message.
    if ERROR_MARKER not in reply:
        st.rerun()
