"""
Training plan tools for COROS MCP server.

Multi-week plan management: create, view, activate, delete.
Delegates to api.plans for the heavy lifting.
"""

import json
import logging

from fastmcp import Context

from coros_mcp.client_factory import get_client
from coros_mcp.api import plans as api_plans

logger = logging.getLogger(__name__)


def register_tools(app):
    """Register training plan tools with the MCP app."""

    @app.tool()
    async def list_training_plans(
        ctx: Context,
        status: str = "draft",
    ) -> str:
        """
        List training plan templates.

        Args:
            status: Filter by status: "draft" (not yet applied) or "active" (applied to calendar).
                    Default: "draft"

        Returns:
            JSON list of plans with id, name, weeks, workout count
        """
        client = get_client(ctx)
        result = api_plans.list_plans(client, status)
        return json.dumps(result, indent=2)

    @app.tool()
    async def get_training_plan(
        ctx: Context,
        plan_id: str,
    ) -> str:
        """
        Get full details of a training plan.

        Returns the plan with all workouts, their exercises, and day offsets.

        Args:
            plan_id: The plan ID from list_training_plans

        Returns:
            JSON with plan details and all workouts
        """
        client = get_client(ctx)
        result = api_plans.get_plan(client, plan_id)
        return json.dumps(result, indent=2)

    @app.tool()
    async def create_training_plan(
        ctx: Context,
        name: str,
        overview: str,
        workouts: list[dict],
    ) -> str:
        """
        Create a multi-week training plan template.

        The plan is created as a template (draft). Use activate_training_plan
        to apply it to the calendar at a specific start date.

        Args:
            name: Short plan name
            overview: Plan description (shown in COROS app)
            workouts: List of workout definitions. Each workout is a dict with:
                - day: Day offset (0 = first day, 1 = second day, etc.)
                - name: Workout name
                - sport: Sport type (running, bike, etc.)
                - exercises: Exercise blocks (same format as create_workout)
                Example: [
                    {"day": 0, "name": "Easy Run", "sport": "running",
                     "exercises": [{"type": "warmup", "duration_minutes": 30}]},
                    {"day": 2, "name": "Intervals", "sport": "running",
                     "exercises": [
                         {"type": "warmup", "duration_minutes": 15},
                         {"type": "interval", "distance_m": 800, "repeats": 6, "rest_seconds": 90},
                         {"type": "cooldown", "duration_minutes": 10}
                     ]}
                ]

        Returns:
            JSON with creation result including plan_id
        """
        client = get_client(ctx)
        try:
            result = api_plans.create_plan(client, name, overview, workouts)
        except Exception as e:
            result = {"success": False, "error": f"Plan creation failed: {str(e)}"}
        return json.dumps(result, indent=2)

    @app.tool()
    async def add_workout_to_plan(
        ctx: Context,
        plan_id: str,
        day: int,
        name: str,
        sport: str,
        exercises: list[dict],
    ) -> str:
        """
        Add a workout to an existing plan template.

        Args:
            plan_id: The plan ID to add the workout to
            day: Day offset within the plan (0 = first day)
            name: Workout name
            sport: Sport type (running, bike, etc.)
            exercises: Exercise blocks (same format as create_workout)

        Returns:
            JSON with the new workout's ID and position
        """
        client = get_client(ctx)
        try:
            result = api_plans.add_workout_to_plan(client, plan_id, day, name, sport, exercises)
        except Exception as e:
            result = {"success": False, "error": str(e)}
        return json.dumps(result, indent=2)

    @app.tool()
    async def activate_training_plan(
        ctx: Context,
        plan_id: str,
        start_date: str,
    ) -> str:
        """
        Apply a plan template to the training calendar.

        Copies the plan's workouts into the calendar starting from the given date.
        Each workout is placed at its day offset relative to start_date.

        Args:
            plan_id: The plan ID to activate
            start_date: Calendar start date in YYYY-MM-DD format

        Returns:
            JSON with activation confirmation
        """
        client = get_client(ctx)
        try:
            result = api_plans.activate_plan(client, plan_id, start_date)
        except Exception as e:
            result = {"success": False, "error": str(e)}
        return json.dumps(result, indent=2)

    @app.tool()
    async def delete_training_plans(
        ctx: Context,
        plan_ids: list[str],
    ) -> str:
        """
        Delete training plan templates.

        Args:
            plan_ids: List of plan IDs to delete

        Returns:
            JSON with deletion confirmation
        """
        client = get_client(ctx)
        try:
            result = api_plans.delete_plans(client, plan_ids)
        except Exception as e:
            result = {"success": False, "error": str(e)}
        return json.dumps(result, indent=2)

    return app
