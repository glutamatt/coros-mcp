"""
Client factory for COROS MCP server.

Provides session-based client management using FastMCP Context.
Each MCP connection has isolated session state via mcp-session-id header.

Session Persistence:
- FastMCP Context state (ctx._state) doesn't persist across HTTP requests
- Solution: File-based session store using ctx.session_id as key
- Sessions stored in /data/coros_sessions/{session_id}.json
"""

import os
import json
from pathlib import Path
from fastmcp import Context

from coros_mcp.coros_client import CorosClient


COROS_TOKENS_KEY = "coros_tokens"
SESSION_STORE_DIR = Path(os.environ.get("COROS_SESSION_DIR", "/data/coros_sessions"))


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


def _get_session_file_path(session_id: str) -> Path:
    """Get the file path for a session's data."""
    # Ensure session store directory exists
    SESSION_STORE_DIR.mkdir(parents=True, exist_ok=True)
    # Sanitize session_id to prevent path traversal
    safe_session_id = "".join(c for c in session_id if c.isalnum() or c in "-_")
    return SESSION_STORE_DIR / f"{safe_session_id}.json"


def _load_session_data(session_id: str) -> dict:
    """Load session data from file system."""
    session_file = _get_session_file_path(session_id)
    if not session_file.exists():
        return {}
    try:
        with open(session_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _save_session_data(session_id: str, data: dict) -> None:
    """Save session data to file system."""
    session_file = _get_session_file_path(session_id)
    try:
        with open(session_file, "w") as f:
            json.dump(data, f)
    except IOError as e:
        # Log error but don't fail - session won't persist but tool will still work
        print(f"Warning: Failed to save session data: {e}")


def _get_session_tokens(ctx: Context) -> str | None:
    """
    Get COROS tokens from persistent session store.

    First checks in-memory Context state (for performance within same request),
    then falls back to file-based session store for cross-request persistence.
    """
    # First try in-memory state (fast path for same-request calls)
    tokens = ctx.get_state(COROS_TOKENS_KEY)
    if tokens:
        return tokens

    # Fall back to persistent session store
    try:
        session_id = ctx.session_id
        session_data = _load_session_data(session_id)
        tokens = session_data.get(COROS_TOKENS_KEY)

        # Cache in context state for this request
        if tokens:
            ctx.set_state(COROS_TOKENS_KEY, tokens)

        return tokens
    except RuntimeError:
        # session_id not available (not in request context)
        return None


def _set_session_tokens_persistent(ctx: Context, tokens: str) -> None:
    """
    Store COROS tokens in both in-memory Context and persistent session store.
    """
    # Store in context state (for current request)
    ctx.set_state(COROS_TOKENS_KEY, tokens)

    # Store in persistent session store (for future requests)
    try:
        session_id = ctx.session_id
        session_data = _load_session_data(session_id)
        session_data[COROS_TOKENS_KEY] = tokens
        _save_session_data(session_id, session_data)
    except RuntimeError:
        # session_id not available (not in request context)
        # Fall back to context state only (non-persistent)
        pass


def _clear_session_tokens_persistent(ctx: Context) -> None:
    """
    Clear COROS tokens from both in-memory Context and persistent session store.
    """
    # Clear from context state
    ctx.set_state(COROS_TOKENS_KEY, None)

    # Clear from persistent session store
    try:
        session_id = ctx.session_id
        session_file = _get_session_file_path(session_id)
        if session_file.exists():
            session_file.unlink()
    except RuntimeError:
        # session_id not available (not in request context)
        pass


def get_client(ctx: Context) -> CorosClient:
    """
    Get COROS client from session Context.

    Automatically loads tokens from persistent session store if not in memory.

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
    Store COROS tokens in persistent session store.

    Tokens are stored both in-memory (for current request) and on disk
    (for future requests with same session_id).

    Args:
        ctx: FastMCP Context
        tokens: Serialized tokens from CorosClient.export_token()
    """
    _set_session_tokens_persistent(ctx, tokens)


def clear_session_tokens(ctx: Context) -> None:
    """
    Clear COROS tokens from persistent session store.

    Removes tokens from both in-memory context and disk storage.

    Args:
        ctx: FastMCP Context
    """
    _clear_session_tokens_persistent(ctx)


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
