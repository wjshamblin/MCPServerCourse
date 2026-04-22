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
