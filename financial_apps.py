"""
Step 11: MCP Apps — Interactive Financial Dashboards

Three interactive MCP Apps that render inside AI client conversations
(Claude Desktop, Cursor, VS Code Copilot). Each app uses FastMCPApp
with Prefab UI components for server-driven interactive UIs.

Apps:
  1. Department Spending Dashboard (spending_app)
     - Select department and fiscal year from dropdowns
     - Bar chart comparing budget vs actual by expense category
     - Key totals (actual spend, budget)

  2. Grant Portfolio Monitor (grant_app)
     - Filter grants by sponsor (NSF, NIH, DOD...) and status (active/closed)
     - Cards with progress bars showing % spent
     - Click a grant to drill into spending by category (bar chart)
       and recent transactions

  3. Grant Spending Projection (projection_app)
     - Select a grant and projection timeframe (4-24 months)
     - Key metrics: budget, remaining, avg monthly spend, months to exhaustion
     - Area chart of monthly spending history
     - Line chart of cumulative spend vs budget with future projection

All backend tools are exposed to both the app UI (via CallTool) and
the LLM (via model=True), so the same data is accessible with or
without the interactive UI.

Requires: fastmcp[apps], prefab-ui, aiosqlite
Auth: inherited from the server that registers the apps (financial_server.py)
"""

import logging

from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Column, Row, Heading, Text, Badge, Separator, Metric,
    ForEach, If, Form, Select, SelectOption, Button,
    Card, CardHeader, CardTitle, CardContent, Progress,
)
from prefab_ui.components.charts import AreaChart, BarChart, ChartSeries, LineChart
from prefab_ui.actions import SetState, ShowToast
from prefab_ui.actions.mcp import CallTool
from prefab_ui.rx import ERROR, RESULT, Rx, STATE

from fastmcp import FastMCPApp

from database import execute_query, DatabaseError
from config import load_config

logger = logging.getLogger(__name__)
config = load_config()
db_path = config.database_path_resolved


# =============================================================================
# App 1: Department Spending Dashboard (FastMCPApp with selectors)
# =============================================================================

spending_app = FastMCPApp("SpendingDashboard")


@spending_app.tool(model=True)
async def get_spending(department_code: str = "COMPSCI", fiscal_year: str = "2025") -> dict:
    """Query budget vs actual spending by expense subcategory for a department."""
    logger.info(f"get_spending called: department_code={department_code!r}, fiscal_year={fiscal_year!r}")
    fy = int(fiscal_year)
    sql = f"""
        SELECT
            account_subcategory as category,
            ROUND(SUM(CASE WHEN entry_type = 'actual' THEN amount ELSE 0 END), 2) as actual,
            ROUND(SUM(CASE WHEN entry_type = 'budget' THEN budget_amount ELSE 0 END), 2) as budget
        FROM gl_transactions
        WHERE department_code = '{department_code}'
          AND fiscal_year = {fy}
          AND account_category = 'expense'
        GROUP BY account_subcategory
        HAVING actual > 0 OR budget > 0
        ORDER BY actual DESC
    """
    try:
        rows, _ = await execute_query(db_path, sql, max_rows=50)
    except DatabaseError:
        rows = []

    total_actual = sum(r["actual"] for r in rows)
    total_budget = sum(r["budget"] for r in rows)

    return {
        "department": department_code,
        "fiscal_year": fy,
        "total_actual": round(total_actual, 2),
        "total_budget": round(total_budget, 2),
        "categories": rows,
    }


