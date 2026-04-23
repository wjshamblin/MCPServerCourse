"""
Step 13: Financial Projections Dashboard — MCP App Capstone

A four-tab Prefab UI backed by a SQLite research-admin dataset:

  * Overview       — four stat cards, a stacked monthly-spending bar
                     chart, a fund-balance donut, and a table of funds.
  * Grants & Funds — per-fund cards: project dates, budget utilization,
                     additional-funding rows, and a personnel roster.
  * Personnel      — stacked-bar effort distribution + per-fund rosters.
  * Transactions   — projected fund flows plus a filterable, sortable
                     transactions table (Fund / Category filters round-trip
                     through ``CallTool`` to the ``get_transactions`` tool).

Every tool is registered with ``model=True`` on a single ``FastMCPApp``,
so the LLM can also call them directly ("summarize my lab's spending
for this quarter") without opening the dashboard.

Data lives in ``data/fin.db`` — see ``db.py`` for schema, seed, and
queries. The seed is deterministic; same numbers every run.

Run:  python server.py
Connect from Claude Desktop / Cursor / VS Code Copilot and open
the "Financial Dashboard" app.
"""

from __future__ import annotations

import logging
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.apps import FastMCPApp
from prefab_ui.actions import SetState
from prefab_ui.actions.mcp import CallTool
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Badge,
    Button,
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
    Column,
    DataTable,
    DataTableColumn,
    Dot,
    ForEach,
    Grid,
    Heading,
    If,
    Metric,
    Row,
    Select,
    SelectOption,
    Separator,
    Tab,
    Tabs,
    Text,
)
from prefab_ui.components.charts import (
    BarChart,
    ChartSeries,
    LineChart,
    PieChart,
)
from prefab_ui.rx import RESULT, STATE, Rx

import db

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


# === Make sure the database is seeded ========================================

if not db.db_exists():
    logger.info("No database found; seeding demo data…")
    db.seed_database()


# === MCP server ==============================================================

mcp = FastMCP(
    "FinancialDashboard",
    instructions=(
        "Research-admin financial projections for a single lab. Open the "
        "'Financial Dashboard' app for an interactive view, or call any of "
        "the data tools directly (get_funds_summary / get_fund_detail / "
        "get_personnel / get_transactions / get_spending_summary / "
        "get_monthly_spending)."
    ),
)

dashboard_app = FastMCPApp("Financial Dashboard")


# === Backing tools ===========================================================
# All are `model=True` so the LLM can drive the dashboard conversationally.


@dashboard_app.tool(model=True)
def get_funds_summary() -> list[dict[str, Any]]:
    """Return every fund with balances, type, and a computed Healthy/Watch status."""
    funds = db.get_all_funds()
    return [
        {
            "id": f["id"],
            "name": f["name"],
            "type": f["type"],
            "available_balance": f["available_balance"],
            "projected_available": f["projected_available"],
            "status": "Healthy" if f["available_balance"] > 30000 else "Watch",
        }
        for f in funds
    ]


@dashboard_app.tool(model=True)
def get_fund_detail(fund_id: str) -> dict[str, Any]:
    """Return one fund plus its personnel roster and additional-funding rows."""
    fund = db.get_fund_by_id(fund_id)
    if fund is None:
        return {"error": f"Fund {fund_id} not found"}

    people = {p["id"]: p for p in db.get_all_personnel()}
    allocations = db.get_effort_allocations_by_fund(fund_id)
    personnel = [
        {
            **a,
            "name": people.get(a["personnel_id"], {}).get("name"),
            "title": people.get(a["personnel_id"], {}).get("title"),
        }
        for a in allocations
    ]
    return {
        **fund,
        "personnel": personnel,
        "additional_funding": db.get_additional_funding(fund_id),
    }


