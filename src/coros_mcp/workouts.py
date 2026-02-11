"""
Workout builder tools for COROS MCP server.

Create structured workouts, estimate load, and reschedule.
"""

import json
import uuid
from datetime import datetime

from fastmcp import Context

from coros_mcp.client_factory import get_client
from coros_mcp.utils import date_to_coros, format_duration, format_distance


# Sport type mapping for workout programs (program context, not activity context)
PROGRAM_SPORT_TYPES = {
    "running": 1,
    "run": 1,
    "strength": 4,
    "bike": 6,
    "cycling": 6,
    "pool_swim": 9,
    "swim": 9,
    "open_water": 10,
    "trail": 3,
    "hike": 5,
}

# Exercise type codes
EXERCISE_TYPES = {
    "warmup": 1,
    "interval": 2,
    "work": 2,
    "cooldown": 3,
    "recovery": 4,
}


def register_tools(app):
    """Register workout builder tools with the MCP app."""

    @app.tool()
    async def create_workout(
        ctx: Context,
        name: str,
        date: str,
        sport_type: str,
        exercises: list[dict],
        plan_version: int = None,
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
                Example: [
                    {"type": "warmup", "duration_minutes": 15},
                    {"type": "interval", "distance_m": 800, "repeats": 6, "rest_seconds": 90},
                    {"type": "cooldown", "duration_minutes": 10}
                ]
            plan_version: Current plan pbVersion for optimistic concurrency (optional, fetched if not provided)

        Returns:
            JSON with creation result including estimated training load
        """
        client = get_client(ctx)

        sport_code = PROGRAM_SPORT_TYPES.get(sport_type.lower())
        if sport_code is None:
            return json.dumps({
                "error": f"Unknown sport type '{sport_type}'. Use: {', '.join(PROGRAM_SPORT_TYPES.keys())}",
            }, indent=2)

        coros_date = date_to_coros(date)
        program_id = str(uuid.uuid4()).replace("-", "")[:24]

        # Build exercise model
        coros_exercises, is_simple = _build_exercises(exercises)

        # Build program
        program = {
            "id": program_id,
            "name": name,
            "sportType": sport_code,
            "happenDay": coros_date,
            "simple": is_simple,
            "exercises": coros_exercises,
        }

        # Calculate workout to get load estimate and bar chart
        calc_payload = {
            "entity": {"happenDay": coros_date, "idInPlan": program_id, "sortNo": 1},
            "program": program,
        }

        try:
            calc_result = client.calculate_workout(calc_payload)
        except Exception as e:
            return json.dumps({
                "error": f"Workout calculation failed: {str(e)}",
                "hint": "Check exercise definitions. Duration should be in minutes, distance in km or m.",
            }, indent=2)

        # Get plan version if not provided
        if plan_version is None:
            try:
                today = datetime.now().date()
                schedule = client.get_training_schedule(
                    date_to_coros(today.isoformat()),
                    coros_date,
                )
                plan_version = schedule.get("pbVersion", 0)
            except Exception:
                plan_version = 0

        # Update program with calculated values
        program["planDistance"] = calc_result.get("planDistance")
        program["planDuration"] = calc_result.get("planDuration")
        program["planTrainingLoad"] = calc_result.get("planTrainingLoad")
        program["planElevGain"] = calc_result.get("planElevGain")

        # Push to schedule
        schedule_payload = {
            "pbVersion": plan_version,
            "entities": [
                {
                    "happenDay": coros_date,
                    "idInPlan": program_id,
                    "sortNo": 1,
                    "dayNo": 0,
                    "sortNoInPlan": 0,
                    "sortNoInSchedule": 0,
                    "exerciseBarChart": calc_result.get("exerciseBarChart", []),
                }
            ],
            "programs": [program],
            "versionObjects": [
                {"id": program_id, "status": 1},  # status 1 = new
            ],
        }

        try:
            response = client.update_training_schedule(schedule_payload)
        except Exception as e:
            return json.dumps({
                "error": f"Failed to push workout to calendar: {str(e)}",
                "workout_calculated": True,
                "planned_load": calc_result.get("planTrainingLoad"),
            }, indent=2)

        if response.get("result") == "0000":
            return json.dumps({
                "success": True,
                "workout_id": program_id,
                "name": name,
                "date": date,
                "sport": sport_type,
                "estimated_distance": format_distance(calc_result.get("planDistance", 0)),
                "estimated_duration": format_duration(calc_result.get("planDuration", 0)),
                "estimated_load": calc_result.get("planTrainingLoad"),
                "message": f"Workout '{name}' scheduled for {date}. It will sync to the COROS watch.",
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": response.get("message", "Unknown error pushing to calendar"),
            }, indent=2)

    @app.tool()
    async def estimate_workout_load(
        ctx: Context,
        sport_type: str,
        exercises: list[dict],
        date: str = None,
    ) -> str:
        """
        Preview the training load of a workout before creating it.

        Use this to iterate on workout design — check if the load is appropriate
        before committing to the training calendar.

        Args:
            sport_type: Sport type (running, bike, swim, etc.)
            exercises: Exercise blocks (same format as create_workout)
            date: Optional date in YYYY-MM-DD format (default: today)

        Returns:
            JSON with estimated distance, duration, and training load
        """
        client = get_client(ctx)

        sport_code = PROGRAM_SPORT_TYPES.get(sport_type.lower())
        if sport_code is None:
            return json.dumps({
                "error": f"Unknown sport type '{sport_type}'. Use: {', '.join(PROGRAM_SPORT_TYPES.keys())}",
            }, indent=2)

        if not date:
            date = datetime.now().date().isoformat()

        coros_date = date_to_coros(date)
        program_id = "estimate_preview"

        coros_exercises, is_simple = _build_exercises(exercises)

        program = {
            "id": program_id,
            "name": "Preview",
            "sportType": sport_code,
            "happenDay": coros_date,
            "simple": is_simple,
            "exercises": coros_exercises,
        }

        payload = {
            "entity": {"happenDay": coros_date, "idInPlan": program_id, "sortNo": 1},
            "program": program,
        }

        try:
            result = client.estimate_workout(payload)
        except Exception as e:
            return json.dumps({
                "error": f"Estimation failed: {str(e)}",
            }, indent=2)

        return json.dumps({
            "estimated_distance": format_distance(result.get("distance", 0)),
            "estimated_duration": format_duration(result.get("duration", 0)),
            "estimated_load": result.get("trainingLoad"),
            "sets": result.get("sets"),
        }, indent=2)

    @app.tool()
    async def reschedule_workout(
        ctx: Context,
        workout_id: str,
        new_date: str,
        plan_version: int,
    ) -> str:
        """
        Move a scheduled workout to a different date.

        Args:
            workout_id: The workout/program ID from get_training_schedule
            new_date: New date in YYYY-MM-DD format
            plan_version: Current plan pbVersion (for optimistic concurrency)

        Returns:
            JSON with reschedule result
        """
        client = get_client(ctx)

        new_coros_date = date_to_coros(new_date)

        # First get current schedule to find the workout
        today = datetime.now().date()
        try:
            schedule = client.get_training_schedule(
                date_to_coros(today.isoformat()),
                new_coros_date + 30,  # Search range wide enough
            )
        except Exception:
            schedule = {"programs": []}

        # Find the workout
        target_program = None
        for p in schedule.get("programs", []):
            if p.get("id") == workout_id:
                target_program = p
                break

        if not target_program:
            return json.dumps({
                "error": f"Workout {workout_id} not found in current plan",
            }, indent=2)

        # Update the program date
        target_program["happenDay"] = new_coros_date

        payload = {
            "pbVersion": plan_version,
            "entities": [
                {
                    "happenDay": new_coros_date,
                    "idInPlan": workout_id,
                    "sortNo": 1,
                    "dayNo": 0,
                    "sortNoInPlan": 0,
                    "sortNoInSchedule": 0,
                }
            ],
            "programs": [target_program],
            "versionObjects": [
                {"id": workout_id, "status": 1},  # status 1 = update
            ],
        }

        try:
            response = client.update_training_schedule(payload)
        except Exception as e:
            return json.dumps({
                "error": f"Reschedule failed: {str(e)}",
            }, indent=2)

        if response.get("result") == "0000":
            return json.dumps({
                "success": True,
                "message": f"Workout '{target_program.get('name', workout_id)}' moved to {new_date}",
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": response.get("message", "Unknown error"),
            }, indent=2)

    return app


def _build_exercises(exercises: list[dict]) -> tuple[list[dict], bool]:
    """
    Convert AI-friendly exercise definitions to COROS exercise model.

    Returns (coros_exercises, is_simple).
    """
    if len(exercises) == 1 and exercises[0].get("type") not in ("interval", "work"):
        # Single non-interval exercise = simple workout
        return [_build_single_exercise(exercises[0], sort_no=1)], True

    coros_exercises = []
    sort_no = 1

    for ex in exercises:
        repeats = ex.get("repeats")

        if repeats and repeats > 1:
            # Create repeat group
            group_sort = sort_no
            group = {
                "sortNo": group_sort,
                "exerciseType": 0,  # Group/repeat
                "isGroup": True,
                "sets": repeats,
                "restType": 0 if ex.get("rest_seconds") else 3,
                "restValue": ex.get("rest_seconds", 0),
                "name": f"{repeats}x",
            }
            coros_exercises.append(group)
            sort_no += 1

            # Work step inside group
            work_step = _build_single_exercise(ex, sort_no=sort_no, exercise_type=2)
            work_step["groupId"] = group_sort
            coros_exercises.append(work_step)
            sort_no += 1

            # Recovery step inside group (if rest specified)
            if ex.get("rest_seconds"):
                recovery = {
                    "sortNo": sort_no,
                    "exerciseType": 4,  # Recovery
                    "groupId": group_sort,
                    "targetType": 2,  # Duration
                    "targetValue": ex["rest_seconds"],
                    "targetDisplayUnit": 0,
                    "intensityType": 0,
                    "name": "Recovery",
                }
                coros_exercises.append(recovery)
                sort_no += 1
        else:
            coros_exercises.append(_build_single_exercise(ex, sort_no=sort_no))
            sort_no += 1

    return coros_exercises, False


def _build_single_exercise(ex: dict, sort_no: int, exercise_type: int = None) -> dict:
    """Build a single COROS exercise from an AI-friendly definition."""
    ex_type = exercise_type or EXERCISE_TYPES.get(ex.get("type", "interval"), 2)

    result = {
        "sortNo": sort_no,
        "exerciseType": ex_type,
        "intensityType": 0,  # Open/free pace by default
        "name": ex.get("name", _default_exercise_name(ex_type)),
    }

    # Set target: duration or distance
    if ex.get("duration_minutes"):
        result["targetType"] = 2  # Duration
        result["targetValue"] = int(ex["duration_minutes"] * 60)
        result["targetDisplayUnit"] = 0  # Seconds
    elif ex.get("distance_km"):
        result["targetType"] = 5  # Distance
        result["targetValue"] = int(ex["distance_km"] * 1000)
        result["targetDisplayUnit"] = 2  # Kilometers
    elif ex.get("distance_m"):
        result["targetType"] = 5  # Distance
        result["targetValue"] = int(ex["distance_m"])
        result["targetDisplayUnit"] = 1  # Meters

    return result


def _default_exercise_name(exercise_type: int) -> str:
    """Get default name for an exercise type."""
    names = {1: "Warm Up", 2: "Work", 3: "Cool Down", 4: "Recovery"}
    return names.get(exercise_type, "Exercise")
