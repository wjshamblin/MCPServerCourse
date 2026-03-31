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
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Run the server
uv run python server.py
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

---

# Step 03: Context, Logging, and Elicitation

This step introduces the **Context** object — a tool's connection back to the MCP client. Context enables tools to log messages, report progress, prompt the user for input, and access server resources during execution.

## Context Injection

When a tool function includes a parameter typed as `ctx: Context`, FastMCP automatically injects the context object at call time. The `ctx` parameter is **hidden from the tool's JSON schema**, so clients never see it or need to provide it.

```python
from fastmcp import Context

@mcp.tool
async def my_tool(arg: str, ctx: Context) -> str:
    await ctx.info("This log message is sent to the client")
    return "done"
```

Tools that use Context methods **must** be defined with `async def` because the context methods are all asynchronous.

## Context Methods

| Method | Purpose |
|--------|---------|
| `ctx.info(message)` | Log an informational message to the client |
| `ctx.warning(message)` | Log a warning message to the client |
| `ctx.error(message)` | Log an error message to the client |
| `ctx.debug(message)` | Log a debug message to the client |
| `ctx.report_progress(progress, total)` | Report numeric progress (e.g., 3 of 10) |
| `ctx.elicit(message, response_type)` | Request structured input from the user mid-execution |
| `ctx.read_resource(uri)` | Read a server resource by URI from within a tool |
| `ctx.sample(message)` | Ask the LLM to generate a completion (nested sampling) |

## Elicitation

`ctx.elicit()` pauses tool execution and asks the MCP client to prompt the user for input. The user's response comes back as an `ElicitResult` with two fields:

- **`result.action`** — One of three values:
  - `"accept"` — the user provided a response
  - `"decline"` — the user declined to respond
  - `"cancel"` — the user cancelled the operation
- **`result.data`** — The user's response value (typed according to `response_type`)

This is useful for destructive operations that need explicit user confirmation before proceeding.

> **Client support note:** Elicitation requires client support. As of March 2026:
> - **Claude Code** (v2.1.77+): Supported — shows an interactive prompt
> - **Claude Desktop**: Not yet supported — will error
> - **Claude.ai (web)**: Not yet supported — will error
>
> **Always provide a non-interactive fallback** (like a `confirm` parameter) so the tool works with any client. The `delete_records` tool demonstrates this pattern with a try/except that catches unsupported clients gracefully.

## New Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `analyze_text` | `text` | Analyzes text (word count, character count, sentence count, top words) with progress reporting and logging |
| `delete_records` | `table`, `confirm?` | Simulates a destructive delete with elicitation — prompts the user for confirmation unless `confirm=True` |
| `process_items` | `items` | Processes a list of strings with per-item progress reporting |
