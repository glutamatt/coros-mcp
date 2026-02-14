"""
Calendar — what's coming up?

Scheduled workouts, races (eventTags), and adherence tracking.
"""

from datetime import datetime, timedelta

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import training as sdk_training
from coros_mcp.api.exercises import from_coros
from coros_mcp.utils import date_to_coros, coros_to_date, format_duration, format_distance, get_sport_name


def get_calendar(
    client: CorosClient,
    start_date: str = None,
    end_date: str = None,
) -> dict:
    """Upcoming workouts for date range.

    Links entities to programs, formats exercises.
    Also surfaces competitions and eventTags (races) when present.
    """
    if not start_date or not end_date:
        today = datetime.now().date()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        start_date = start_date or monday.isoformat()
        end_date = end_date or sunday.isoformat()

    data = sdk_training.get_training_schedule(
        client, date_to_coros(start_date), date_to_coros(end_date),
    )

    # Entity lookup: idInPlan → entity
    entity_by_id = {}
    for e in data.get("entities", []):
        entity_by_id[e.get("idInPlan")] = e

    # Scheduled workouts
    workouts = []
    for p in data.get("programs", []):
        id_in_plan = p.get("idInPlan")
        entity = entity_by_id.get(id_in_plan, {})

        workout = _clean_nones({
            "id": id_in_plan,
            "name": p.get("name"),
            "sport": get_sport_name(p.get("sportType", 0)),
            "date": coros_to_date(entity.get("happenDay")),
            "planned_distance": format_distance(p.get("planDistance", 0)),
            "planned_duration": format_duration(p.get("planDuration", 0)),
            "planned_load": p.get("planTrainingLoad"),
            "actual_distance": format_distance(p.get("actualDistance", 0)) if p.get("actualDistance") else None,
            "actual_duration": format_duration(p.get("actualDuration", 0)) if p.get("actualDuration") else None,
            "actual_load": p.get("actualTrainingLoad") or None,
            "status": _workout_status(p),
        })

        # Exercises
        exercises = p.get("exercises", [])
        if exercises:
            workout["exercises"] = from_coros(exercises)

        workouts.append(workout)

    # Unplanned activities
    unplanned = [
        _clean_nones({
            "name": a.get("name"),
            "sport": get_sport_name(a.get("sportType", 0)),
            "date": coros_to_date(a.get("happenDay")),
            "distance": format_distance(a.get("distance", 0)),
            "duration": format_duration(a.get("duration", 0)),
            "training_load": a.get("trainingLoad"),
            "activity_id": a.get("labelId"),
        })
        for a in data.get("sportDatasNotInPlan", [])
    ]

    # Week stages
    week_stages = [
        {"week_start": coros_to_date(ws.get("firstDayInWeek")), "stage": ws.get("stage")}
        for ws in data.get("weekStages", [])
    ]

    result = {
        "period": {"start_date": start_date, "end_date": end_date},
        "plan_name": data.get("name"),
        "scheduled_workouts": workouts,
        "unplanned_activities": unplanned,
        "week_stages": week_stages,
    }

    # Event tags (races, competitions)
    event_tags = data.get("eventTags", [])
    if event_tags:
        result["events"] = [
            _clean_nones({
                "name": et.get("name"),
                "type": "competition" if et.get("type") == 2 else "event",
                "date": coros_to_date(et.get("happenDay")),
            })
            for et in event_tags
        ]

    return result


def get_adherence(
    client: CorosClient,
    start_date: str = None,
    end_date: str = None,
) -> dict:
    """Planned vs actual: daily + weekly comparison."""
    if not start_date or not end_date:
        today = datetime.now().date()
        four_weeks_ago = today - timedelta(weeks=4)
        start_date = start_date or four_weeks_ago.isoformat()
        end_date = end_date or today.isoformat()

    data = sdk_training.get_training_summary(
        client, date_to_coros(start_date), date_to_coros(end_date),
    )

    # Today's summary
    today_sum = data.get("todayTrainingSum", {})
    today_data = _clean_nones({
        "actual_distance": format_distance(today_sum.get("actualDistance", 0)),
        "planned_distance": format_distance(today_sum.get("planDistance", 0)),
        "actual_duration": format_duration(today_sum.get("actualDuration", 0)),
        "planned_duration": format_duration(today_sum.get("planDuration", 0)),
        "actual_load": today_sum.get("actualTrainingLoad"),
        "planned_load": today_sum.get("planTrainingLoad"),
    })

    # Weekly summaries
    weeks = []
    for w in data.get("weekTrains", []):
        ws = w.get("weekTrainSum", {})
        weeks.append(_clean_nones({
            "week_start": coros_to_date(w.get("firstDayInWeek")),
            "actual_distance": format_distance(ws.get("actualDistance", 0)),
            "planned_distance": format_distance(ws.get("planDistance", 0)),
            "actual_duration": format_duration(ws.get("actualDuration", 0)),
            "planned_duration": format_duration(ws.get("planDuration", 0)),
            "actual_load": ws.get("actualTrainingLoad"),
            "planned_load": ws.get("planTrainingLoad"),
        }))

    # Daily summaries
    days = []
    for d in data.get("dayTrainSums", []):
        ds = d.get("dayTrainSum", {})
        days.append(_clean_nones({
            "date": coros_to_date(d.get("happenDay")),
            "actual_distance": format_distance(ds.get("actualDistance", 0)),
            "planned_distance": format_distance(ds.get("planDistance", 0)),
            "actual_load": ds.get("actualTrainingLoad"),
            "planned_load": ds.get("planTrainingLoad"),
        }))

    return {
        "period": {"start_date": start_date, "end_date": end_date},
        "today": today_data,
        "weekly": weeks,
        "daily": days,
    }


def _workout_status(program: dict) -> str:
    """Determine workout completion status."""
    actual_load = program.get("actualTrainingLoad", 0)
    planned_load = program.get("planTrainingLoad", 0)
    if actual_load and actual_load > 0:
        if planned_load and planned_load > 0:
            ratio = actual_load / planned_load
            return "completed" if ratio >= 0.8 else "partial"
        return "completed"
    return "planned"


def _clean_nones(d):
    """Recursively remove None values from a dict."""
    if isinstance(d, dict):
        return {k: _clean_nones(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [_clean_nones(i) for i in d]
    return d