@spending_app.ui()
async def spending_dashboard() -> PrefabApp:
    """Open the Department Spending Dashboard — select a department and fiscal
    year to see budget vs actual spending by expense category."""

    with Column(gap=4, css_class="p-6") as view:
        Heading("Department Spending Dashboard", level=2)
        Text("Select a department and fiscal year, then click Load.",
             css_class="text-gray-400 text-sm")

        # --- Selectors ---
        with Form(
            on_submit=CallTool(
                get_spending,
                arguments={
                    "department_code": STATE.department_code,
                    "fiscal_year": STATE.fiscal_year,
                },
                on_success=[
                    SetState("spending", RESULT),
                    ShowToast("Spending data loaded", variant="success"),
                ],
            ),
            css_class="mt-2",
        ):
            with Row(gap=3, css_class="items-end flex-wrap"):
                with Select(name="department_code", label="Department", css_class="w-52"):
                    SelectOption(value="COMPSCI", label="Computer Science")
                    SelectOption(value="CHEM", label="Chemistry")
                    SelectOption(value="PHYS", label="Physics")
                    SelectOption(value="MATH", label="Mathematics")
                    SelectOption(value="BIO", label="Biology")
                    SelectOption(value="ECE", label="Electrical & Computer Eng")
                    SelectOption(value="BME", label="Biomedical Engineering")
                    SelectOption(value="MECHENG", label="Mechanical Engineering")
                    SelectOption(value="ECON", label="Economics")
                    SelectOption(value="PSYCH", label="Psychology")
                    SelectOption(value="MEDSCHOOL", label="School of Medicine")
                    SelectOption(value="LAW", label="School of Law")
                    SelectOption(value="BUSINESS", label="School of Business")
                    SelectOption(value="ATHLET", label="Athletics")
                    SelectOption(value="ITDEPT", label="Information Technology")
                    SelectOption(value="LIBR", label="University Libraries")
                    SelectOption(value="FACMGMT", label="Facilities Management")
                    SelectOption(value="NURSING", label="School of Nursing")
                with Select(name="fiscal_year", label="Fiscal Year", css_class="w-32"):
                    SelectOption(value="2025", label="FY2025")
                    SelectOption(value="2024", label="FY2024")
                    SelectOption(value="2023", label="FY2023")
                    SelectOption(value="2022", label="FY2022")
                Button("Load", variant="default")

        Separator()

        # --- Results ---
        with If("spending"):
            with Row(gap=6, css_class="mb-2"):
                with Column(gap=0):
                    Text("Total Actual", css_class="text-xs text-gray-400")
                    Text(Rx("spending.total_actual"), css_class="font-mono text-lg")
                with Column(gap=0):
                    Text("Total Budget", css_class="text-xs text-gray-400")
                    Text(Rx("spending.total_budget"), css_class="font-mono text-lg")

            with If("spending.categories"):
                BarChart(
                    data=Rx("spending.categories"),
                    series=[
                        ChartSeries(data_key="actual", label="Actual Spending", color="#ef4444"),
                        ChartSeries(data_key="budget", label="Budget", color="#3b82f6"),
                    ],
                    x_axis="category",
                )

    # Pre-load with default department
    initial = await get_spending("COMPSCI", "2025")
    return PrefabApp(view=view, state={
        "spending": initial,
        "department_code": "COMPSCI",
        "fiscal_year": "2025",
    })


# =============================================================================
# App 2: Grant Portfolio Monitor (FastMCPApp with filters and drill-down)
# =============================================================================

grant_app = FastMCPApp("GrantPortfolio")


