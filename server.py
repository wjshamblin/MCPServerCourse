"""
Step 05: NL2SQL — Natural Language to SQL

A database-backed MCP server for querying university general ledger data.
Provides SQL query execution with safety checks, schema resources, and
domain knowledge resources.
"""

import json
import logging

from fastmcp import FastMCP, Context
from fastmcp.prompts import Message

from config import load_config
from database import execute_query, get_table_info, get_column_info, SQLValidationError, DatabaseError
from nl2sql import nl_to_sql

config = load_config()
logging.basicConfig(level=config.get_log_level(), format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "FinancialData",
    instructions=(
        "University General Ledger query server. Use the schema:// resources to "
        "discover tables and columns. Use domain:// resources to understand fund "
        "accounting concepts. Use query_sql to execute SELECT queries."
    ),
)


# === Tools ===


@mcp.tool
async def query_sql(sql: str, ctx: Context) -> str:
    """Execute a SQL SELECT query against the university general ledger database.

    IMPORTANT:
    - Only SELECT queries are allowed (read-only access).
    - Results are limited to 2000 rows. If your query returns more, add a LIMIT clause.
    - Use schema:// resources to discover available tables and columns.
    - Use domain:// resources to understand fund accounting terminology.
    """
    try:
        rows, total = await execute_query(config.database_path_resolved, sql, max_rows=config.max_rows)
    except SQLValidationError as e:
        return f"Query validation error: {e}"
    except DatabaseError as e:
        return f"Database error: {e}"

    if total > config.warning_rows:
        await ctx.warning(
            f"Query returned {total:,} rows (showing first {min(total, config.max_rows):,}). "
            f"Consider adding a LIMIT clause or more specific WHERE conditions."
        )

    if total > config.max_rows:
        await ctx.info(f"Results truncated from {total:,} to {config.max_rows:,} rows.")

    return json.dumps({"total_rows": total, "returned_rows": len(rows), "truncated": total > config.max_rows, "data": rows})


@mcp.tool
async def get_database_info(ctx: Context) -> str:
    """Get a summary of all tables, their columns, and row counts.
    Call this first to understand the database structure before writing queries.
    """
    try:
        tables = await get_table_info(config.database_path_resolved)
    except DatabaseError as e:
        return f"Error: {e}"
    await ctx.info(f"Found {len(tables)} tables")
    return json.dumps(tables, indent=2)


# === Schema Resources ===


@mcp.resource("schema://tables", mime_type="application/json")
async def list_tables() -> str:
    """List all available tables with their row counts."""
    tables = await get_table_info(config.database_path_resolved)
    summary = [{"table": t["table_name"], "rows": t["row_count"], "columns": len(t["columns"])} for t in tables]
    return json.dumps(summary, indent=2)


@mcp.resource("schema://{table_name}/columns", mime_type="application/json")
async def table_columns(table_name: str) -> str:
    """Get column details for a specific table."""
    try:
        info = await get_column_info(config.database_path_resolved, table_name)
    except SQLValidationError as e:
        return json.dumps({"error": str(e)})
    return json.dumps(info, indent=2)


# === Domain Resources ===


@mcp.resource("domain://funds", mime_type="text/markdown")
def fund_types() -> str:
    """Explains university fund accounting types."""
    return """# Fund Types in University Accounting

| Fund Code | Name | Type | Description |
|-----------|------|------|-------------|
| 10 | General Operating | Unrestricted | Primary university operations — faculty salaries, utilities, supplies |
| 20 | Restricted Grants | Restricted | Externally sponsored research (NSF, NIH, DOD). Must be spent per grant terms |
| 25 | Restricted Gifts | Restricted | Donor-restricted gifts. Spending limited to donor's specified purpose |
| 30 | Endowment | Endowment | Permanent funds — only investment returns can be spent |
| 40 | Auxiliary Enterprises | Auxiliary | Self-supporting: housing, dining, parking, bookstore |
| 50 | Agency Funds | Agency | Held on behalf of student organizations and affiliates |
| 60 | Plant Funds | Unrestricted | Capital projects, building construction, major equipment |
| 70 | Loan Funds | Restricted | Student loan programs (Perkins, institutional) |

## Key concepts

- **Restricted vs Unrestricted**: Restricted funds have external constraints on how they can be spent
- **Encumbrances**: Commitments (purchase orders, contracts) that reserve budget but haven't been paid
- **Budget vs Actual**: Budget entries show planned spending; actual entries show real spending
- **Indirect Cost Recovery (IDC)**: Overhead charges on grants (~50-60% of direct costs)
"""


