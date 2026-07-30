# Codebase Concierge

A chat web app whose backend is a Claude Agent SDK agent that answers questions
about **another** repository (`TARGET_REPO`), not this one.

## Run and verify

```bash
uv sync
uv run uvicorn app.main:app --reload --port 8000      # http://localhost:8000

curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"what does this repo do?","conversation_id":"t1"}'
```

Auth: `ANTHROPIC_API_KEY` in `.env`, or an already-authenticated Claude Code CLI
on the machine. `curl localhost` can fail on this Mac (IPv6) — use `127.0.0.1`.

## Architecture

```
static/index.html ──fetch/EventSource──▶ app/main.py ──▶ app/agent.py ──▶ query()
                                         (HTTP only)     (the SDK seam)   app/tools.py
```

- **`app/agent.py` is the seam.** All SDK contact lives here; it exposes
  `stream_reply()` (events) and `generate_reply()` (final text). `main.py` must
  never import `claude_agent_sdk`.
- One `query()` per user message. `conversation_id` (browser) → `session_id`
  (SDK) in `_sessions`, passed back as `resume=` so follow-ups keep context.
  An `asyncio.Lock` per conversation prevents two concurrent turns on one session.
- Agent failures become a polite chat reply, never a 500.

## Guardrails — do not weaken

`ALLOWED_TOOLS` in `app/config.py` is read-only (`Read`/`Glob`/`Grep` + the two
in-process tools) and `max_turns` is capped. There is no human at a permission
prompt on a server, so this allowlist *is* the permission gate. Custom tools
need the `mcp__concierge__<name>` prefix to be reachable. Tools resolve every
path inside `TARGET_REPO` and refuse anything outside it.

## Conventions

- Plain HTML/CSS/JS in `static/` — no framework, no build step, no CDN.
- New agent capability = a tool in `app/tools.py` + an entry in `ALLOWED_TOOLS`
  + a line in `_describe()` so it shows up in the UI's activity feed.
- Anything user-supplied that reaches the DOM goes through `escapeHtml()` first.
