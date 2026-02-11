"""
Workout builder tools for COROS MCP server.

Create structured workouts, estimate load, and reschedule.
Payload structures reverse-engineered from COROS Training Hub web app HAR captures.
"""

import json
import logging
from datetime import datetime, timedelta

from fastmcp import Context

from coros_mcp.client_factory import get_client
from coros_mcp.utils import date_to_coros, format_duration, format_distance

logger = logging.getLogger(__name__)

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

# Default COROS exercise template metadata (running)
_EXERCISE_TEMPLATES = {
    1: {"name": "T1120", "overview": "sid_run_warm_up_dist",
        "originId": "425895398452936705", "createTimestamp": 1586584068, "defaultOrder": 1},
    2: {"name": "T3001", "overview": "sid_run_training",
        "originId": "426109589008859136", "createTimestamp": 1587381919, "defaultOrder": 2, "isDefaultAdd": 1},
    3: {"name": "T1122", "overview": "sid_run_cool_down_dist",
        "originId": "425895456971866112", "createTimestamp": 1586584214, "defaultOrder": 3},
    4: {"name": "T1123", "overview": "sid_run_cool_down_dist",
        "originId": "425895398452936705", "createTimestamp": 1586584214, "defaultOrder": 3},
}

# Default source IDs (from COROS exercise library)
_SOURCE_ID = "425868113867882496"
_SOURCE_URL = "https://d31oxp44ddzkyk.cloudfront.net/source/source_default/0/5a9db1c3363348298351aaabfd70d0f5.jpg"


def _get_plan_info(client, coros_date: int) -> dict:
    """Fetch plan metadata: planId, pbVersion, next idInPlan."""
    try:
        schedule = client.get_training_schedule(coros_date, coros_date)
        plan_id = schedule.get("id", "")
        pb_version = schedule.get("pbVersion", 0)
        max_id = int(schedule.get("maxIdInPlan", "0"))
        return {
            "plan_id": plan_id,
            "pb_version": pb_version,
            "next_id": max_id + 1,
        }
    except Exception:
        return {"plan_id": "", "pb_version": 0, "next_id": 1}


def _build_estimate_program(id_in_plan: int, name: str, sport_code: int,
                            is_simple: bool, exercises: list) -> dict:
    """Build lean estimate program matching COROS web app HAR.

    The estimate payload is intentionally minimal — only fields the web app sends.
    NO planId, userId, authorId, nickname, distance, duration, etc.
    """
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
        "sourceId": _SOURCE_ID,
        "sourceUrl": _SOURCE_URL,
        "referExercise": {"intensityType": 0, "hrType": 0, "valueType": 0},
        "poolLengthId": 1,
        "poolLength": 2500,
        "poolLengthUnit": 2,
    }


def _build_calculate_program(name: str, sport_code: int, is_simple: bool,
                             exercises: list, overview: str = "") -> dict:
    """Build calculate program matching COROS web app HAR.

    The calculate payload has more fields than estimate, but with zeroed/empty
    identity fields (id="0", userId="0", authorId="0", idInPlan="0").
    """
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
        "overview": overview,
        "pbVersion": 2,
        "planIdIndex": 0,
        "poolLength": 2500,
        "profile": "",
        "referExercise": {"intensityType": 0, "hrType": 0, "valueType": 0},
        "sex": 0,
        "shareUrl": "",
        "simple": is_simple,
        "sourceUrl": _SOURCE_URL,
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
        "sourceId": _SOURCE_ID,
    }


