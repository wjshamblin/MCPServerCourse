# Step 11 — Add a Generative UI App

**Date:** 2026-04-21
**Branch:** `11-mcp-apps`
**Status:** Approved design, ready for implementation plan

## Goal

Extend the Step 11 MCP Apps lesson to cover FastMCP's **Generative UI**
provider (https://gofastmcp.com/apps/generative) alongside the three
existing hand-built Prefab apps (Counter, Progress, Deploy).

The teaching point: students have now seen how to *build* a Prefab UI
server-side. Generative UI flips that around — the **LLM writes the
Prefab code at runtime**, in a Pyodide sandbox, streamed into the client
as it generates.

## Non-Goals

- No changes to the Counter, Progress, or Deploy apps.
- No authentication changes (the branch remains `auth = None`).
- No new files, no new dependencies (`fastmcp[apps]` already ships
  `GenerativeUI` and the Pyodide sandbox).
- No persistence — the seed data is hard-coded in the tool.

## What Gets Added

### 1. Generative UI provider registration

```python
from fastmcp.apps.generative import GenerativeUI

mcp.add_provider(GenerativeUI())
```

Registering the provider automatically exposes two tools on the MCP
server:

| Tool | Purpose |
|------|---------|
| `generate_prefab_ui` | Accepts a `code` string (and optional `data` dict). Executes the code in a Pyodide sandbox and renders the result as a Prefab app. Supports streaming — partial code is executed browser-side as the LLM types. |
| `search_prefab_components` | Lets the LLM discover what components exist in `prefab_ui.components` before writing code. |

A short teaching comment block above the registration will explain the
mechanic (LLM writes code → forwarded via `ontoolinputpartial` →
executed in browser Pyodide → validated server-side when the call
finishes) and link to the docs page.

### 2. Seed-data tool: `get_lab_spending`

```python
@mcp.tool
def get_lab_spending() -> dict:
    """Return last-quarter departmental spending by category and month.

    Pair with generate_prefab_ui to build a visualization:
    "Call get_lab_spending, then visualize it as a bar chart
    grouped by category, with stat cards for total and top spender."
    """
```

**Return shape:**

```python
{
    "quarter": "Q1 2026",
    "rows": [
        {"month": "Jan", "category": "Equipment",   "amount": 12400},
        {"month": "Jan", "category": "Travel",      "amount":  2100},
        {"month": "Jan", "category": "Stipends",    "amount": 18500},
        {"month": "Jan", "category": "Software",    "amount":  3200},
        {"month": "Jan", "category": "Conferences", "amount":  1500},
        # Feb, Mar rows with similar shape — 15 rows total
        ...
    ],
    "summary": {
        "total": 146_800,
        "top_category": "Stipends",
        "mom_change_pct": 8.4,
    },
}
```

**Design choices:**

- **Deterministic** (not random). The lecture demo looks the same every
  run so the teacher can rely on the numbers when narrating.
- **Five categories × 3 months = 15 rows.** Small enough to read in the
  docstring, big enough for a non-trivial chart.
- **Pre-computed `summary`** so the LLM has clean numbers for stat
  cards without needing sandbox arithmetic across all 15 rows.
- **Categories chosen for a university lab:** Equipment, Travel,
  Stipends, Software, Conferences. Vivid enough that LLM-generated
  labels feel specific, not toy-like.

### 3. Module docstring update

The file-level docstring currently describes three apps (Counter,
Progress, Deploy). Add a fourth bullet for the Generative UI provider
and a line about the paired `get_lab_spending` seed tool.

### 4. README — docs catch-up + Generative UI section

The Step 11 section of `README.md` (lines 514–589) currently only
documents the Counter app. `server.py` already ships **Progress** and
**Deploy** apps that are undocumented. While doing the Generative UI
write-up, we'll also bring those up to date so the lesson materials
match the code.

Concretely, the Step 11 section gets restructured as:

1. **Overview** — one paragraph naming all four surfaces
   (Counter, Progress, Deploy, Generative UI).
2. **The MCP Apps pattern** — existing content, kept as-is.
3. **App: Counter** — existing content, lightly edited.
4. **App: Progress** *(new)* — Loader / Ring / Progress components,
   the 4-stage CallTool chain, and the companion top-level
   `render_report` tool that demonstrates `ctx.report_progress()`.
5. **App: Deploy Console** *(new)* — Grid + Card + Badge dashboard,
   Dialog-gated destructive action, and server-side `ctx.elicit()` for
   rollback confirmation. Explicit pointer: *"elicitation is rendered
   by the client, not by Prefab — it's a protocol feature."*
6. **Generative UI** *(new)* — what the provider is, the two
   auto-registered tools, the `get_lab_spending` seed-tool demo
   flow, and the Pyodide sandbox limitation (stdlib + Prefab only,
   no NumPy/pandas/requests).
7. **Running / Adding auth / New dependencies** — existing content,
   kept as-is.

### 5. Slide-deck — docs catch-up + Generative UI slides

`docs/slides/11-mcp-apps.html` currently has 14 slides, all about the
Counter app. We'll:

**Keep as-is:** Slides 1–11 (title, concept, pattern, imports, Counter
tools + UI, reactive state cheat sheet, CallTool round-trip, models +
apps together). These remain the core teaching spine.

**Move to the end:** Slides 12–14 (Run it, Where to go next, Key
takeaways) get pushed after the new material.

**Insert new slides between** (after "Models and Apps together"):

1. **Progress — Loader / Ring / Progress components** — the three
   new primitives with tiny code snippets.
2. **Progress — The 4-stage CallTool chain** — shows
   `_build_stage_chain` and the right-nested on_success pattern.
3. **Deploy Console — Stat cards + Badges** — the flashy dashboard
   row and environment-status pills.
4. **Deploy Console — Dialog-gated actions** — the Dialog pattern
   (first child = trigger, remaining = body).
5. **Deploy Console — `ctx.elicit()`** — server-side elicitation,
   rendered by the client, not by Prefab.
6. **Generative UI — The LLM Writes the UI** — concept slide.
7. **Generative UI — One Line to Register** — code snippet and the
   two tools it exposes.
8. **Generative UI — Demo: Visualize Lab Spending** — the prompt
   flow and Pyodide sandbox limitations.

Total new slides: 8. Final deck length: ~22 slides.

## Data Flow

```
User (in Claude Desktop / Cursor / VS Code)
  │
  │  "Call get_lab_spending, then visualize it as a bar chart…"
  ▼
LLM ──▶ calls get_lab_spending (plain @mcp.tool)
  │         returns {"rows": [...], "summary": {...}}
  │
  ├──▶ optionally calls search_prefab_components("Chart")
  │         returns list of BarChart, AreaChart, etc.
  │
  └──▶ calls generate_prefab_ui(
            code="from prefab_ui.components import ...",
            data={"spending": <result of get_lab_spending>}
        )
           │
           ▼
     MCP Apps protocol forwards partial args → browser Pyodide
     executes what compiles → user watches the UI build up
           │
           ▼
     On completion: server-side Pyodide validates full code;
     renderer replaces streaming preview with validated result.
```

## Error Handling

All error paths are owned by the `GenerativeUI` provider, not by code
we're adding:

- Sandbox `ImportError` (LLM tries `import numpy`) → surfaced as a tool
  error; the LLM typically retries with a different approach.
- Syntax error in generated code → server-side Pyodide rejects it;
  streaming preview is discarded.
- Client doesn't support MCP Apps → the provider falls back to
  returning the generated code as a plain tool result.

Our `get_lab_spending` tool has no failure modes — it returns a
hard-coded dict.

## Testing

This repo has no test suite (each branch is a self-contained lesson).
Verification is manual:

1. `uv sync` — confirm the existing lockfile still resolves.
2. `uv run python server.py` — server starts cleanly on :8000 and the
   startup log lists all four providers (Counter, Progress, Deploy,
   Generative UI).
3. Connect from an MCP client (Claude Desktop or the FastMCP inspector)
   and confirm:
   - `get_lab_spending` is callable as a plain tool.
   - `generate_prefab_ui` and `search_prefab_components` show up.
   - The end-to-end prompt *"Call get_lab_spending then visualize it as
     a bar chart"* renders a chart inline.

## Out of Scope (Future Work)

- Multiple seed-data tools (e.g., enrollment data, fleet telemetry).
  One seed tool is enough to teach the concept.
- Custom `tool_name` / `components_tool_name` overrides on
  `GenerativeUI()`. Defaults are fine for a lesson.
- Persistence layer behind `get_lab_spending` (CSV, SQLite). Hard-coded
  dict is the point.

## Acceptance Criteria

**Code:**
- [ ] `server.py` imports `GenerativeUI` and calls
      `mcp.add_provider(GenerativeUI())`.
- [ ] `get_lab_spending()` returns the documented shape with
      deterministic values.
- [ ] Module docstring lists all four apps/providers.

**README (`README.md`, Step 11 section):**
- [ ] Overview paragraph names all four surfaces.
- [ ] Progress section added.
- [ ] Deploy Console section added.
- [ ] Generative UI section added.
- [ ] Existing Counter content preserved with minor edits only.

**Slide deck (`docs/slides/11-mcp-apps.html`):**
- [ ] Progress slides (2) inserted after "Models and Apps together".
- [ ] Deploy Console slides (3) inserted after Progress slides.
- [ ] Generative UI slides (3) inserted after Deploy slides.
- [ ] "Run it" / "Where to go next" / "Key takeaways" pushed to end.

**Verification:**
- [ ] Server boots cleanly. Startup log shows all four providers
      registered.
- [ ] Manual demo prompt (*"Call get_lab_spending, then visualize as
      a bar chart"*) renders a chart inline in an MCP Apps client.
