# Step 04: Financial Dataset & Query Server

This step creates a synthetic university general ledger dataset and a database-backed MCP server to query it. The dataset is large enough (~500K+ rows) to overwhelm LLM context windows, which motivates the SQL-based query patterns used here and the NL2SQL approach in later steps.

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

## Server Architecture

| File | Purpose |
|------|---------|
| `server.py` | Main MCP server — tools, resources, and entry point |
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
# Generate the database first
uv run python generate_data.py

# Copy and edit the environment config
cp .env.example .env

# Start the financial server
uv run python server.py
```

The server starts on `http://0.0.0.0:8000` by default. Connect a client the same way as previous steps, pointing at `http://localhost:8000/mcp`.
