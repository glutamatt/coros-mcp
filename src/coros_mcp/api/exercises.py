"""
Exercise translation between domain model and COROS protocol.

The hard part: converting human-friendly exercise dicts to COROS's internal
format and back. Handles centimeter encoding, pace×1000, HR ranges, repeat
groups, and simple vs complex workout detection.
"""

from coros_mcp.api.model import Exercise
from coros_mcp.sdk.types import (
    ExerciseType,
    TargetType,
    TargetDisplayUnit,
    RestType,
    SportType,
    SPORT_NAME_TO_CODE,
    EXERCISE_TEMPLATES,
    DEFAULT_SOURCE_ID,
    DEFAULT_SOURCE_URL,
)


# ── Public API ──────────────────────────────────────────────────────────


def to_coros(exercises: list, sport: str) -> tuple[list[dict], bool]:
    """Convert domain exercises to COROS format.

    Args:
        exercises: List of Exercise objects or dicts
        sport: Sport name (e.g. "running", "bike")

    Returns:
        (coros_exercises, is_simple) — list of COROS exercise dicts and
        whether this is a "simple" (single-step) workout.
    """
    sport_code = _resolve_sport(sport)
    parsed = [_ensure_exercise(e) for e in exercises]

    # Simple workout: single non-interval exercise with no repeats
    if (len(parsed) == 1
            and parsed[0].type not in ("interval",)
            and not parsed[0].repeats):
        ex = parsed[0]
        coros_ex = _build_step(ex, exercise_id=1, sort_no=1, sport_code=sport_code)
        return [coros_ex], True

    coros_exercises = []
    exercise_id = 1
    sort_no = 1

    for ex in parsed:
        if ex.repeats and ex.repeats > 1:
            # Repeat group
            group_id = exercise_id
            group = _build_group(group_id, sort_no, ex.repeats, ex.rest_seconds)
            coros_exercises.append(group)
            exercise_id += 1

            # Work step inside group (shares sortNo with group)
            work = _build_step(
                ex, exercise_id=exercise_id, sort_no=sort_no,
                sport_code=sport_code, force_type=ExerciseType.INTERVAL,
            )
            work["groupId"] = group_id
            coros_exercises.append(work)
            exercise_id += 1
            sort_no += 1

            # Recovery step inside group (if rest specified)
            if ex.rest_seconds:
                recovery = _build_step_defaults(
                    exercise_id, sort_no, ExerciseType.RECOVERY, sport_code,
                )
                recovery["groupId"] = group_id
                recovery["targetType"] = TargetType.DURATION
                recovery["targetValue"] = ex.rest_seconds
                recovery["targetDisplayUnit"] = TargetDisplayUnit.SECONDS
                coros_exercises.append(recovery)
                exercise_id += 1
                sort_no += 1
        else:
            step = _build_step(
                ex, exercise_id=exercise_id, sort_no=sort_no,
                sport_code=sport_code,
            )
            coros_exercises.append(step)
            exercise_id += 1
            sort_no += 1

    return coros_exercises, False


