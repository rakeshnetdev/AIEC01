"""The concierge agent: one `query()` per user message, streamed as events.

This module is the seam the echo stub used to occupy. `/api/chat` never talks
to the SDK directly — it consumes the events produced here.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKError,
    ResultMessage,
    SystemMessage,
    ToolUseBlock,
    query,
)

from .config import ALLOWED_TOOLS, MAX_TURNS, MODEL, SYSTEM_PROMPT, TARGET_REPO
from .tools import concierge_server

logger = logging.getLogger(__name__)

FALLBACK_REPLY = (
    "I hit a problem while looking through the repository. Please try again — "
    "and if it keeps happening, check the server logs and that "
    "`ANTHROPIC_API_KEY` is set."
)

# conversation_id (browser) -> session_id (SDK). In-memory is fine for today;
# a real deployment would use Redis or the SDK's session store.
_sessions: dict[str, str] = {}
# One in-flight query per conversation: resuming a session twice concurrently
# would interleave two turns into the same history.
_locks: dict[str, asyncio.Lock] = {}


def _lock_for(conversation_id: str) -> asyncio.Lock:
    return _locks.setdefault(conversation_id, asyncio.Lock())


def _options(conversation_id: str) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=ALLOWED_TOOLS,
        mcp_servers={"concierge": concierge_server},
        cwd=str(TARGET_REPO),
        max_turns=MAX_TURNS,
        model=MODEL,
        # Resume the SDK session bound to this browser conversation, so
        # follow-up questions ("what are *its* dependencies?") have context.
        resume=_sessions.get(conversation_id),
    )


def _describe(block: ToolUseBlock) -> str | None:
    """A short, human-readable line for the browser's activity feed.

    Returns None for the harness's own bookkeeping tools (e.g. ToolSearch),
    which are noise to someone watching the agent work.
    """
    args: dict[str, Any] = block.input if isinstance(block.input, dict) else {}
    match block.name:
        case "Read":
            return f"Reading {args.get('file_path', '')}".strip()
        case "Glob":
            return f"Globbing {args.get('pattern', '')}".strip()
        case "Grep":
            return f"Searching for “{args.get('pattern', '')}”"
        case "mcp__concierge__count_lines":
            return f"Counting lines in {args.get('path', '.')}"
        case "mcp__concierge__git_log":
            scope = args.get("path")
            return f"Reading git history{f' for {scope}' if scope else ''}"
        case name if name in ALLOWED_TOOLS:
            return f"Using {name}"
        case _:
            return None


def reset_conversation(conversation_id: str) -> None:
    """Forget the SDK session for a conversation (used by the New chat button)."""
    _sessions.pop(conversation_id, None)
    _locks.pop(conversation_id, None)


async def stream_reply(
    message: str, conversation_id: str
) -> AsyncIterator[dict[str, Any]]:
    """Run one agent turn, yielding `activity` events then exactly one terminal
    event (`reply` or `error`)."""
    async with _lock_for(conversation_id):
        reply = ""
        try:
            async for event in query(prompt=message, options=_options(conversation_id)):
                if isinstance(event, SystemMessage) and event.subtype == "init":
                    session_id = event.data.get("session_id")
                    if session_id:
                        _sessions[conversation_id] = session_id

                elif isinstance(event, AssistantMessage):
                    for block in event.content:
                        if isinstance(block, ToolUseBlock):
                            detail = _describe(block)
                            if detail is None:
                                continue
                            logger.info("[%s] tool: %s", conversation_id, detail)
                            yield {"type": "activity", "detail": detail}

                elif isinstance(event, ResultMessage):
                    # Late safety net: session_id is also on the result.
                    _sessions.setdefault(conversation_id, event.session_id)
                    if event.is_error or not event.result:
                        logger.error(
                            "[%s] agent error: subtype=%s result=%r",
                            conversation_id,
                            event.subtype,
                            event.result,
                        )
                        yield {"type": "error", "reply": _explain(event)}
                        return
                    reply = event.result
                    logger.info(
                        "[%s] done: %s turns, $%.4f",
                        conversation_id,
                        event.num_turns,
                        event.total_cost_usd or 0.0,
                    )

        except ClaudeSDKError as exc:
            logger.exception("SDK failure")
            yield {"type": "error", "reply": f"{FALLBACK_REPLY}\n\n`{exc}`"}
            return
        except Exception:  # never let an agent failure become a 500
            logger.exception("Unexpected failure")
            yield {"type": "error", "reply": FALLBACK_REPLY}
            return

        yield {"type": "reply", "reply": reply or FALLBACK_REPLY}


def _explain(result: ResultMessage) -> str:
    if result.subtype == "error_max_turns":
        return (
            f"I used up my {MAX_TURNS}-step budget on that one. Try asking "
            "something narrower — a specific file or directory."
        )
    return FALLBACK_REPLY


async def generate_reply(message: str, conversation_id: str) -> str:
    """Non-streaming path: drain the stream and return the final text."""
    reply = FALLBACK_REPLY
    async for event in stream_reply(message, conversation_id):
        if event["type"] in ("reply", "error"):
            reply = event["reply"]
    return reply
