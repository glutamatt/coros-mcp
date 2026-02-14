"""
Workout operations — build & schedule individual workouts.

Composes exercises.py for translation + SDK for API calls.
Full create flow: get plan info → build exercises → calculate → schedule/update.
"""

from datetime import datetime

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import training as sdk_training
from coros_mcp.sdk import workouts as sdk_workouts
from coros_mcp.sdk.types import SPORT_NAME_TO_CODE, DEFAULT_SOURCE_ID, DEFAULT_SOURCE_URL
from coros_mcp.api.exercises import to_coros
from coros_mcp.utils import date_to_coros, format_duration, format_distance


def create_workout(
    client: CorosClient,
    name: str,
    date: str,
    sport: str,
    exercises: list,
) -> dict:
    """Full flow: plan_info → build exercises → calculate → schedule/update.

    Returns {success, workout_id, name, date, estimated_load, ...}
    """
    sport_code = _resolve_sport(sport)
    coros_date = date_to_coros(date)

    # Get plan info
    plan_info = _get_plan_info(client, coros_date)
    id_in_plan = plan_info["next_id"]

    # Build exercises
    coros_exercises, is_simple = to_coros(exercises, sport)

    # Calculate workout
    calc_program = _build_calculate_program(name, sport_code, is_simple, coros_exercises)
    calc_result = sdk_workouts.calculate_workout(client, calc_program)

    # Build schedule update
    schedule_program = _build_schedule_program(calc_program, calc_result, id_in_plan)

    payload = {
        "pbVersion": plan_info["pb_version"],
        "entities": [{
            "happenDay": str(coros_date),
            "idInPlan": id_in_plan,
            "sortNo": 0,
            "dayNo": 0,
            "sortNoInPlan": 0,
            "sortNoInSchedule": 0,
            "exerciseBarChart": calc_result.get("exerciseBarChart", []),
        }],
        "programs": [schedule_program],
        "versionObjects": [{"id": id_in_plan, "status": 1}],
    }

    response = sdk_training.update_training_schedule(client, payload)

    if response.get("result") == "0000":
        return {
            "success": True,
            "workout_id": str(id_in_plan),
            "name": name,
            "date": date,
            "sport": sport,
            "estimated_distance": format_distance(_parse_distance(calc_result.get("planDistance", 0))),
            "estimated_duration": format_duration(calc_result.get("planDuration", 0)),
            "estimated_load": calc_result.get("planTrainingLoad"),
        }
    else:
        return {
            "success": False,
            "error": response.get("message", "Unknown error"),
        }


def estimate_workout(
    client: CorosClient,
    sport: str,
    exercises: list,
    date: str = None,
) -> dict:
    """Preview only. Returns {distance, duration, load}."""
    sport_code = _resolve_sport(sport)
    if not date:
        date = datetime.now().date().isoformat()
    coros_date = date_to_coros(date)

    plan_info = _get_plan_info(client, coros_date)
    id_in_plan = plan_info["next_id"]

    coros_exercises, is_simple = to_coros(exercises, sport)

    program = _build_estimate_program(id_in_plan, "Preview", sport_code, is_simple, coros_exercises)
    payload = {
        "entity": {
            "happenDay": str(coros_date),
            "idInPlan": id_in_plan,
            "sortNo": 0, "dayNo": 0, "sortNoInPlan": 0, "sortNoInSchedule": 0,
        },
        "program": program,
    }

    result = sdk_workouts.estimate_workout(client, payload)

    return {
        "estimated_distance": format_distance(_parse_distance(result.get("distance", 0))),
        "estimated_duration": format_duration(result.get("duration", 0)),
        "estimated_load": result.get("trainingLoad"),
    }


def reschedule_workout(
    client: CorosClient,
    workout_id: str,
    new_date: str,
) -> dict:
    """Move workout to new date."""
    new_coros_date = date_to_coros(new_date)

    # Fetch schedule covering the workout
    today = datetime.now().date()
    end_dt = max(today, datetime.strptime(new_date, "%Y-%m-%d").date())
    from datetime import timedelta
    start = date_to_coros((today - timedelta(days=7)).isoformat())
    end = date_to_coros((end_dt + timedelta(days=7)).isoformat())

    schedule = sdk_training.get_training_schedule(client, start, end)

    # Find entity and program
    target_entity = None
    for e in schedule.get("entities", []):
        if str(e.get("idInPlan")) == str(workout_id):
            target_entity = e
            break

    target_program = None
    for p in schedule.get("programs", []):
        if str(p.get("idInPlan")) == str(workout_id):
            target_program = p
            break

    if not target_entity or not target_program:
        return {"success": False, "error": f"Workout {workout_id} not found in schedule"}

    plan_id = target_entity.get("planId", "")
    target_entity["happenDay"] = new_coros_date

    payload = {
        "pbVersion": schedule.get("pbVersion", 0),
        "entities": [target_entity],
        "programs": [target_program],
        "versionObjects": [{
            "type": 0,
            "id": workout_id,
            "planProgramId": workout_id,
            "planId": plan_id,
            "status": 2,
        }],
    }

    sdk_training.update_training_schedule(client, payload)
    return {
        "success": True,
        "message": f"Workout '{target_program.get('name', workout_id)}' moved to {new_date}",
    }


