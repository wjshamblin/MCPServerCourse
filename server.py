"""
Step 07: Mount an existing FastAPI app as an MCP server

This lesson remixes step 04. The domain is identical — the university
general-ledger database, its schema, and the same fund-accounting
knowledge — but the framing is different:

  1. We first build a plain **FastAPI** app exposing the data as a REST
     API (``POST /query``, ``GET /database/info``, ``GET /schema/...``,
     ``GET /domain/...``).
  2. Then we wrap it with ``FastMCP.from_fastapi(app)`` — one line —
     and the same endpoints are now discoverable as MCP tools.
  3. We serve *both* interfaces from one uvicorn process by splatting
     the MCP ASGI app's routes into a combined FastAPI.

The pedagogical punch: compare this file to step 04's ``server.py``.
Same data, same query logic, same domain content. What changes is the
framing — you can author in the FastAPI style you already know and get
an MCP server for free.

Docs:
  - FastAPI integration: https://gofastmcp.com/integrations/fastapi
  - OpenAPI integration: https://gofastmcp.com/integrations/openapi

Run:
  python server.py

Then:
  REST:  curl http://localhost:8000/database/info
  MCP:   point your MCP client at http://localhost:8000/mcp/
"""

import logging

from fastapi import FastAPI, HTTPException
from fastmcp import FastMCP
from pydantic import BaseModel, Field

from config import load_config
from database import (
    DatabaseError,
    SQLValidationError,
    execute_query,
    get_column_info,
    get_table_info,
)

config = load_config()
logging.basicConfig(
    level=config.get_log_level(),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# 1. The FastAPI app — a plain REST API over the GL database
# -----------------------------------------------------------------------------
# This is a normal FastAPI server. Nothing MCP-specific yet. If you only
# care about REST, you could stop here and deploy it as-is.
#
# Two things to notice that matter later:
#   * Every route has an explicit ``operation_id=`` — FastMCP uses this
#     as the MCP tool name, and auto-generated names are ugly
#     (e.g. ``list_tables_schema_tables_get``).
#   * Every route has a docstring — FastMCP propagates it to the tool
#     description so LLMs know what the tool does.
# =============================================================================


class QueryRequest(BaseModel):
    sql: str = Field(..., description="A read-only SELECT or WITH query.")


class QueryResponse(BaseModel):
    total_rows: int
    returned_rows: int
    truncated: bool
    data: list[dict]


app = FastAPI(
    title="University GL API",
    version="1.0.0",
    description=(
        "Read-only REST API for the university general-ledger database. "
        "The same surface is exposed as an MCP server via FastMCP.from_fastapi()."
    ),
)


@app.post("/query", response_model=QueryResponse, operation_id="query_sql")
async def query_sql(request: QueryRequest) -> QueryResponse:
    """Execute a read-only SELECT query.

    Only SELECT (or WITH … SELECT) is allowed — see ``database.validate_sql``.
    Results are truncated to ``MAX_ROWS`` (default 2000); the response
    indicates whether truncation occurred.
    """
    try:
        rows, total = await execute_query(
            config.database_path_resolved, request.sql, max_rows=config.max_rows
        )
    except SQLValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))

    return QueryResponse(
        total_rows=total,
        returned_rows=len(rows),
        truncated=total > config.max_rows,
        data=rows,
    )


@app.get("/database/info", operation_id="get_database_info")
async def get_database_info() -> list[dict]:
    """Return a summary of every table — columns and row counts.

    Call this first when exploring the database. Pair it with
    ``/schema/tables/{table}/columns`` for full column details.
    """
    try:
        return await get_table_info(config.database_path_resolved)
    except DatabaseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/schema/tables", operation_id="list_schema_tables")
async def list_schema_tables() -> list[dict]:
    """List all tables with row counts and column counts."""
    tables = await get_table_info(config.database_path_resolved)
    return [
        {"table": t["table_name"], "rows": t["row_count"], "columns": len(t["columns"])}
        for t in tables
    ]


@app.get(
    "/schema/tables/{table_name}/columns", operation_id="get_schema_table_columns"
)
async def get_schema_table_columns(table_name: str) -> dict:
    """Get column details (name, type, nullable, sample values) for one table."""
    try:
        return await get_column_info(config.database_path_resolved, table_name)
    except SQLValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


# --- Domain knowledge endpoints ----------------------------------------------
# In step 04 these were MCP resources (read-only, URI-addressed). In
# FastAPI they're just GET endpoints that return markdown. After
# FastMCP.from_fastapi(), the LLM sees them as tools it can call.


