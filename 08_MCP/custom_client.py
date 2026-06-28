import argparse
import asyncio
import json
import os
import webbrowser
from typing import Any
from urllib.parse import parse_qs, urlsplit

from dotenv import load_dotenv
import httpx
from pydantic import AnyUrl

# Import Model Context Protocol (MCP) client modules
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken


DEFAULT_SERVER_URL = "http://localhost:6060"


# -----------------------------------------------------------------------------
# Token Storage
# -----------------------------------------------------------------------------
# An in-memory implementation of the TokenStorage interface.
# It holds the active OAuth tokens (access token, refresh token) and client details
# during the application's lifecycle.
class InMemoryTokenStorage(TokenStorage):
    def __init__(self) -> None:
        self._tokens: OAuthToken | None = None
        self._client_info: OAuthClientInformationFull | None = None

    async def get_tokens(self) -> OAuthToken | None:
        return self._tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self._tokens = tokens

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self._client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self._client_info = client_info


# -----------------------------------------------------------------------------
# Local Callback Server
# -----------------------------------------------------------------------------
# A lightweight asynchronous socket server that listens locally (e.g. on port 9090).
# Once the user signs in via the browser, the authorization server redirects the
# browser back to this server's callback endpoint containing the auth 'code' and 'state'.
# We extract these query parameters, fulfill the Future callback, and shut down the server.
class OAuthCallbackServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 9090) -> None:
        self.host = host
        self.port = port
        self._server: asyncio.AbstractServer | None = None
        self._callback: asyncio.Future[tuple[str, str | None]] | None = None

    @property
    def callback_url(self) -> str:
        return f"http://{self.host}:{self.port}/callback"

    async def __aenter__(self) -> "OAuthCallbackServer":
        # Initialize a Future that will resolve once the callback request is parsed
        self._callback = asyncio.get_running_loop().create_future()
        # Start a local TCP socket server
        self._server = await asyncio.start_server(
            self._handle_request, self.host, self.port
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        # Shut down the TCP server when exiting the context manager
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

    async def wait_for_callback(self) -> tuple[str, str | None]:
        if self._callback is None:
            raise RuntimeError("The OAuth callback server has not started.")
        # Block until the callback handles the request and sets the result
        return await self._callback

    async def _handle_request(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        try:
            # Read the HTTP request line (e.g., "GET /callback?code=xxx HTTP/1.1")
            request_line = (await reader.readline()).decode("utf-8").strip()
            parts = request_line.split(" ", maxsplit=2)
            target = parts[1] if len(parts) >= 2 else "/"

            # Read and discard the HTTP request headers
            while await reader.readline() not in (b"", b"\r\n"):
                pass

            # Parse query parameters from the request path
            parsed = urlsplit(target)
            params = parse_qs(parsed.query)
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]
            error = params.get("error", [None])[0]

            # Fulfill callback if we successfully captured the authorization code
            if parsed.path == "/callback" and code:
                if self._callback is not None and not self._callback.done():
                    self._callback.set_result((code, state))
                status = "200 OK"
                body = "<h1>Signed in</h1><p>You can return to the Cat Shop custom client.</p>"
            elif error:
                if self._callback is not None and not self._callback.done():
                    self._callback.set_exception(
                        RuntimeError(f"OAuth authorization failed: {error}")
                    )
                status = "400 Bad Request"
                body = "<h1>Sign-in failed</h1><p>You can close this window.</p>"
            else:
                status = "400 Bad Request"
                body = "<h1>Invalid callback</h1><p>You can close this window.</p>"

            # Send HTTP response back to the user's browser
            response = (
                f"HTTP/1.1 {status}\r\n"
                "Content-Type: text/html; charset=utf-8\r\n"
                f"Content-Length: {len(body.encode('utf-8'))}\r\n"
                "Connection: close\r\n\r\n"
                f"{body}"
            )
            writer.write(response.encode("utf-8"))
            await writer.drain()
        finally:
            writer.close()
            await writer.wait_closed()


# Helper function to print/open the login page url in the default web browser
async def open_authorization_page(auth_url: str, *, open_browser: bool) -> None:
    print(f"\nSign in to Cat Shop: {auth_url}\n")
    if open_browser:
        webbrowser.open(auth_url)


# Helper function to print MCP tool response blocks clearly in terminal
def print_tool_response(tool_name: str, result: Any) -> None:
    print(f"\n==================================================")
    print(f"🛠️  Invoking Tool: {tool_name}")
    print(f"==================================================")
    for block in result.content:
        if hasattr(block, "text"):
            try:
                # Format JSON string responses nicely
                data = json.loads(block.text)
                print(json.dumps(data, indent=2))
            except json.JSONDecodeError:
                # Fallback to plain text printing
                print(block.text)
    print(f"==================================================\n")


# -----------------------------------------------------------------------------
# Main Client Orchestration Flow
# -----------------------------------------------------------------------------
async def run_client(server_url: str, callback_port: int, open_browser: bool) -> None:
    server_url = server_url.rstrip("/")
    mcp_url = f"{server_url}/mcp"

    # 1. Start callback listener server context
    async with OAuthCallbackServer(port=callback_port) as callback_server:
        
        async def redirect_handler(auth_url: str) -> None:
            await open_authorization_page(auth_url, open_browser=open_browser)

        # Initialize the token storage and client provider configuration
        storage = InMemoryTokenStorage()
        oauth = OAuthClientProvider(
            server_url=server_url,
            client_metadata=OAuthClientMetadata(
                client_name="Cat Shop Custom Client",
                redirect_uris=[AnyUrl(callback_server.callback_url)],
                grant_types=["authorization_code", "refresh_token"],
                response_types=["code"],
                scope="read write",
            ),
            storage=storage,
            redirect_handler=redirect_handler,
            callback_handler=callback_server.wait_for_callback,
        )

        print("Initiating OAuth 2.0 PKCE flow...")
        # 2. Trigger the PKCE Authorization code grant flow
        # Making a request using the httpx client equipped with our oauth client provider
        # intercepts request, automatically opens browser, intercepts code, and acquires tokens.
        async with httpx.AsyncClient(auth=oauth) as http_client:
            await http_client.get(mcp_url)

        # Retrieve the acquired access token
        tokens = await storage.get_tokens()
        if not tokens or not tokens.access_token:
            print("Failed to acquire access token.")
            return

        print(f"Successfully authenticated! Access Token: {tokens.access_token[:10]}...")

        # Inject token into Bearer Authorization header for JSON-RPC transport
        headers = {"Authorization": f"Bearer {tokens.access_token}"}

        print(f"Connecting to MCP server over Streamable HTTP/SSE at {mcp_url}...")
        # 3. Establish the bidirectional Streamable HTTP / SSE transport connection
        async with streamablehttp_client(mcp_url, headers=headers) as (read_stream, write_stream, _):
            # 4. Wrap connection streams in an MCP ClientSession
            async with ClientSession(read_stream, write_stream) as session:
                print("Performing handshake and initializing session...")
                # Exchange capabilities and perform connection handshake
                await session.initialize()
                print("Handshake completed successfully!")

                # =====================================================================
                # Orchestrate Shopping Sequence Tools
                # =====================================================================
                
                # --- 1. list_products ---
                # Retrieve catalog list
                result = await session.call_tool("list_products")
                print_tool_response("list_products", result)

                # --- 2. get_product ---
                # Fetch full specifications for item with ID 1 (Whisker Wand)
                result = await session.call_tool("get_product", arguments={"product_id": 1})
                print_tool_response("get_product (product_id=1)", result)

                # --- 3. add_to_cart (first product) ---
                # Add 2x Whisker Wand (ID 1)
                result = await session.call_tool("add_to_cart", arguments={"product_id": 1, "quantity": 2})
                print_tool_response("add_to_cart (product_id=1, quantity=2)", result)

                # --- 4. add_to_cart (second product) ---
                # Add 1x Laser Pointer Pro (ID 3)
                result = await session.call_tool("add_to_cart", arguments={"product_id": 3, "quantity": 1})
                print_tool_response("add_to_cart (product_id=3, quantity=1)", result)

                # --- 5. view_cart (before item removal) ---
                # Verify cart contents before modding
                result = await session.call_tool("view_cart")
                print_tool_response("view_cart (before item removal)", result)

                # --- 6. remove_from_cart ---
                # Remove the Laser Pointer Pro (ID 3)
                result = await session.call_tool("remove_from_cart", arguments={"product_id": 3})
                print_tool_response("remove_from_cart (product_id=3)", result)

                # --- 7. view_cart (after item removal) ---
                # Verify that only the Whisker Wands remain
                result = await session.call_tool("view_cart")
                print_tool_response("view_cart (after item removal)", result)

                # --- 8. checkout ---
                # Place purchase order, clear cart, write record to DB 'orders' table
                result = await session.call_tool("checkout")
                print_tool_response("checkout", result)

                # --- 9. get_purchase_history ---
                # Verify order has been successfully logged in purchase history table
                result = await session.call_tool("get_purchase_history")
                print_tool_response("get_purchase_history", result)


# -----------------------------------------------------------------------------
# Script Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Custom MCP Client with OAuth and tool flow orchestration.")
    parser.add_argument(
        "--server-url",
        default=os.getenv("MCP_SERVER_URL", DEFAULT_SERVER_URL),
        help="Base URL of the MCP server (default: %(default)s).",
    )
    parser.add_argument(
        "--callback-port",
        type=int,
        default=9090,
        help="Local port that receives the OAuth callback (default: %(default)s).",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Print the sign-in URL without opening a browser.",
    )
    args = parser.parse_args()

    asyncio.run(
        run_client(
            server_url=args.server_url,
            callback_port=args.callback_port,
            open_browser=not args.no_browser,
        )
    )


if __name__ == "__main__":
    main()
