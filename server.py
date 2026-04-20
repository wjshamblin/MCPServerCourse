"""
Step 08: Composed Server with Azure OAuth (Confidential Client)

Top-level entry point. Declares the Azure OAuth proxy on the main
FastMCP instance (so /.well-known/oauth-* endpoints are advertised)
and mounts the financial server as a namespaced child.

The `auth` object is built in financial_server.py so the child can
also be run standalone for testing; the composed main re-uses it.
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
