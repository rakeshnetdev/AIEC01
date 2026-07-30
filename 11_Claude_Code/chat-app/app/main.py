"""FastAPI app: static chat UI + the /api/chat seam."""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .agent import generate_reply, reset_conversation, stream_reply
from .config import ALLOWED_TOOLS, MAX_TURNS, PROJECT_ROOT, TARGET_REPO

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

STATIC_DIR = PROJECT_ROOT / "static"

app = FastAPI(title="Codebase Concierge")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    conversation_id: str = Field(default="default", min_length=1, max_length=100)


class ChatResponse(BaseModel):
    reply: str
    conversation_id: str


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/config")
async def config() -> dict[str, object]:
    """What the UI shows in its header — repo under inspection and the guardrails."""
    return {
        "target_repo": str(TARGET_REPO),
        "repo_name": TARGET_REPO.name,
        "allowed_tools": ALLOWED_TOOLS,
        "max_turns": MAX_TURNS,
    }


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Blocking path — one request, one reply. Handy for curl and tests."""
    reply = await generate_reply(request.message, request.conversation_id)
    return ChatResponse(reply=reply, conversation_id=request.conversation_id)


@app.get("/api/chat/stream")
async def chat_stream(message: str, conversation_id: str = "default") -> StreamingResponse:
    """Streaming path (EventSource): tool activity as it happens, then the reply."""

    async def events():
        async for event in stream_reply(message, conversation_id):
            yield f"event: {event['type']}\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


class ResetRequest(BaseModel):
    conversation_id: str = Field(default="default", min_length=1, max_length=100)


@app.post("/api/chat/reset")
async def reset(request: ResetRequest) -> dict[str, str]:
    """Drop a conversation's SDK session so the next message starts fresh."""
    reset_conversation(request.conversation_id)
    return {"status": "reset", "conversation_id": request.conversation_id}
