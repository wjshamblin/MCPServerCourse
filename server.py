"""
Step 01: Hello World MCP Server

A minimal MCP server demonstrating the basics:
- Creating a FastMCP server instance
- Defining tools with @mcp.tool
- Type annotations for automatic schema generation
- Running with HTTP streamable transport
"""

from fastmcp import FastMCP

mcp = FastMCP(
    "HelloWorld",
    instructions="A simple demo MCP server. Use the echo tool to echo messages and the add tool to add numbers.",
)


@mcp.tool
def echo(message: str) -> str:
    """Echo a message back to the caller."""
    return f"Echo: {message}"


@mcp.tool
def add(a: int, b: int) -> int:
    """Add two numbers together and return the result."""
    return a + b


@mcp.tool
def greet(name: str, greeting: str = "Hello") -> str:
    """Greet someone by name. Optionally customize the greeting."""
    return f"{greeting}, {name}! Welcome to MCP."


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
