"""
Step 11: Minimal MCP Apps Demo

The smallest possible server that demonstrates MCP Apps — interactive UIs
rendered inside the AI client (Claude Desktop, Cursor, VS Code Copilot)
via Prefab UI components, backed by tools that the LLM can also call
directly.

This branch deliberately strips the auth, database, and OBO machinery
from earlier steps (auth was already covered in 07–10) so the App
mechanic is the only new concept on the page.

The pattern:

    1. Create a `FastMCPApp` per app — it bundles UI + backing tools.
    2. Decorate backing functions with `@app.tool(model=True)` so they're
       callable from BOTH the UI (via `CallTool`) and from the LLM directly.
    3. Decorate the UI entry point with `@app.ui()` and return a
       `PrefabApp`-wrapped layout built from `prefab_ui.components`.
    4. Register the app on the main server with `mcp.add_provider(app)`.

This file ships three hand-built apps plus one Generative UI provider:
  * "Counter"     — the minimal end-to-end demo (button round-trips state)
  * "Progress"    — Loader / Ring / Progress components driven by a
                    4-stage server-side tool chain
  * "Deploy"      — kitchen-sink dashboard: stat cards, Dialog-gated
                    deploy, and server-side `ctx.elicit()` rollback
  * GenerativeUI  — provider that lets the LLM *write Prefab code at
                    runtime* in a Pyodide sandbox. Paired with
                    `get_lab_spending()` for a reproducible
                    "visualize this data" demo.
                    (https://gofastmcp.com/apps/generative)

…alongside a few plain tools, including `render_report(pages)` which
demonstrates `ctx.report_progress()` (https://gofastmcp.com/servers/progress).

Replace the inline auth stub at the top of the file with any of the
auth proxies from steps 07–10 to gate the apps and tools.

Run:  python server.py

Connect from Claude Desktop / Cursor / VS Code, then look for the
"Counter" / "Progress" app entries and open them. The backing tools
can also be invoked directly by the model.
"""

import asyncio
import logging
import random
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastmcp import Context, FastMCP
from fastmcp.apps import FastMCPApp
from fastmcp.apps.generative import GenerativeUI
from fastmcp.server.elicitation import AcceptedElicitation
from prefab_ui.actions import Action, SetState, ShowToast
from prefab_ui.actions.mcp import CallTool
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Alert, AlertDescription, AlertTitle, Badge, Button, Card, CardContent,
    CardDescription, CardHeader, CardTitle, Column, Dialog, Dot, Elif, Else,
    Grid, Heading, If, Loader, Metric, Progress, Ring, Row, Select,
    SelectOption, Separator, Text,
)
from prefab_ui.rx import RESULT, Rx, STATE
from pydantic import BaseModel, Field

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


# === Auth stub ===
# This minimal demo runs without auth so you can poke at the App UI in
# Claude Desktop / Cursor without setting up a tenant. To gate the
# server, copy an auth block from steps 07 (Duke OIDC), 08/09 (Azure
# OAuth), or 10 (Azure + OBO) and pass `auth=auth` to FastMCP(...).
auth = None


# === Plain tools ===

mcp = FastMCP(
    "MCPAppsDemo",
    instructions=(
        "MCP Apps demo. Open the 'Counter', 'Progress', or 'Deploy' apps "
        "to interact with them in your AI client. For Generative UI, call "
        "`get_lab_spending` and then `generate_prefab_ui` with code that "
        "visualizes it. All backing tools are also callable directly."
    ),
    auth=auth,
)


