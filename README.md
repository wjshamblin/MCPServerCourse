# Step 07: Mount an Existing FastAPI App as an MCP Server

This lesson remixes step 04. The domain is identical — the university
general-ledger database, its schema, and the same fund-accounting
content — but the framing is different. Instead of authoring MCP tools
and resources directly, we build a plain **FastAPI** app and then wrap
it with one line:

```python
mcp = FastMCP.from_fastapi(app=app)
```

FastMCP reads the FastAPI app's OpenAPI spec and creates one MCP tool
per endpoint — automatically.

## The punchline

Compare this branch's `server.py` with the step 04 `server.py`. Same
data layer (`config.py`, `database.py`, `data/university_gl.db`), same
domain content (fund types, chart of accounts, departments). What
changes is the framing: FastAPI first, MCP wrapping second.

One file, two interfaces:

| Interface | URL | Consumer |
|---|---|---|
| REST | `http://localhost:8000/query`, `/schema/tables`, `/domain/funds`, … | Normal HTTP clients, curl, dashboards |
| MCP | `http://localhost:8000/mcp` | Claude Desktop, Cursor, VS Code Copilot, any MCP client |

## The three pieces of `server.py`

1. **A plain FastAPI app.** Nothing MCP-specific. If all you wanted was
   a REST API, you could deploy this as-is.
2. **`FastMCP.from_fastapi(app=app)`.** One line. Every FastAPI route
   becomes an MCP tool.
3. **A combined ASGI app** that splats both route sets into a single
   FastAPI so one `uvicorn` serves both.

## Endpoints → MCP tools

| FastAPI route | MCP tool name (via `operation_id`) |
|---|---|
| `POST /query` | `query_sql` |
| `GET /database/info` | `get_database_info` |
| `GET /schema/tables` | `list_schema_tables` |
| `GET /schema/tables/{table_name}/columns` | `get_schema_table_columns` |
| `GET /domain/funds` | `get_domain_funds` |
| `GET /domain/accounts` | `get_domain_accounts` |
| `GET /domain/departments` | `get_domain_departments` |

## Why `operation_id` matters

Without it, FastMCP invents tool names from the route + method:
`list_tables_schema_tables_get`, `query_sql_query_post`, etc. Ugly and
hard for the LLM to reason about. Always set an explicit
`operation_id=` — FastMCP uses it verbatim as the tool name.

```python
# Good — explicit, readable tool name
@app.get("/database/info", operation_id="get_database_info")
def get_database_info() -> list[dict]: ...

# Ugly tool name: list_tables_schema_tables_get
@app.get("/schema/tables")
def list_tables() -> list[dict]: ...
```

## Running

```bash
uv sync
python server.py
```

Hit both interfaces:

```bash
# REST
curl http://localhost:8000/schema/tables
curl -X POST http://localhost:8000/query \
     -H 'Content-Type: application/json' \
     -d '{"sql": "SELECT COUNT(*) as n FROM gl_transactions"}'

# OpenAPI + Swagger UI (FastAPI's built-ins)
open http://localhost:8000/docs

# MCP — point your MCP client at
http://localhost:8000/mcp
```

## When to use this pattern (and when not to)

**Use `from_fastapi` when:**

- You already have a FastAPI app and want to offer it to LLM clients
  without duplicating the code.
- You're prototyping — it takes one line to get an MCP server running.
- Your REST surface is already shaped the way you'd want the MCP surface
  to look.

**Avoid it when:**

- You're designing the MCP surface from scratch. Purpose-built MCP tools
  with clean parameters almost always beat auto-converted endpoints.
- Your REST API has lots of URL path parameters, nested query params,
  or complex auth — the auto-conversion can get awkward.

The FastMCP team explicitly recommends **hand-crafted MCP tools for
production** — see their blog post
["Stop Converting Your REST APIs to MCP"](https://www.jlowin.dev/blog/stop-converting-rest-apis-to-mcp).
`from_fastapi` is for bootstrapping and prototyping.

## Docs reference

| Topic | Link |
|---|---|
| FastAPI integration | [gofastmcp.com/integrations/fastapi](https://gofastmcp.com/integrations/fastapi) |
| OpenAPI integration (underlying mechanism) | [gofastmcp.com/integrations/openapi](https://gofastmcp.com/integrations/openapi) |
| Mounting an MCP server inside FastAPI | [gofastmcp.com/integrations/fastapi#mounting-an-mcp-server](https://gofastmcp.com/integrations/fastapi#mounting-an-mcp-server) |
| Route mapping (GET → Resource vs Tool) | [gofastmcp.com/integrations/fastapi#custom-route-mapping](https://gofastmcp.com/integrations/fastapi#custom-route-mapping) |
| FastAPI docs | [fastapi.tiangolo.com](https://fastapi.tiangolo.com) |