@dashboard_app.tool(model=True)
def get_personnel() -> list[dict[str, Any]]:
    """Return every person with their effort allocations across funds."""
    funds = {f["id"]: f for f in db.get_all_funds()}
    allocations_by_person: dict[int, list[dict[str, Any]]] = {}
    for a in db.get_effort_allocations():
        allocations_by_person.setdefault(a["personnel_id"], []).append(
            {
                "fund_id": a["fund_id"],
                "fund_name": funds.get(a["fund_id"], {}).get("name"),
                "effort_pct": a["effort_pct"],
                "fringe_rate": a["fringe_rate"],
                "projected_total": a["projected_total"],
            }
        )

    return [
        {
            **p,
            "total_effort": sum(e["effort_pct"] for e in allocations_by_person.get(p["id"], [])),
            "allocations": allocations_by_person.get(p["id"], []),
        }
        for p in db.get_all_personnel()
    ]


@dashboard_app.tool(model=True)
def get_transactions(
    fund_id: str | None = None,
    category: str | None = None,
    sort_by: str = "date",
    sort_order: str = "desc",
) -> dict[str, Any]:
    """Return filtered & sorted transactions.

    Args:
        fund_id: Filter to a single fund by ID.
        category: Filter to a single expense category.
        sort_by: One of date, fund_id, category, description, amount. Defaults to date.
        sort_order: asc or desc (default).
    """
    txns = db.get_transactions(
        fund_id=fund_id or None,
        category=category or None,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return {
        "transactions": txns,
        "count": len(txns),
        "total": round(sum(t["amount"] for t in txns), 2),
    }


@dashboard_app.tool(model=True)
def get_spending_summary() -> dict[str, float]:
    """Return the aggregate projections shown on the Overview cards."""
    return db.get_spending_summary()


@dashboard_app.tool(model=True)
def get_monthly_spending(months: int = 6) -> list[dict[str, Any]]:
    """Return monthly totals split personnel vs non-personnel (last N months)."""
    return db.get_monthly_spending(months)


# === UI helpers ==============================================================


_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
           "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _fmt_currency(n: float | int | None) -> str:
    if n is None:
        return "—"
    return f"${round(n):,}"


def _fmt_month(ym: str) -> str:
    """'2026-01' → 'Jan-26'."""
    year, month = ym.split("-")
    return f"{_MONTHS[int(month) - 1]}-{year[-2:]}"


def _fmt_date(d: str | None) -> str:
    """'2024-03-01' → '03/01/24'."""
    if not d:
        return "—"
    y, m, day = d.split("-")
    return f"{m}/{day}/{y[-2:]}"


def _monthly_chart_data() -> list[dict[str, Any]]:
    rows = db.get_monthly_spending(9)
    return [
        {
            "month": _fmt_month(r["month"]),
            "Personnel": r["personnel"],
            "Non-Personnel": r["non_personnel"],
        }
        for r in rows
    ]


def _fund_pie_data(funds: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "name": f"{f['name']} {_fmt_currency(f['available_balance'])}",
            "value": f["available_balance"],
        }
        for f in funds
    ]


def _stat_card(label: str, value: str, *, detail: str | None = None,
               tone: str = "slate") -> None:
    """One Overview stat card. Call inside a Grid."""
    with Card(css_class=f"p-5 border-l-4 border-l-{tone}-500"):
        with Column(gap=1):
            Text(label, css_class="text-xs uppercase tracking-wider text-gray-500")
            Text(value, css_class="text-2xl font-bold text-gray-100")
            if detail:
                Text(detail, css_class="text-xs text-gray-500")


def _labeled_field(label: str, value: str, *, value_class: str = "") -> None:
    """A compact label/value pair used on the fund-detail cards."""
    with Column(gap=0):
        Text(label, css_class="text-xs text-gray-500 uppercase")
        Text(value, css_class=f"font-semibold text-sm text-gray-200 {value_class}")


# === Pre-compute panel data ==================================================
# We build most UI state at app-open time from synchronous queries. The
# Transactions filter is the one place that reloads data via CallTool.


