"""
Entry point for running coros_mcp as a module.

Usage:
    python -m coros_mcp                    # Run with stdio transport
    python -m coros_mcp --http             # Run with HTTP transport
    python -m coros_mcp --http --port 9000 # Run HTTP on custom port
"""

import argparse
import os

from coros_mcp import create_app


def main():
    parser = argparse.ArgumentParser(
        description="COROS MCP Server - Multi-user session-based COROS Training Hub API"
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Use http transport instead of stdio"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8081,
        help="Port for HTTP transport (default: 8081)"
    )

    args = parser.parse_args()

    # Set environment variables for the app
    if args.http:
        os.environ["MCP_TRANSPORT"] = "http"
        os.environ["MCP_HOST"] = args.host
        os.environ["MCP_PORT"] = str(args.port)
    else:
        os.environ["MCP_TRANSPORT"] = "stdio"

    app = create_app()

    if args.http:
        print(f"Starting COROS MCP server on http://{args.host}:{args.port}/mcp")
        app.run(transport="http", host=args.host, port=args.port)
    else:
        app.run()


if __name__ == "__main__":
    main()
