# Step 12: MCP Apps

An MCP server that demonstrates **[MCP Apps](https://gofastmcp.com/apps/overview)**:
interactive UIs rendered inside the AI client (Claude Desktop, Cursor,
VS Code Copilot) via [Prefab UI](https://gofastmcp.com/apps/prefab)
components, backed by tools that the LLM can also call directly.

Like steps 08–10, this branch deliberately strips earlier-step machinery
(database, auth, OBO) so the App mechanic is the only new concept.

## Quick reference: FastMCP docs

| Topic | Link |
|---|---|
| MCP Apps overview | [gofastmcp.com/apps/overview](https://gofastmcp.com/apps/overview) |
| `FastMCPApp` (interactive apps) | [gofastmcp.com/apps/interactive-apps](https://gofastmcp.com/apps/interactive-apps) |
| Prefab UI (components + actions) | [gofastmcp.com/apps/prefab](https://gofastmcp.com/apps/prefab) |
| Prefab Patterns (copy-paste catalog) | [gofastmcp.com/apps/patterns](https://gofastmcp.com/apps/patterns) |
| Generative UI (LLM writes the UI) | [gofastmcp.com/apps/generative](https://gofastmcp.com/apps/generative) |
| `GenerativeUI` provider reference | [gofastmcp.com/apps/providers/generative](https://gofastmcp.com/apps/providers/generative) |
| Local app preview (`fastmcp dev apps`) | [gofastmcp.com/apps/development](https://gofastmcp.com/apps/development) |
| `ctx.report_progress()` | [gofastmcp.com/servers/progress](https://gofastmcp.com/servers/progress) |
| `ctx.elicit()` | [gofastmcp.com/servers/elicitation](https://gofastmcp.com/servers/elicitation) |
| `Context` (logging, progress, elicit) | [gofastmcp.com/servers/context](https://gofastmcp.com/servers/context) |

## What you get

`server.py` is the only Python file. It exposes **four UI surfaces**
plus a few plain tools:

| Surface | Purpose |
|---|---|
| **Counter** app | One-screen interactive UI: live counter with +1 / +10 / Reset / Refresh buttons. The smallest end-to-end example. |
| **Progress** app | `Loader` / `Ring` / `Progress` components driven by a 4-stage server-side tool chain, so progress is *real* (not faked client-side). |
| **Deploy Console** app | Kitchen-sink dashboard: stat cards, environment-status pills, a Dialog-gated deploy action, and server-side [`ctx.elicit()`](https://gofastmcp.com/servers/elicitation) for rollback confirmation. |
| **Generative UI** provider | Lets the LLM write Prefab UI code at runtime in a Pyodide sandbox. Paired with a seed-data tool (`get_lab_spending`) for a reproducible "visualize this data" demo. |

### Plain tools (no UI)

These are regular LLM-callable tools included alongside the apps so
students can contrast the two surfaces:

| Tool | Purpose |
|---|---|
| `hello(name)` | Smallest possible `@mcp.tool` — a baseline for "this is an MCP tool." |
| `add(a, b)` | Type-annotated numeric tool — shows the auto-generated schema. |
| `render_report(pages)` | Simulates a long-running render and streams progress via [`ctx.report_progress()`](https://gofastmcp.com/servers/progress). Clients with native progress UI (Claude Desktop, Cursor) show a real spinner/bar while it runs. Pairs conceptually with the Progress app. |

## The MCP Apps pattern

See [**Interactive Apps**](https://gofastmcp.com/apps/interactive-apps)
for the full treatment. In ~10 lines:

```python
from fastmcp.apps import FastMCPApp
from prefab_ui.app import PrefabApp
from prefab_ui.components import Button, Column, Heading, Metric
from prefab_ui.actions.mcp import CallTool

counter_app = FastMCPApp("Counter")

@counter_app.tool(model=True)        # callable by UI AND by the LLM
def bump_counter(by: int = 1) -> dict:
    ...

@counter_app.ui()                    # the UI entry point
async def counter_view() -> PrefabApp:
    with Column(...) as view:
        Heading("Counter", level=2)
        Button("+1", on_click=CallTool(bump_counter, arguments={"by": 1}, ...))
    return view

mcp.add_provider(counter_app)        # register the app on the main server
```

Three pieces to internalise:

1. **[`FastMCPApp`](https://gofastmcp.com/apps/interactive-apps)** bundles a UI + the tools that back it.
2. **`@app.tool(model=True)`** marks a function as callable by both the UI
   (via [`CallTool`](https://gofastmcp.com/apps/prefab) actions) and the LLM directly.
   (`model=False` would hide it from the LLM — useful for purely UI-internal helpers.)
3. **`@app.ui()`** returns a [Prefab UI](https://gofastmcp.com/apps/prefab) component tree.
   Buttons fire `CallTool(...)` actions, which round-trip back through MCP to invoke
   the matching tool, then update UI state with `SetState(...)`.

## App: Counter

The minimal end-to-end demo. One screen, one `Metric`, four buttons.
Every button fires a `CallTool(...)` that round-trips to an `@app.tool`
function on the server and pipes the return value into `SetState(...)`
to update the UI.

The state lives *client-side* (under the key `"count"`). The Refresh
button seeds it on first render by calling `get_counter()` and copying
the result back into state.

**See also:** [FastMCPApp](https://gofastmcp.com/apps/interactive-apps)
· [Prefab actions (`CallTool`, `SetState`, `ShowToast`)](https://gofastmcp.com/apps/prefab)

## App: Progress

A visually richer demo. Three panels, top to bottom:

1. **Spinner gallery** — all five `Loader` variants (`spin`, `dots`,
   `pulse`, `bars`, `ios`) animating at once.
2. **Live run** — a big `Ring` plus a horizontal `Progress` bar that
   animate through four server-backed stages when you click
   **Render Report**. Each stage is a real `CallTool` round-trip —
   the percentages you see come from the server, not a client-side
   timer.
3. **Status strip** — an `If / Elif / Else` that shows "Running…",
   "✓ Complete", or "Idle" based on state.

The 4-stage chain is built programmatically via `_build_stage_chain`,
which right-nests `CallTool(...)` actions through their `on_success`
branches so the code reads left-to-right instead of collapsing into a
pyramid of callbacks.

Companion plain tool: **`render_report(pages)`** — uses
`ctx.report_progress(done, total)` so clients with native progress UI
(Claude Desktop, Cursor) show a real spinner/bar.

**See also:** [Progress reporting](https://gofastmcp.com/servers/progress)
· [`Context` API](https://gofastmcp.com/servers/context)
· [Prefab UI components](https://gofastmcp.com/apps/prefab)

## App: Deploy Console

The kitchen-sink showcase. One screen, six patterns:

- **Stat cards** — `Grid` of `Card` + `Dot` + `Metric` for a flashy
  dashboard row (services up, active deploys, 24h failures).
- **Environment pills** — `Badge` + `Dot` whose colors flip reactively
  (`healthy`/`degraded`/`down`) via nested ternaries on reactive state,
  *without* a server round-trip.
- **Dialog-gated deploy** — A Prefab `Dialog` wrapping a destructive
  action. First child = trigger button; remaining children = body.
- **Server-side elicitation** — The Rollback button fires a tool that
  calls `ctx.elicit(message, response_type=RollbackConfirmation)`. The
  confirmation UI is rendered by your **MCP client**, not by Prefab —
  elicitation is a protocol feature, not a UI gadget.
- **Conditional Alert banner** — `If(STATE.last_deploy)` renders a
  success banner only after a deploy completes.
- **Toasts** — `ShowToast(...)` for in-UI success/error feedback.

All three backing tools are `model=True`, so the LLM can drive the
console conversationally: *"deploy orders-api"* / *"roll back billing"*.

**See also:** [Elicitation](https://gofastmcp.com/servers/elicitation)
· [Prefab Dialog / Alert / Badge](https://gofastmcp.com/apps/prefab)
· [`Context` API](https://gofastmcp.com/servers/context)

## Generative UI

The three apps above are **hand-built** — you define the Prefab
component tree server-side and the client just renders it.

[**Generative UI**](https://gofastmcp.com/apps/generative) flips this
around: the LLM *writes the Prefab code at runtime*, in a Pyodide
sandbox, streamed into the client token by token as it generates. The
user watches the UI assemble itself — components appearing as the
model types them.

### The one-liner

```python
from fastmcp.apps.generative import GenerativeUI
mcp.add_provider(GenerativeUI())
```

That single line registers three things:

| Thing | What it is |
|---|---|
| `generate_prefab_ui(code, data=?)` | A tool that accepts Prefab Python code, executes it in a Pyodide sandbox, and renders the result as a Prefab app. Supports streaming. |
| `search_prefab_components(query)` | A tool that introspects the installed `prefab_ui` package so the LLM can discover what components exist (always up to date with the version on your server). |
| The generative renderer | A `ui://` resource with browser-side Pyodide that does the progressive rendering. |

### How streaming actually works

This is the mechanic that makes Generative UI feel magical. When the
LLM calls `generate_prefab_ui`, **the renderer iframe is created in
parallel with the tool call** — so the app is already running when
partial arguments start flowing. As the LLM generates each token:

1. The MCP host forwards partial tool arguments to the app via
   `ontoolinputpartial`.
2. The renderer extracts the growing `code` string.
3. Browser-side Pyodide executes whatever **compiles successfully** so
   far — bad syntax is just ignored until more tokens arrive.
4. The user sees components appear as they're written: first the
   `Heading`, then the `BarChart`, then the stat cards, etc.

When the LLM finishes, the server runs the **complete** code in a
server-side Pyodide sandbox for validation, and the renderer replaces
the streaming preview with the final server-validated result.

### What the LLM actually writes

The tool description bundled with `GenerativeUI` includes code
examples that teach the LLM the Prefab patterns. A typical generation
looks like:

```python
from prefab_ui.components import Column, Row, Heading, Text, Badge, Card, CardContent
from prefab_ui.components.charts import BarChart, ChartSeries
from prefab_ui.app import PrefabApp

with PrefabApp() as app:
    with Column(gap=6, css_class="p-6"):
        Heading("Q3 Revenue Report")

        BarChart(
            data=[
                {"month": "Jul", "revenue": 42000},
                {"month": "Aug", "revenue": 51000},
                {"month": "Sep", "revenue": 63000},
            ],
            series=[ChartSeries(data_key="revenue", label="Revenue")],
            x_axis="month",
        )

        with Row(gap=4):
            with Card():
                with CardContent():
                    Text("Total", css_class="text-sm text-muted-foreground")
                    Heading("$156,000")
            with Card():
                with CardContent():
                    Text("Growth", css_class="text-sm text-muted-foreground")
                    Badge("+18%", variant="success")
```

The model writes *real* Python — loops, f-strings, computation,
helper functions. Prefab's component library gives it charts, tables,
forms, cards, badges, and layout primitives to work with. No JSX-like
intermediate representation; the code that runs is the code the LLM
wrote.

### The component search workflow

Before writing code, the LLM can call `search_prefab_components` to
discover what's available:

```
search_prefab_components("Chart")
→ 7 components matching 'Chart':
  AreaChart  — from prefab_ui.components.charts import AreaChart
  BarChart   — from prefab_ui.components.charts import BarChart
  LineChart  — from prefab_ui.components.charts import LineChart
  PieChart   — from prefab_ui.components.charts import PieChart
  ...
```

Passing `detail=True` returns full field descriptions and docstrings
so the LLM can pick the right props without guessing. The search tool
**introspects the actual classes at runtime**, so it's always in sync
with whatever `prefab-ui` version is installed on your server — even
if the docs haven't caught up yet.

### Passing your own data

`generate_prefab_ui` accepts a `data=` parameter. Anything passed
here becomes a global variable in the sandbox:

```python
# The LLM's generated code can reference `spending` directly.
await generate_prefab_ui(
    code="""
        from prefab_ui.components.charts import BarChart, ChartSeries
        ...
        BarChart(data=spending, series=[ChartSeries(data_key='amount')], x_axis='category')
    """,
    data={"spending": [{"category": "Equipment", "amount": 12400}, ...]},
)
```

That's how this branch's seed-data tool plays in — the LLM calls
`get_lab_spending()`, then passes the result into
`generate_prefab_ui(data={"spending": ...})` so the generated chart
uses real numbers, not inventions.

### The seed-data tool

```python
@mcp.tool
def get_lab_spending() -> dict:
    """Return last-quarter (Q1 2026) departmental lab spending."""
    # 15 deterministic rows across Jan–Mar × 5 categories, plus a
    # pre-computed summary (total / top_category / mom_change_pct).
```

**Try this prompt in your client:**

> *"Call `get_lab_spending`, then visualize it as a bar chart grouped
> by category, with stat cards for total spend, the top-spending
> category, and MoM change."*

The LLM calls `get_lab_spending`, optionally calls
`search_prefab_components("Chart")` to check what's available, then
calls `generate_prefab_ui(code=..., data={"spending": ...})`. You
watch the chart build up as the code streams.

### Configuration

`GenerativeUI` accepts a few options for customizing tool names or
disabling the component search tool:

```python
GenerativeUI(
    tool_name="generate_prefab_ui",                   # default
    components_tool_name="search_prefab_components",  # default
    include_components_tool=True,                     # default
)
```

Set `include_components_tool=False` if you want to ship only the
renderer and keep the LLM on a leash (it'll have to rely on whatever
components it already knows).

### Requirements & sandbox limits

- **`fastmcp[apps]`** installs `prefab-ui` and everything the provider
  needs. The server-side Pyodide sandbox additionally requires **Deno**,
  which installs automatically on first use.
- The browser-side renderer loads **Pyodide from CDN**. The CSP is
  configured automatically by the provider — no manual setup.
- **The Pyodide sandbox ships only the Python stdlib + Prefab.** No
  `numpy`, `pandas`, `requests`, or anything else that needs native
  extensions. If the LLM tries to import one, it gets `ImportError`
  and typically retries with a different approach.

**See also:** [Generative UI](https://gofastmcp.com/apps/generative)
· [GenerativeUI provider reference](https://gofastmcp.com/apps/providers/generative)
· [Prefab component reference](https://gofastmcp.com/apps/prefab)
· [Local preview with `fastmcp dev apps`](https://gofastmcp.com/apps/development)

## Prefab Patterns — where to go next

The four apps above are concrete examples of a few [**Prefab
patterns**](https://gofastmcp.com/apps/patterns). FastMCP ships a
copy-paste catalog of common tool-UI patterns, organized by what
you're building. Use this as the "what do I reach for when I want to
build _X_" reference after this step:

| Category | Patterns | Where it shows up in this branch |
|---|---|---|
| **Charts** | Bar, Line, Area, Pie, Radar, Radial, Scatter, Sparkline, Histogram | Not used in this branch — explore when you need visualizations. Generative UI can emit any of them. |
| **Data Tables** | Sortable `DataTable` with search + pagination | Not used — the Deploy Console uses flat `Card` grids. Step 13 uses `DataTable` extensively. |
| **Status Displays** | `Card` + `Badge` + `Progress` + `Dot` dashboards | **Deploy Console** — stat cards, environment pills, success Alert banner. |
| **Reactive Displays** | `Switch` + `If/Elif/Else`, `Tabs`, `Accordion`, state-driven layout | **Progress** app (status strip uses `If/Elif/Else`). Tabs + Accordion are untouched here. |
| **Interactive Patterns** | `Form` + `Input`/`Select`/`Textarea` with `CallTool` round-trips | **Counter** + **Deploy Console** demonstrate the `CallTool` → `on_success` → `SetState` round-trip. A full `Form` isn't in this branch. |

### Patterns not shown here (worth exploring)

Things that appear in the Patterns catalog but that this branch doesn't
demonstrate — good "go try this" exercises:

- **Area charts with `curve="smooth"`** for time-series displays.
- **Pie / donut charts** with `inner_radius=60`.
- **`DataTable`** with `search=True, paginated=True, page_size=15`.
- **Feature toggles** — `Switch(name="flag")` bound to reactive state,
  `If(Rx("flag"))` to conditionally show sections. No server call needed.
- **`Tabs` + `Tab`** for organizing a one-tool multi-section UI.
- **`Accordion` + `AccordionItem`** for collapsible detail rows.
- **Contact-form-style submissions** — `Form(on_submit=CallTool(...))`
  with `Input`, `Select`, `Textarea`, and `RESULT` piped into state.

### Pick your flavor

The Patterns page and the feature comparison below help you decide
*which* Prefab mechanic fits a given problem:

| You want to... | Reach for |
|---|---|
| Show a one-shot chart or table with no interaction | `@mcp.tool(app=True)` returning a `PrefabApp`. No `FastMCPApp` needed. |
| Build an interactive multi-tool UI (buttons, forms, server round-trips) | `FastMCPApp` + `@app.tool(model=True)` + `@app.ui()`. This branch's Counter / Progress / Deploy all use this. |
| Let the LLM construct bespoke UIs per request | `GenerativeUI()` provider. |
| Ship a full custom HTML app | `@mcp.tool(app=AppConfig(resource_uri="..."))`. Escape hatch for when Prefab doesn't fit — see `/apps/low-level`. |

**See also:** [Prefab Patterns catalog](https://gofastmcp.com/apps/patterns)
· [Prefab component reference](https://prefab.prefect.io/docs/components)
· [Prefab UI](https://gofastmcp.com/apps/prefab)

## Running

```bash
uv sync
python server.py
```

Connect from Claude Desktop, Cursor, or VS Code Copilot. Clients that
support MCP Apps will offer to open the **Counter**, **Progress**, and
**Deploy** apps. Clients that don't still see the underlying tools and
can call them directly.

For local iteration without a full MCP client, use
[`fastmcp dev apps`](https://gofastmcp.com/apps/development) to preview
Apps in a browser.

## Adding auth

This demo runs unauthenticated so you can poke at the UI without
configuring a tenant. Drop in any `auth=...` block from steps 08–11 and
you're done — the Apps mechanic is orthogonal to auth.

## New dependencies

- `fastmcp[apps]` — the Apps extension to FastMCP (includes the Pyodide
  sandbox used by Generative UI)
- `prefab-ui` — declarative UI components
- **Deno** — required at runtime by the Pyodide sandbox that Generative
  UI uses to validate LLM-generated code. Install once via
  `brew install deno` (or [deno.land](https://deno.land)).

The repo ships a one-line `deno.json` (`{"nodeModulesDir": "auto"}`)
in the project root so Deno auto-installs the `npm:pyodide` package
on first use. Without that file, Deno 2.x refuses npm imports and
`generate_prefab_ui` fails with *"Could not find a matching package
for 'npm:pyodide@0.27.4'"*.