def _build_initial_state() -> dict[str, Any]:
    funds = get_funds_summary()
    details = [get_fund_detail(f["id"]) for f in funds]
    personnel = get_personnel()
    txns = get_transactions(sort_by="date", sort_order="desc")
    summary = get_spending_summary()
    monthly = _monthly_chart_data()
    pie = _fund_pie_data(funds)

    sponsored_total = sum(f["available_balance"] for f in funds if f["type"] == "Sponsored")
    non_sponsored_total = sum(f["available_balance"] for f in funds if f["type"] != "Sponsored")

    # Unique categories (for the Transactions filter dropdown)
    categories = sorted({t["category"] for t in txns["transactions"]})

    # Pre-shape everything the UI binds to. Keep calc out of the UI.
    fund_details = [_shape_fund_detail(fd) for fd in details]
    personnel_rows = [_shape_personnel_row(p) for p in personnel]
    personnel_by_fund = _shape_personnel_by_fund(personnel, funds)
    effort_chart = _shape_effort_chart(personnel)

    return {
        # Tab state
        "tab": "overview",

        # Overview
        "summary": summary,
        "monthly_chart": monthly,
        "pie": pie,
        "sponsored_total": sponsored_total,
        "non_sponsored_total": non_sponsored_total,
        "funds_table": [_shape_funds_row(f) for f in funds],

        # Grants & Funds
        "fund_details": fund_details,

        # Personnel
        "effort_chart": effort_chart,
        "effort_fund_names": sorted(
            {alloc["fund_name"] for p in personnel for alloc in p["allocations"]
             if alloc.get("fund_name")}
        ),
        "personnel_rows": personnel_rows,
        "personnel_by_fund": personnel_by_fund,

        # Transactions
        "filter_fund": "",       # "" means all
        "filter_category": "",   # "" means all
        "filter_sort_by": "date",
        "filter_sort_order": "desc",
        "funds_for_filter": [{"value": f["id"], "label": f["id"]} for f in funds],
        "categories_for_filter": [{"value": c, "label": c} for c in categories],
        "txn_rows": [_shape_txn_row(t) for t in txns["transactions"]],
        "txn_count": txns["count"],
        "txn_total": _fmt_currency(txns["total"]),
    }


def _shape_funds_row(f: dict[str, Any]) -> dict[str, Any]:
    return {
        "name_block": f"{f['name']}\n{f['id']}",
        "name": f["name"],
        "id": f["id"],
        "type": f["type"],
        "available": _fmt_currency(f["available_balance"]),
        "projected": _fmt_currency(f["projected_available"]),
        "status": f["status"],
    }


def _shape_fund_detail(fd: dict[str, Any]) -> dict[str, Any]:
    """Flatten one fund's detail into shape the cards can render directly."""
    utilization = None
    if fd.get("plan_itd") and fd.get("actual_itd"):
        utilization = fd["actual_itd"] / fd["plan_itd"] * 100

    return {
        "id": fd["id"],
        "name": fd["name"],
        "type": fd["type"],
        "sponsor": fd.get("sponsor"),
        "project_dates": (
            f"{_fmt_date(fd.get('project_start'))} — {_fmt_date(fd.get('project_end'))}"
            if fd.get("project_start") else None
        ),
        "budget_period": fd.get("budget_period"),
        "grant_life": (
            f"{fd['grant_life_years']} years"
            if fd.get("grant_life_years") is not None and fd["grant_life_years"] > 0
            else None
        ),
        "fa_rate": (
            f"{round(fd['fa_rate'] * 100)}%" if fd.get("fa_rate") is not None else None
        ),
        "plan_itd": _fmt_currency(fd.get("plan_itd")) if fd.get("plan_itd") else None,
        "actual_itd": _fmt_currency(fd.get("actual_itd")) if fd.get("actual_itd") else None,
        "available": _fmt_currency(fd["available_balance"]),
        "projected_available": (
            _fmt_currency(fd["projected_available"])
            if fd.get("projected_available") is not None else None
        ),
        "utilization_pct": round(utilization, 1) if utilization is not None else None,
        "utilization_bar": min(round(utilization), 100) if utilization is not None else 0,
        "remaining_pct": (
            round(100 - utilization, 1) if utilization is not None else None
        ),
        "additional_funding": [
            {"period": af["period"], "amount_fmt": _fmt_currency(af["amount"])}
            for af in fd.get("additional_funding", [])
        ],
        "personnel_rows": [
            {
                "name": p["name"],
                "title": p["title"],
                "effort_fmt": f"{p['effort_pct'] * 100:.1f}%",
                "fringe_fmt": f"{p['fringe_rate'] * 100:.1f}%",
                "projected_fmt": _fmt_currency(p["projected_total"]),
            }
            for p in fd.get("personnel", [])
        ],
    }


