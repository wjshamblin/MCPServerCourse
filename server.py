"""
Step 11: Composed Server — Finance (with MCP Apps) + Directory (OBO)

Mounts both the financial and directory servers under one endpoint.
The financial server exposes three interactive MCP Apps (dashboards)
in addition to its SQL query tools.
"""

from fastmcp import FastMCP

from financial_server import mcp as financial_mcp
from directory_server import mcp as directory_mcp

main = FastMCP(
    "UniversityServices",
    instructions=(
        "Unified university services. Use finance_* tools for financial data, "
        "directory_* tools for people lookup."
    ),
)

main.mount(financial_mcp, namespace="finance")
main.mount(directory_mcp, namespace="directory")

if __name__ == "__main__":
    main.run(transport="http", host="0.0.0.0", port=8000)
