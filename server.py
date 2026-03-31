"""
Step 02: Resources and Prompts

Building on the hello world server, we add:
- Resources: read-only data the LLM can access (static and dynamic)
- Resource templates: parameterized URIs for dynamic content
- Prompts: reusable message templates for common interactions
"""

import json
from datetime import datetime, timezone
from fastmcp import FastMCP
from fastmcp.prompts import Message

mcp = FastMCP(
    "HelloWorld",
    instructions=(
        "A demo MCP server with tools, resources, and prompts. "
        "Read the 'about' resource first to understand what's available."
    ),
)


# === Tools (from step-01) ===


@mcp.tool
def echo(message: str) -> str:
    """Echo a message back to the caller."""
    return f"Echo: {message}"


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together and return the result."""
    return a + b


@mcp.tool
def greet(name: str, greeting: str = "Hello") -> str:
    """Greet someone by name. Optionally customize the greeting."""
    return f"{greeting}, {name}! Welcome to MCP."


# === Resources ===


@mcp.resource("resource://about", mime_type="text/plain")
def get_about() -> str:
    """Static information about this server."""
    return (
        "HelloWorld MCP Server v0.2\n"
        "A demo server for learning MCP concepts.\n"
        "Available: tools (echo, add, greet), resources, and prompts."
    )


@mcp.resource("resource://server-time", mime_type="application/json")
def get_server_time() -> str:
    """Dynamic resource that returns the current server time."""
    now = datetime.now(timezone.utc)
    return json.dumps({
        "utc": now.isoformat(),
        "unix_timestamp": int(now.timestamp()),
    })


@mcp.resource("resource://greeting/{name}", mime_type="text/plain")
def get_greeting_resource(name: str) -> str:
    """Resource template — generates a personalized greeting for any name."""
    return f"Hello, {name}! This greeting was generated from a resource template."


@mcp.resource(
    "data://server-config",
    mime_type="application/json",
    description="Server configuration and capabilities (read-only)",
)
def get_server_config() -> str:
    """Exposes server metadata as structured JSON."""
    return json.dumps({
        "server_name": "HelloWorld",
        "version": "0.2",
        "transport": "http-streamable",
        "capabilities": ["tools", "resources", "prompts"],
    })


# === Prompts ===


@mcp.prompt
def code_review(language: str, code: str) -> list[Message]:
    """Generate a code review request for the given code."""
    return [
        Message(
            f"Please review the following {language} code for bugs, style issues, "
            f"and potential improvements:\n\n```{language}\n{code}\n```"
        ),
    ]


@mcp.prompt
def summarize(text: str, style: str = "concise") -> str:
    """Generate a summarization request with a specified style."""
    return f"Please provide a {style} summary of the following text:\n\n{text}"


@mcp.prompt
def explain_concept(concept: str, audience: str = "beginner") -> list[Message]:
    """Generate a request to explain a concept for a specific audience."""
    return [
        Message(
            f"You are an expert teacher. Explain '{concept}' to a {audience} audience. "
            f"Use analogies and examples where helpful."
        ),
        Message("I'll explain this step by step.", role="assistant"),
    ]


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