def _shape_personnel_row(p: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": p["name"],
        "title": p["title"],
        "total_effort_fmt": f"{p['total_effort'] * 100:.1f}%",
        "allocation_count": len(p["allocations"]),
    }


def _shape_effort_chart(personnel: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One row per person; one column per fund_name; values are effort%."""
    rows = []
    for p in personnel:
        row: dict[str, Any] = {"name": p["name"]}
        for alloc in p["allocations"]:
            if alloc.get("fund_name"):
                row[alloc["fund_name"]] = round(alloc["effort_pct"] * 100, 1)
        rows.append(row)
    return rows


def _shape_personnel_by_fund(
    personnel: list[dict[str, Any]], funds: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Group personnel under each fund they have effort on."""
    out = []
    for f in funds:
        members = []
        for p in personnel:
            alloc = next((a for a in p["allocations"] if a["fund_id"] == f["id"]), None)
            if alloc:
                members.append({
                    "name": p["name"],
                    "title": p["title"],
                    "effort_fmt": f"{alloc['effort_pct'] * 100:.1f}%",
                    "fringe_fmt": f"{alloc['fringe_rate'] * 100:.1f}%",
                    "projected_fmt": _fmt_currency(alloc["projected_total"]),
                })
        if members:
            out.append({
                "fund_id": f["id"],
                "fund_name": f["name"],
                "members": members,
            })
    return out


def _shape_txn_row(t: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": _fmt_date(t["date"]),
        "fund_id": t["fund_id"],
        "category": t["category"],
        "description": t["description"] or "—",
        "amount_fmt": _fmt_currency(t["amount"]),
    }


# === UI ======================================================================


@dashboard_app.ui()
async def financial_dashboard() -> PrefabApp:
    """Open the financial projections dashboard."""
    initial = _build_initial_state()

    with PrefabApp(
        title="Financial Dashboard",
        state=initial,
        css_class="p-6 max-w-6xl mx-auto space-y-4",
    ) as app:

        # --- Header -----------------------------------------------------
        with Row(gap=3, css_class="items-center justify-between"):
            with Column(gap=0):
                Heading("Financial Projections Dashboard", level=2)
                Text(
                    "Chen Lab · research-admin view · as of 01/31/2026",
                    css_class="text-xs text-gray-500",
                )
            with Row(gap=2, css_class="items-center"):
                Dot(variant="success", size="default")
                Text("Live data", css_class="text-xs text-gray-500")

        # --- Tabs -------------------------------------------------------
        with Tabs(name="tab", value="overview"):
            with Tab(title="Overview", value="overview"):
                _overview_tab()
            with Tab(title="Grants & Funds", value="grants"):
                _grants_tab()
            with Tab(title="Personnel", value="personnel"):
                _personnel_tab()
            with Tab(title="Transactions", value="transactions"):
                _transactions_tab()

    return app


# ---- Overview ---------------------------------------------------------------


def _overview_tab() -> None:
    with Column(gap=4):
        # Stat cards
        with Grid(columns=4, gap=3):
            _stat_card(
                "Total Available Now",
                STATE.summary.total_available.currency(),
                detail=(
                    f"Sponsored {STATE.sponsored_total.currency()} · "
                    f"Non-Sponsored {STATE.non_sponsored_total.currency()}"
                ),
                tone="emerald",
            )
            _stat_card(
                "12-Mo Projected Expenses",
                STATE.summary.total_projected_expenses.currency(),
                detail="Personnel + non-personnel burn",
                tone="blue",
            )
            _stat_card(
                "Projected Incoming",
                STATE.summary.projected_incoming.currency(),
                detail="Future-period award amounts",
                tone="cyan",
            )
            _stat_card(
                "12-Mo Surplus / Deficit",
                STATE.summary.surplus_deficit.currency(),
                detail="Available + incoming − projected expenses",
                tone="amber",
            )

        # Charts
        with Grid(columns=2, gap=3):
            with Card(css_class="p-4"):
                with CardHeader():
                    CardTitle("Monthly Direct Costs")
                    CardDescription("Stacked personnel / non-personnel, last 9 months.")
                with CardContent():
                    BarChart(
                        data=STATE.monthly_chart,
                        series=[
                            ChartSeries(data_key="Personnel", label="Personnel",
                                        color="#3b82f6"),
                            ChartSeries(data_key="Non-Personnel", label="Non-Personnel",
                                        color="#ec4899"),
                        ],
                        x_axis="month",
                        stacked=True,
                        height=260,
                        y_axis_format="compact",
                    )

            with Card(css_class="p-4"):
                with CardHeader():
                    CardTitle("Fund Balances")
                    CardDescription("Available balance per fund.")
                with CardContent():
                    PieChart(
                        data=STATE.pie,
                        data_key="value",
                        name_key="name",
                        inner_radius=55,
                        height=320,
                    )

        # All funds table
        with Card(css_class="p-4"):
            with CardHeader():
                CardTitle("All Funds")
                CardDescription("Balances as of 01/31/2026.")
            with CardContent():
                DataTable(
                    rows=STATE.funds_table,
                    columns=[
                        DataTableColumn(key="name", header="Fund", sortable=True),
                        DataTableColumn(key="id", header="ID"),
                        DataTableColumn(key="type", header="Type", sortable=True),
                        DataTableColumn(key="available", header="Available",
                                        align="right", sortable=True),
                        DataTableColumn(key="projected", header="Proj. Avail",
                                        align="right"),
                        DataTableColumn(key="status", header="Status", align="right"),
                    ],
                )


# ---- Grants & Funds ---------------------------------------------------------


def _grants_tab() -> None:
    with Grid(columns=2, gap=4):
        with ForEach("fund_details") as fund:
            _fund_card(fund)


def _fund_card(fund) -> None:  # noqa: ANN001 — fund is an Rx proxy
    with Card(css_class="p-5 space-y-3"):
        with CardHeader():
            with Row(gap=3, css_class="items-start justify-between"):
                with Column(gap=0):
                    CardTitle(f"{fund.name} — {fund.id}")
                    CardDescription(fund.type)
                Badge(fund.type, variant="default")

        with CardContent():
            with Column(gap=3):
                # Key/value grid — only render rows whose source field is present.
                with Grid(columns=2, gap=2):
                    with If(fund.project_dates):
                        _labeled_field_rx("Project Dates", fund.project_dates)
                    with If(fund.budget_period):
                        _labeled_field_rx("Budget Period", fund.budget_period)
                    with If(fund.grant_life):
                        _labeled_field_rx("Grant Life", fund.grant_life)
                    with If(fund.sponsor):
                        _labeled_field_rx("Sponsor", fund.sponsor)
                    with If(fund.fa_rate):
                        _labeled_field_rx("F&A Rate", fund.fa_rate)
                    with If(fund.plan_itd):
                        _labeled_field_rx("Plan ITD", fund.plan_itd)
                    with If(fund.actual_itd):
                        _labeled_field_rx("Actual ITD", fund.actual_itd)
                    _labeled_field_rx("Available", fund.available,
                                      value_class="text-emerald-400")
                    with If(fund.projected_available):
                        _labeled_field_rx(
                            "Proj. Available", fund.projected_available,
                            value_class="text-emerald-400",
                        )

                # Budget utilization — only when we have both plan and actual ITD.
                with If(fund.utilization_pct):
                    with Column(gap=1):
                        Text("Budget Utilization",
                             css_class="text-xs text-gray-500 uppercase")
                        # Prefab's Progress component takes a 0–100 value.
                        from prefab_ui.components import Progress
                        Progress(value=fund.utilization_bar, variant="info")
                        with Row(gap=2, css_class="justify-between"):
                            Text(Rx("$item").utilization_pct + "% spent",  # noqa: E501
                                 css_class="text-xs text-gray-500")
                            Text(Rx("$item").remaining_pct + "% remaining",  # noqa: E501
                                 css_class="text-xs text-gray-500")

                # Additional-funding rows
                with If(fund.additional_funding):
                    with Column(gap=1):
                        Text("Additional Funding",
                             css_class="text-xs text-gray-500 uppercase")
                        with ForEach(fund.additional_funding) as af:
                            with Row(gap=2, css_class="justify-between"):
                                Text(af.period, css_class="text-sm")
                                Text(af.amount_fmt,
                                     css_class="text-sm text-emerald-400 font-mono")

                # Personnel roster for this fund
                with If(fund.personnel_rows):
                    with Column(gap=1):
                        Text("Personnel",
                             css_class="text-xs text-gray-500 uppercase")
                        DataTable(
                            rows=fund.personnel_rows,
                            columns=[
                                DataTableColumn(key="name", header="Name"),
                                DataTableColumn(key="title", header="Title"),
                                DataTableColumn(key="effort_fmt", header="Effort",
                                                align="right"),
                                DataTableColumn(key="fringe_fmt", header="Fringe",
                                                align="right"),
                                DataTableColumn(key="projected_fmt",
                                                header="Projected", align="right"),
                            ],
                        )


def _labeled_field_rx(label: str, value, *, value_class: str = "") -> None:  # noqa: ANN001
    with Column(gap=0):
        Text(label, css_class="text-xs text-gray-500 uppercase")
        Text(value, css_class=f"font-semibold text-sm text-gray-200 {value_class}")


# ---- Personnel --------------------------------------------------------------


def _personnel_tab() -> None:
    # Effort-distribution stacked bar (horizontal). Colors default.
    with Column(gap=4):
        with Card(css_class="p-4"):
            with CardHeader():
                CardTitle("Effort Distribution")
                CardDescription("Percent of effort by fund, per person.")
            with CardContent():
                # One series per fund name. Built at render time off the
                # precomputed `effort_fund_names` list — safe to use Python
                # iteration here because this runs once at app-open.
                series = [
                    ChartSeries(data_key=name, label=name)
                    for name in _render_effort_fund_names()
                ]
                BarChart(
                    data=STATE.effort_chart,
                    series=series,
                    x_axis="name",
                    stacked=True,
                    horizontal=True,
                    height=max(240, 60 * _render_personnel_count() + 60),
                    y_axis_format="auto",
                )

        # Per-fund personnel cards
        with ForEach("personnel_by_fund") as group:
            with Card(css_class="p-4"):
                with CardHeader():
                    with Row(gap=2, css_class="items-center justify-between"):
                        CardTitle(group.fund_name + " Personnel")
                        Text(group.fund_id, css_class="text-xs text-gray-500 font-mono")
                with CardContent():
                    DataTable(
                        rows=group.members,
                        columns=[
                            DataTableColumn(key="name", header="Name"),
                            DataTableColumn(key="title", header="Title"),
                            DataTableColumn(key="effort_fmt", header="Effort",
                                            align="right"),
                            DataTableColumn(key="fringe_fmt", header="Fringe",
                                            align="right"),
                            DataTableColumn(key="projected_fmt",
                                            header="Projected Total", align="right"),
                        ],
                    )


def _render_effort_fund_names() -> list[str]:
    """Build-time query so the BarChart series list is concrete."""
    personnel = get_personnel()
    return sorted({a["fund_name"] for p in personnel for a in p["allocations"]
                   if a.get("fund_name")})


def _render_personnel_count() -> int:
    return len(db.get_all_personnel())


# ---- Transactions -----------------------------------------------------------


def _transactions_tab() -> None:
    with Column(gap=4):
        # Projected fund flows summary
        with Card(css_class="p-5"):
            with CardHeader():
                CardTitle("Projected Fund Flows")
                CardDescription("12-month projection.")
            with CardContent():
                with Column(gap=1):
                    _flow_row("Current Available Balance",
                              STATE.summary.total_available.currency(),
                              tone="text-emerald-400")
                    _flow_row("Projected Incoming",
                              "+" + STATE.summary.projected_incoming.currency(),
                              tone="text-emerald-400")
                    _flow_row("12-Month Projected Expenses",
                              "−" + STATE.summary.total_projected_expenses.currency(),
                              tone="text-rose-400")
                    Separator()
                    with Row(gap=2, css_class="justify-between items-center"):
                        Badge("Projected Surplus / Deficit", variant="warning")
                        Text(STATE.summary.surplus_deficit.currency(),
                             css_class="font-bold text-lg text-gray-100")

        # Filters + transactions table
        with Card(css_class="p-5"):
            with CardHeader():
                CardTitle("Recent Transactions")
                CardDescription(
                    "Filter by fund or category — each change round-trips to "
                    "the get_transactions tool."
                )
            with CardContent():
                with Column(gap=3):
                    # Filter row
                    with Row(gap=3, css_class="items-end flex-wrap"):
                        with Column(gap=1, css_class="min-w-48"):
                            Text("Fund",
                                 css_class="text-xs text-gray-500 uppercase")
                            with Select(
                                name="filter_fund",
                                placeholder="All funds",
                                on_change=_refilter_action(),
                            ):
                                SelectOption(value="", label="All funds")
                                with ForEach("funds_for_filter") as f:
                                    SelectOption(value=f.value, label=f.label)

                        with Column(gap=1, css_class="min-w-64"):
                            Text("Category",
                                 css_class="text-xs text-gray-500 uppercase")
                            with Select(
                                name="filter_category",
                                placeholder="All categories",
                                on_change=_refilter_action(),
                            ):
                                SelectOption(value="", label="All categories")
                                with ForEach("categories_for_filter") as c:
                                    SelectOption(value=c.value, label=c.label)

                        Button(
                            "Reset",
                            variant="ghost",
                            on_click=[
                                SetState("filter_fund", ""),
                                SetState("filter_category", ""),
                                _refilter_action(),
                            ],
                        )

                    # Table
                    DataTable(
                        rows=STATE.txn_rows,
                        columns=[
                            DataTableColumn(key="date", header="Date", sortable=True),
                            DataTableColumn(key="fund_id", header="Fund",
                                            sortable=True),
                            DataTableColumn(key="category", header="Category",
                                            sortable=True),
                            DataTableColumn(key="description", header="Description"),
                            DataTableColumn(key="amount_fmt", header="Amount",
                                            align="right"),
                        ],
                        paginated=True,
                        page_size=15,
                    )

                    # Footer
                    with Row(gap=2, css_class="justify-between text-sm text-gray-400"):
                        Text(STATE.txn_count + " transactions")
                        Text("Total: " + STATE.txn_total,
                             css_class="font-semibold text-gray-200")


def _flow_row(label: str, value, *, tone: str = "") -> None:  # noqa: ANN001
    with Row(gap=2, css_class="justify-between"):
        Text(label, css_class="text-sm text-gray-300")
        Text(value, css_class=f"text-sm font-mono {tone}")


def _refilter_action():
    """Fire `get_transactions` with current filter state, update table rows."""
    return CallTool(
        get_transactions,
        arguments={
            "fund_id": STATE.filter_fund,
            "category": STATE.filter_category,
            "sort_by": STATE.filter_sort_by,
            "sort_order": STATE.filter_sort_order,
        },
        on_success=[
            # RESULT is the returned dict: {transactions, count, total}.
            # We can't run Python list comprehensions on RESULT inside the
            # wire protocol, so store raw rows in state and let DataTable
            # read them via a computed Rx if needed. In practice the format
            # the UI shows is already close to the raw shape.
            SetState("txn_rows_raw", RESULT["transactions"]),
            SetState("txn_count", RESULT["count"]),
            SetState("txn_total", RESULT["total"]),
        ],
    )


# === Register + run ==========================================================

mcp.add_provider(dashboard_app)


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
