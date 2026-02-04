"""
Client factory for COROS MCP server.

Provides session-based client management using FastMCP Context.
"""

from fastmcp import Context

from coros_mcp.coros_client import CorosClient


COROS_TOKENS_KEY = "coros_tokens"


def create_client_from_tokens(tokens: str) -> CorosClient:
    """
    Create a COROS client from serialized tokens.

    Args:
        tokens: JSON string from CorosClient.export_token()

    Returns:
        Authenticated CorosClient instance
    """
    client = CorosClient()
    client.load_token(tokens)
    return client


def serialize_tokens(client: CorosClient) -> str:
    """
    Serialize a client's tokens for storage.

    Args:
        client: Authenticated CorosClient instance

    Returns:
        JSON string that can be used with create_client_from_tokens()
    """
    return client.export_token()


def get_client(ctx: Context) -> CorosClient:
    """
    Get COROS client from session.

    Args:
        ctx: FastMCP Context

    Returns:
        Authenticated CorosClient instance

    Raises:
        ValueError: If no session exists (user not logged in)
    """
    tokens = ctx.get_state(COROS_TOKENS_KEY)
    if not tokens:
        raise ValueError("No COROS session. Call coros_login() first.")
    return create_client_from_tokens(tokens)


def set_session_tokens(ctx: Context, tokens: str) -> None:
    """
    Store tokens in the session.

    Args:
        ctx: FastMCP Context
        tokens: Serialized tokens from CorosClient.export_token()
    """
    ctx.set_state(COROS_TOKENS_KEY, tokens)


def clear_session_tokens(ctx: Context) -> None:
    """
    Clear tokens from the session.

    Args:
        ctx: FastMCP Context
    """
    ctx.set_state(COROS_TOKENS_KEY, None)
