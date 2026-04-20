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

This file ships one app — a tiny "Counter" — plus a couple of plain
tools. Replace the inline auth stub at the top of the file with any of
the auth proxies from steps 07–10 to gate the apps and tools.

Run:  python server.py

Connect from Claude Desktop / Cursor / VS Code, then look for the
"Counter" app entry and open it. The same `bump_counter` tool can also
be invoked directly by the model.
"""

import logging

from dotenv import load_dotenv
from fastmcp import FastMCP
from fastmcp.apps import FastMCPApp
from prefab_ui.app import PrefabApp
from prefab_ui.components import (
    Button, Column, Heading, Metric, Row, Separator, Text,
)
from prefab_ui.actions import SetState, ShowToast
from prefab_ui.actions.mcp import CallTool
from prefab_ui.rx import RESULT, Rx, STATE

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
        "Minimal MCP Apps demo. Open the 'Counter' app to interact with it "
        "in your AI client, or call hello() / add() / bump_counter() directly."
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


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