@mcp.resource("domain://accounts", mime_type="text/markdown")
def chart_of_accounts() -> str:
    """Explains the chart of accounts structure."""
    return """# Chart of Accounts

University GL accounts follow a standard numbering system:

| Range | Category | Examples |
|-------|----------|----------|
| 1xxx | Assets | Cash, Receivables, Investments, Buildings |
| 2xxx | Liabilities | Accounts Payable, Deferred Revenue, Bonds |
| 3xxx | Net Assets (Equity) | Unrestricted, Temporarily Restricted, Permanently Restricted |
| 4xxx | Revenue | Tuition, Grants, Gifts, Investment Income, Clinical Revenue |
| 5xxx | Salaries & Benefits | Faculty Salaries, Staff Salaries, Benefits, Stipends |
| 6xxx | Operating Expenses | Supplies, Travel, Equipment, Services, Facilities |
| 7xxx | Transfers & Debt | Internal Transfers, Debt Service |

## Key subcategories for expenses

- **salaries** (5110-5140): Faculty, staff, graduate stipends, hourly wages
- **benefits** (5200-5230): Health insurance, retirement, tuition remission
- **supplies** (6100-6130): Office, lab, computer, medical supplies
- **travel** (6200-6220): Domestic, international, conference registration
- **equipment** (6300-6330): Computers, lab equipment, furniture (capital items)
- **services** (6400-6440): Software, cloud computing, consulting, maintenance
"""


@mcp.tool
async def ask(question: str, ctx: Context) -> str:
    """Ask a natural language question about university financial data.

    Converts your question to SQL, executes it, and returns results.
    Examples:
    - "What did Computer Science spend on travel last year?"
    - "Which grants have less than 10% budget remaining?"
    - "Show me total expenses by department for FY2025"
    """
    await ctx.info(f"Understanding question: {question}")

    try:
        sql = await nl_to_sql(question, config)
    except ValueError as e:
        return f"Configuration error: {e}"
    except Exception as e:
        logger.error(f"NL2SQL error: {e}")
        return f"Failed to generate SQL: {e}"

    await ctx.info(f"Generated SQL: {sql}")

    try:
        rows, total = await execute_query(config.database_path_resolved, sql, max_rows=config.max_rows)
    except SQLValidationError as e:
        return f"Generated SQL failed validation: {e}\nSQL: {sql}"
    except DatabaseError as e:
        return f"Query execution error: {e}\nSQL: {sql}"

    if total > config.warning_rows:
        await ctx.warning(f"Query returned {total:,} rows (showing {min(total, config.max_rows):,})")

    return json.dumps({"question": question, "sql": sql, "total_rows": total, "returned_rows": len(rows), "data": rows})


@mcp.resource("domain://departments", mime_type="text/markdown")
def department_list() -> str:
    """Lists all departments organized by school."""
    return """# University Departments

## Arts & Sciences
COMPSCI (Computer Science), MATH (Mathematics), PHYS (Physics), CHEM (Chemistry),
BIO (Biology), ENGLISH (English), HISTORY (History), POLISCI (Political Science),
ECON (Economics), PSYCH (Psychology), SOCIOL (Sociology), PHILO (Philosophy),
ROMANCE (Romance Studies), STATS (Statistical Science), NEURO (Neuroscience)

## Engineering
ECE (Electrical & Computer Engineering), MECHENG (Mechanical Engineering),
CIVENG (Civil & Environmental Engineering), BME (Biomedical Engineering),
MATSCI (Materials Science)

## Medicine
MEDSCHOOL (School of Medicine), PATHOL (Pathology), PEDS (Pediatrics),
SURG (Surgery), NEUROMD (Neurology), CARDIO (Cardiology),
ONCOL (Oncology), RADIOL (Radiology)

## Law
LAW (School of Law), LAWCLIN (Law Clinical Programs)

## Business
BUSINESS (School of Business), FINANCE (Finance Department), MKTG (Marketing)

## Other Schools
PUBPOL (Public Policy), ENVIRON (Environmental Policy), NURSING (School of Nursing),
DIVINITY (Divinity School), GRADSCH (Graduate School Administration)

## Central Administration
PROVOST (Provost Office), FINAID (Financial Aid), REGIST (Registrar),
ITDEPT (Information Technology), FACMGMT (Facilities Management), HR (Human Resources),
LIBR (University Libraries), ATHLET (Athletics), ALUMNI (Alumni Affairs),
RESADM (Research Administration)
"""


# === Prompts ===


@mcp.prompt
def budget_analysis(department: str, fiscal_year: int = 2025) -> list[Message]:
    """Generate a budget vs actual analysis request for a department."""
    return [
        Message(
            f"Analyze the budget vs actual spending for the {department} department "
            f"in fiscal year {fiscal_year}. Compare budgeted amounts to actual spending "
            f"by account category. Highlight any categories that are over or under budget "
            f"by more than 10%."
        ),
    ]


@mcp.prompt
def grant_status(status: str = "active") -> list[Message]:
    """Generate a grant status report request."""
    return [
        Message(
            f"Generate a report of all {status} grants. For each grant, show: "
            f"grant name, PI, sponsor, department, total budget, remaining budget, "
            f"and percentage spent. Flag any grants with less than 10% budget remaining."
        ),
    ]


@mcp.prompt
def department_spending(fiscal_year: int = 2025) -> list[Message]:
    """Generate a department spending comparison request."""
    return [
        Message(
            f"Compare total actual spending across all departments for fiscal year "
            f"{fiscal_year}. Break down by expense subcategory (salaries, supplies, "
            f"travel, equipment, services). Show the top 10 departments by total spending."
        ),
    ]


if __name__ == "__main__":
    mcp.run(transport="http", host=config.server_host, port=config.server_port)
