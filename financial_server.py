"""
Step 08a: Duke OIDC Authentication

Adds:
- Duke OIDC authentication via OIDCProxy
- Custom IntrospectionTokenVerifier for scope validation
- Encrypted persistent token storage
"""

import csv
import io
import json
import logging
from pathlib import Path
from typing import Any

import httpx

from fastmcp import FastMCP, Context
from fastmcp.server.auth import AccessToken, TokenVerifier
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.lifespan import lifespan
from fastmcp.prompts import Message
from key_value.aio.stores.disk import DiskStore
from key_value.aio.wrappers.encryption.fernet import FernetEncryptionWrapper

from config import load_config, DukeOIDCSettings
from database import DatabasePool, SQLValidationError, DatabaseError
from nl2sql import nl_to_sql

config = load_config()
duke_config = DukeOIDCSettings()
logging.basicConfig(level=config.get_log_level(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


class IntrospectionTokenVerifier(TokenVerifier):
    """Token verifier using OAuth 2.0 Token Introspection (RFC 7662).

    Duke OIDC tokens don't include scope claims in JWTs, so standard
    JWT validation can't verify scopes. Instead, we call Duke's
    introspection endpoint which returns the full token metadata
    including scopes.
    """

    def __init__(self, introspection_endpoint: str, client_id: str, client_secret: str):
        self.introspection_endpoint = introspection_endpoint
        self.client_id = client_id
        self.client_secret = client_secret

    async def verify_token(self, token: str) -> AccessToken | None:
        """Verify a token by calling the introspection endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.introspection_endpoint,
                data={"token": token},
                auth=(self.client_id, self.client_secret),
            )

            if response.status_code != 200:
                logger.error(f"Introspection failed: {response.status_code}")
                return None

            data = response.json()

            if not data.get("active", False):
                logger.warning("Token is not active")
                return None

            # Build claims from introspection response
            claims = {
                "sub": data.get("sub", ""),
                "client_id": data.get("client_id", ""),
                "scope": data.get("scope", ""),
                "dukeNetID": data.get("dukeNetID", ""),
                "email": data.get("email", ""),
                "name": data.get("name", ""),
                "given_name": data.get("given_name", ""),
                "family_name": data.get("family_name", ""),
                "dukeUniqueID": data.get("dukeUniqueID", ""),
                "dukePrimaryAffiliation": data.get("dukePrimaryAffiliation", ""),
            }

            scopes = data.get("scope", "").split() if data.get("scope") else []
            return AccessToken(token=token, claims=claims, scopes=scopes)


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


# === Duke OIDC Auth Setup ===

auth = None
if duke_config.oidc_enabled:
    # Fetch OIDC configuration to get introspection endpoint
    oidc_config = httpx.get(duke_config.oidc_well_known_url).json()
    introspection_endpoint = oidc_config.get("introspection_endpoint")

    # Create token verifier using introspection
    token_verifier = IntrospectionTokenVerifier(
        introspection_endpoint=introspection_endpoint,
        client_id=duke_config.oidc_client_id,
        client_secret=duke_config.oidc_client_secret,
    )

    # Set up encrypted persistent token storage
    storage_path = Path(duke_config.storage_dir)
    storage_path.mkdir(parents=True, exist_ok=True)
    client_storage = FernetEncryptionWrapper(
        DiskStore(directory=storage_path),
        source_material=duke_config.oidc_client_secret,
        salt="mcp-server-course",
    )

    auth = OIDCProxy(
        config_url=duke_config.oidc_well_known_url,
        client_id=duke_config.oidc_client_id,
        client_secret=duke_config.oidc_client_secret,
        base_url=duke_config.base_url,
        token_verifier=token_verifier,
        client_storage=client_storage,
        extra_authorize_params={"scope": duke_config.oidc_scopes},
    )
    logger.info("Duke OIDC authentication enabled")


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


# === Tools ===


@mcp.tool
async def query_sql(sql: str, ctx: Context) -> str:
    """Execute a SQL SELECT query against the university general ledger database.

    Only SELECT queries are allowed. Results limited to 2000 rows.
    """
    db = get_db(ctx)
    try:
        rows, total = await db.execute_query(sql, max_rows=config.max_rows)
    except SQLValidationError as e:
        return f"Query validation error: {e}"
    except DatabaseError as e:
        return f"Database error: {e}"

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
    await ctx.info(f"Understanding: {question}")
    db = get_db(ctx)

    try:
        sql = await nl_to_sql(question, config)
    except Exception as e:
        return f"Failed to generate SQL: {e}"

    await ctx.info(f"Generated SQL: {sql}")

    try:
        rows, total = await db.execute_query(sql, max_rows=config.max_rows)
    except (SQLValidationError, DatabaseError) as e:
        return f"Query error: {e}\nSQL: {sql}"

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
    """Get information about the currently authenticated Duke user.

    Returns the user's identity from their Duke OIDC token including
    NetID, email, name, and affiliation.
    """
    token = get_access_token()
    if token is None:
        return json.dumps({"error": "Not authenticated"})

    claims = token.claims or {}
    return json.dumps({
        "netid": claims.get("dukeNetID", "unknown"),
        "email": claims.get("email", "unknown"),
        "name": claims.get("name", "unknown"),
        "given_name": claims.get("given_name", ""),
        "family_name": claims.get("family_name", ""),
        "duke_unique_id": claims.get("dukeUniqueID", ""),
        "affiliation": claims.get("dukePrimaryAffiliation", ""),
        "sub": claims.get("sub", ""),
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


if __name__ == "__main__":
    mcp.run(transport="http", host=config.server_host, port=config.server_port)
