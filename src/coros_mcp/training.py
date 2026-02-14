"""
Training schedule tools for COROS MCP server.

Training plan viewing, plan adherence, and workout deletion.
Delegates to api.calendar and api.workouts for formatting.
"""

import json
import logging

from fastmcp import Context

logger = logging.getLogger(__name__)

from coros_mcp.client_factory import get_client
from coros_mcp.api import calendar as api_calendar
from coros_mcp.api import workouts as api_workouts


def register_tools(app):
    """Register training schedule tools with the MCP app."""

    @app.tool()
    async def get_training_schedule(
        ctx: Context,
        start_date: str = None,
        end_date: str = None,
    ) -> str:
        """
        Get the current training plan with all scheduled workouts.

        Shows what's planned for the given date range including workout details,
        completed activities not in the plan, and weekly training stages.

        Args:
            start_date: Start date in YYYY-MM-DD format (default: start of current week)
            end_date: End date in YYYY-MM-DD format (default: end of current week)

        Returns:
            JSON with training schedule data
        """
        client = get_client(ctx)
        result = api_calendar.get_calendar(client, start_date, end_date)
        return json.dumps(result, indent=2)

    @app.tool()
    async def get_plan_adherence(
        ctx: Context,
        start_date: str = None,
        end_date: str = None,
    ) -> str:
        """
        Get actual vs planned training compliance.

        Compares planned and actual distance, duration, and training load
        at daily and weekly levels. Essential for tracking plan adherence.

        Args:
            start_date: Start date in YYYY-MM-DD format (default: 4 weeks ago)
            end_date: End date in YYYY-MM-DD format (default: today)

        Returns:
            JSON with plan adherence data
        """
        client = get_client(ctx)
        result = api_calendar.get_adherence(client, start_date, end_date)
        return json.dumps(result, indent=2)

    @app.tool()
    async def delete_scheduled_workout(
        ctx: Context,
        workout_id: str,
        date: str,
    ) -> str:
        """
        Delete a scheduled workout from the training plan.

        Removes a specific workout. Use get_training_schedule first to find workout IDs and dates.

        Args:
            workout_id: The workout ID from get_training_schedule
            date: The workout date in YYYY-MM-DD format (from get_training_schedule)

        Returns:
            JSON with deletion result
        """
        client = get_client(ctx)
        try:
            result = api_workouts.delete_workout(client, workout_id, date)
        except ValueError as e:
            logger.error(f"delete_scheduled_workout failed: {e}")
            result = {"success": False, "error": str(e)}
        return json.dumps(result, indent=2)

    return app
