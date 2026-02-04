"""
Modular MCP Server for COROS Training Hub Data

Provides tools to authenticate with COROS and retrieve activity data
via the Model Context Protocol (MCP).

This server uses a non-public API from COROS Training Hub.
The API could change without notice.

Supports two transport modes:
- stdio: For single-user local usage (default)
- http: For multi-user HTTP server deployment
"""

import os

from fastmcp import FastMCP

from coros_mcp import auth_tool
from coros_mcp import activities


def create_app() -> FastMCP:
    """Create and configure the MCP app with all tools registered."""
    # Create the MCP app
    app = FastMCP("COROS Training Hub v1.0")

    # Register auth tools (login, session management, identity)
    app = auth_tool.register_tools(app)

    # Register activity tools
    app = activities.register_tools(app)

    return app


def main():
    """Initialize the MCP server and run with configured transport.

    Environment variables:
    - MCP_TRANSPORT: 'stdio' (default) or 'http'
    - MCP_HOST: Host to bind to (default: '0.0.0.0')
    - MCP_PORT: Port for HTTP transport (default: 8081)
    """
    app = create_app()

    transport = os.environ.get("MCP_TRANSPORT", "stdio")

    if transport == "http":
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("MCP_PORT", "8081"))
        app.run(transport="http", host=host, port=port)
    else:
        # Default to stdio for backward compatibility
        app.run()


if __name__ == "__main__":
    main()
