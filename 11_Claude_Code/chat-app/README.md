# Codebase Concierge

A chat app that answers questions about a repository. The browser talks to
FastAPI; FastAPI hands each message to a **Claude Agent SDK** agent with
read-only tools, and streams the agent's tool calls back to the page while it
works.

```
browser ──▶ POST /api/chat            ──▶ agent.generate_reply()  ──┐
        └─▶ GET  /api/chat/stream(SSE)──▶ agent.stream_reply()    ──┴─▶ query()
                                                                       ├ Read / Glob / Grep
                                                                       ├ mcp__concierge__count_lines
                                                                       └ mcp__concierge__git_log
```

## Setup

```bash
uv sync
cp .env.example .env        # optional
```

Auth, either one:

- put `ANTHROPIC_API_KEY=sk-ant-...` in `.env` (programmatic use is billed via
  the API), **or**
- run on a machine where the Claude Code CLI is already authenticated — the SDK
  reuses those credentials.

`TARGET_REPO` picks the repository the concierge reads. It defaults to the
course repo (`AIEC01/`), so it works with no configuration.

## Run

```bash
uv run uvicorn app.main:app --reload --port 8000
```

Open <http://localhost:8000>, ask *"what does this repo do?"*, then a follow-up
like *"what are its main dependencies?"* — the second answer knows what "its"
refers to.

Command line check (use `127.0.0.1`; `localhost` resolves to IPv6 on some Macs):

```bash
curl -s -X POST http://127.0.0.1:8000/api/chat \
  -H 'Content-Type: application/json' \
  -d '{"message":"what does this repo do?","conversation_id":"t1"}'

curl -N "http://127.0.0.1:8000/api/chat/stream?message=biggest%20file%20in%20app/&conversation_id=t1"
```

`uv run scratch_query.py "your question"` runs one `query()` outside the web app
and prints the message types as the loop turns.

## Endpoints

| Method | Path               | Purpose                                                     |
| ------ | ------------------ | ----------------------------------------------------------- |
| GET    | `/`                | The chat UI                                                 |
| GET    | `/api/config`      | Target repo + guardrails, shown in the header               |
| POST   | `/api/chat`        | `{message, conversation_id}` → `{reply, conversation_id}`   |
| GET    | `/api/chat/stream` | Same, as SSE: `activity` events, then one `reply` / `error` |
| POST   | `/api/chat/reset`  | Forget a conversation's SDK session ("New chat")            |

## Custom tools

Defined in `app/tools.py` as an in-process SDK MCP server (`concierge`):

- **`count_lines`** — lines in a file, or the largest files under a directory.
  *"what's the biggest file in `app/`?"*
- **`git_log`** — recent commits, optionally scoped to a path. History isn't in
  the working tree, so `Read`/`Grep` structurally cannot answer *"what changed
  recently?"* — this is the tool that earns its keep.

Both resolve paths inside `TARGET_REPO` and refuse anything outside it.

## Safety model

There is no human clicking "approve" on a server, so the configuration *is* the
permission gate:

- `allowed_tools` — `Read`, `Glob`, `Grep`, and the two custom tools. No
  `Write`, `Edit`, or `Bash`. A prompt-injected "delete everything" has no tool
  to do it with.
- `max_turns=25` — a hard ceiling on loop iterations per message.
- `cwd=TARGET_REPO` — plus an explicit path check inside each custom tool.
- Agent errors return a chat reply, not a stack trace.

## Layout

```
app/config.py   env config, system prompt, ALLOWED_TOOLS
app/tools.py    custom in-process tools (SDK MCP server)
app/agent.py    the SDK seam: query(), session map, event stream
app/main.py     FastAPI routes
static/         chat UI (plain HTML/CSS/JS, no build step)
scratch_query.py  Task 5 scratch script
```
