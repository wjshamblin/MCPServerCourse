"""
Step 11: Financial Server with Azure Public Client Auth + MCP Apps

Adds:
- Everything from step 10 (lifespan, OAuth, audit, OBO — when mounted)
- Three interactive MCP Apps (spending_app, grant_app, projection_app)
  rendered inside MCP clients via Prefab UI components.
"""

import csv
import io
import json
import logging

from fastmcp import FastMCP, Context
from fastmcp.server.lifespan import lifespan
from fastmcp.server.auth import OAuthProxy
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.dependencies import get_access_token
from fastmcp.prompts import Message

from audit import AuditLogger
from config import load_config
from database import DatabasePool, SQLValidationError, DatabaseError
from financial_apps import spending_app, grant_app, projection_app
from nl2sql import nl_to_sql

config = load_config()
logging.basicConfig(level=config.get_log_level(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

audit = AuditLogger(config.audit_log_dir)


# === Lifespan ===


@lifespan
async def db_lifespan(server):
    """Open database on startup, close on shutdown.

    The yielded dict becomes the 'lifespan context' —
    tools access it via ctx.lifespan_context['db'].
    """
    db = DatabasePool(config.database_path_resolved)
    await db.connect()
    try:
        yield {"db": db}
    finally:
        await db.close()


# === Auth Setup ===

auth = None
if config.auth_enabled:
    tenant = config.azure_tenant_id
    token_verifier = JWTVerifier(
        jwks_uri=f"https://login.microsoftonline.com/{tenant}/discovery/v2.0/keys",
        issuer=f"https://login.microsoftonline.com/{tenant}/v2.0",
        audience=config.azure_client_id,
    )
    auth = OAuthProxy(
        upstream_authorization_endpoint=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
        upstream_token_endpoint=f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
        upstream_client_id=config.azure_client_id,
        upstream_client_secret=config.azure_client_secret,
        upstream_scopes=[config.full_mcp_scope] + config.additional_auth_scopes_list,
        token_verifier=token_verifier,
        base_url=config.oauth_base_url,
    )
    logger.info("Azure OAuth enabled")

mcp = FastMCP(
    "FinancialData",
    instructions=(
        "University General Ledger query server. Use the schema:// resources to "
        "discover tables and columns. Use domain:// resources to understand fund "
        "accounting concepts. Use query_sql or ask to query the data."
    ),
    lifespan=db_lifespan,
    auth=auth,
)


def get_db(ctx: Context) -> DatabasePool:
    """Helper to get the database from lifespan context."""
    return ctx.lifespan_context["db"]


def get_user_email() -> str:
    """Get the current user's email from their token, or 'anonymous'."""
    if not config.auth_enabled:
        return "anonymous"
    token = get_access_token()
    if token and token.claims:
        return token.claims.get("preferred_username", "unknown")
    return "unknown"


def check_user_allowed(email: str) -> bool:
    """Check if user is in the allowlist (if configured)."""
    allowed = config.allowed_users_list
    if not allowed:
        return True
    return email.lower() in allowed


# === Tools ===


@mcp.tool
async def query_sql(sql: str, ctx: Context) -> str:
    """Execute a SQL SELECT query against the university general ledger database.

    Only SELECT queries are allowed. Results limited to 2000 rows.
    """
    user_email = get_user_email()
    if not check_user_allowed(user_email):
        audit.log(user_email, "DENIED", f"query_sql: {sql[:200]}")
        return json.dumps({"error": "Access denied. Your account is not authorized."})

    db = get_db(ctx)
    try:
        rows, total = await db.execute_query(sql, max_rows=config.max_rows)
    except SQLValidationError as e:
        audit.log(user_email, "QUERY_ERROR", str(e))
        return f"Query validation error: {e}"
    except DatabaseError as e:
        audit.log(user_email, "QUERY_ERROR", str(e))
        return f"Database error: {e}"

    audit.log(user_email, "QUERY", sql[:200], result_count=total)

    if total > config.warning_rows:
        await ctx.warning(f"Query returned {total:,} rows (showing {min(total, config.max_rows):,})")

    return json.dumps({"total_rows": total, "returned_rows": len(rows), "data": rows})


@mcp.tool
async def ask(question: str, ctx: Context) -> str:
    """Ask a natural language question about university financial data.

    Converts your question to SQL, executes it, and returns results.
    Examples:
    - "What did Computer Science spend on travel last year?"
    - "Which grants have less than 10% budget remaining?"
    - "Show me total expenses by department for FY2025"
    """
    user_email = get_user_email()
    if not check_user_allowed(user_email):
        audit.log(user_email, "DENIED", f"ask: {question[:200]}")
        return json.dumps({"error": "Access denied. Your account is not authorized."})

    await ctx.info(f"Understanding: {question}")
    db = get_db(ctx)

    try:
        sql = await nl_to_sql(question, config)
    except Exception as e:
        audit.log(user_email, "NL2SQL_ERROR", str(e))
        return f"Failed to generate SQL: {e}"

    await ctx.info(f"Generated SQL: {sql}")

    try:
        rows, total = await db.execute_query(sql, max_rows=config.max_rows)
    except (SQLValidationError, DatabaseError) as e:
        audit.log(user_email, "QUERY_ERROR", f"{e} | SQL: {sql[:100]}")
        return f"Query error: {e}\nSQL: {sql}"

    audit.log(user_email, "NL_QUERY", f"Q: {question[:100]} | SQL: {sql[:100]}", result_count=total)

    return json.dumps({"question": question, "sql": sql, "total_rows": total, "data": rows})


@mcp.tool
async def get_database_info(ctx: Context) -> str:
    """Get a summary of all tables, columns, and row counts."""
    db = get_db(ctx)
    tables = await db.get_table_info()
    return json.dumps(tables, indent=2)


@mcp.tool(task=True)
async def export_report(
    query_description: str,
    sql: str,
    ctx: Context,
) -> str:
    """Export a query result as a CSV report (runs as a background task).

    Use this for large exports that might take a while. The task runs
    in the background and you can check its progress.

    Args:
        query_description: What this report is (e.g., "FY2025 travel expenses")
        sql: The SQL query to execute
    """
    db = get_db(ctx)
    await ctx.info(f"Starting report export: {query_description}")

    try:
        rows, total = await db.execute_query(sql, max_rows=50_000)
    except (SQLValidationError, DatabaseError) as e:
        return f"Export failed: {e}"

    await ctx.info(f"Retrieved {total:,} rows, generating CSV...")

    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    csv_content = output.getvalue()
    await ctx.info(f"Report complete: {len(rows):,} rows, {len(csv_content):,} bytes")

    return json.dumps({
        "description": query_description,
        "sql": sql,
        "total_rows": total,
        "exported_rows": len(rows),
        "csv": csv_content,
    })


@mcp.tool
async def get_authenticated_user() -> str:
    """Get information about the currently authenticated user.

    Returns the user's claims from their Azure AD token.
    """
    token = get_access_token()
    if token is None:
        return json.dumps({"error": "Not authenticated"})

    claims = token.claims or {}
    return json.dumps({
        "email": claims.get("preferred_username", "unknown"),
        "name": claims.get("name", "unknown"),
        "tenant_id": claims.get("tid", "unknown"),
        "token_issuer": claims.get("iss", "unknown"),
    })


# === Schema Resources ===


@mcp.resource("schema://tables", mime_type="application/json")
async def list_tables(ctx: Context) -> str:
    """List all available tables with their row counts."""
    db = get_db(ctx)
    tables = await db.get_table_info()
    summary = [{"table": t["table_name"], "rows": t["row_count"]} for t in tables]
    return json.dumps(summary, indent=2)


# === Domain Resources ===


@mcp.resource("domain://funds", mime_type="text/markdown")
def fund_types() -> str:
    """Explains university fund accounting types."""
    return """# Fund Types in University Accounting

| Fund Code | Name | Type | Description |
|-----------|------|------|-------------|
| 10 | General Operating | Unrestricted | Primary university operations |
| 20 | Restricted Grants | Restricted | Sponsored research (NSF, NIH, DOD) |
| 25 | Restricted Gifts | Restricted | Donor-restricted gifts |
| 30 | Endowment | Endowment | Permanent funds — only returns spent |
| 40 | Auxiliary Enterprises | Auxiliary | Self-supporting: housing, dining, parking |
| 50 | Agency Funds | Agency | Held on behalf of student organizations |
| 60 | Plant Funds | Unrestricted | Capital projects and equipment |
| 70 | Loan Funds | Restricted | Student loan programs |
"""


@mcp.resource("domain://accounts", mime_type="text/markdown")
def chart_of_accounts() -> str:
    """Chart of accounts reference."""
    return """# Chart of Accounts
| Range | Category | Examples |
|-------|----------|----------|
| 1xxx | Assets | Cash, Receivables, Investments |
| 2xxx | Liabilities | Accounts Payable, Deferred Revenue |
| 3xxx | Net Assets | Unrestricted, Restricted |
| 4xxx | Revenue | Tuition, Grants, Gifts |
| 5xxx | Salaries & Benefits | Faculty, Staff, Benefits |
| 6xxx | Operating Expenses | Supplies, Travel, Equipment |
| 7xxx | Transfers & Debt | Internal Transfers, Debt Service |
"""


@mcp.resource("domain://departments", mime_type="text/markdown")
def department_list() -> str:
    """Department listing by school."""
    return """# Departments
Arts & Sciences: COMPSCI, MATH, PHYS, CHEM, BIO, ENGLISH, HISTORY, POLISCI, ECON, PSYCH, SOCIOL, PHILO, ROMANCE, STATS, NEURO
Engineering: ECE, MECHENG, CIVENG, BME, MATSCI
Medicine: MEDSCHOOL, PATHOL, PEDS, SURG, NEUROMD, CARDIO, ONCOL, RADIOL
Law: LAW, LAWCLIN
Business: BUSINESS, FINANCE, MKTG
Other: PUBPOL, ENVIRON, NURSING, DIVINITY, GRADSCH
Admin: PROVOST, FINAID, REGIST, ITDEPT, FACMGMT, HR, LIBR, ATHLET, ALUMNI, RESADM
"""


# === Prompts ===


@mcp.prompt
def budget_analysis(department: str, fiscal_year: int = 2025) -> list[Message]:
    """Budget vs actual analysis for a department."""
    return [Message(f"Analyze budget vs actual for {department} in FY{fiscal_year}.")]


@mcp.prompt
def grant_status(status: str = "active") -> list[Message]:
    """Grant status report."""
    return [Message(f"Report on all {status} grants with budget remaining.")]


@mcp.prompt
def department_spending(fiscal_year: int = 2025) -> list[Message]:
    """Department spending comparison."""
    return [Message(f"Compare department spending for FY{fiscal_year} by category.")]


# === MCP Apps ===
# Interactive dashboards rendered inside MCP clients (Claude Desktop, Cursor,
# etc.) via Prefab UI components. Each app exposes @app.ui() entry points the
# LLM can open, plus @app.tool(model=True) backends callable from both the UI
# and the LLM.
mcp.add_provider(spending_app)
mcp.add_provider(grant_app)
mcp.add_provider(projection_app)


if __name__ == "__main__":
    mcp.run(transport="http", host=config.server_host, port=config.server_port)
