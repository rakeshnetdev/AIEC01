# DEPLOYMENT AND CONFIGURATION DOCUMENTATION

This document summarizes all configuration settings, database connections, and architecture schemas established during this coding session to deploy the **Cat Health Agent Server** (LangGraph Backend + Next.js Frontend).

---

## 1. System Architecture

```
                  ┌──────────────────────────────────────────────┐
                  │              Render (Backend)                │
                  │                                              │
Client (HTTPS) ───┼─► [LangGraph API (Port 8000)]                │
(Vercel Frontend) │         │ (Internal VPC Bridge)              │
                  │         ├────────────────────────┐           │
                  │         ▼                        ▼           │
                  │   [Redis Cache (6379)]     [Postgres (5432)] │
                  └──────────────────────────────────────────────┘
```

---

## 2. Configuration Artifacts

### A. Graph Definition (`langgraph.json`)
Registers our compiled graph and defines accessible assistant routers in local dev / production:
```json
{
  "dependencies": ["."],
  "env": ".env",
  "graphs": {
    "simple_agent": "app.graphs.simple_agent:graph"
  },
  "assistants": {
    "agent": {
      "graph_id": "simple_agent",
      "name": "Simple Agent",
      "description": "Agent with tools using conditional tool-calling."
    }
  }
}
```

### B. Standalone Server Infrastructure (`render.yaml`)
Automates creation of a secure Postgres and Redis infrastructure on **Render**:
```yaml
databases:
  - name: langgraph-postgres
    plan: free
    databaseName: langgraph_db
    user: langgraph_user

services:
  - type: redis
    name: langgraph-redis
    plan: free
    ipAllowList: []

  - type: web
    name: langgraph-api
    plan: free
    env: docker
    dockerfilePath: Dockerfile
    dockerContext: .
    envVars:
      - key: DATABASE_URI
        fromDatabase:
          name: langgraph-postgres
          property: connectionString
      - key: REDIS_URI
        fromService:
          type: redis
          name: langgraph-redis
          property: connectionString
      - key: LANGSERVE_GRAPHS
        value: '{"simple_agent": "app.graphs.simple_agent:graph"}'
      - key: RAG_DATA_DIR
        value: "data"
      - key: OPENAI_CHAT_MODEL
        value: "gpt-4o-mini"
      - key: OPENAI_EMBEDDING_MODEL
        value: "text-embedding-3-small"
      - key: LANGSMITH_TRACING
        value: "true"
      - key: OPENAI_API_KEY
        sync: false
      - key: TAVILY_API_KEY
        sync: false
      - key: LANGSMITH_API_KEY
        sync: false
```

### C. Host & Container Port Maps (`docker-compose.yml`)
Standardizes custom parameters and maps host port `2024` down to standard internal container port `8000`:
* **Port Mapping**: `2024:8000`
* **Checkpointer DB**: `DATABASE_URI` (using full prefix: `postgresql://...`)
* **State Queue**: `REDIS_URI`

---

## 3. Client & Frontend Settings

### A. Client-Side API Resolution
Modified `frontend/components/chat.tsx` to safely resolve absolute HTTP addresses dynamically on runtime, completely eliminating browser `TypeError: Failed to construct 'URL'` exceptions:

```typescript
const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (typeof window !== "undefined"
    ? `${window.location.origin}/api`
    : "http://localhost:3000/api");
```

### B. Vercel Configuration
To avoid the standard Next.js development proxy stream-buffering delay ("Failed to Fetch") and prevent serverless timeouts (limited to 10 seconds on free accounts), the frontend is set to talk **directly** to our secure CORS-enabled Render endpoint:

* **Production Setting**:
  ```env
  NEXT_PUBLIC_API_URL=https://langgraph-api-zaxu.onrender.com
  ```

---

## 4. Verification & Testing

### A. Core Agent Logic (Annotated Code)
Detailed inline steps and explanations were added inside `app/rag.py` describing:
* Dynamic document loader PyMuPDF loaders.
* Chunk size specifications (750 tokens) and tokenization via `tiktoken`.
* Instantiation of `OpenAIEmbeddings` and local memory vector storage.

### B. Verifying streams via Standalone Smoke Test (`smoke_test.py`)
Provides automated integration validation using standard asynchronous methods:
```python
import asyncio
import os
from dotenv import load_dotenv
from langgraph_sdk import get_client

load_dotenv()
URL = os.environ.get("LANGGRAPH_API_URL", "http://localhost:2024")

async def run_smoke_test():
    client = get_client(url=URL)
    async for chunk in client.runs.stream(
        thread_id=None,
        assistant_id="simple_agent",
        input={"messages": [{"role": "human", "content": "How often should I deworm my cat?"}]},
        stream_mode="updates",
    ):
        print(chunk)

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
```

* **Local dev test execution**: `uv run python smoke_test.py`
* **Live cloud test execution**: `LANGGRAPH_API_URL=https://langgraph-api-zaxu.onrender.com uv run python smoke_test.py`
