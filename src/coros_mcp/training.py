"""
Training schedule tools for COROS MCP server.

Training plan viewing, plan adherence, and workout deletion.
"""

import json
from datetime import datetime, timedelta

from fastmcp import Context

from coros_mcp.client_factory import get_client
from coros_mcp.utils import date_to_coros, coros_to_date, format_duration, format_distance, get_sport_name


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

        # Default to current week (Monday to Sunday)
        if not start_date or not end_date:
            today = datetime.now().date()
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)
            start_date = start_date or monday.isoformat()
            end_date = end_date or sunday.isoformat()

        data = client.get_training_schedule(
            date_to_coros(start_date),
            date_to_coros(end_date),
        )

        # Parse programs (scheduled workouts)
        programs = []
        for p in data.get("programs", []):
            program = {
                "id": p.get("id"),
                "name": p.get("name"),
                "sport_type": get_sport_name(p.get("sportType", 0)),
                "date": coros_to_date(p.get("happenDay")),
                "planned_distance": p.get("planDistance"),
                "planned_duration": p.get("planDuration"),
                "planned_load": p.get("planTrainingLoad"),
                "actual_distance": p.get("actualDistance"),
                "actual_duration": p.get("actualDuration"),
                "actual_load": p.get("actualTrainingLoad"),
                "status": _workout_status(p),
            }

            # Parse exercises if present
            exercises = p.get("exercises", [])
            if exercises:
                program["exercises"] = _parse_exercises(exercises)

            programs.append(_clean_nones(program))

        # Activities not in the plan
        unplanned = [
            {
                "name": a.get("name"),
                "sport": get_sport_name(a.get("sportType", 0)),
                "date": coros_to_date(a.get("happenDay")),
                "distance_display": format_distance(a.get("distance", 0)),
                "duration_display": format_duration(a.get("duration", 0)),
                "training_load": a.get("trainingLoad"),
                "activity_id": a.get("labelId"),
            }
            for a in data.get("sportDatasNotInPlan", [])
        ]

        # Week stages
        week_stages = [
            {
                "week_start": coros_to_date(ws.get("firstDayInWeek")),
                "stage": ws.get("stage"),
                "total_load": ws.get("trainSum"),
            }
            for ws in data.get("weekStages", [])
        ]

        result = {
            "period": {"start_date": start_date, "end_date": end_date},
            "plan_name": data.get("name"),
            "scheduled_workouts": programs,
            "unplanned_activities": unplanned,
            "week_stages": week_stages,
        }

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

        if not start_date or not end_date:
            today = datetime.now().date()
            four_weeks_ago = today - timedelta(weeks=4)
            start_date = start_date or four_weeks_ago.isoformat()
            end_date = end_date or today.isoformat()

        data = client.get_training_summary(
            date_to_coros(start_date),
            date_to_coros(end_date),
        )

        # Today's summary
        today_sum = data.get("todayTrainingSum", {})
        today_data = {
            "actual_distance": today_sum.get("actualDistance"),
            "planned_distance": today_sum.get("planDistance"),
            "actual_duration": today_sum.get("actualDuration"),
            "planned_duration": today_sum.get("planDuration"),
            "actual_load": today_sum.get("actualTrainingLoad"),
            "planned_load": today_sum.get("planTrainingLoad"),
            "actual_ati": today_sum.get("actualAti"),
            "actual_cti": today_sum.get("actualCti"),
            "tired_rate": today_sum.get("actualTiredRateNew"),
        }

        # Weekly summaries
        weeks = []
        for w in data.get("weekTrains", []):
            ws = w.get("weekTrainSum", {})
            weeks.append(_clean_nones({
                "week_start": coros_to_date(w.get("firstDayInWeek")),
                "actual_distance": ws.get("actualDistance"),
                "planned_distance": ws.get("planDistance"),
                "actual_duration": ws.get("actualDuration"),
                "planned_duration": ws.get("planDuration"),
                "actual_load": ws.get("actualTrainingLoad"),
                "planned_load": ws.get("planTrainingLoad"),
                "actual_load_ratio": ws.get("actualTrainingLoadRatio"),
                "planned_load_ratio": ws.get("planTrainingLoadRatio"),
                "actual_tired_rate": ws.get("actualTiredRateNew"),
                "planned_tired_rate": ws.get("planTiredRateNew"),
            }))

        # Daily summaries
        days = []
        for d in data.get("dayTrainSums", []):
            ds = d.get("dayTrainSum", {})
            days.append(_clean_nones({
                "date": coros_to_date(d.get("happenDay")),
                "actual_distance": ds.get("actualDistance"),
                "planned_distance": ds.get("planDistance"),
                "actual_duration": ds.get("actualDuration"),
                "planned_duration": ds.get("planDuration"),
                "actual_load": ds.get("actualTrainingLoad"),
                "planned_load": ds.get("planTrainingLoad"),
            }))

        result = {
            "period": {"start_date": start_date, "end_date": end_date},
            "today": _clean_nones(today_data),
            "weekly": weeks,
            "daily": days,
        }

        return json.dumps(result, indent=2)

    @app.tool()
    async def delete_scheduled_workout(
        ctx: Context,
        workout_id: str,
        plan_version: int,
        happen_day: int,
    ) -> str:
        """
        Delete a scheduled workout from the training plan.

        Removes a specific workout by sending an empty program update.
        Use get_training_schedule first to find workout IDs and plan version.

        Args:
            workout_id: The workout/program ID from get_training_schedule
            plan_version: Current plan pbVersion (for optimistic concurrency)
            happen_day: The date of the workout as YYYYMMDD integer

        Returns:
            JSON with deletion result
        """
        client = get_client(ctx)

        payload = {
            "pbVersion": plan_version,
            "entities": [],
            "programs": [],
            "versionObjects": [
                {"id": workout_id, "status": 2},  # status 2 = deleted
            ],
        }

        response = client.update_training_schedule(payload)

        if response.get("result") == "0000":
            return json.dumps({
                "success": True,
                "message": f"Workout {workout_id} deleted from plan",
            }, indent=2)
        else:
            return json.dumps({
                "success": False,
                "error": response.get("message", "Unknown error"),
            }, indent=2)

    return app


