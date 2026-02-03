"""
Modular MCP Server for COROS Training Hub Data

Provides tools to authenticate with COROS and retrieve activity data
via the Model Context Protocol (MCP).

This server uses a non-public API from COROS Training Hub.
The API could change without notice.
"""

import sys

from mcp.server.fastmcp import FastMCP

from coros_mcp import auth_tool
from coros_mcp import activities


def main():
    """Initialize the MCP server and register all tools."""

    print("Starting COROS MCP Server...", file=sys.stderr)
    print(
        "Note: Use coros_login_tool to authenticate before using data tools.",
        file=sys.stderr,
    )

    # Create the MCP app
    app = FastMCP("COROS Training Hub v1.0")

    # Register auth tools (login, session management, identity)
    app = auth_tool.register_tools(app)

    # Register activity tools
    app = activities.register_tools(app)

    # Run the MCP server
    app.run()


if __name__ == "__main__":
    main()