def delete_workout(
    client: CorosClient,
    workout_id: str,
    date: str,
) -> dict:
    """Remove workout from calendar."""
    coros_date = date_to_coros(date)
    schedule = sdk_training.get_training_schedule(client, coros_date, coros_date)
    pb_version = schedule.get("pbVersion")

    if pb_version is None:
        return {"success": False, "error": "No active training plan found"}

    # Find plan_id from entities
    plan_id = None
    workout_name = workout_id
    for e in schedule.get("entities", []):
        if e.get("idInPlan") == workout_id:
            plan_id = e.get("planId")
            break

    if plan_id is None:
        return {"success": False, "error": f"Workout {workout_id} not found on {date}"}

    for p in schedule.get("programs", []):
        if p.get("idInPlan") == workout_id:
            workout_name = p.get("name", workout_id)
            break

    payload = {
        "pbVersion": pb_version,
        "entities": [],
        "programs": [],
        "versionObjects": [{
            "id": workout_id,
            "planProgramId": workout_id,
            "planId": plan_id,
            "status": 3,
        }],
    }

    sdk_training.update_training_schedule(client, payload)
    return {"success": True, "message": f"Workout '{workout_name}' deleted"}


# ── Internal helpers ────────────────────────────────────────────────────


def _resolve_sport(sport: str) -> int:
    code = SPORT_NAME_TO_CODE.get(sport.lower())
    if code is None:
        raise ValueError(
            f"Unknown sport '{sport}'. Use: {', '.join(sorted(SPORT_NAME_TO_CODE.keys()))}"
        )
    return int(code)


def _parse_distance(value) -> float:
    """Parse distance from calculate/estimate response.

    The API returns distance in centimeters (e.g. "180000.00" = 1800 m).
    Divides by 100 to return meters.
    """
    try:
        return float(value) / 100
    except (TypeError, ValueError):
        return 0.0


def _get_plan_info(client: CorosClient, coros_date: int) -> dict:
    """Fetch plan metadata: planId, pbVersion, next idInPlan."""
    try:
        schedule = sdk_training.get_training_schedule(client, coros_date, coros_date)
        return {
            "plan_id": schedule.get("id", ""),
            "pb_version": schedule.get("pbVersion", 0),
            "next_id": int(schedule.get("maxIdInPlan", "0")) + 1,
        }
    except Exception:
        return {"plan_id": "", "pb_version": 0, "next_id": 1}


def _build_estimate_program(
    id_in_plan: int, name: str, sport_code: int,
    is_simple: bool, exercises: list,
) -> dict:
    """Build lean estimate program (HAR pattern)."""
    step_count = sum(1 for e in exercises if not e.get("isGroup"))
    return {
        "idInPlan": id_in_plan,
        "name": name,
        "sportType": sport_code,
        "subType": 0 if is_simple else 65535,
        "totalSets": step_count if is_simple else 0,
        "sets": step_count if is_simple else 0,
        "exerciseNum": "",
        "targetType": "",
        "targetValue": "",
        "version": 0,
        "simple": is_simple,
        "exercises": exercises,
        "access": 1,
        "essence": 0,
        "estimatedTime": 0,
        "originEssence": 0,
        "overview": "",
        "type": 0,
        "unit": 0,
        "pbVersion": 2,
        "sourceId": DEFAULT_SOURCE_ID,
        "sourceUrl": DEFAULT_SOURCE_URL,
        "referExercise": {"intensityType": 0, "hrType": 0, "valueType": 0},
        "poolLengthId": 1,
        "poolLength": 2500,
        "poolLengthUnit": 2,
    }


def _build_calculate_program(
    name: str, sport_code: int, is_simple: bool, exercises: list,
) -> dict:
    """Build calculate program (HAR pattern, zeroed identity for new workouts)."""
    return {
        "access": 1,
        "authorId": "0",
        "createTimestamp": 0,
        "distance": 0,
        "duration": 0,
        "essence": 0,
        "estimatedType": 0,
        "estimatedValue": 0,
        "exerciseNum": 0,
        "exercises": exercises,
        "headPic": "",
        "id": "0",
        "idInPlan": "0",
        "name": name,
        "nickname": "",
        "originEssence": 0,
        "overview": "",
        "pbVersion": 2,
        "planIdIndex": 0,
        "poolLength": 2500,
        "profile": "",
        "referExercise": {"intensityType": 0, "hrType": 0, "valueType": 0},
        "sex": 0,
        "shareUrl": "",
        "simple": is_simple,
        "sourceUrl": DEFAULT_SOURCE_URL,
        "sportType": sport_code,
        "star": 0,
        "subType": 0 if is_simple else 65535,
        "targetType": 0,
        "targetValue": 0,
        "thirdPartyId": 0,
        "totalSets": 0,
        "trainingLoad": 0,
        "type": 0,
        "unit": 0,
        "userId": "0",
        "version": 0,
        "videoCoverUrl": "",
        "videoUrl": "",
        "fastIntensityTypeName": "",
        "poolLengthId": 1,
        "poolLengthUnit": 2,
        "sourceId": DEFAULT_SOURCE_ID,
    }


def _build_schedule_program(
    calc_program: dict, calc_result: dict, id_in_plan: int,
) -> dict:
    """Enrich a calculate program with results for schedule/update."""
    program = {**calc_program}
    program["idInPlan"] = id_in_plan
    try:
        plan_distance = float(calc_result.get("planDistance", 0))
    except (TypeError, ValueError):
        plan_distance = 0.0
    program["distance"] = f"{plan_distance:.2f}"
    program["duration"] = calc_result.get("planDuration", 0)
    program["trainingLoad"] = calc_result.get("planTrainingLoad", 0)
    program["pitch"] = calc_result.get("planPitch", 0)
    program["exerciseBarChart"] = calc_result.get("exerciseBarChart", [])
    program["distanceDisplayUnit"] = 1  # 1 = km
    return program
