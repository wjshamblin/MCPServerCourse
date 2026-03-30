# MCP Server Course: From Hello World to Enterprise Auth

## Overview

A progressive, branch-based course teaching FastMCP (Python) server development. Each of 10 git branches (`step-01` through `step-10`) builds on the previous, introducing new concepts. Target audience: competent programmers unfamiliar with MCP, NL2SQL, or Azure OAuth.

All servers use HTTP streamable transport. All code uses the latest FastMCP Python SDK (https://gofastmcp.com).

## Dataset: University General Ledger

~500K+ synthetic financial transactions modeled on a large university's general ledger system.

### Schema: `gl_transactions` table
- `transaction_id` (TEXT, PK) — UUID
- `fiscal_year` (INTEGER) — 2022, 2023, 2024, 2025
- `fiscal_period` (INTEGER) — 1-12 (July=1 for higher-ed fiscal year)
- `transaction_date` (TEXT) — ISO date
- `posting_date` (TEXT) — ISO date
- `department_code` (TEXT) — e.g., "CHEM", "COMPSCI", "ATHLET"
- `department_name` (TEXT) — e.g., "Chemistry", "Computer Science", "Athletics"
- `fund_code` (TEXT) — e.g., "10", "20", "30", "40", "50"
- `fund_name` (TEXT) — e.g., "General Operating", "Restricted Grants", "Endowment", "Auxiliary", "Agency"
- `fund_type` (TEXT) — "unrestricted", "restricted", "endowment", "auxiliary", "agency"
- `account_code` (TEXT) — natural GL account code, e.g., "5110", "6200"
- `account_name` (TEXT) — e.g., "Faculty Salaries", "Lab Supplies"
- `account_category` (TEXT) — "revenue", "expense", "asset", "liability", "equity"
- `account_subcategory` (TEXT) — e.g., "salaries", "benefits", "supplies", "travel", "equipment", "tuition_revenue", "grant_revenue"
- `amount` (REAL) — transaction amount (positive = debit for expenses/assets, credit for revenue/liabilities)
- `budget_amount` (REAL, nullable) — budgeted amount for the line
- `encumbrance_amount` (REAL, nullable) — committed but not yet spent
- `encumbrance_type` (TEXT, nullable) — "purchase_order", "contract", "salary_commitment"
- `vendor_name` (TEXT, nullable) — for expense transactions
- `description` (TEXT) — transaction description
- `grant_id` (TEXT, nullable) — for restricted fund transactions
- `grant_name` (TEXT, nullable) — e.g., "NSF Award #2345678"
- `grant_pi` (TEXT, nullable) — principal investigator name
- `grant_start_date` (TEXT, nullable)
- `grant_end_date` (TEXT, nullable)
- `grant_total_budget` (REAL, nullable)
- `source_system` (TEXT) — "SAP", "Concur", "Workday", "Manual"
- `entry_type` (TEXT) — "actual", "budget", "encumbrance"
- `is_adjustment` (INTEGER) — 0 or 1

### Supporting tables
- `departments` — department_code, department_name, division, school
- `chart_of_accounts` — account_code, account_name, account_category, account_subcategory, normal_balance
- `funds` — fund_code, fund_name, fund_type, description
- `grants` — grant_id, grant_name, grant_pi, sponsor, start_date, end_date, total_budget, remaining_budget, status

### Data characteristics
- 50+ departments across schools (Arts & Sciences, Engineering, Medicine, Law, Business, etc.)
- ~80 GL accounts in the chart of accounts
- 5 fund types with realistic distributions (70% operating, 15% grants, 5% endowment, 7% auxiliary, 3% agency)
- 4 fiscal years (2022-2025)
- Grant data with PIs, sponsors (NSF, NIH, DOD, DOE, private foundations), start/end dates, budgets
- Encumbrances on ~15% of expense transactions
- Adjustments on ~3% of transactions
- Seasonal patterns (higher spending in Q1/Q4 of fiscal year)
- Realistic vendor names for expense categories

## Branch Progression

### step-01: Hello World MCP Server (20 min)

**Files created:**
- `server.py` — minimal FastMCP server with `echo` and `add` tools
- `requirements.txt` — `fastmcp`
- `README.md` — what MCP is, how to install, how to connect

**Concepts:**
- What is MCP (Model Context Protocol)
- The `@mcp.tool` decorator
- Type annotations drive schema generation
- HTTP streamable transport
- Running with `mcp.run(transport="http")`

**Code sketch:**
```python
from fastmcp import FastMCP

mcp = FastMCP("HelloWorld", instructions="A simple demo server.")

@mcp.tool
def echo(message: str) -> str:
    """Echo a message back."""
    return f"Echo: {message}"

@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

### step-02: Resources and Prompts (25 min)

**Files modified:** `server.py`
**Concepts:** `@mcp.resource`, `@mcp.prompt`, resource templates, MIME types, `Message` class

**Additions:**
- Static resource (`resource://about`)
- Dynamic resource (`resource://server-time`)
- Resource template (`resource://greeting/{name}`)
- Prompt for code review (`code_review` prompt with `language` and `code` params)
- Prompt for summarization

### step-03: Context, Logging, and Elicitation (25 min)

**Files modified:** `server.py`
**Concepts:** `Context` injection, `ctx.info/warning/error`, `ctx.report_progress`, `ctx.elicit`

**Additions:**
- Tool that uses Context for logging
- Tool with progress reporting (simulated long operation)
- Tool that uses elicitation to confirm a destructive action

### step-04: Financial Dataset Generator (15 min)

**Files created:**
- `generate_data.py` — script to generate ~500K+ transactions into SQLite
- `data/` directory for the generated database

**Concepts:** Domain introduction — fund accounting, chart of accounts, encumbrances, fiscal years

### step-05: Basic Financial Query Server (35 min)

**Files created:**
- `financial_server.py` — SQLite-backed MCP server
- `database.py` — async database layer with SQL safety
- `config.py` — Pydantic settings

**Replaces:** `server.py` from steps 01-03 (those were learning exercises)

**Tools:**
- `query_sql(sql: str)` — execute SELECT queries with row limits
- `get_database_info()` — list tables, schemas, row counts

**Resources:**
- `schema://tables` — table listing
- `schema://{table_name}/columns` — column details with types
- `domain://funds` — fund type explanations
- `domain://accounts` — chart of accounts hierarchy
- `domain://departments` — department listing by school/division

**Concepts:** SQL injection prevention (whitelist tables/columns, block dangerous keywords), row limits with warnings, domain resources for LLM context

### step-06: Natural Language to SQL (40 min)

**Files modified:** `financial_server.py`, `database.py`
**Files created:** `nl2sql.py` — NL-to-SQL pipeline

**Tools added:**
- `ask(question: str)` — natural language → SQL → results

**Prompts added:**
- `budget_analysis` — template for budget vs actual queries
- `grant_status` — template for grant balance/status queries
- `department_spending` — template for department expense analysis

**Concepts:** DDL-based prompt construction, domain context injection, LLM provider integration, result size management (token estimation, truncation warnings)

### step-07: Lifespans, Tasks, and Composition (30 min)

**Files modified:** `financial_server.py`
**Files created:** `composed_server.py` — demonstrates mounting

**Additions:**
- Lifespan for database connection pool (setup/teardown)
- `export_report` tool with `task=True` for background CSV generation
- `composed_server.py` that mounts the financial server with namespace

**Concepts:** `@lifespan` decorator, yielded context dict, `task=True` for async execution, `mcp.mount()` with namespaces

### step-08: Azure OAuth — Confidential Client (45 min)

**Files modified:** `financial_server.py`, `config.py`
**Files created:**
- `docs/azure-setup-step08.md` — Azure portal walkthrough
- `.env.example` — environment variable template

**Additions:**
- `OAuthProxy` with Azure AD configuration
- `get_authenticated_user` tool
- Token access via `get_access_token()`
- User identity in query audit logging

**Azure setup doc covers:**
- Creating app registration in Azure Portal
- Setting redirect URI (`http://localhost:8000/mcp/oauth/callback`)
- Creating client secret
- Exposing an API → custom scope `access_as_user`
- API permissions (delegated): `openid`, `profile`, `email`, `offline_access`
- `.env` variable mapping

### step-09: Azure Public Client + Security (30 min)

**Files modified:** `financial_server.py`, `config.py`
**Files created:**
- `docs/azure-setup-step09.md` — changes from step-08
- `audit.py` — audit logging with hash chain

**Additions:**
- Public client flow (no client secret, PKCE enabled)
- User allowlist (email-based authorization)
- Audit logging (FERPA-style tamper-detected hash chain)

**Azure setup doc covers:**
- Enabling "Allow public client flows" in app registration
- Removing client secret
- Why public clients + PKCE are more secure for certain deployments
- Platform configuration for mobile/desktop
- When to use confidential vs public clients

### step-10: OBO Flow — Directory Server (50 min)

**Files created:**
- `directory_server.py` — directory lookup MCP server
- `token_exchange.py` — OBO token cache and exchange
- `ms_graph_client.py` — MS Graph API wrapper
- `directory_service.py` — business logic
- `models.py` — Pydantic models for user results
- `docs/azure-setup-step10.md` — two app registrations walkthrough
- `composed_server.py` updated to mount both financial + directory

**Tools:**
- `find_user(query: str)` — search by name, email, NetID
- `find_users_batch(queries: list[str])` — bulk lookup
- `get_user_groups(user_id: str)` — group memberships
- `health_check()` — service status

**Resources:**
- `directory://auth/user` — authenticated user info

**Azure setup doc covers:**
- Creating a SECOND app registration for the directory server
- Exposing an API with `access_as_user` scope
- Adding MS Graph delegated permissions: `User.Read.All`, `Directory.Read.All`
- Configuring `knownClientApplications` for consent propagation
- Admin consent: when it's required and how to grant it
- The OBO token exchange flow (diagram)
- Two `.env` sections: financial server credentials + directory server credentials

**Concepts:** On-Behalf-Of grant type, two-token architecture, token caching (TTL + LRU), downstream API calls with delegated permissions, PII sanitization in logs, batch API calls

## Implementation Approach

- Initialize git repo on `main` with just a README
- Create each `step-XX` branch from the previous step's branch
- Use parallel agents in worktrees for independent stages
- Each branch includes a README explaining that stage's concepts

## Parallelization Plan

**Wave 1 (independent):**
- step-01, step-04 (dataset generator)

**Wave 2 (depends on wave 1):**
- step-02 (from step-01), step-05 (needs step-04's schema knowledge)

**Wave 3:**
- step-03 (from step-02), step-06 (from step-05)

**Wave 4:**
- step-07 (from step-06)

**Wave 5:**
- step-08 (from step-07)

**Wave 6:**
- step-09 (from step-08)

**Wave 7:**
- step-10 (from step-09)
