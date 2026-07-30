"""Runtime configuration, read once from the environment (.env supported)."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# The repository the concierge answers questions about. Defaults to the course
# repo two levels up (11_Claude_Code/chat-app -> AIEC01) so the app is useful
# with zero configuration.
TARGET_REPO = Path(
    os.getenv("TARGET_REPO") or PROJECT_ROOT.parent.parent
).expanduser().resolve()

MODEL = os.getenv("CONCIERGE_MODEL") or None
MAX_TURNS = int(os.getenv("CONCIERGE_MAX_TURNS", "25"))

# Read-only built-ins + our in-process tools. This list is the entire safety
# story for a headless agent: nothing here can write to the filesystem.
ALLOWED_TOOLS = [
    "Read",
    "Glob",
    "Grep",
    "mcp__concierge__count_lines",
    "mcp__concierge__git_log",
]

SYSTEM_PROMPT = f"""You are the Codebase Concierge for the repository at {TARGET_REPO}.

You answer questions about this repository for people browsing it in a web chat.

Rules:
- Ground every claim in files you actually read. Never guess at contents.
- Cite file paths (repo-relative, e.g. `app/main.py:42`) for anything specific.
- Be concise: a short paragraph or a tight bullet list. No preamble, no
  "Great question!", no restating the question.
- Use Markdown sparingly — bullets, inline code, fenced blocks for real code.
- You are read-only. If asked to change, run, or install anything, explain that
  you can only read and search this repository.
- If the answer genuinely isn't in the repo, say so plainly.
"""
