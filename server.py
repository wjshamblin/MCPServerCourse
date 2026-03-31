"""
Step 03: Context, Logging, and Elicitation

Building on the hello world server, we add:
- Resources: read-only data the LLM can access (static and dynamic)
- Resource templates: parameterized URIs for dynamic content
- Prompts: reusable message templates for common interactions
- Context-aware tools: logging, progress reporting, and elicitation
"""

import asyncio
import json
from datetime import datetime, timezone
from fastmcp import Context, FastMCP
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
        "HelloWorld MCP Server v0.3\n"
        "A demo server for learning MCP concepts.\n"
        "Tools: echo, add, greet, analyze_text, delete_records, process_items\n"
        "Resources: about, server-time, greeting/{name}, server-config\n"
        "Prompts: code_review, summarize, explain_concept"
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
        "version": "0.3",
        "transport": "http-streamable",
        "tools": ["echo", "add", "greet", "analyze_text", "delete_records", "process_items"],
        "resources": ["about", "server-time", "greeting/{name}", "server-config"],
        "prompts": ["code_review", "summarize", "explain_concept"],
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


# === Context-Aware Tools ===


@mcp.tool
async def analyze_text(text: str, ctx: Context) -> str:
    """Analyze text with progress reporting and context logging.

    Demonstrates:
    - Context injection (ctx parameter is auto-injected, hidden from schema)
    - Logging to the client via ctx.info(), ctx.warning()
    - Progress reporting via ctx.report_progress()
    """
    await ctx.info("Starting text analysis...")

    # Step 1: Basic stats
    await ctx.report_progress(progress=1, total=4)
    words = text.split()
    word_count = len(words)
    char_count = len(text)
    await ctx.info(f"Counted {word_count} words, {char_count} characters")

    # Step 2: Word frequency
    await ctx.report_progress(progress=2, total=4)
    freq: dict[str, int] = {}
    for word in words:
        w = word.lower().strip(".,!?;:")
        freq[w] = freq.get(w, 0) + 1
    top_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)[:5]

    # Step 3: Sentence count
    await ctx.report_progress(progress=3, total=4)
    sentences = len([s for s in text.split(".") if s.strip()])

    if word_count > 1000:
        await ctx.warning("Large text detected — analysis may be approximate")

    # Step 4: Done
    await ctx.report_progress(progress=4, total=4)
    await ctx.info("Analysis complete")

    return json.dumps({
        "word_count": word_count,
        "character_count": char_count,
        "sentence_count": sentences,
        "top_words": [{"word": w, "count": c} for w, c in top_words],
    })


@mcp.tool
async def delete_records(table: str, confirm: bool = False, ctx: Context = None) -> str:
    """Simulate deleting records with elicitation for confirmation.

    Demonstrates ctx.elicit() — requesting structured input from the user
    during tool execution. The LLM client will prompt the user for confirmation.
    """
    if not confirm:
        result = await ctx.elicit(
            message=f"Are you sure you want to delete all records from '{table}'? This cannot be undone.",
            response_type=bool,
        )

        if result.action != "accept" or not result.data:
            await ctx.info("Delete cancelled by user")
            return "Operation cancelled."

    await ctx.warning(f"Simulating delete of all records from '{table}'")
    await asyncio.sleep(0.5)
    return f"(Simulated) Deleted all records from '{table}'."


@mcp.tool
async def process_items(items: list[str], ctx: Context) -> str:
    """Process a list of items with detailed progress reporting.

    Demonstrates progress reporting for batch operations where
    total is known upfront and progress increments per item.
    """
    results = []
    total = len(items)
    await ctx.info(f"Processing {total} items...")

    for i, item in enumerate(items):
        await ctx.report_progress(progress=i + 1, total=total)
        await ctx.info(f"Processing: {item}")
        await asyncio.sleep(0.2)
        results.append(f"Processed: {item.upper()}")

    await ctx.info("All items processed")
    return json.dumps(results)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