def _workout_status(program: dict) -> str:
    """Determine workout completion status."""
    actual_load = program.get("actualTrainingLoad", 0)
    planned_load = program.get("planTrainingLoad", 0)
    if actual_load and actual_load > 0:
        if planned_load and planned_load > 0:
            ratio = actual_load / planned_load
            if ratio >= 0.8:
                return "completed"
            return "partial"
        return "completed"
    return "planned"


def _parse_exercises(exercises: list) -> list:
    """Parse exercise list into readable format."""
    result = []
    exercise_types = {0: "repeat", 1: "warmup", 2: "interval", 3: "cooldown", 4: "recovery"}
    target_types = {2: "duration", 5: "distance"}

    for ex in exercises:
        parsed = {
            "type": exercise_types.get(ex.get("exerciseType"), f"type_{ex.get('exerciseType')}"),
            "name": ex.get("name"),
        }

        target_type = ex.get("targetType")
        target_value = ex.get("targetValue")
        if target_type and target_value:
            parsed["target"] = {
                "type": target_types.get(target_type, f"target_{target_type}"),
                "value": target_value,
            }
            if target_type == 2:
                parsed["target"]["display"] = format_duration(target_value)
            elif target_type == 5:
                parsed["target"]["display"] = format_distance(target_value)

        if ex.get("isGroup"):
            parsed["repeats"] = ex.get("sets", 1)
            if ex.get("restValue"):
                parsed["rest_seconds"] = ex.get("restValue")

        result.append(_clean_nones(parsed))

    return result


def _clean_nones(d):
    """Recursively remove None values from a dict."""
    if isinstance(d, dict):
        return {k: _clean_nones(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [_clean_nones(i) for i in d]
    return d
