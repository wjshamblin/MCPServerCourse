"""
Composed University Services Server

Mounts both the financial and directory servers under one endpoint.
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
