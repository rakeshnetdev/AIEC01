import asyncio
import os
from dotenv import load_dotenv
from langgraph_sdk import get_client

# Load environment variables from .env file (like OPENAI_API_KEY, TAVILY_API_KEY, etc.)
load_dotenv()

# Default to http://localhost:2024 (the local LangGraph dev server),
# or fall back to any URL set in the environment variables.
URL = os.environ.get("LANGGRAPH_API_URL", "http://localhost:2024")


async def run_smoke_test():
    """
    Asynchronous smoke test using `get_client`.
    This matches the standard asynchronous pattern of LangGraph clients.
    """
    print("--- Running Smoke Test ---")
    print(f"Connecting to LangGraph API server at: {URL}")
    
    client = get_client(url=URL)
    print(client);
    try:
        # We stream updates asynchronously from the "simple_agent" assistant (or "agent" depending on platform configuration)
        # In local development mode, we can target the graph ID "simple_agent" directly.
        async for chunk in client.runs.stream(
            thread_id=None,  # Passing None automatically creates a new thread for this run
            assistant_id="simple_agent",
            input={"messages": [{"role": "human", "content": "How often should I deworm my cat?"}]},
            stream_mode="updates",
        ):
            print(chunk)
    except Exception as e:
        print(f"\n[ERROR] Smoke test failed: {e}")
        print("Make sure your LangGraph dev server is running (e.g., via `uv run langgraph dev` or `langgraph up`).\n")


if __name__ == "__main__":
    asyncio.run(run_smoke_test())


# uv run python smoke_test.py