# Step 06: Lifespans, Tasks, and Composition

This step refactors the financial server to use three advanced FastMCP features: **lifespans** for resource management, **background tasks** for long-running operations, and **server composition** for combining multiple servers.

## Lifespans

A lifespan manages resources that should be created once at startup and cleaned up on shutdown. Instead of opening a new database connection for every tool call, the lifespan opens a single connection when the server starts and closes it when the server stops.

### The `@lifespan` Decorator

```python
from fastmcp.server.lifespan import lifespan

@lifespan
async def db_lifespan(server):
    db = DatabasePool(config.database_path_resolved)
    await db.connect()
    try:
        yield {"db": db}
    finally:
        await db.close()

mcp = FastMCP("FinancialData", lifespan=db_lifespan)
```

The function runs up to `yield` at startup, and everything after `yield` runs at shutdown. The dict passed to `yield` becomes the **lifespan context** — tools access it via `ctx.lifespan_context`:

```python
def get_db(ctx: Context) -> DatabasePool:
    return ctx.lifespan_context["db"]
```

### DatabasePool

The `DatabasePool` class in `database.py` wraps a persistent `aiosqlite` connection. It provides the same `execute_query` and `get_table_info` methods as the per-request functions but reuses a single connection.

## Background Tasks

Tools decorated with `task=True` run as background tasks. The client receives a task ID immediately and can poll for progress and results.

```python
@mcp.tool(task=True)
async def export_report(query_description: str, sql: str, ctx: Context) -> str:
    ...
```

Background tasks require the `tasks` extra:

```bash
uv add "fastmcp[tasks]>=2.14.0"
```

The `export_report` tool executes a query and formats the results as CSV. Because it allows up to 50,000 rows, it can take longer than a normal tool call, making it a good fit for background execution.

## Server Composition

FastMCP servers can be composed using `mount()`. The `server.py` file demonstrates mounting the financial server under a namespace:

```python
from fastmcp import FastMCP
from financial_server import mcp as financial_mcp

main = FastMCP("UniversityServices")
main.mount(financial_mcp, namespace="finance")
```

When mounted with a namespace, all tools, resources, and prompts from the child server are prefixed. For example, `query_sql` becomes `finance_query_sql`. This allows multiple servers to be combined without name collisions.

## Architecture

| File | Purpose |
|------|---------|
| `server.py` | Composition entry point — mounts the financial server under a namespace |
| `financial_server.py` | Child server with lifespan and background task (mounted by `server.py`) |
| `database.py` | Added `DatabasePool` class for persistent connections |
