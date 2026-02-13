"""
Plan operations — build & activate multi-week plans.

A plan is a template of workouts at relative day offsets.
Once activated (executed), it's copied into the calendar.
"""

import math

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import plans as sdk_plans
from coros_mcp.sdk import workouts as sdk_workouts
from coros_mcp.sdk.types import DEFAULT_SOURCE_ID, DEFAULT_SOURCE_URL
from coros_mcp.api.exercises import to_coros, from_coros
from coros_mcp.utils import coros_to_date, format_duration, format_distance, get_sport_name


def list_plans(client: CorosClient, status: str = "draft") -> list[dict]:
    """List plans. status: 'draft' or 'active'."""
    status_list = [0] if status == "draft" else [1]
    raw_plans = sdk_plans.query_plans(client, status_list=status_list)

    if not isinstance(raw_plans, list):
        return []

    return [
        {
            "id": p.get("id"),
            "name": p.get("overview") or p.get("name"),
            "status": "active" if p.get("status") == 1 else "draft",
            "total_days": p.get("totalDay"),
            "weeks": p.get("maxWeeks", 1),
            "workout_count": len(p.get("entities", [])),
            "created": p.get("createTime"),
        }
        for p in raw_plans
    ]


def get_plan(client: CorosClient, plan_id: str) -> dict:
    """Full plan detail with formatted workouts."""
    data = sdk_plans.get_plan_detail(client, plan_id)

    # Entity lookup
    entity_by_id = {}
    for e in data.get("entities", []):
        entity_by_id[e.get("idInPlan")] = e

    workouts = []
    for p in data.get("programs", []):
        id_in_plan = p.get("idInPlan")
        entity = entity_by_id.get(id_in_plan, {})

        workout = {
            "id": id_in_plan,
            "name": p.get("name"),
            "sport": get_sport_name(p.get("sportType", 0)),
            "day": entity.get("dayNo", 0),
            "distance": format_distance(p.get("distance", 0)),
            "duration": format_duration(p.get("duration", 0)),
            "training_load": p.get("trainingLoad"),
        }

        # Format date if present (active plans have happenDay)
        happen_day = entity.get("happenDay")
        if happen_day:
            workout["date"] = coros_to_date(happen_day)

        exercises = p.get("exercises", [])
        if exercises:
            workout["exercises"] = from_coros(exercises)

        workouts.append(workout)

    return {
        "id": data.get("id"),
        "name": data.get("overview") or data.get("name"),
        "total_days": data.get("totalDay"),
        "weeks": data.get("maxWeeks", 1),
        "workouts": workouts,
    }


def create_plan(
    client: CorosClient,
    name: str,
    overview: str,
    workouts: list[dict],
) -> dict:
    """Create plan. workouts: [{day, name, sport, exercises}].

    Handles calculate for each workout + plan/add.
    """
    entities = []
    programs = []
    version_objects = []
    max_day = 0

    for i, w in enumerate(workouts):
        id_in_plan = i + 1
        day = w.get("day", 0)
        max_day = max(max_day, day)
        sport = w.get("sport", "running")
        w_name = w.get("name", f"Workout {id_in_plan}")
        w_exercises = w.get("exercises", [])

        # Build COROS exercises
        coros_exercises, is_simple = to_coros(w_exercises, sport)

        # Calculate workout
        calc_program = _build_calc_program(w_name, sport, is_simple, coros_exercises)
        calc_result = sdk_workouts.calculate_workout(client, calc_program)

        # Build entity (relative day, no happenDay for templates)
        entities.append({
            "happenDay": "",
            "idInPlan": id_in_plan,
            "sortNo": 0,
            "dayNo": day,
            "sortNoInPlan": 0,
            "sortNoInSchedule": 0,
        })

        # Build program with calculate results
        program = {**calc_program}
        program["idInPlan"] = id_in_plan
        try:
            plan_distance = float(calc_result.get("planDistance", 0))
        except (TypeError, ValueError):
            plan_distance = 0.0
        program["distance"] = f"{plan_distance / 1000:.2f}"
        program["duration"] = calc_result.get("planDuration", 0)
        program["trainingLoad"] = calc_result.get("planTrainingLoad", 0)
        program["pitch"] = calc_result.get("planPitch", 0)
        program["exerciseBarChart"] = calc_result.get("exerciseBarChart", [])
        program["distanceDisplayUnit"] = 1
        programs.append(program)

        version_objects.append({"id": id_in_plan, "status": 1})

    total_day = max_day + 1
    weeks = math.ceil(total_day / 7)

    payload = {
        "name": "N1117",  # COROS internal name
        "overview": overview or name,
        "entities": entities,
        "programs": programs,
        "weekStages": [],
        "maxIdInPlan": len(workouts),
        "totalDay": total_day,
        "unit": 0,
        "sourceId": DEFAULT_SOURCE_ID,
        "sourceUrl": DEFAULT_SOURCE_URL,
        "minWeeks": weeks,
        "maxWeeks": weeks,
        "region": 3,  # EU
        "pbVersion": 2,
        "versionObjects": version_objects,
    }

    plan_id = sdk_plans.add_plan(client, payload)

    return {
        "success": True,
        "plan_id": plan_id,
        "name": overview or name,
        "total_days": total_day,
        "weeks": weeks,
        "workout_count": len(workouts),
    }


