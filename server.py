"""
Step 09: Composed Server with Azure Public Client + Security

Top-level entry point. Declares the Azure Public Client auth proxy
on the main FastMCP instance (so /.well-known/oauth-* endpoints are
advertised) and mounts the financial server as a namespaced child.

The `auth` object (plus allowlist + audit wiring) is built in
financial_server.py so the child can also be run standalone; the
composed main re-uses it.
"""

from financial_server import mcp as financial_mcp, auth
from fastmcp import FastMCP
from config import load_config

config = load_config()

main = FastMCP(
    "UniversityServices",
    instructions=(
        "Unified university services server. Use finance_* tools for "
        "financial data queries, and other namespaced tools as available."
    ),
    auth=auth,
)

main.mount(financial_mcp, namespace="finance")

if __name__ == "__main__":
    main.run(transport="http", host=config.server_host, port=config.server_port)
