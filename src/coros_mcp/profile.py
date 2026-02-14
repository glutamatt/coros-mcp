"""
Athlete profile tool for COROS MCP server.

Delegates to api.profile for formatting.
"""

import json

from fastmcp import Context

from coros_mcp.client_factory import get_client
from coros_mcp.api import profile as api_profile


def register_tools(app):
    """Register profile tools with the MCP app."""

    @app.tool()
    async def get_athlete_profile(ctx: Context) -> str:
        """
        Get the athlete's full profile with biometrics and training zones.

        Returns height, weight, max HR, resting HR, LTHR, FTP,
        and all training zones (HR, pace, power). Essential context
        for all coaching decisions.

        Returns:
            JSON with athlete profile and training zones
        """
        client = get_client(ctx)
        result = api_profile.get_athlete_profile(client)
        return json.dumps(result, indent=2)

    return app