_FUND_TYPES_MD = """# Fund Types in University Accounting

| Fund Code | Name | Type | Description |
|-----------|------|------|-------------|
| 10 | General Operating | Unrestricted | Primary operations — faculty salaries, utilities, supplies |
| 20 | Restricted Grants | Restricted | Externally sponsored research (NSF, NIH, DOD) |
| 25 | Restricted Gifts | Restricted | Donor-restricted gifts with specified purposes |
| 30 | Endowment | Endowment | Permanent funds — only investment returns can be spent |
| 40 | Auxiliary Enterprises | Auxiliary | Self-supporting: housing, dining, parking, bookstore |
| 50 | Agency Funds | Agency | Held on behalf of student organizations |
| 60 | Plant Funds | Unrestricted | Capital projects, building construction |
| 70 | Loan Funds | Restricted | Student loan programs (Perkins, institutional) |

## Key concepts

- **Restricted vs Unrestricted**: Restricted funds have external spending constraints.
- **Encumbrances**: Commitments (POs, contracts) that reserve budget but aren't yet paid.
- **Budget vs Actual**: Budget entries show planned spending; actual entries show real spending.
- **Indirect Cost Recovery (IDC)**: Overhead charges on grants (~50–60% of direct costs).
"""

_ACCOUNTS_MD = """# Chart of Accounts

University GL accounts follow a standard numbering system:

| Range | Category | Examples |
|-------|----------|----------|
| 1xxx | Assets | Cash, Receivables, Investments, Buildings |
| 2xxx | Liabilities | Accounts Payable, Deferred Revenue, Bonds |
| 3xxx | Net Assets (Equity) | Unrestricted, Temporarily Restricted, Permanently Restricted |
| 4xxx | Revenue | Tuition, Grants, Gifts, Investment Income |
| 5xxx | Salaries & Benefits | Faculty, Staff, Stipends, Benefits |
| 6xxx | Operating Expenses | Supplies, Travel, Equipment, Services |
| 7xxx | Transfers & Debt | Internal Transfers, Debt Service |

## Key expense subcategories

- **salaries** (5110–5140): Faculty, staff, graduate stipends, hourly wages
- **benefits** (5200–5230): Health insurance, retirement, tuition remission
- **supplies** (6100–6130): Office, lab, computer, medical supplies
- **travel** (6200–6220): Domestic, international, conference registration
- **equipment** (6300–6330): Computers, lab equipment, furniture
- **services** (6400–6440): Software, cloud, consulting, maintenance
"""

_DEPARTMENTS_MD = """# University Departments

## Arts & Sciences
COMPSCI, MATH, PHYS, CHEM, BIO, ENGLISH, HISTORY, POLISCI, ECON, PSYCH,
SOCIOL, PHILO, ROMANCE, STATS, NEURO

## Engineering
ECE, MECHENG, CIVENG, BME, MATSCI

## Medicine
MEDSCHOOL, PATHOL, PEDS, SURG, NEUROMD, CARDIO, ONCOL, RADIOL

## Law
LAW, LAWCLIN

## Business
BUSINESS, FINANCE, MKTG

## Other Schools
PUBPOL, ENVIRON, NURSING, DIVINITY, GRADSCH

## Central Administration
PROVOST, FINAID, REGIST, ITDEPT, FACMGMT, HR, LIBR, ATHLET, ALUMNI, RESADM
"""


@app.get("/domain/funds", operation_id="get_domain_funds")
def get_domain_funds() -> dict:
    """University fund-accounting taxonomy (markdown inside a JSON envelope).

    Use this to understand what fund codes 10/20/25/... mean before
    querying the ``funds`` table.
    """
    return {"markdown": _FUND_TYPES_MD}


@app.get("/domain/accounts", operation_id="get_domain_accounts")
def get_domain_accounts() -> dict:
    """The chart-of-accounts numbering scheme (1xxx–7xxx)."""
    return {"markdown": _ACCOUNTS_MD}


@app.get("/domain/departments", operation_id="get_domain_departments")
def get_domain_departments() -> dict:
    """All university departments, grouped by school."""
    return {"markdown": _DEPARTMENTS_MD}


# =============================================================================
# 2. Wrap the FastAPI app as an MCP server
# -----------------------------------------------------------------------------
# One line. ``FastMCP.from_fastapi()`` inspects ``app.openapi()`` and
# creates one MCP tool per route. Because every route has an
# ``operation_id=``, the tool names are clean: ``query_sql``,
# ``get_database_info``, etc.
# =============================================================================

mcp = FastMCP.from_fastapi(
    app=app,
    name="FinancialData (via FastAPI)",
)


# =============================================================================
# 3. Serve both interfaces from one process
# -----------------------------------------------------------------------------
# The recipe from https://gofastmcp.com/integrations/fastapi#offering-an-
# llm-friendly-api: build the MCP ASGI app, then create a combined
# FastAPI that splats both route sets and borrows the MCP lifespan.
#
#   REST: http://localhost:8000/query, /database/info, /schema/..., /domain/...
#   MCP:  http://localhost:8000/mcp/
# =============================================================================

mcp_app = mcp.http_app(path="/mcp")

combined_app = FastAPI(
    title="University GL — REST + MCP",
    version="1.0.0",
    description="Both a normal FastAPI REST API and an MCP server, from the same code.",
    lifespan=mcp_app.lifespan,
    routes=[*mcp_app.routes, *app.routes],
)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        combined_app,
        host=config.server_host,
        port=config.server_port,
    )
