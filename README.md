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

## New Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `analyze_text` | `text` | Analyzes text (word count, character count, sentence count, top words) with progress reporting and logging |
| `delete_records` | `table`, `confirm?` | Simulates a destructive delete with elicitation — prompts the user for confirmation unless `confirm=True` |
| `process_items` | `items` | Processes a list of strings with per-item progress reporting |

---

# Step 04: Financial Dataset Generator

This step creates a standalone data generator that produces ~500K+ synthetic university general ledger transactions in SQLite. The resulting database is large enough to overwhelm LLM context windows, which motivates the NL2SQL patterns in later steps.

## Fund Accounting

Universities use **fund accounting** — money is tracked in separate funds based on restrictions and purpose.

| Fund Code | Fund Name | Type | Purpose |
|-----------|-----------|------|---------|
| 10 | General Operating | unrestricted | Primary university operating fund |
| 20 | Restricted Grants | restricted | Sponsored research and grants |
| 25 | Restricted Gifts | restricted | Donor-restricted gifts and endowment income |
| 30 | Endowment | endowment | Endowment principal and investment returns |
| 40 | Auxiliary Enterprises | auxiliary | Self-supporting operations (housing, dining, parking) |
| 50 | Agency Funds | agency | Funds held on behalf of others (student organizations) |
| 60 | Plant Funds | unrestricted | Capital projects and equipment |
| 70 | Loan Funds | restricted | Student loan programs |

## Chart of Accounts

GL account codes follow standard numbering:

| Range | Category |
|-------|----------|
| 1xxx | Assets (cash, receivables, investments, fixed assets) |
| 2xxx | Liabilities (payables, accrued, deferred revenue, bonds) |
| 3xxx | Equity (net assets by restriction level) |
| 4xxx | Revenue (tuition, grants, gifts, investment, auxiliary, clinical) |
| 5xxx-7xxx | Expenses (salaries, benefits, supplies, travel, equipment, services) |

## Fiscal Year

Higher education uses a **July-June fiscal year**:
- FY2025 runs from July 1, 2024 through June 30, 2025
- July = fiscal period 1, June = fiscal period 12

## Encumbrances

An **encumbrance** is a commitment to spend money that hasn't been paid yet (e.g., a purchase order). The dataset includes:
- **Encumbrance entries** — recording the commitment
- **Liquidations** — negative encumbrance amounts when the actual expense posts
- **Types** — purchase orders, contracts, salary commitments, travel authorizations

## Generating the Dataset

```bash
uv sync
uv run python generate_data.py
```

Options:
- `--output PATH` — Output database path (default: `data/university_gl.db`)
- `--transactions N` — Number of transactions to generate (default: 500,000)

The generated `.db` file is gitignored. Generation takes a few minutes and produces a ~100+ MB database.

---

# Step 05: Basic Financial Query Server

This step creates the first "real" MCP server — a database-backed query engine for the university general ledger data generated in step-04.

## Architecture

| File | Purpose |
|------|---------|
| `financial_server.py` | Main MCP server — tools, resources, and entry point |
| `database.py` | Async SQLite layer with SQL validation and safety checks |
| `config.py` | Pydantic settings loaded from environment variables / `.env` file |
| `.env.example` | Template for environment variable configuration |

## Tools

| Tool | Description |
|------|-------------|
| `query_sql(sql)` | Execute a SQL SELECT query against the GL database. Results are capped at 2,000 rows with warnings for large result sets. |
| `get_database_info()` | Returns all table names, column definitions, and row counts. Call this first to understand the schema. |

## Resources

### Schema Resources

| URI | Description |
|-----|-------------|
| `schema://tables` | JSON summary of all tables with row counts and column counts |
| `schema://{table_name}/columns` | Column details (name, type, nullable, primary key) for a specific table |

### Domain Resources

| URI | Description |
|-----|-------------|
| `domain://funds` | Explains university fund accounting types (unrestricted, restricted, endowment, etc.) |
| `domain://accounts` | Chart of accounts structure — account number ranges and expense subcategories |
| `domain://departments` | All departments organized by school |

## SQL Safety

The database layer enforces several safety measures:

- **SELECT-only**: Queries must start with `SELECT`. All other statement types are rejected.
- **Dangerous keyword blocking**: Patterns like `DROP`, `DELETE`, `INSERT`, `UPDATE`, `ALTER`, `CREATE`, `TRUNCATE`, `ATTACH`, SQL comments (`--`, `/*`) are blocked.
- **Table allowlist**: Schema introspection only exposes tables in the allowlist (`gl_transactions`, `departments`, `chart_of_accounts`, `funds`, `grants`).
- **Row limits**: Results are capped at `MAX_ROWS` (default 2,000). Queries exceeding `WARNING_ROWS` (default 100) trigger a client warning.

## Running the Server

```bash
# Generate the database first (step-04)
uv run python generate_data.py

# Copy and edit the environment config
cp .env.example .env

# Start the financial server
uv run python financial_server.py
```

The server starts on `http://0.0.0.0:8000` by default. Connect a client the same way as previous steps, pointing at `http://localhost:8000/mcp`.

---

# Step 06: Natural Language to SQL

This step adds an NL-to-SQL capability so users can ask questions in plain English. An LLM generates a SQL query, the server validates it with the same safety checks as `query_sql`, and executes it.

## How It Works

1. **Question** — User asks a natural language question via the `ask` tool
2. **LLM generates SQL** — The question is sent to an LLM (Anthropic or OpenAI) along with the full database DDL as context
3. **Validation** — The generated SQL passes through the same safety checks as manual queries (SELECT-only, dangerous keyword blocking)
4. **Execution** — The validated query runs against the database and results are returned as JSON

## DDL-Based Context

Rather than using few-shot examples or retrieval, the NL-to-SQL pipeline sends the complete database DDL (CREATE TABLE statements with column comments) to the LLM. This gives the model full knowledge of:

- All table and column names
- Data types and constraints
- Inline comments explaining codes, ranges, and relationships
- Query generation hints (e.g., fiscal year conventions, entry type filters)

## New Tool

| Tool | Description |
|------|-------------|
| `ask(question)` | Ask a natural language question about university financial data. Converts to SQL, validates, executes, and returns results. |

## Prompts

Prompts are reusable templates that help clients construct common financial analysis requests.

| Prompt | Parameters | Description |
|--------|------------|-------------|
| `budget_analysis` | `department`, `fiscal_year` (default 2025) | Budget vs actual analysis for a department |
| `grant_status` | `status` (default "active") | Grant status report filtered by status |
| `department_spending` | `fiscal_year` (default 2025) | Department spending comparison with subcategory breakdown |

## Configuration

Set `LLM_PROVIDER` in `.env` to choose the LLM backend:

```bash
# Anthropic (default)
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-5

# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# OpenAI-compatible proxy
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://your-proxy.example.com/v1
```

## Architecture

| File | Purpose |
|------|---------|
| `nl2sql.py` | NL-to-SQL pipeline — schema context, LLM calls, SQL extraction |
| `financial_server.py` | MCP server — `ask` tool, prompt templates |
| `config.py` | LLM provider settings (API keys, model names, base URLs) |

---

# Step 07: Lifespans, Tasks, and Composition

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

FastMCP servers can be composed using `mount()`. The `composed_server.py` file demonstrates mounting the financial server under a namespace:

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
| `financial_server.py` | Refactored server with lifespan and background task |
| `composed_server.py` | Composition demo — mounts the financial server under a namespace |
| `database.py` | Added `DatabasePool` class for persistent connections |