def from_coros(coros_exercises: list[dict]) -> list[dict]:
    """Convert COROS exercises to human-readable dicts.

    Returns a list of dicts with keys like:
    type, target, duration, distance, pace, hr, repeats, rest
    """
    result = []
    exercise_types = {0: "repeat", 1: "warmup", 2: "interval", 3: "cooldown", 4: "recovery"}
    groups = {}  # id → group dict

    for ex in coros_exercises:
        if ex.get("isGroup"):
            groups[ex["id"]] = ex
            entry = {
                "type": "repeat",
                "repeats": ex.get("sets", 1),
            }
            if ex.get("restType") == 0 and ex.get("restValue"):
                entry["rest_seconds"] = ex["restValue"]
            result.append(entry)
            continue

        entry = {
            "type": exercise_types.get(ex.get("exerciseType"), f"type_{ex.get('exerciseType')}"),
        }

        # Target
        target_type = ex.get("targetType")
        target_value = ex.get("targetValue", 0)
        display_unit = ex.get("targetDisplayUnit", 0)

        if target_type == TargetType.DURATION and target_value:
            entry["duration_seconds"] = target_value
            entry["duration_display"] = _format_duration(target_value)
        elif target_type == TargetType.DISTANCE and target_value:
            # Value is in centimeters
            meters = target_value / 100
            if meters >= 1000:
                entry["distance_km"] = round(meters / 1000, 2)
            else:
                entry["distance_m"] = int(meters)

        # Intensity (pace or HR)
        intensity_type = ex.get("intensityType", 0)
        if intensity_type == 3:  # Pace
            multiplier = ex.get("intensityMultiplier", 0)
            value = ex.get("intensityValue", 0)
            extend = ex.get("intensityValueExtend", 0)
            if multiplier == 1000 and value:
                pace_sec = value / 1000
                entry["pace_per_km"] = _format_pace_value(pace_sec)
                if extend:
                    entry["pace_per_km"] += f"-{_format_pace_value(extend / 1000)}"
        elif intensity_type == 2:  # HR
            value = ex.get("intensityValue", 0)
            extend = ex.get("intensityValueExtend", 0)
            if value:
                entry["hr_bpm"] = str(value)
                if extend:
                    entry["hr_bpm"] += f"-{extend}"

        # Group membership
        group_id = ex.get("groupId")
        if group_id and group_id != "" and group_id in groups:
            entry["in_group"] = True

        result.append(entry)

    return result


def parse_pace(s: str) -> tuple[int, int]:
    """Parse pace string to COROS intensity values (sec/km × 1000).

    Args:
        s: "5:00" or "4:30-5:00"

    Returns:
        (low_value, high_value) — both in sec/km × 1000.
        For single value, low == high.
    """
    parts = s.split("-")
    values = [_pace_str_to_ms(p.strip()) for p in parts]
    if len(values) == 1:
        return values[0], values[0]
    return values[0], values[1]


def parse_hr(s: str) -> tuple[int, int]:
    """Parse HR string to BPM values.

    Args:
        s: "150" or "150-160"

    Returns:
        (low_bpm, high_bpm). For single value, low == high.
    """
    parts = s.split("-")
    values = [int(p.strip()) for p in parts]
    if len(values) == 1:
        return values[0], values[0]
    return values[0], values[1]


# ── Internal helpers ────────────────────────────────────────────────────


def _resolve_sport(sport: str) -> int:
    """Resolve sport name to COROS sport code."""
    code = SPORT_NAME_TO_CODE.get(sport.lower())
    if code is None:
        raise ValueError(
            f"Unknown sport '{sport}'. "
            f"Use: {', '.join(sorted(SPORT_NAME_TO_CODE.keys()))}"
        )
    return int(code)


def _ensure_exercise(e) -> Exercise:
    """Convert dict or Exercise to validated Exercise."""
    if isinstance(e, Exercise):
        ex = e
    elif isinstance(e, dict):
        ex = Exercise.from_dict(e)
    else:
        raise TypeError(f"Expected Exercise or dict, got {type(e)}")
    ex.validate()
    return ex


_EXERCISE_TYPE_MAP = {
    "warmup": ExerciseType.WARMUP,
    "interval": ExerciseType.INTERVAL,
    "cooldown": ExerciseType.COOLDOWN,
    "recovery": ExerciseType.RECOVERY,
}


