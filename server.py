"""
Step 08: Composed Server with Azure OAuth (Confidential Client)

Demonstrates mounting multiple FastMCP servers into a single endpoint.
The financial server is mounted with a namespace prefix.
"""

from fastmcp import FastMCP

from financial_server import mcp as financial_mcp

main = FastMCP(
    "UniversityServices",
    instructions=(
        "Unified university services server. Use finance_* tools for "
        "financial data queries, and other namespaced tools as available."
    ),
)

main.mount(financial_mcp, namespace="finance")

if __name__ == "__main__":
    main.run(transport="http", host="0.0.0.0", port=8000)
