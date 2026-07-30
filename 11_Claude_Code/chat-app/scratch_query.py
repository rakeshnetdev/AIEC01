"""Task 5 scratch script: feel the `query()` primitive in isolation.

    uv run scratch_query.py ["your question"]

Prints the anatomy of the agent loop — one line per message type — then the
final result.
"""

import asyncio
import sys

from claude_agent_sdk import ClaudeAgentOptions, query

from app.config import TARGET_REPO

PROMPT = "What does this project do? Answer in two sentences."


async def main() -> None:
    prompt = sys.argv[1] if len(sys.argv) > 1 else PROMPT
    print(f"repo: {TARGET_REPO}\nprompt: {prompt}\n")

    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Glob", "Grep"],
            cwd=str(TARGET_REPO),
            max_turns=15,
        ),
    ):
        print(type(message).__name__)
        if hasattr(message, "result"):
            print("\n" + (message.result or "(no result)"))


asyncio.run(main())
