# Step 01: Hello World MCP Server

## What is MCP?

The **Model Context Protocol (MCP)** is an open standard that lets AI models interact with external tools and data sources through a unified interface. Instead of building custom integrations for every tool, MCP provides a single protocol that any AI client can use to discover and call tools exposed by any MCP server.

## What This Step Demonstrates

- Creating a `FastMCP` server instance
- Defining tools with the `@mcp.tool` decorator
- Using Python type annotations for automatic JSON schema generation
- Running the server with HTTP streamable transport

## Tools

| Tool | Description |
|------|-------------|
| `echo(message)` | Echoes a message back to the caller |
| `add(a, b)` | Adds two integers and returns the result |
| `greet(name, greeting?)` | Greets someone by name with an optional custom greeting |

## Running the Server

```bash
pip install -r requirements.txt
python server.py
```

The server starts on `http://0.0.0.0:8000`.

## Connecting a Client

Add this to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "hello-world": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

## Key Concepts

- **Tools** — Functions decorated with `@mcp.tool` that an AI client can discover and call. Each tool has a name, description, and input schema derived from the function signature.
- **Transport** — How the client and server communicate. This step uses HTTP streamable transport, which runs a web server that clients connect to over HTTP.
- **Schema Generation** — FastMCP automatically generates JSON schemas from Python type annotations and docstrings, so clients know what parameters each tool accepts.
