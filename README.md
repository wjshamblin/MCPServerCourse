# Step 13: Financial Projections Dashboard — Capstone

A research-admin financial dashboard built entirely with **FastMCP +
Prefab UI**. Four tabs, SQLite-backed, interactive in any MCP client
that renders MCP Apps (Claude Desktop, Cursor, VS Code Copilot).

This is the capstone for the MCP Apps arc: every pattern from step 12
— `FastMCPApp`, `@app.tool(model=True)`, reactive `STATE`, `CallTool`
actions, `ForEach`, `DataTable`, multiple charts — composed into a
single, production-shaped app. The backing tools are all LLM-callable,
so a user can either open the dashboard *or* ask *"what's my 12-month
surplus / deficit?"* and get the same answer.

## What the dashboard shows

Four tabs, switched via a Prefab `Tabs` container:

| Tab | Contents |
|---|---|
| **Overview** | Four stat cards (Available, Projected Expenses, Projected Incoming, Surplus / Deficit), a stacked monthly-spending bar chart (personnel vs non-personnel), a fund-balance donut, and a sortable funds table. |
| **Grants & Funds** | One `Card` per fund with project dates, budget period, F&A rate, Plan vs Actual ITD, a budget-utilization `Progress` bar, additional-funding rows, and a personnel roster. |
| **Personnel** | A horizontal stacked-bar effort chart (one row per person, one series per fund) plus per-fund personnel tables. |
| **Transactions** | A projected fund-flow summary and a filterable, sortable transactions table. The Fund and Category filters round-trip to `get_transactions` — the one place where a UI change triggers a real server call. |

## Files

```
.
├── server.py     # FastMCP server + FastMCPApp + UI view (4 tabs)
├── db.py         # SQLite schema, deterministic seed, query functions
├── data/fin.db   # auto-created on first run
├── docs/
│   └── slides/13-financial-dashboard.html
├── pyproject.toml
└── README.md
```

Two Python files. No build step, no `npm install`, no browser-side
bundling. The sandboxed renderer inside the MCP host takes the wire
payload from `@dashboard_app.ui()` and turns it into DOM — that's it.

## The six data tools

All are registered with `model=True` on the same `FastMCPApp`, so the
LLM can drive the dashboard conversationally:

| Tool | Purpose |
|---|---|
| `get_funds_summary()` | List funds with balances and a Healthy/Watch status. |
| `get_fund_detail(fund_id)` | One fund + personnel roster + additional-funding rows. |
| `get_personnel()` | People with their effort allocations across funds. |
| `get_transactions(fund_id?, category?, sort_by, sort_order)` | Filterable, sortable transaction list with a total. |
| `get_spending_summary()` | Aggregate projections: available, expenses, incoming, surplus / deficit. |
| `get_monthly_spending(months)` | Monthly totals split personnel vs non-personnel. |

Plus one UI tool: **`financial_dashboard`** — the dashboard itself.

## What this branch demonstrates

This is the proof that **FastMCP + Prefab is enough to build a real
dashboard**. Concretely, the pieces that land on the page:

- **`FastMCPApp`** bundles one UI + its backing tools.
- **`@app.ui()`** returns a `PrefabApp` — the whole view tree is built
  once, seeded with data from synchronous DB calls.
- **`Tabs` / `Tab`** organize the four panels with a reactive `tab`
  state key.
- **`DataTable` + `DataTableColumn`** for sortable, paginated tables —
  no hand-rolled HTML, no `<thead>/<tbody>` plumbing.
- **`BarChart`, `LineChart`, `PieChart`** from `prefab_ui.components.charts`,
  with `stacked=True`, `horizontal=True`, `inner_radius=55` (donuts),
  etc.
- **`ForEach`** iterates over state — so each fund's card is a single
  template instead of four near-duplicates.
- **`Rx` pipes** — `STATE.summary.total_available.currency()` formats
  numbers at render time, no Python f-strings needed.
- **`CallTool(...)`** in the Transactions filter — changing the Fund
  dropdown fires `get_transactions(fund_id=...)` and pipes the result
  into state via `SetState`.
- **`Progress`** for budget-utilization bars on each fund card.
- **`Badge`, `Dot`, `Card`, `Metric`** — the Deploy-Console toolkit,
  now doing real dashboard work.

## Running

```bash
uv sync
python server.py
```

The first run creates `data/fin.db` and seeds it. Subsequent runs skip
re-seeding unless you delete the file.

Connect from Claude Desktop / Cursor / VS Code Copilot. In the app
picker you'll see **Financial Dashboard** — open it to get the
interactive view. Or just ask the model directly:

> *"How much is my lab projected to spend on personnel next year?"*
> *"Show me all transactions over $300 against the R01."*
> *"Which fund has the tightest runway?"*

All seven tools are callable; the model routes the question to the
right ones.

## Re-seed the database

Edit `data/fin.db` away or delete it; it will re-seed on next start.
Or force a reseed without restarting:

```bash
python db.py --force
```

## Docs reference

| Topic | Link |
|---|---|
| MCP Apps overview | [gofastmcp.com/apps/overview](https://gofastmcp.com/apps/overview) |
| `FastMCPApp` | [gofastmcp.com/apps/interactive-apps](https://gofastmcp.com/apps/interactive-apps) |
| Prefab UI (components + actions) | [gofastmcp.com/apps/prefab](https://gofastmcp.com/apps/prefab) |
| Prefab component reference | [prefab.prefect.io/docs/components](https://prefab.prefect.io/docs/components) |
| Local preview: `fastmcp dev apps` | [gofastmcp.com/apps/development](https://gofastmcp.com/apps/development) |
