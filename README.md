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

---

# Step 02: Resources and Prompts

Building on the tools from step-01, this step introduces two more MCP primitives: **resources** and **prompts**.

## Resources

Resources are **read-only data** that a server exposes to clients. Unlike tools (which perform actions), resources provide information the LLM can read to inform its responses. Clients fetch resources by URI.

### Resource Types

| Type | URI Example | Description |
|------|-------------|-------------|
| **Static** | `resource://about` | Fixed content that doesn't change between reads |
| **Dynamic** | `resource://server-time` | Content generated at read time (e.g., current timestamp) |
| **Template** | `resource://greeting/{name}` | Parameterized URI — the client fills in `{name}` to get personalized content |

### Resources Defined

| Resource | URI | MIME Type | Description |
|----------|-----|-----------|-------------|
| `get_about` | `resource://about` | `text/plain` | Static server description |
| `get_server_time` | `resource://server-time` | `application/json` | Current UTC time and Unix timestamp |
| `get_greeting_resource` | `resource://greeting/{name}` | `text/plain` | Personalized greeting (template) |
| `get_server_config` | `data://server-config` | `application/json` | Server metadata and capabilities |

## Prompts

Prompts are **reusable message templates** that help clients construct common interactions. They accept parameters and return pre-formatted messages the LLM can use as conversation starters or context.

### Prompts Defined

| Prompt | Parameters | Description |
|--------|------------|-------------|
| `code_review` | `language`, `code` | Generates a code review request with the code in a fenced block |
| `summarize` | `text`, `style?` (default: `"concise"`) | Generates a summarization request with a configurable style |
| `explain_concept` | `concept`, `audience?` (default: `"beginner"`) | Generates a multi-message explanation request with a system-like setup and assistant priming |

### Prompt Return Types

Prompts can return either a plain `str` (converted to a single user message) or a `list[Message]` for multi-message sequences. The `explain_concept` prompt demonstrates multi-message prompts by including both a user message and an assistant priming message.

## Resources vs. Tools

| | Resources | Tools |
|---|-----------|-------|
| **Purpose** | Provide data for the LLM to read | Perform actions or computations |
| **Access** | Read-only | Can have side effects |
| **Invocation** | Client reads by URI | Client calls with arguments |
| **Discovery** | Listed with URIs and MIME types | Listed with names and input schemas |

## New Concepts

- **`@mcp.resource(uri)`** — Decorator that registers a function as a resource at the given URI.
- **`mime_type`** — Tells the client how to interpret the resource content (e.g., `text/plain`, `application/json`).
- **Resource templates** — URIs with `{parameter}` placeholders that the client fills in, e.g., `resource://greeting/{name}`.
- **`@mcp.prompt`** — Decorator that registers a function as a reusable prompt template.
- **`Message(content, role)`** — A prompt message. Defaults to `role="user"`. Use `role="assistant"` for priming messages that set up the assistant's response pattern.
