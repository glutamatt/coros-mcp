"""
Workout builder tools for COROS MCP server.

Create structured workouts, estimate load, and reschedule.
Delegates to api.workouts for the heavy lifting.
"""

import json
import logging

from fastmcp import Context

from coros_mcp.client_factory import get_client
from coros_mcp.api import workouts as api_workouts

logger = logging.getLogger(__name__)


def register_tools(app):
    """Register workout builder tools with the MCP app."""

    @app.tool()
    async def create_workout(
        ctx: Context,
        name: str,
        date: str,
        sport_type: str,
        exercises: list[dict],
    ) -> str:
        """
        Create a structured workout and push it to the COROS training calendar.

        Builds a workout from exercise blocks and schedules it for the given date.
        The workout syncs to the athlete's COROS watch.

        Args:
            name: Workout name (e.g. "Tempo Run", "6x800m Intervals")
            date: Workout date in YYYY-MM-DD format
            sport_type: Sport type - one of: running, bike, cycling, swim, pool_swim, trail, strength, hike
            exercises: List of exercise blocks. Each block is a dict with:
                - type: "warmup", "interval", "cooldown", or "recovery"
                - duration_minutes: Duration in minutes (for time-based exercises)
                - distance_km: Distance in km (for distance-based exercises)
                - distance_m: Distance in meters (for short intervals like 400m)
                - repeats: Number of repetitions (creates a repeat group)
                - rest_seconds: Rest between repetitions (only with repeats)
                - pace_per_km: Target pace as "M:SS" or "M:SS-M:SS" range
                - hr_bpm: Target HR as "150" or "150-160" range
                Example: [
                    {"type": "warmup", "duration_minutes": 15},
                    {"type": "interval", "distance_m": 800, "repeats": 6, "rest_seconds": 90},
                    {"type": "cooldown", "duration_minutes": 10}
                ]

        Returns:
            JSON with creation result including estimated training load
        """
        client = get_client(ctx)
        try:
            result = api_workouts.create_workout(client, name, date, sport_type, exercises)
        except ValueError as e:
            result = {"success": False, "error": str(e)}
        except Exception as e:
            result = {"success": False, "error": f"Workout creation failed: {str(e)}"}
        return json.dumps(result, indent=2)

    @app.tool()
    async def estimate_workout_load(
        ctx: Context,
        sport_type: str,
        exercises: list[dict],
        date: str = None,
    ) -> str:
        """
        Preview the training load of a workout before creating it.

        Use this to iterate on workout design -- check if the load is appropriate
        before committing to the training calendar.

        Args:
            sport_type: Sport type (running, bike, swim, etc.)
            exercises: Exercise blocks (same format as create_workout)
            date: Optional date in YYYY-MM-DD format (default: today)

        Returns:
            JSON with estimated distance, duration, and training load
        """
        client = get_client(ctx)
        try:
            result = api_workouts.estimate_workout(client, sport_type, exercises, date)
        except ValueError as e:
            result = {"error": str(e)}
        except Exception as e:
            result = {"error": f"Estimation failed: {str(e)}"}
        return json.dumps(result, indent=2)

    @app.tool()
    async def reschedule_workout(
        ctx: Context,
        workout_id: str,
        new_date: str,
    ) -> str:
        """
        Move a scheduled workout to a different date.

        Args:
            workout_id: The workout/program ID from get_training_schedule
            new_date: New date in YYYY-MM-DD format

        Returns:
            JSON with reschedule result
        """
        client = get_client(ctx)
        try:
            result = api_workouts.reschedule_workout(client, workout_id, new_date)
        except ValueError as e:
            result = {"success": False, "error": str(e)}
        return json.dumps(result, indent=2)

    return app
