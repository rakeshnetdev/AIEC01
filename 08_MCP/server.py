# Model Context Protocol connects (MCP) AI applications to external systems. 

# MCP Client: The application hosting the AI model (like Claude Desktop or an IDE).

# MCP Server: The program that exposes the actual tools connecting to resources like databases, calendars, or emails.

# Authorization Server:  Security checkpoint that verifies user identity before handing over access tokens to the client.

# Streamable HTTP: a Server-Sent Events stream for real-time updates from server to client, 
#                 and standard HTTP POST requests for JSON-RPC messages from client to server. 


from app import mcp

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
