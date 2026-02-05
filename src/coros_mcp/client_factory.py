"""
Client factory for COROS MCP server.

Provides stateless session-based client management using FastMCP Context.
Each MCP connection has isolated session state via mcp-session-id header.

Multi-user support:
- HTTP transport with mcp-session-id header provides session isolation
- Tokens stored in memory (per-request context) only
- Frontend manages token persistence via cookies
- No file storage required

Session Management:
- Tokens passed from frontend on each request via setSession()
- Stored in FastMCP Context state (memory-only, per-request)
- Ephemeral clients created from tokens in request context
"""

import json
import logging
from fastmcp import Context

from coros_mcp.coros_client import CorosClient

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


COROS_TOKENS_KEY = "coros_tokens"


def create_client_from_tokens(tokens: str) -> CorosClient:
    """
    Create a COROS client from serialized tokens.

    Args:
        tokens: JSON string from CorosClient.export_token()

    Returns:
        Authenticated CorosClient instance
    """
    # Use EU region by default (most users are in Europe)
    client = CorosClient(region="eu")
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


def _get_session_tokens(ctx: Context) -> str | None:
    """
    Get COROS tokens from request context (memory-only).

    Tokens are passed from frontend on each request via setSession().
    No file-based persistence - frontend manages token lifecycle via cookies.

    Args:
        ctx: FastMCP Context (automatically injected by framework)

    Returns:
        JSON string of tokens or None if not set
    """
    return ctx.get_state(COROS_TOKENS_KEY)


def _set_session_tokens(ctx: Context, tokens: str) -> None:
    """
    Store COROS tokens in request context (memory-only).

    Tokens are stored for the duration of the request only.
    Frontend is responsible for persisting tokens across requests.

    Args:
        ctx: FastMCP Context
        tokens: JSON string from CorosClient.export_token()
    """
    ctx.set_state(COROS_TOKENS_KEY, tokens)


def _clear_session_tokens(ctx: Context) -> None:
    """
    Clear COROS tokens from request context (memory-only).

    This only clears the in-memory state. Frontend must also clear
    its stored tokens (cookies) for complete logout.

    Args:
        ctx: FastMCP Context
    """
    ctx.set_state(COROS_TOKENS_KEY, None)


def get_client(ctx: Context) -> CorosClient:
    """
    Get COROS client from session Context (memory-only).

    Tokens must be set via set_coros_session() before calling tools.
    Frontend passes tokens on each request - no file-based persistence.

    Usage in tools:
        @app.tool()
        async def get_activities(ctx: Context) -> str:
            client = get_client(ctx)
            return json.dumps(client.get_activities())

    Args:
        ctx: FastMCP Context (automatically injected by framework)

    Returns:
        Authenticated CorosClient instance

    Raises:
        ValueError: If no COROS session is active
    """
    tokens = _get_session_tokens(ctx)
    if not tokens:
        raise ValueError("No COROS session. Call coros_login() first.")
    return create_client_from_tokens(tokens)


def set_session_tokens(ctx: Context, tokens: str) -> None:
    """
    Store COROS tokens in request context (memory-only).

    This only stores tokens for the current request. Frontend is responsible
    for persisting tokens across requests (typically via cookies).

    Args:
        ctx: FastMCP Context
        tokens: Serialized tokens from CorosClient.export_token()
    """
    _set_session_tokens(ctx, tokens)


def clear_session_tokens(ctx: Context) -> None:
    """
    Clear COROS tokens from request context (memory-only).

    Frontend must also clear its stored tokens for complete logout.

    Args:
        ctx: FastMCP Context
    """
    _clear_session_tokens(ctx)


def is_token_expired_error(error: Exception) -> bool:
    """
    Check if an error indicates that the COROS access token has expired.

    COROS tokens can expire at any time without warning. The API returns
    "Access token is invalid" when a token has expired or been invalidated
    (e.g., by logging in via the webapp).

    Args:
        error: The exception to check

    Returns:
        True if the error indicates an expired/invalid token
    """
    error_msg = str(error).lower()
    return "access token is invalid" in error_msg or "token" in error_msg and "invalid" in error_msg


def handle_token_expired(ctx: Context) -> str:
    """
    Handle an expired COROS token by clearing the session.

    When a token expires, we clear it from the session store so that
    the user is prompted to log in again on their next request.

    Args:
        ctx: FastMCP Context

    Returns:
        Error message to return to the user
    """
    try:
        clear_session_tokens(ctx)
    except Exception:
        # Ignore errors during cleanup
        pass

    return json.dumps({
        "error": "Your COROS session has expired. Please log in again.",
        "error_code": "SESSION_EXPIRED",
        "note": "COROS tokens can expire at any time. Logging in via the COROS webapp will also invalidate tokens from this app."
    }, indent=2)
