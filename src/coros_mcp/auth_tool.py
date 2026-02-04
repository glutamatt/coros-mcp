"""
Authentication tools for COROS MCP server.

Provides login, session management, and common identity tools.
"""

import json

from fastmcp import Context

from coros_mcp.coros_platform import coros_login
from coros_mcp.client_factory import (
    get_client,
    set_session_tokens,
    clear_session_tokens,
    is_token_expired_error,
    handle_token_expired,
)


def register_tools(app):
    """Register authentication and identity tools with the MCP app."""

    @app.tool()
    async def coros_login_tool(email: str, password: str, ctx: Context) -> dict:
        """
        Login to COROS Training Hub.

        Validates credentials with COROS servers and stores session tokens
        for subsequent API calls.

        Args:
            email: Your COROS account email address
            password: Your COROS account password

        Returns:
            Login result with user info or error message
        """
        result = coros_login(email, password)
        if result.success:
            set_session_tokens(ctx, result.tokens)
        return result.to_dict()

    @app.tool()
    async def set_coros_session(coros_tokens: str, ctx: Context) -> dict:
        """
        Restore a COROS session from stored tokens.

        Use this to restore a previous login without re-entering credentials.
        Tokens are typically stored in cookies on the frontend.

        Args:
            coros_tokens: Previously saved session tokens from login

        Returns:
            Session restoration result
        """
        try:
            set_session_tokens(ctx, coros_tokens)
            return {"success": True, "message": "Session restored"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @app.tool()
    async def coros_logout(ctx: Context) -> dict:
        """
        Logout from the current COROS session.

        Clears all session data. User will need to login again.

        Returns:
            Logout confirmation
        """
        clear_session_tokens(ctx)
        return {"success": True, "message": "Logged out"}

    @app.tool()
    async def get_user_name(ctx: Context) -> str:
        """
        Get the current user's display name.

        Returns:
            JSON with user's nickname/display name
        """
        try:
            client = get_client(ctx)
            user = client.get_account()
            return json.dumps({
                "name": user.nickname,
                "user_id": user.user_id,
                "email": user.email,
            }, indent=2)
        except ValueError as e:
            if is_token_expired_error(e):
                return handle_token_expired(ctx)
            raise

    @app.tool()
    async def get_available_features(ctx: Context) -> str:
        """
        Get list of available COROS data features.

        Returns a summary of what data types and tools are available
        through this MCP server.

        Returns:
            JSON with available feature categories
        """
        # COROS has a more limited API compared to Garmin
        # List what we actually support
        features = {
            "platform": "COROS Training Hub",
            "auth": [
                "coros_login_tool - Authenticate with COROS",
                "set_coros_session - Restore saved session",
                "coros_logout - Clear session",
            ],
            "user": [
                "get_user_name - Get display name and user info",
                "get_available_features - This feature list",
            ],
            "activities": [
                "get_activities - List activities with filters",
                "get_activity_details - Detailed activity data",
                "get_activity_download_url - Download activity file",
            ],
            "notes": [
                "COROS API does not provide sleep, HRV, stress, or body battery data",
                "For those metrics, use Garmin or request data export from COROS support",
            ],
        }
        return json.dumps(features, indent=2)

    return app