def _build_schedule_program(calc_program: dict, calc_result: dict,
                            id_in_plan: int) -> dict:
    """Enrich a calculate program with results for schedule/update."""
    program = {**calc_program}
    program["idInPlan"] = id_in_plan
    # Enrich with calculate results (distance becomes string with 2 decimals)
    try:
        plan_distance = float(calc_result.get("planDistance", 0))
    except (TypeError, ValueError):
        plan_distance = 0.0
    program["distance"] = f"{plan_distance:.2f}"
    program["duration"] = calc_result.get("planDuration", 0)
    program["trainingLoad"] = calc_result.get("planTrainingLoad", 0)
    program["pitch"] = calc_result.get("planPitch", 0)
    program["exerciseBarChart"] = calc_result.get("exerciseBarChart", [])
    program["distanceDisplayUnit"] = 1
    return program


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
                Example: [
                    {"type": "warmup", "duration_minutes": 15},
                    {"type": "interval", "distance_m": 800, "repeats": 6, "rest_seconds": 90},
                    {"type": "cooldown", "duration_minutes": 10}
                ]

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

        # Get plan info (planId, pbVersion, next sequential idInPlan)
        plan_info = _get_plan_info(client, coros_date)
        plan_id = plan_info["plan_id"]
        pb_version = plan_info["pb_version"]
        id_in_plan = plan_info["next_id"]

        # Build exercise model
        coros_exercises, is_simple = _build_exercises(exercises, sport_code)

        # Calculate workout (zeroed identity — HAR pattern for new workouts)
        calc_program = _build_calculate_program(
            name, sport_code, is_simple, coros_exercises,
        )
        try:
            calc_result = client.calculate_workout(calc_program)
        except Exception as e:
            return json.dumps({
                "error": f"Workout calculation failed: {str(e)}",
                "hint": "Check exercise definitions. Duration should be in minutes, distance in km or m.",
            }, indent=2)

        # Build schedule update with real identity
        schedule_program = _build_schedule_program(calc_program, calc_result, id_in_plan)

        schedule_payload = {
            "pbVersion": pb_version,
            "entities": [
                {
                    "happenDay": str(coros_date),
                    "idInPlan": id_in_plan,
                    "sortNo": 0,
                    "dayNo": 0,
                    "sortNoInPlan": 0,
                    "sortNoInSchedule": 0,
                    "exerciseBarChart": calc_result.get("exerciseBarChart", []),
                }
            ],
            "programs": [schedule_program],
            "versionObjects": [
                {
                    "id": id_in_plan,
                    "status": 1,  # status 1 = new
                },
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
                "workout_id": str(id_in_plan),
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

        # Get plan info for next idInPlan
        plan_info = _get_plan_info(client, coros_date)
        id_in_plan = plan_info["next_id"]

        coros_exercises, is_simple = _build_exercises(exercises, sport_code)

        # Build lean estimate payload (no planId, no userId — HAR pattern)
        program = _build_estimate_program(
            id_in_plan, "Preview", sport_code, is_simple, coros_exercises,
        )

        payload = {
            "entity": {
                "happenDay": str(coros_date),
                "idInPlan": id_in_plan,
                "sortNo": 0,
                "dayNo": 0,
                "sortNoInPlan": 0,
                "sortNoInSchedule": 0,
                # NO planId — HAR doesn't include it for new workouts
            },
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

        new_coros_date = date_to_coros(new_date)

        # Fetch current schedule — use proper date math
        today = datetime.now().date()
        end_date = max(today, datetime.strptime(new_date, "%Y-%m-%d").date()) + timedelta(days=7)
        # Search starts 7 days before today to catch workouts in the recent past
        start_date = today - timedelta(days=7)
        start = date_to_coros(start_date.isoformat())
        end = date_to_coros(end_date.isoformat())
        try:
            schedule = client.get_training_schedule(start, end)
        except Exception as e:
            logger.error("Reschedule: get_training_schedule failed: %s", e)
            schedule = {"programs": []}

        # Find entity and program by idInPlan (compare as strings — API returns mixed types)
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
            entity_ids = [str(e.get("idInPlan")) for e in schedule.get("entities", [])]
            program_ids = [str(p.get("idInPlan")) for p in schedule.get("programs", [])]
            logger.warning(
                "Workout %s not found. Entity idInPlans: %s, Program idInPlans: %s",
                workout_id, entity_ids, program_ids,
            )
            return json.dumps({
                "error": f"Workout {workout_id} not found in current plan",
            }, indent=2)

        pb_version = schedule.get("pbVersion", 0)
        plan_id = target_entity.get("planId", "")

        # Update entity date for the move
        target_entity["happenDay"] = new_coros_date

        payload = {
            "pbVersion": pb_version,
            "entities": [target_entity],
            "programs": [target_program],
            "versionObjects": [
                {
                    "type": 0,
                    "id": workout_id,
                    "planProgramId": workout_id,
                    "planId": plan_id,
                    "status": 2,  # status 2 = move/update
                },
            ],
        }

        try:
            client.update_training_schedule(payload)
            return json.dumps({
                "success": True,
                "message": f"Workout '{target_program.get('name', workout_id)}' moved to {new_date}",
            }, indent=2)
        except ValueError as e:
            return json.dumps({
                "error": f"Reschedule failed: {str(e)}",
            }, indent=2)

    return app


def _build_exercises(exercises: list[dict], sport_type: int = 1) -> tuple[list[dict], bool]:
    """
    Convert AI-friendly exercise definitions to COROS exercise model.

    COROS conventions (from HAR analysis of new workout creation):
    - exercise_id: sequential across ALL exercises (including groups)
    - sort_no: sequential, shared between group and its first child
    - groupId references the group exercise's `id`
    - Groups have sequential sortNo (NOT id << 24, which is server-side encoding)

    Returns (coros_exercises, is_simple).
    """
    if len(exercises) == 1 and exercises[0].get("type") not in ("interval", "work"):
        # Single non-interval exercise = simple workout
        return [_build_single_exercise(exercises[0], exercise_id=1, sort_no=1, sport_type=sport_type)], True

    coros_exercises = []
    exercise_id = 1  # Sequential across ALL exercises (including groups)
    sort_no = 1      # Sequential, groups share sortNo with their first child

    for ex in exercises:
        repeats = ex.get("repeats")

        if repeats and repeats > 1:
            # Create repeat group — sortNo = current sort_no (shared with first child)
            group_exercise_id = exercise_id
            group = _group_defaults(exercise_id, sort_no)
            group.update({
                "sets": repeats,
                "restType": 0 if ex.get("rest_seconds") else 3,
                "restValue": ex.get("rest_seconds", 0),
            })
            coros_exercises.append(group)
            exercise_id += 1

            # Work step inside group — shares sortNo with group
            work_step = _build_single_exercise(
                ex, exercise_id=exercise_id, sort_no=sort_no,
                exercise_type=2, sport_type=sport_type,
            )
            work_step["groupId"] = group_exercise_id
            coros_exercises.append(work_step)
            exercise_id += 1
            sort_no += 1

            # Recovery step inside group (if rest specified)
            if ex.get("rest_seconds"):
                recovery = _step_defaults(exercise_id, sort_no, 4, sport_type)
                recovery.update({
                    "groupId": group_exercise_id,
                    "targetType": 2,  # Duration
                    "targetValue": ex["rest_seconds"],
                })
                coros_exercises.append(recovery)
                exercise_id += 1
                sort_no += 1
        else:
            coros_exercises.append(
                _build_single_exercise(ex, exercise_id=exercise_id, sort_no=sort_no, sport_type=sport_type)
            )
            exercise_id += 1
            sort_no += 1

    return coros_exercises, False


def _group_defaults(exercise_id: int, sort_no: int) -> dict:
    """Base exercise object for a repeat group (matches HAR group field set).

    Groups have NO: hrType, userId, isIntensityPercent, targetDisplayUnit,
    groupId, equipment, part, createTimestamp, intensityDisplayUnit, intensityPercent*.
    Groups have: programId, targetType="" (empty string).
    """
    return {
        "access": 0,
        "defaultOrder": 0,
        "exerciseType": 0,
        "id": exercise_id,
        "intensityCustom": 0,
        "intensityMultiplier": 0,
        "intensityType": 0,
        "intensityValue": 0,
        "intensityValueExtend": 0,
        "isDefaultAdd": 0,
        "isGroup": True,
        "name": "",
        "originId": "",
        "overview": "",
        "programId": "",
        "restType": 0,
        "restValue": 0,
        "sets": 1,
        "sortNo": sort_no,
        "sourceId": "0",
        "sourceUrl": "",
        "sportType": 0,
        "subType": 0,
        "targetType": "",  # Empty string for groups (HAR pattern)
        "targetValue": 0,
        "videoUrl": "",
    }


def _step_defaults(exercise_id: int, sort_no: int, exercise_type: int, sport_type: int = 1) -> dict:
    """Base exercise object for a non-group step (matches HAR step field set).

    Key HAR observations:
    - intensityDisplayUnit is INTEGER 0, not string
    - intensityMultiplier is 0 (not 1000, which is pace-specific)
    - Template metadata (name, originId, overview, createTimestamp, defaultOrder) from COROS library
    """
    tmpl = _EXERCISE_TEMPLATES.get(exercise_type, {})
    return {
        "access": 0,
        "createTimestamp": tmpl.get("createTimestamp", 0),
        "defaultOrder": tmpl.get("defaultOrder", 0),
        "equipment": [1],
        "exerciseType": exercise_type,
        "groupId": "",
        "hrType": 0,
        "id": exercise_id,
        "intensityCustom": 0,
        "intensityDisplayUnit": 0,  # INTEGER 0 (not string "1")
        "intensityMultiplier": 0,   # 0 for no intensity (1000 = pace-specific)
        "intensityPercent": 0,
        "intensityPercentExtend": 0,
        "intensityType": 0,
        "intensityValue": 0,
        "intensityValueExtend": 0,
        "isDefaultAdd": tmpl.get("isDefaultAdd", 0),
        "isGroup": False,
        "isIntensityPercent": False,
        "name": tmpl.get("name", ""),
        "originId": tmpl.get("originId", ""),
        "overview": tmpl.get("overview", ""),
        "part": [0],
        "restType": 3,
        "restValue": 0,
        "sets": 1,
        "sortNo": sort_no,
        "sourceId": "0",
        "sourceUrl": "",
        "sportType": sport_type,
        "subType": 0,
        "targetDisplayUnit": 0,
        "targetType": 0,
        "targetValue": 0,
        "userId": 0,
        "videoUrl": "",
    }


def _build_single_exercise(
    ex: dict, exercise_id: int, sort_no: int,
    exercise_type: int = None, sport_type: int = 1,
) -> dict:
    """Build a single COROS exercise from an AI-friendly definition."""
    ex_type = exercise_type or EXERCISE_TYPES.get(ex.get("type", "interval"), 2)

    result = _step_defaults(exercise_id, sort_no, ex_type, sport_type)

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


def _compute_target_value(ex: dict) -> int:
    """Compute the target value for an exercise definition (seconds or meters)."""
    if ex.get("duration_minutes"):
        return int(ex["duration_minutes"] * 60)
    elif ex.get("distance_km"):
        return int(ex["distance_km"] * 1000)
    elif ex.get("distance_m"):
        return int(ex["distance_m"])
    return 0