@mcp.tool
def hello(name: str = "world") -> str:
    """Return a friendly greeting."""
    return f"hello, {name}!"


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two integers and return the sum."""
    return a + b


@mcp.tool
async def render_report(ctx: Context, pages: int = 50) -> dict:
    """Render a multi-stage report, streaming progress to the client.

    Demonstrates ``ctx.report_progress()`` — MCP clients that support
    progress (Claude Desktop, Cursor) will render a native progress
    indicator (spinner / bar) while this tool runs. Clients that don't
    support progress see no change; the tool still completes normally.

    The render is split into four weighted stages (collect, query, render,
    package). Each step sleeps briefly to simulate real work and then
    calls ``ctx.report_progress(progress, total)``.

    Args:
        pages: Number of pages to "render". Purely cosmetic — affects the
            reported page count but not the duration.
    """
    stages: list[tuple[str, float]] = [
        ("Collecting data", 0.15),
        ("Querying database", 0.25),
        ("Rendering pages", 0.45),
        ("Packaging PDF", 0.15),
    ]
    total = 100
    done = 0
    for label, weight in stages:
        steps = max(1, int(weight * total))
        await ctx.info(f"{label}…")
        for _ in range(steps):
            done += 1
            await asyncio.sleep(0.05)
            await ctx.report_progress(progress=done, total=total)
    await ctx.report_progress(progress=total, total=total)
    return {"status": "ok", "pages": pages, "stages": len(stages)}


# === MCP App: a tiny shared counter ===
# In-memory state — fine for a demo. A real app would persist this somewhere.

_state: dict[str, int] = {"count": 0}

counter_app = FastMCPApp("Counter")


@counter_app.tool(model=True)
def get_counter() -> dict:
    """Return the current counter value."""
    return {"count": _state["count"]}


@counter_app.tool(model=True)
def bump_counter(by: int = 1) -> dict:
    """Increment (or decrement) the shared counter and return the new value.

    Callable both from the App UI button and directly by the model.
    """
    _state["count"] += by
    return {"count": _state["count"], "delta": by}


@counter_app.tool(model=True)
def reset_counter() -> dict:
    """Reset the counter to zero."""
    _state["count"] = 0
    return {"count": 0}


@counter_app.ui()
async def counter_view() -> PrefabApp:
    """Open the Counter — a one-screen demo of an MCP App.

    The UI tree is built once at registration time. Buttons fire
    `CallTool(...)` actions, which round-trip back through the MCP
    server to invoke the matching @app.tool functions, then update
    UI state from the tool's return value.
    """
    with Column(gap=4, css_class="p-6") as view:
        Heading("Counter", level=2)
        Text("A shared in-memory counter. Click a button (or just ask the model "
             "to bump it) and watch the value update.",
             css_class="text-gray-400 text-sm")

        Separator()

        # The current count is stored in client-side state under
        # `STATE.count`. We seed it on first render by calling get_counter
        # via a hidden refresh button below.
        with Row(gap=8, css_class="items-center"):
            Metric(label="Count", value=Rx("count"))

        with Row(gap=2):
            Button(
                "Refresh",
                variant="ghost",
                on_click=CallTool(
                    get_counter,
                    on_success=[SetState("count", RESULT["count"])],
                ),
            )
            Button(
                "+1",
                variant="default",
                on_click=CallTool(
                    bump_counter,
                    arguments={"by": 1},
                    on_success=[
                        SetState("count", RESULT["count"]),
                        ShowToast("+1", variant="success"),
                    ],
                ),
            )
            Button(
                "+10",
                variant="default",
                on_click=CallTool(
                    bump_counter,
                    arguments={"by": 10},
                    on_success=[SetState("count", RESULT["count"])],
                ),
            )
            Button(
                "Reset",
                variant="destructive",
                on_click=CallTool(
                    reset_counter,
                    on_success=[
                        SetState("count", RESULT["count"]),
                        ShowToast("Counter reset", variant="warning"),
                    ],
                ),
            )

    return view


mcp.add_provider(counter_app)


# === MCP App: Progress showcase ===
# A visually richer demo than the Counter. Shows off Prefab's spinner
# (`Loader`), circular (`Ring`), and bar (`Progress`) components, driven
# by a 4-stage server-side tool chain so the progress you see is real
# (not faked client-side). The chain is built programmatically so the
# nesting reads left-to-right instead of collapsing into pyramid-of-doom
# callbacks.
#
# Pair this with the top-level `render_report` tool, which demonstrates
# the canonical FastMCP `ctx.report_progress()` pattern for clients that
# render native progress UI (see https://gofastmcp.com/servers/progress).

progress_app = FastMCPApp("Progress")

_STAGES: list[dict[str, object]] = [
    {"percent": 25,  "label": "Collecting data"},
    {"percent": 55,  "label": "Querying database"},
    {"percent": 85,  "label": "Rendering pages"},
    {"percent": 100, "label": "Packaging PDF"},
]


@progress_app.tool(model=True)
async def render_stage(stage: int) -> dict:
    """Run one stage of a simulated report render.

    Sleeps briefly, then returns the cumulative percent complete after
    this stage together with a human-readable label. The UI chains four
    of these to animate its Ring / Progress bar; the LLM can also call
    a stage directly ("run stage 2") to see the same output.

    Args:
        stage: 1-indexed stage number (1–4). Values outside that range
            are clamped.
    """
    await asyncio.sleep(0.7)
    idx = max(1, min(stage, len(_STAGES))) - 1
    info = _STAGES[idx]
    return {"stage": idx + 1, "percent": info["percent"], "label": info["label"]}


def _build_stage_chain(stages: list[int]) -> list[Action]:
    """Right-nest a CallTool chain across ``stages``, updating UI state after each.

    After the last stage fires ``on_success``, the terminal actions flip
    ``running`` off and show a success toast. Any stage failure short-
    circuits through its ``on_error`` branch to the same terminal.
    """
    if not stages:
        return [
            SetState("running", False),
            SetState("stage_label", "Complete"),
            ShowToast("Report rendered", variant="success"),
        ]

    head, *tail = stages
    return [
        CallTool(
            render_stage,
            arguments={"stage": head},
            on_success=[
                SetState("percent", RESULT["percent"]),
                SetState("stage_label", RESULT["label"]),
                *_build_stage_chain(tail),
            ],
            on_error=[
                SetState("running", False),
                SetState("stage_label", "Failed"),
                ShowToast("Render failed", variant="error"),
            ],
        )
    ]


_LOADER_VARIANTS = ("spin", "dots", "pulse", "bars", "ios")


@progress_app.ui()
async def progress_view() -> PrefabApp:
    """Open the Progress showcase — Loader gallery + Ring + Progress bar.

    Three panels, top to bottom:
      1. *Spinner styles* — all five `Loader` variants animating at once.
      2. *Live run* — a big `Ring` plus a horizontal `Progress` bar that
         together animate through four real server-backed stages when
         the user clicks **Render Report**.
      3. *Status* — a small conditional strip: a dots spinner while
         running, a checkmark when complete, "Idle" otherwise.
    """
    with PrefabApp(
        title="Progress Showcase",
        state={"running": False, "percent": 0, "stage_label": "Idle"},
        css_class="p-8 max-w-2xl mx-auto space-y-6",
    ) as app:
        # --- header --------------------------------------------------
        Heading("Progress Showcase", level=2)
        Text(
            "A live-progress demo built from Prefab's Loader, Ring, and "
            "Progress components — driven by a 4-stage server-side tool "
            "chain, so the numbers you see come from real round-trips.",
            css_class="text-gray-400 text-sm",
        )

        # --- panel 1: spinner gallery --------------------------------
        Separator()
        Heading("Spinner styles", level=3)
        Text(
            "Five Loader variants — always animating.",
            css_class="text-gray-500 text-xs",
        )
        with Row(gap=6, css_class="items-end justify-around py-6"):
            for variant in _LOADER_VARIANTS:
                with Column(gap=2, css_class="items-center"):
                    Loader(variant=variant, size="lg")
                    Text(variant, css_class="text-xs text-gray-500 font-mono")

        # --- panel 2: live run ---------------------------------------
        Separator()
        Heading("Live run", level=3)
        Text(
            "Click Render Report — each stage is a real CallTool round-trip.",
            css_class="text-gray-500 text-xs",
        )
        with Row(gap=8, css_class="items-center py-4"):
            Ring(
                value=STATE.percent,
                label=f"{STATE.percent}%",
                variant="info",
                size="lg",
                thickness=10,
            )
            with Column(gap=3, css_class="flex-1"):
                Text(
                    STATE.stage_label,
                    css_class="text-lg font-semibold text-gray-200",
                )
                Progress(
                    value=STATE.percent,
                    variant="info",
                    size="lg",
                )
                Text(
                    f"{STATE.percent}% complete",
                    css_class="text-xs text-gray-500 font-mono",
                )
                with Row(gap=2, css_class="pt-2"):
                    Button(
                        "Render Report",
                        icon="play",
                        variant="default",
                        disabled=STATE.running,
                        on_click=[
                            SetState("running", True),
                            SetState("percent", 0),
                            SetState("stage_label", "Starting…"),
                            *_build_stage_chain([1, 2, 3, 4]),
                        ],
                    )
                    Button(
                        "Reset",
                        icon="rotate-ccw",
                        variant="ghost",
                        disabled=STATE.running,
                        on_click=[
                            SetState("percent", 0),
                            SetState("stage_label", "Idle"),
                        ],
                    )

        # --- panel 3: status strip -----------------------------------
        Separator()
        with Row(gap=3, css_class="items-center py-2"):
            with If(STATE.running):
                Loader(variant="dots", size="sm")
                Text("Running…", css_class="text-amber-400 text-sm")
            with Elif(STATE.percent == 100):
                Text("✓ Complete", css_class="text-emerald-400 text-sm")
            with Else():
                Text("Idle", css_class="text-gray-500 text-sm")

        # --- current-value metric, for folks who like numbers --------
        Separator()
        with Row(gap=8, css_class="items-center"):
            Metric(label="Stage", value=STATE.stage_label)
            Metric(label="Progress", value=f"{STATE.percent}%")

    return app


mcp.add_provider(progress_app)


# =============================================================================
# MCP App: Deploy Console — the "kitchen sink" showcase
# -----------------------------------------------------------------------------
# Shows off several more Prefab patterns that pair nicely with MCP Apps:
#
#   * Stat cards       — Grid + Card + Metric + Dot for a flashy dashboard row
#   * Environment pill — Badge + Dot for compact status
#   * Confirmation UI  — Prefab Dialog gating a destructive CallTool
#   * Elicitation      — server-side `ctx.elicit()` with a typed Pydantic model
#   * Conditional UI   — Alert banner that only renders after an outcome
#   * Toasts           — ShowToast on success/error for in-UI feedback
#
# The backing tools are all `model=True`, so the LLM can also drive the
# console conversationally ("deploy orders-api" / "roll back billing").
# =============================================================================

deploy_app = FastMCPApp("Deploy")


# --- in-memory "fleet" state (demo only) -------------------------------------

_SERVICES = ["orders-api", "billing", "web-frontend", "search-indexer"]
_ENVS = ("dev", "staging", "prod")


def _snapshot_stats() -> dict:
    """Return a fresh fleet snapshot. Small amount of jitter so the
    Refresh button has something visible to change."""
    services_up = len(_SERVICES)
    total = len(_SERVICES)
    in_flight = random.randint(0, 2)
    failures_24h = random.randint(0, 1)
    return {
        "services_up": services_up,
        "services_total": total,
        "in_flight": in_flight,
        "failures_24h": failures_24h,
        "envs": {
            "dev":     {"status": "healthy", "version": "v4.2.1"},
            "staging": {"status": "healthy", "version": "v4.2.0"},
            "prod":    {"status": random.choice(["healthy", "healthy", "degraded"]),
                        "version": "v4.1.9"},
        },
    }


# --- Elicitation schema ------------------------------------------------------
# `ctx.elicit(message, response_type=Model)` lets a tool pause and ask the
# client to collect typed input. The client renders whatever UI it wants
# (Claude Desktop renders a modal form, Cursor renders an inline prompt),
# and the response is validated against this model before we see it.


class RollbackConfirmation(BaseModel):
    """Typed confirmation payload for a rollback operation."""

    confirm: bool = Field(
        default=False,
        description="Check to confirm rollback to previous version.",
    )
    reason: str = Field(
        default="",
        description="Short reason for the rollback (required for audit log).",
        min_length=0,
        max_length=200,
    )


# --- Backing tools -----------------------------------------------------------


@deploy_app.tool(model=True)
def get_deploy_stats() -> dict:
    """Return the current fleet snapshot used by the Deploy Console UI."""
    return _snapshot_stats()


@deploy_app.tool(model=True)
async def deploy_service(service: str) -> dict:
    """Deploy a single service to production.

    Pretends to do real work by sleeping briefly. Returns a payload the
    UI uses to populate a success Alert banner and a toast.
    """
    if service not in _SERVICES:
        return {"ok": False, "service": service, "error": "unknown service"}

    await asyncio.sleep(1.2)
    version = f"v4.2.{random.randint(2, 9)}"
    return {
        "ok": True,
        "service": service,
        "version": version,
        "env": "prod",
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


@deploy_app.tool(model=True)
async def rollback_service(service: str, ctx: Context) -> dict:
    """Roll a service back to the previous version, gated by `ctx.elicit()`.

    Demonstrates the canonical FastMCP elicitation flow:

        1. The tool pauses and asks the client for structured input
           (a ``RollbackConfirmation`` with a checkbox + reason field).
        2. The client renders that request to the user.
        3. The user accepts / declines / cancels. We only proceed on
           accept + ``confirm=True``.

    This runs inside the same tool call that the UI's Rollback button
    fires — so clicking "Roll back orders-api" opens the dialog inside
    the *client*, not inside our Prefab UI. That's exactly the point:
    elicitation is a protocol feature, not a UI gadget.
    """
    if service not in _SERVICES:
        return {"ok": False, "service": service, "error": "unknown service"}

    result = await ctx.elicit(
        message=f"Roll {service} back to the previous version in production?",
        response_type=RollbackConfirmation,
    )

    if not isinstance(result, AcceptedElicitation) or not result.data.confirm:
        await ctx.info(f"Rollback of {service} declined or cancelled.")
        return {"ok": False, "service": service, "reason": "not confirmed"}

    await ctx.info(
        f"Rolling back {service} — audit reason: "
        f"{result.data.reason or '(none provided)'}"
    )
    await asyncio.sleep(0.8)
    return {
        "ok": True,
        "service": service,
        "rolled_back_to": "v4.1.8",
        "reason": result.data.reason,
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


# --- UI helpers --------------------------------------------------------------


def _stat_card(title: str, value: Rx, caption: str, *, icon: str, tone: str) -> None:
    """One flashy stat card. Call inside a Grid container."""
    with Card(css_class=f"p-6 border-l-4 border-l-{tone}-500"):
        with Row(gap=3, css_class="items-center"):
            Dot(variant="muted", size="lg", css_class=f"bg-{tone}-500")
            with Column(gap=1, css_class="flex-1"):
                Text(title, css_class="text-xs uppercase tracking-wider text-gray-500")
                Text(value, css_class="text-3xl font-bold text-gray-100")
                Text(caption, css_class="text-xs text-gray-500")


_ENV_TONE = {"healthy": "success", "degraded": "warning", "down": "destructive"}


# --- UI ----------------------------------------------------------------------


@deploy_app.ui()
async def deploy_view() -> PrefabApp:
    """Open the Deploy Console — flashy cards, confirmation dialog, elicitation."""

    initial = _snapshot_stats()

    with PrefabApp(
        title="Deploy Console",
        state={
            "selected_service": _SERVICES[0],
            "stats": initial,
            "last_deploy": None,  # {"service","version","env","at"} after success
        },
        css_class="p-8 max-w-3xl mx-auto space-y-6",
    ) as app:
        # --- header ----------------------------------------------------------
        with Row(gap=3, css_class="items-center justify-between"):
            with Column(gap=1):
                Heading("Deploy Console", level=2)
                Text(
                    "One screen showing off cards, badges, a dialog, and "
                    "server-side elicitation.",
                    css_class="text-gray-400 text-sm",
                )
            Button(
                "Refresh",
                icon="refresh-cw",
                variant="ghost",
                on_click=CallTool(
                    get_deploy_stats,
                    on_success=[
                        SetState("stats", RESULT),
                        ShowToast("Fleet refreshed", variant="info"),
                    ],
                ),
            )

        # --- success banner (conditional) ------------------------------------
        with If(STATE.last_deploy):
            with Alert(variant="success", icon="rocket"):
                AlertTitle("Deploy complete")
                AlertDescription(
                    f"{STATE.last_deploy.service} → {STATE.last_deploy.env} "
                    f"@ {STATE.last_deploy.version} ({STATE.last_deploy.at})"
                )

        # --- stat cards ------------------------------------------------------
        with Grid(columns=3, gap=4):
            _stat_card(
                "Services up",
                value=f"{STATE.stats.services_up}/{STATE.stats.services_total}",
                caption="All green",
                icon="check-circle",
                tone="emerald",
            )
            _stat_card(
                "Active deploys",
                value=STATE.stats.in_flight,
                caption="Rolling right now",
                icon="rocket",
                tone="blue",
            )
            _stat_card(
                "Failures (24h)",
                value=STATE.stats.failures_24h,
                caption="Since yesterday",
                icon="triangle-alert",
                tone="amber",
            )

        # --- environment status ---------------------------------------------
        with Card(css_class="p-6"):
            with CardHeader():
                CardTitle("Environments")
                CardDescription("Live health per environment.")
            with CardContent():
                with Row(gap=6, css_class="items-center flex-wrap"):
                    for env in _ENVS:
                        env_status = STATE.stats.envs[env].status
                        env_version = STATE.stats.envs[env].version
                        # Map status → variant via nested ternaries so the
                        # Dot/Badge flip colors reactively without a server
                        # round-trip:
                        #   healthy  → success (green)
                        #   degraded → warning (amber)
                        #   anything else → destructive (red)
                        tone = (env_status == "healthy").then(
                            "success",
                            (env_status == "degraded").then("warning", "destructive"),
                        )
                        with Row(gap=2, css_class="items-center"):
                            Dot(variant=tone, size="default")
                            Text(env.upper(), css_class="font-mono text-sm text-gray-300")
                            Badge(env_status, variant=tone)
                            Text(env_version, css_class="text-xs text-gray-500 font-mono")

        # --- deploy section (dialog-gated) ----------------------------------
        with Card(css_class="p-6"):
            with CardHeader():
                CardTitle("Deploy a service")
                CardDescription(
                    "Pick a service, click Deploy, and confirm in the dialog."
                )
            with CardContent():
                with Row(gap=3, css_class="items-end flex-wrap"):
                    with Column(gap=2, css_class="flex-1 min-w-48"):
                        Text("Service", css_class="text-xs text-gray-500 uppercase")
                        with Select(
                            name="selected_service",
                            placeholder="Choose a service…",
                            value=_SERVICES[0],
                        ):
                            for svc in _SERVICES:
                                SelectOption(value=svc, label=svc)

                    # The Dialog's FIRST child is the trigger; remaining
                    # children form the body.
                    with Dialog(
                        name="deploy_dialog",
                        title="Confirm production deploy",
                        description=(
                            f"Deploy {STATE.selected_service} to production? "
                            f"This takes ~1s and will show a success banner."
                        ),
                    ):
                        Button(
                            "Deploy to prod",
                            icon="rocket",
                            variant="default",
                        )
                        with Column(gap=3):
                            with Alert(variant="warning", icon="triangle-alert"):
                                AlertTitle("Heads up")
                                AlertDescription(
                                    "Production deploys are observable. The "
                                    "rollout appears in #deploys and can be "
                                    "rolled back from the panel below."
                                )
                            with Row(gap=2, css_class="justify-end"):
                                Button(
                                    "Cancel",
                                    variant="outline",
                                    on_click=SetState("deploy_dialog", False),
                                )
                                Button(
                                    "Confirm deploy",
                                    icon="rocket",
                                    variant="default",
                                    on_click=[
                                        SetState("deploy_dialog", False),
                                        CallTool(
                                            deploy_service,
                                            arguments={"service": STATE.selected_service},
                                            on_success=[
                                                SetState("last_deploy", RESULT),
                                                ShowToast(
                                                    f"Deployed {STATE.selected_service}",
                                                    variant="success",
                                                ),
                                                CallTool(
                                                    get_deploy_stats,
                                                    on_success=SetState("stats", RESULT),
                                                ),
                                            ],
                                            on_error=ShowToast(
                                                "Deploy failed", variant="error"
                                            ),
                                        ),
                                    ],
                                )

        # --- rollback section (elicitation-gated) ---------------------------
        with Card(css_class="p-6"):
            with CardHeader():
                CardTitle("Roll back")
                CardDescription(
                    "Server-side elicitation: the tool pauses and asks the "
                    "client to collect a typed confirmation + reason."
                )
            with CardContent():
                with Row(gap=3, css_class="items-center flex-wrap"):
                    Button(
                        "Roll back selected service",
                        icon="undo-2",
                        variant="destructive",
                        on_click=CallTool(
                            rollback_service,
                            arguments={"service": STATE.selected_service},
                            on_success=[
                                # RESULT.ok is reactive; show different toasts.
                                ShowToast(
                                    f"Rolled back {STATE.selected_service}",
                                    variant="info",
                                ),
                                CallTool(
                                    get_deploy_stats,
                                    on_success=SetState("stats", RESULT),
                                ),
                            ],
                            on_error=ShowToast("Rollback failed", variant="error"),
                        ),
                    )
                    Text(
                        "→ Clicking this fires a tool that calls "
                        "ctx.elicit(RollbackConfirmation). The confirmation "
                        "UI is rendered by your MCP client, not by Prefab.",
                        css_class="text-xs text-gray-500 flex-1",
                    )

        # --- status footer --------------------------------------------------
        with Row(gap=3, css_class="items-center justify-between pt-2"):
            with Row(gap=2, css_class="items-center"):
                Loader(variant="pulse", size="sm")
                Text(
                    "Streaming from MCPAppsDemo",
                    css_class="text-xs text-gray-500",
                )
            Text(
                f"Selected: {STATE.selected_service}",
                css_class="text-xs text-gray-500 font-mono",
            )

    return app


mcp.add_provider(deploy_app)


# =============================================================================
# Generative UI — the LLM writes the UI at runtime
# -----------------------------------------------------------------------------
# The three apps above are "hand-built": we define the Prefab component tree
# server-side and the client just renders it. Generative UI flips that around.
# The `GenerativeUI()` provider registers two tools:
#
#   * `generate_prefab_ui`     — accepts Python code (and an optional data
#                                dict), executes it in a Pyodide sandbox, and
#                                renders the result as a Prefab app. The MCP
#                                Apps protocol streams partial code into the
#                                browser as the LLM generates, so the user
#                                watches the UI build up token by token.
#   * `search_prefab_components` — lets the LLM discover what components
#                                exist before writing code.
#
# Pair it with the `get_lab_spending` seed tool below so the lecture demo has
# a reliable "visualize this data" moment:
#
#   "Call get_lab_spending, then visualize it as a bar chart grouped by
#    category, with stat cards for total spend and top category."
#
# Sandbox note: Pyodide includes stdlib + Prefab only. No numpy / pandas /
# requests. If the LLM tries to import one, the sandbox raises ImportError.
# =============================================================================


@mcp.tool
def get_lab_spending() -> dict:
    """Return last-quarter (Q1 2026) departmental lab spending.

    A deterministic demo dataset shaped for Generative UI. Pair with
    ``generate_prefab_ui`` to build a visualization on the fly, e.g.:

        "Call get_lab_spending, then visualize it as a bar chart
         grouped by category, with stat cards for total spend and
         the top-spending category."

    Returns:
        A dict with ``quarter`` (str), ``rows`` (list of
        ``{month, category, amount}``), and ``summary``
        (total / top_category / mom_change_pct).
    """
    rows = [
        # Jan
        {"month": "Jan", "category": "Equipment",   "amount": 12_400},
        {"month": "Jan", "category": "Travel",      "amount":  2_100},
        {"month": "Jan", "category": "Stipends",    "amount": 18_500},
        {"month": "Jan", "category": "Software",    "amount":  3_200},
        {"month": "Jan", "category": "Conferences", "amount":  1_500},
        # Feb
        {"month": "Feb", "category": "Equipment",   "amount":  8_900},
        {"month": "Feb", "category": "Travel",      "amount":  3_400},
        {"month": "Feb", "category": "Stipends",    "amount": 18_500},
        {"month": "Feb", "category": "Software",    "amount":  2_800},
        {"month": "Feb", "category": "Conferences", "amount":  4_200},
        # Mar
        {"month": "Mar", "category": "Equipment",   "amount":  6_300},
        {"month": "Mar", "category": "Travel",      "amount":  5_100},
        {"month": "Mar", "category": "Stipends",    "amount": 19_000},
        {"month": "Mar", "category": "Software",    "amount":  3_200},
        {"month": "Mar", "category": "Conferences", "amount":  9_700},
    ]
    total = sum(r["amount"] for r in rows)
    by_category: dict[str, int] = {}
    for r in rows:
        by_category[r["category"]] = by_category.get(r["category"], 0) + r["amount"]
    top_category = max(by_category, key=by_category.__getitem__)
    # Feb vs Jan monthly total, as a simple MoM% the LLM can stat-card.
    jan_total = sum(r["amount"] for r in rows if r["month"] == "Jan")
    feb_total = sum(r["amount"] for r in rows if r["month"] == "Feb")
    mom_change_pct = round((feb_total - jan_total) / jan_total * 100, 1)
    return {
        "quarter": "Q1 2026",
        "rows": rows,
        "summary": {
            "total": total,
            "top_category": top_category,
            "mom_change_pct": mom_change_pct,
        },
    }


mcp.add_provider(GenerativeUI())


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