@grant_app.tool(model=True)
async def get_grants(sponsor_filter: str = "", status_filter: str = "") -> list[dict]:
    """Get grants with optional sponsor and status filtering."""
    logger.info(f"get_grants called: sponsor_filter={sponsor_filter!r}, status_filter={status_filter!r}")
    conditions = []
    if sponsor_filter and sponsor_filter != "All Sponsors":
        conditions.append(f"g.sponsor = '{sponsor_filter}'")
    if status_filter and status_filter != "All Status":
        conditions.append(f"g.status = '{status_filter}'")

    where_clause = ""
    if conditions:
        where_clause = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT
            g.grant_id,
            g.title as grant_name,
            g.pi_name as grant_pi,
            g.sponsor,
            g.department,
            g.total_budget,
            g.remaining_budget,
            g.status,
            g.start_date,
            g.end_date,
            ROUND((g.total_budget - g.remaining_budget) / g.total_budget * 100, 1) as pct_spent
        FROM grants g
        {where_clause}
        ORDER BY pct_spent DESC
        LIMIT 50
    """
    try:
        rows, _ = await execute_query(db_path, sql, max_rows=50)
    except DatabaseError:
        rows = []
    return rows


@grant_app.tool(model=True)
async def get_grant_detail(grant_id: str) -> dict:
    """Get spending breakdown by category and recent transactions for a grant."""
    category_sql = f"""
        SELECT
            account_subcategory as category,
            ROUND(SUM(amount), 2) as spent
        FROM gl_transactions
        WHERE grant_id = '{grant_id}'
          AND entry_type = 'actual'
          AND amount > 0
        GROUP BY account_subcategory
        ORDER BY spent DESC
    """
    try:
        categories, _ = await execute_query(db_path, category_sql, max_rows=20)
    except DatabaseError:
        categories = []

    txn_sql = f"""
        SELECT
            transaction_date,
            account_name,
            account_subcategory,
            ROUND(amount, 2) as amount,
            vendor_name,
            description
        FROM gl_transactions
        WHERE grant_id = '{grant_id}'
          AND entry_type = 'actual'
          AND amount > 0
        ORDER BY transaction_date DESC
        LIMIT 15
    """
    try:
        transactions, _ = await execute_query(db_path, txn_sql, max_rows=15)
    except DatabaseError:
        transactions = []

    return {
        "categories": categories,
        "transactions": transactions,
    }


@grant_app.ui()
async def grant_portfolio() -> PrefabApp:
    """Open the Grant Portfolio Monitor — filter by sponsor and status,
    click a grant to see spending breakdown and transactions."""

    with Column(gap=4, css_class="p-6") as view:
        Heading("Grant Portfolio Monitor", level=2)
        Text("Filter by sponsor and status, then click a grant for details.",
             css_class="text-gray-400 text-sm")

        # --- Filters ---
        with Form(
            on_submit=CallTool(
                get_grants,
                arguments={
                    "sponsor_filter": STATE.sponsor_filter,
                    "status_filter": STATE.status_filter,
                },
                on_success=[
                    SetState("grants", RESULT),
                    SetState("selected_grant", ""),
                    SetState("detail", None),
                    ShowToast("Grants filtered", variant="success"),
                ],
            ),
            css_class="mt-2",
        ):
            with Row(gap=3, css_class="items-end flex-wrap"):
                with Select(name="sponsor_filter", label="Sponsor", css_class="w-48"):
                    SelectOption(value="All Sponsors", label="All Sponsors")
                    SelectOption(value="NSF", label="NSF")
                    SelectOption(value="NIH", label="NIH")
                    SelectOption(value="DOD", label="DOD")
                    SelectOption(value="DOE", label="DOE")
                    SelectOption(value="NASA", label="NASA")
                    SelectOption(value="DARPA", label="DARPA")
                    SelectOption(value="HHMI", label="HHMI")
                    SelectOption(value="Gates Foundation", label="Gates Foundation")
                    SelectOption(value="Mellon Foundation", label="Mellon Foundation")
                    SelectOption(value="Ford Foundation", label="Ford Foundation")
                    SelectOption(value="Sloan Foundation", label="Sloan Foundation")
                    SelectOption(value="Simons Foundation", label="Simons Foundation")
                    SelectOption(value="ACS", label="ACS")
                    SelectOption(value="AHA", label="AHA")
                    SelectOption(value="NEH", label="NEH")
                with Select(name="status_filter", label="Status", css_class="w-36"):
                    SelectOption(value="All Status", label="All Status")
                    SelectOption(value="active", label="Active")
                    SelectOption(value="closed", label="Closed")
                    SelectOption(value="pending", label="Pending")
                Button("Filter", variant="default")

        Separator()

        # --- Grant List ---
        with ForEach("grants") as grant:
            with Card(
                css_class="mb-2 cursor-pointer hover:bg-gray-800",
                on_click=CallTool(
                    get_grant_detail,
                    arguments={"grant_id": grant.grant_id},
                    on_success=[
                        SetState("selected_grant", grant.grant_name),
                        SetState("selected_grant_id", grant.grant_id),
                        SetState("detail", RESULT),
                        ShowToast("Grant details loaded", variant="info"),
                    ],
                ),
            ):
                with CardHeader():
                    with Row(gap=3, css_class="justify-between items-center"):
                        CardTitle(grant.grant_name, css_class="text-sm")
                        with Row(gap=1):
                            Badge(grant.sponsor, variant="default")
                            Badge(grant.status, variant="secondary")
                with CardContent():
                    with Row(gap=4, css_class="text-xs text-gray-400"):
                        Text(grant.grant_pi)
                        Text(grant.department)
                    with Row(gap=2, css_class="items-center mt-2"):
                        Progress(value=grant.pct_spent, css_class="flex-1")
                        Text(grant.pct_spent, css_class="font-mono text-xs w-12 text-right")
                        Text("%", css_class="text-xs text-gray-500")

        Separator()

        # --- Grant Detail (after clicking a grant) ---
        with If("selected_grant"):
            Heading(Rx("selected_grant"), level=3)

            with If("detail.categories"):
                Text("Spending by Category", css_class="text-sm text-gray-400 mt-2 mb-1")
                BarChart(
                    data=Rx("detail.categories"),
                    series=[ChartSeries(data_key="spent", label="Spent", color="#ef4444")],
                    x_axis="category",
                )

            with If("detail.transactions"):
                Text("Recent Transactions", css_class="text-sm text-gray-400 mt-4 mb-1")
                with ForEach("detail.transactions") as txn:
                    with Row(gap=4, css_class="py-1 border-b border-gray-800 text-xs"):
                        Text(txn.transaction_date, css_class="text-gray-500 font-mono w-20")
                        Text(txn.account_name, css_class="flex-1 truncate")
                        Text(txn.vendor_name, css_class="text-gray-500 truncate w-32")
                        Text(txn.amount, css_class="font-mono text-right w-20")

    # Pre-load with active grants
    initial_grants = await get_grants(status_filter="active")
    return PrefabApp(
        view=view,
        state={
            "grants": initial_grants,
            "selected_grant": "",
            "selected_grant_id": "",
            "detail": None,
            "sponsor_filter": "All Sponsors",
            "status_filter": "active",
        },
    )


# =============================================================================
# App 3: Grant Spending Projection (LineChart with future projection)
# =============================================================================

projection_app = FastMCPApp("SpendingProjection")


@projection_app.tool(model=True)
async def get_grant_list() -> list[dict]:
    """Get active grants for the dropdown selector."""
    sql = """
        SELECT grant_id, title as grant_name, pi_name, sponsor,
               total_budget, remaining_budget, status, start_date, end_date
        FROM grants
        WHERE status = 'active'
        ORDER BY title
        LIMIT 100
    """
    try:
        rows, _ = await execute_query(db_path, sql, max_rows=100)
    except DatabaseError:
        rows = []
    return rows


@projection_app.tool(model=True)
async def get_spending_projection(grant_id: str = "", projection_months: str = "4") -> dict:
    """Get monthly spending history and compute a linear projection."""
    num_months = min(int(projection_months), 24)
    logger.info(f"get_spending_projection called: grant_id={grant_id!r}, months={num_months}")

    if not grant_id:
        return {"error": "No grant selected", "history": [], "projection": [], "stats": {}}

    # Get grant info
    grant_sql = f"""
        SELECT grant_id, title, pi_name, sponsor, department,
               total_budget, remaining_budget, status, start_date, end_date
        FROM grants WHERE grant_id = '{grant_id}'
    """
    try:
        grant_rows, _ = await execute_query(db_path, grant_sql, max_rows=1)
    except DatabaseError:
        grant_rows = []

    if not grant_rows:
        return {"error": "Grant not found", "history": [], "projection": [], "stats": {}}

    grant = grant_rows[0]

    # Get monthly spending by fund type
    history_sql = f"""
        SELECT
            fiscal_year,
            fiscal_period,
            fund_name,
            ROUND(SUM(amount), 2) as monthly_spend
        FROM gl_transactions
        WHERE grant_id = '{grant_id}'
          AND entry_type = 'actual'
          AND amount > 0
        GROUP BY fiscal_year, fiscal_period, fund_name
        ORDER BY fiscal_year, fiscal_period
    """
    try:
        history_rows, _ = await execute_query(db_path, history_sql, max_rows=500)
    except DatabaseError:
        history_rows = []

    # Convert fiscal periods to readable month labels
    period_to_month = {
        1: "Jul", 2: "Aug", 3: "Sep", 4: "Oct", 5: "Nov", 6: "Dec",
        7: "Jan", 8: "Feb", 9: "Mar", 10: "Apr", 11: "May", 12: "Jun",
    }

    # Aggregate by period across fund types for total line
    period_totals = {}
    fund_data = {}
    for row in history_rows:
        fy = row["fiscal_year"]
        fp = row["fiscal_period"]
        month_label = f"{period_to_month.get(fp, '?')} FY{fy}"
        fund = row["fund_name"]
        spend = row["monthly_spend"]

        period_totals[month_label] = period_totals.get(month_label, 0) + spend

        if fund not in fund_data:
            fund_data[fund] = {}
        fund_data[fund][month_label] = fund_data[fund].get(month_label, 0) + spend

    # Build history chart data
    # Use grant's authoritative spent amount, not raw transaction sums
    all_months = list(period_totals.keys())
    total_budget = grant["total_budget"]
    remaining = grant["remaining_budget"]
    actual_spent = total_budget - remaining

    # Scale monthly spending proportionally so cumulative matches actual_spent
    raw_total = sum(period_totals.values())
    scale = actual_spent / raw_total if raw_total > 0 else 0

    history_chart = []
    cumulative = 0
    for month in all_months:
        spend = period_totals.get(month, 0) * scale
        cumulative += spend
        history_chart.append({
            "month": month,
            "actual": round(spend, 2),
            "cumulative": round(cumulative, 2),
        })

    # Compute projection: average of last 6 months (scaled)
    recent_spends = [period_totals[m] * scale for m in all_months[-6:]] if len(all_months) >= 6 else [v * scale for v in period_totals.values()]
    avg_monthly = sum(recent_spends) / len(recent_spends) if recent_spends else 0

    # Build combined timeline: history + projected future
    combined_chart = []
    for row in history_chart:
        combined_chart.append({
            "month": row["month"],
            "cumulative": row["cumulative"],
            "budget": round(total_budget, 2),
        })

    # Add projected months
    cumulative_projected = actual_spent  # start from authoritative spent
    if avg_monthly > 0:
        for i in range(1, num_months + 1):
            cumulative_projected += avg_monthly
            combined_chart.append({
                "month": f"+{i}mo",
                "cumulative": round(min(cumulative_projected, total_budget), 2),
                "budget": round(total_budget, 2),
            })

    stats = {
        "grant_name": grant["title"],
        "pi": grant["pi_name"],
        "sponsor": grant["sponsor"],
        "total_budget": total_budget,
        "remaining": remaining,
        "pct_spent": round((total_budget - remaining) / total_budget * 100, 1),
        "avg_monthly": round(avg_monthly, 2),
        "months_remaining": round(remaining / avg_monthly, 1) if avg_monthly > 0 else 0,
    }

    return {
        "history": history_chart,
        "combined": combined_chart,
        "stats": stats,
    }


@projection_app.ui()
async def grant_projection() -> PrefabApp:
    """Open the Grant Spending Projection — select a grant to see spending
    history by fund type and a projected budget exhaustion timeline."""

    # Pre-load grant list for dropdown
    grants_list = await get_grant_list()

    with Column(gap=4, css_class="p-6") as view:
        Heading("Grant Spending Projection", level=2)
        Text("Select a grant to see monthly spending history by fund and projected burn rate.",
             css_class="text-gray-400 text-sm")

        # --- Grant Selector + Projection Months ---
        with Form(
            on_submit=CallTool(
                get_spending_projection,
                arguments={
                    "grant_id": STATE.selected_grant_id,
                    "projection_months": STATE.projection_months,
                },
                on_success=[
                    SetState("projection_data", RESULT),
                    ShowToast("Projection loaded", variant="success"),
                ],
                on_error=ShowToast("Failed to load projection", variant="error"),
            ),
            css_class="mt-2",
        ):
            with Row(gap=3, css_class="items-end flex-wrap"):
                with Select(name="selected_grant_id", label="Grant", css_class="w-80"):
                    for g in grants_list:
                        SelectOption(
                            value=g["grant_id"],
                            label=f"{g['grant_name'][:45]} ({g['sponsor']})",
                        )
                with Select(name="projection_months", label="Project Forward", css_class="w-36"):
                    SelectOption(value="4", label="4 months")
                    SelectOption(value="6", label="6 months")
                    SelectOption(value="9", label="9 months")
                    SelectOption(value="12", label="12 months")
                    SelectOption(value="18", label="18 months")
                    SelectOption(value="24", label="24 months")
                Button("Analyze", variant="default")

        Separator()

        # --- Stats ---
        with If("projection_data.stats"):
            with Row(gap=4, css_class="flex-wrap mb-2"):
                Metric(
                    label="Total Budget",
                    value=Rx("projection_data.stats.total_budget"),
                )
                Metric(
                    label="Remaining",
                    value=Rx("projection_data.stats.remaining"),
                )
                Metric(
                    label="% Spent",
                    value=Rx("projection_data.stats.pct_spent"),
                )
                Metric(
                    label="Avg Monthly Spend",
                    value=Rx("projection_data.stats.avg_monthly"),
                )
                Metric(
                    label="Months to Exhaustion",
                    value=Rx("projection_data.stats.months_remaining"),
                    trend="down",
                    trend_sentiment="negative",
                )

            Separator()

            # --- Monthly spending history (area chart) ---
            with If("projection_data.history"):
                Heading("Monthly Spending History", level=3)
                AreaChart(
                    data=Rx("projection_data.history"),
                    series=[ChartSeries(data_key="actual", label="Monthly Spend", color="#ef4444")],
                    x_axis="month",
                )

            # --- Combined cumulative + budget line ---
            with If("projection_data.combined"):
                Heading("Cumulative Spend vs Budget", level=3)
                Text("Actual spending + projected future (dashed = projection)",
                     css_class="text-gray-400 text-xs mb-1")
                LineChart(
                    data=Rx("projection_data.combined"),
                    series=[
                        ChartSeries(data_key="cumulative", label="Cumulative Spend", color="#ef4444"),
                        ChartSeries(data_key="budget", label="Total Budget", color="#3b82f6"),
                    ],
                    x_axis="month",
                )

    return PrefabApp(
        view=view,
        state={
            "selected_grant_id": grants_list[0]["grant_id"] if grants_list else "",
            "projection_months": "4",
            "projection_data": None,
        },
    )
