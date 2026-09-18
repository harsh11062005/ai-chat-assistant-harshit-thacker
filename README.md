# 💬 AI Chat Assistant

A chat app that streams replies in real time. It has a conversation history sidebar and a **Tone Toggle** (Professional / Casual / Concise).

**Stack:** Python · FastAPI (backend) · Streamlit (frontend) · OpenAI API · MongoDB

## Features
| Requirement | How it's implemented |
|---|---|
| Chat interface | Scrollable container (`st.container(height=560)`) with separate user 🧑 and AI 🤖 bubbles (`st.chat_message`) |
| Streaming view | The backend streams OpenAI chunks (`stream=True`) through a FastAPI `StreamingResponse`. The frontend shows them **one character at a time** |
| History sidebar | Past threads, newest first. Click one to reopen it |
| API integration | OpenAI Chat Completions (`backend/llm.py`) |
| Persistence | MongoDB. Each conversation stores `{prompt, response, tone, timestamp}` for every exchange |
| Tone Toggle | The chosen tone is sent to the backend, which adds it to the **system instruction** of the OpenAI request |

## Architecture
```
Streamlit UI  ──HTTP──▶  FastAPI routes  ──▶  chat_service  ──▶  llm.py      (OpenAI, streaming)
(presentation only)       (main.py)           (business logic) └─▶ database.py (MongoDB)
```
The frontend only handles display. Validation, tone handling, prompt building and saving all run on the server.

```
backend/
  config.py        settings loaded from .env
  schemas.py       Pydantic models; validates tone and prompt (bad input returns 422)
  database.py      MongoDB CRUD for the `conversations` collection
  llm.py           tone -> system instruction; OpenAI streaming call
  chat_service.py  one chat turn: build messages -> stream reply -> save to MongoDB
  main.py          FastAPI routes
frontend/
  app.py           Streamlit UI
```

## How the Tone Toggle works
1. The user picks a tone in the sidebar. The list of options comes from `GET /api/tones`.
2. The frontend sends `{conversation_id, prompt, tone}` to `POST /api/chat`.
3. `llm.build_messages()` builds the request:
   - `system`: base instruction + `TONE_INSTRUCTIONS[tone]`
   - the last 10 exchanges as context
   - the new prompt
4. The style changes from the very next reply, and each saved message records which tone was used.

## Data model (`conversations` collection)
```json
{
  "_id": "uuid",
  "title": "First 40 chars of the first prompt",
  "created_at": "datetime",
  "updated_at": "datetime",
  "messages": [
    { "prompt": "...", "response": "...", "tone": "casual", "timestamp": "datetime" }
  ]
}
```

## API
| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Liveness check |
| GET | `/api/tones` | Supported tones |
| POST | `/api/conversations` | Create an empty conversation |
| GET | `/api/conversations` | List conversations (sidebar) |
| GET | `/api/conversations/{id}` | Full conversation with messages |
| POST | `/api/chat` | Stream the AI reply as `text/plain`; the reply is saved when it finishes |

Interactive docs are at http://localhost:8000/docs.

## Setup & run
Prerequisites: Python 3.10+, MongoDB running on `localhost:27017`, and an OpenAI API key.

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env          # then set OPENAI_API_KEY in .env
```

Terminal 1 (backend):
```bash
.venv/bin/uvicorn backend.main:app --reload
```

Terminal 2 (frontend):
```bash
.venv/bin/streamlit run frontend/app.py
```
Open http://localhost:8501.
