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
| Generative UI (LLM writes the UI) | [gofastmcp.com/apps/generative](https://gofastmcp.com/apps/generative) |
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
sandbox, streamed into the client token by token as it generates.

```python
from fastmcp.apps.generative import GenerativeUI
mcp.add_provider(GenerativeUI())
```

That one line registers two tools:

| Tool | Purpose |
|---|---|
| `generate_prefab_ui(code, data=?)` | Executes Prefab Python code in a Pyodide sandbox and renders the result as a Prefab app. Supports streaming — partial code runs browser-side as the LLM types. |
| `search_prefab_components(query)` | Lets the LLM discover what components exist (`BarChart`, `Card`, `Metric`, …) before writing code. |

Paired with a **seed-data tool** so the lecture demo is reproducible:

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
calls `generate_prefab_ui(code=..., data={"spending": ...})`. You watch
the chart build up as the code streams.

**Sandbox note:** Pyodide includes the Python stdlib + Prefab only.
No `numpy` / `pandas` / `requests`. If the LLM tries to import one,
the sandbox raises `ImportError` and the LLM typically retries with a
different approach.

**See also:** [Generative UI](https://gofastmcp.com/apps/generative)
· [Prefab component reference](https://gofastmcp.com/apps/prefab)
· [Local preview with `fastmcp dev apps`](https://gofastmcp.com/apps/development)

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