def _build_step(
    ex: Exercise,
    exercise_id: int,
    sort_no: int,
    sport_code: int,
    force_type: ExerciseType = None,
) -> dict:
    """Build a single COROS exercise step from a domain Exercise."""
    ex_type = force_type or _EXERCISE_TYPE_MAP.get(ex.type, ExerciseType.INTERVAL)
    result = _build_step_defaults(exercise_id, sort_no, ex_type, sport_code)

    # Target: duration or distance
    if ex.duration_minutes:
        result["targetType"] = TargetType.DURATION
        result["targetValue"] = int(ex.duration_minutes * 60)
        result["targetDisplayUnit"] = TargetDisplayUnit.SECONDS
    elif ex.distance_km:
        result["targetType"] = TargetType.DISTANCE
        result["targetValue"] = int(ex.distance_km * 100000)  # km → cm
        result["targetDisplayUnit"] = TargetDisplayUnit.KILOMETERS
    elif ex.distance_m:
        result["targetType"] = TargetType.DISTANCE
        result["targetValue"] = int(ex.distance_m * 100)  # m → cm
        result["targetDisplayUnit"] = TargetDisplayUnit.METERS

    # Intensity: pace or HR
    if ex.pace_per_km:
        low, high = parse_pace(ex.pace_per_km)
        result["intensityType"] = 3
        result["intensityValue"] = low
        result["intensityValueExtend"] = high
        result["intensityMultiplier"] = 1000
        result["intensityDisplayUnit"] = "1"  # min/km (string in requests)
        result["intensityCustom"] = 0
        result["isIntensityPercent"] = False
    elif ex.hr_bpm:
        low, high = parse_hr(ex.hr_bpm)
        result["intensityType"] = 2
        result["intensityValue"] = low
        result["intensityValueExtend"] = high
        result["intensityMultiplier"] = 0
        result["intensityDisplayUnit"] = 0
        result["intensityCustom"] = 2
        result["isIntensityPercent"] = False
        result["hrType"] = 3  # LTHR zones default

    return result


def _build_step_defaults(
    exercise_id: int, sort_no: int, ex_type: int, sport_code: int,
) -> dict:
    """Base COROS exercise step (matches HAR step field set)."""
    tmpl = EXERCISE_TEMPLATES.get(ExerciseType(ex_type), {})
    return {
        "access": 0,
        "createTimestamp": tmpl.get("createTimestamp", 0),
        "defaultOrder": tmpl.get("defaultOrder", 0),
        "equipment": [1],
        "exerciseType": int(ex_type),
        "groupId": "",
        "hrType": 0,
        "id": exercise_id,
        "intensityCustom": 0,
        "intensityDisplayUnit": 0,
        "intensityMultiplier": 0,
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
        "restType": RestType.NO_REST,
        "restValue": 0,
        "sets": 1,
        "sortNo": sort_no,
        "sourceId": "0",
        "sourceUrl": "",
        "sportType": sport_code,
        "subType": 0,
        "targetDisplayUnit": 0,
        "targetType": 0,
        "targetValue": 0,
        "userId": 0,
        "videoUrl": "",
    }


def _build_group(
    exercise_id: int, sort_no: int, repeats: int, rest_seconds: int = None,
) -> dict:
    """Build a COROS repeat group exercise."""
    return {
        "access": 0,
        "defaultOrder": 0,
        "exerciseType": ExerciseType.GROUP,
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
        "restType": RestType.TIMED if rest_seconds else RestType.NO_REST,
        "restValue": rest_seconds or 0,
        "sets": repeats,
        "sortNo": sort_no,
        "sourceId": "0",
        "sourceUrl": "",
        "sportType": 0,
        "subType": 0,
        "targetType": "",
        "targetValue": 0,
        "videoUrl": "",
    }


def _pace_str_to_ms(s: str) -> int:
    """Convert 'M:SS' to sec/km × 1000."""
    mins, secs = s.split(":")
    total_seconds = int(mins) * 60 + int(secs)
    return total_seconds * 1000


def _format_pace_value(sec_per_km: float) -> str:
    """Format seconds/km as 'M:SS'."""
    sec = int(sec_per_km)
    return f"{sec // 60}:{sec % 60:02d}"


def _format_duration(seconds: int) -> str:
    """Format seconds to human-readable duration."""
    if seconds <= 0:
        return "0s"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h{m:02d}m{s:02d}s"
    if m > 0:
        return f"{m}m{s:02d}s"
    return f"{s}s"