def add_workout_to_plan(
    client: CorosClient,
    plan_id: str,
    day: int,
    name: str,
    sport: str,
    exercises: list,
) -> dict:
    """Add workout at day offset to existing plan."""
    # Get current plan
    plan = sdk_plans.get_plan_detail(client, plan_id)

    # Build new workout
    coros_exercises, is_simple = to_coros(exercises, sport)
    calc_program = _build_calc_program(name, sport, is_simple, coros_exercises)
    calc_result = sdk_workouts.calculate_workout(client, calc_program)

    # Determine next idInPlan
    max_id = int(plan.get("maxIdInPlan", "0"))
    new_id = max_id + 1

    # Add new entity
    new_entity = {
        "happenDay": "",
        "idInPlan": new_id,
        "sortNo": 0,
        "dayNo": day,
        "sortNoInPlan": 0,
        "sortNoInSchedule": 0,
    }

    # Build new program
    program = {**calc_program}
    program["idInPlan"] = new_id
    try:
        plan_distance = float(calc_result.get("planDistance", 0))
    except (TypeError, ValueError):
        plan_distance = 0.0
    program["distance"] = f"{plan_distance / 1000:.2f}"
    program["duration"] = calc_result.get("planDuration", 0)
    program["trainingLoad"] = calc_result.get("planTrainingLoad", 0)
    program["pitch"] = calc_result.get("planPitch", 0)
    program["exerciseBarChart"] = calc_result.get("exerciseBarChart", [])
    program["distanceDisplayUnit"] = 1

    # Update plan: full entity/program lists + versionObjects for the new one
    all_entities = plan.get("entities", []) + [new_entity]
    all_programs = plan.get("programs", []) + [program]

    # Recalculate total days
    max_day = max(e.get("dayNo", 0) for e in all_entities)
    total_day = max_day + 1
    weeks = math.ceil(total_day / 7)

    update_payload = {
        **plan,
        "entities": all_entities,
        "programs": all_programs,
        "maxIdInPlan": str(new_id),
        "totalDay": total_day,
        "maxWeeks": weeks,
        "minWeeks": weeks,
        "versionObjects": [{"id": new_id, "status": 1, "type": 0}],
    }

    sdk_plans.update_plan(client, update_payload)

    return {
        "success": True,
        "plan_id": plan_id,
        "workout_id": str(new_id),
        "name": name,
        "day": day,
    }


def activate_plan(
    client: CorosClient,
    plan_id: str,
    start_date: str,
) -> dict:
    """Apply plan template to calendar."""
    from coros_mcp.utils import date_to_coros
    coros_date = date_to_coros(start_date)

    sdk_plans.execute_sub_plan(client, plan_id, coros_date)

    return {
        "success": True,
        "plan_id": plan_id,
        "start_date": start_date,
        "message": f"Plan activated starting {start_date}. Workouts will appear in the calendar.",
    }


def delete_plans(client: CorosClient, plan_ids: list[str]) -> dict:
    """Delete template plans."""
    sdk_plans.delete_plans(client, plan_ids)
    return {
        "success": True,
        "deleted": plan_ids,
    }


# ── Internal helpers ────────────────────────────────────────────────────


def _build_calc_program(
    name: str, sport: str, is_simple: bool, exercises: list,
) -> dict:
    """Build calculate program for plan workouts."""
    from coros_mcp.sdk.types import SPORT_NAME_TO_CODE
    sport_code = int(SPORT_NAME_TO_CODE.get(sport.lower(), 1))

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
