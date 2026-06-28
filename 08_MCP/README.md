<p align="center" draggable="false"><img src="https://github.com/AI-Maker-Space/LLM-Dev-101/assets/37101144/d1343317-fa2f-41e1-8af1-1dbb18399719"
     width="200px"
     height="auto"/>
</p>

<h1 align="center" id="heading">Session 8: Model Context Protocol (MCP)</h1>

### [Quicklinks]()

| Session Sheet | Recording | Slides | Repo | Homework | Feedback |
|:--------------|:----------|:-------|:-----|:---------|:---------|
| [Session 8: MCP](https://github.com/AI-Maker-Space/The-AI-Engineering-Certification-v1.0/tree/main/00_Docs/Modules/08_MCP) |[Recording!](https://us02web.zoom.us/rec/share/rqw5I5hwbOOHy8TrGjnu0IjDJi53ykHb0k897jYfyHqZpgRhUuFP4A18d4NrcEKS.18sNk6Do9XwyaVUy) <br> passcode: `E56&^V+8`| [Session 8 Slides](https://canva.link/k8cixqgkfeghdsn) |You are here! | [Session 8 Assignment](https://forms.gle/TcjjChq38ydMjuqn8) | [Feedback 6/25](https://forms.gle/DvcWDgBXatBWCXqi7) |

## Useful Resources

**MCP (Model Context Protocol)**
- [MCP Official Docs](https://modelcontextprotocol.io/) — Spec, tutorials, and guides
- [MCP-UI](https://mcpui.dev/) — Official standard for interactive UI in MCP
- [MCP Auth Guide (Auth0)](https://auth0.com/blog/mcp-specs-update-all-about-auth/) — Deep dive into MCP auth spec updates

## Main Assignment

In this session, you will build an MCP server with OAuth authentication — a cat
shop application that exposes tools for browsing products, managing a cart, and
checking out.

The main entry point is:

```text
server.py
```

The server implementation lives in:

```text
app/
```

Available MCP tools:

- `list_products`
- `get_product`
- `add_to_cart`
- `view_cart`
- `remove_from_cart`
- `checkout`

## Setup

From this folder:

```bash
uv sync
```

Copy the example env file and fill in your OpenAI API key:

```bash
cp .env.example .env
```

## Running the MCP Server

Run the server locally:

```bash
uv run server.py
```

The server starts on `http://localhost:8000`.

### Expose the server with ngrok

In a separate terminal, start an ngrok tunnel:

```bash
ngrok http 8000
```

Copy the ngrok forwarding URL (e.g. `https://xxxx-xx-xx-xx-xx.ngrok-free.app`) and
restart the server with it:

```bash
ISSUER_URL=https://xxxx-xx-xx-xx-xx.ngrok-free.app uv run server.py
```

> **Note:** The `ISSUER_URL` must match the public URL clients use to reach the
> server, otherwise OAuth authentication will fail.

## Outline

### Breakout Room #1

- Set up the MCP server with OAuth and the product database
- Explore the MCP tools: `list_products`, `get_product`, `add_to_cart`, `view_cart`, `remove_from_cart`, `checkout`

### Breakout Room #2

- Connect an MCP client to the server
- Build an end-to-end interaction flow using the MCP tools

## Ship

The completed MCP server and client integration!

### Deliverables

- A short Loom of either:
  - the MCP server you built and a demo of the client interacting with it; or
  - the notebook you created for the Advanced Build

## Share

Make a social media post about your final application!

### Deliverables

- Make a post on any social media platform about what you built!

Here's a template to get you started:

```
🚀 Exciting News! 🚀

I am thrilled to announce that I have just built and shipped an MCP server with OAuth authentication! 🎉🤖

🔍 Three Key Takeaways:
1️⃣
2️⃣
3️⃣

Let's continue pushing the boundaries of what's possible in the world of AI and tool integration. Here's to many more innovations! 🚀
Shout out to @AIMakerspace !

#MCP #ModelContextProtocol #OAuth #Innovation #AI #TechMilestone

Feel free to reach out if you're curious or would like to collaborate on similar projects! 🤝🔥
```

## Submitting Your Homework 

Follow these steps to prepare and submit your homework assignment:

1. Review the MCP server code in `server.py` and the `app/` directory
2. Run the MCP server locally using `uv run server.py`
3. Connect to the server using an MCP client (e.g., Claude Desktop, or a custom client)
4. Test all available tools: browsing products, adding to cart, viewing cart, removing items, and checkout
5. Record a Loom video reviewing what you have learned from this session

## Questions

### Question #1

Why is OAuth important for MCP servers, and what security considerations should you keep in mind when exposing tools to AI clients?

#### Answer

##### Why OAuth is Important for MCP Servers?
      • Identity Mapping: Standard local connections (like  stdio ) treat all commands as coming from a
      single operator. However, public HTTP-based servers are globally exposed. OAuth provides a       
      mechanism to verify who is calling a tool (e.g. mapping  view_cart  or  checkout  to specific    
      database records for a logged-in user).                                                          
      • Delegated Authority (Scopes): Rather than giving an AI full write/modify privileges to         
      everything, OAuth scopes (like  read ,  write ) allow users to grant limited permissions.        
      • Credential Isolation: The client never sees the user's password; instead, it receives a short- 
      lived access token that can be easily revoked. 

##### Exposing Tools to AI Clients: Security Considerations:
      • Indirect Prompt Injection: Because AI models parse external untrusted text (like emails,       
      reviews, or chat inputs), they can be manipulated into executing tools with harmful arguments (e.
      g., ordering items, clearing a cart).                                                            
      • Human-in-the-Loop Validation: Sensitive operations (such as checkout, transaction processing,  
      or database deletion) must require manual user authorization rather than letting the AI complete 
      the pipeline autonomously.                                                                       
      • Strict Input & Scope Checks: The MCP server must enforce strict sanitization of parameters     
      (checking types, constraints, ranges) and validate incoming token authorization scopes.   


### Question #2

What is Streamable HTTP transport in MCP, and why might you expose a server publicly with OAuth instead of using a local stdio connection?

#### Answer

Streamable HTTP replaces legacy SSE as the modern standard for remote MCP servers by consolidating bidirectional communication into a single HTTP POST endpoint (typically /mcp), instead of juggling separate connections, the server dynamically answers each request with a single JSON object or a scoped SSE stream by mimicking standard web traffic, it is more reliable, firewall-friendly, and seamlessly integrates with existing load balancers and proxies

You would expose an MCP server publicly using Streamable HTTP instead of a local stdio connection when your AI agent needs to access remote resources over the internet, such as cloud-based tools, multi-user enterprise databases, or services hosted behind an API gateway.

Local stdio relies on direct process communication via standard input/output channels, which makes it ideal for zero-latency interactions only when the client and server are running on the same local machine
However, the moment you transition to Streamable HTTP to enable remote access, the server is exposed over the network, opening up your sensitive tools and data to potential attackersm, this is why integrating OAuth 2.1 is critical for public deployments: it acts as a robust security layer that safely handles dynamic agent registration, strict token validation, and multi-tenant access control, ensuring that only authorized clients can reach your infrastructure

## Activity 1: Extend the MCP Server

Add at least one new tool to the cat shop MCP server (e.g., `search_products`, `update_cart_quantity`, or `get_order_history`). Ensure the new tool integrates properly with the existing database and OAuth authentication. Demo the new tool through an MCP client and include it in your Loom video.

- Added get_order_history in tools.py

## Advanced Activity: Build a Custom MCP Client

Build a custom MCP client that connects to the cat shop server over Streamable HTTP, authenticates via OAuth, and orchestrates a multi-step shopping flow (browse → add to cart → checkout). Compare the developer experience of MCP-based tool integration vs. traditional REST API calls.

Include your findings and a demo in your Loom video.

 ### 1. Developer Experience (DX) Comparison Matrix                                               
                                                                                                   
   Dimension               │ MCP Tool Integration              │ Traditional REST API Calls
  ─────────────────────────┼───────────────────────────────────┼───────────────────────────────────
   Server-Side Setup       │ High DX (Automatic): Standard     │ Low DX (Manual): You must define
                           │ Python/JS functions are decorated │ routes, HTTP methods, status
                           │ with  @mcp.tool() . The framework │ codes, Pydantic request/response
                           │ auto-generates schemas from       │ models, and manual
                           │ function docstrings and type      │ OpenAPI/Swagger specs.
                           │ hints.                            │
   Client-Side Maintenance │ Zero-Maintenance: The client      │ High Maintenance: Every server
                           │ queries  /mcp  and dynamically    │ update requires manually editing
                           │ loads all schemas. Adding a new   │ client-side HTTP call methods,
                           │ tool on the server requires zero  │ path strings, and request
                           │ code changes on the client.       │ wrappers.
   LLM / Agent Integration │ Native: MCP payloads are designed │ High Boilerplate: You must
                           │ specifically for LLMs. Adapters   │ manually write adapter code to
                           │ (like LangChain's) automatically  │ transform REST request/response
                           │ map server schemas into LLM       │ shapes into LLM-readable format
                           │ function calls.                   │ (e.g., OpenAI's function JSON
                           │                                   │ schemas).
   Authentication Scope    │ Connection-Level: Auth (like      │ Request-Level: Tokens/credentials
                           │ OAuth PKCE) is negotiated once    │ must be managed, refreshed, and
                           │ when establishing the             │ injected into headers manually
                           │ SSE/Websocket stream. All tool    │ for every individual HTTP
                           │ requests on the stream are        │ request.
                           │ automatically authenticated.      │
   Real-time Streaming     │ Built-in: Supports bidirectional  │ Custom Built: Requires setting up
                           │ logs, callbacks, and progress     │ separate WebSockets, polling
                           │ streaming out of the box via the  │ mechanisms, or webhook endpoints
                           │ Server-Sent Events (SSE) channel. │ to stream progress.

  • Use REST APIs when: Building standard frontend-to-backend web applications (React calling a    
  database) where deterministic execution and structured resource paths (URLs) are required.       
  • Use MCP when: Exposing tools, resources, or prompt templates directly to AI Agents, IDE Panels,
  or LLM-based pipelines. It removes the intermediate documentation layer, allowing servers and    
  agents to self-assemble.