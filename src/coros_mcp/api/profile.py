"""
Athlete profile — who are you?

Identity, biometrics, physiological thresholds, and all training zones.
"""

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import auth as sdk_auth
from coros_mcp.utils import coros_to_date, format_pace


# Zone name labels for human-friendly output
_HR_ZONE_NAMES = ["Recovery", "Aerobic Endurance", "Tempo", "Threshold", "VO2max"]
_PACE_ZONE_NAMES = ["Easy", "Aerobic", "Tempo", "Threshold", "Interval"]


def get_athlete_profile(client: CorosClient) -> dict:
    """Full athlete profile: identity, biometrics, physiological thresholds,
    and all training zones (HR, pace, power).

    From account/query. Essential coaching context — called once per session.
    """
    data = sdk_auth.get_account_full(client)
    zone_data = data.get("zoneData", {})

    result = {
        "identity": _clean_nones({
            "user_id": data.get("userId"),
            "nickname": data.get("nickname"),
            "email": data.get("email"),
            "birthday": coros_to_date(data.get("birthday")),
            "sex": _format_sex(data.get("sex")),
            "country": data.get("countryCode"),
        }),
        "biometrics": _clean_nones({
            "height_cm": data.get("stature"),
            "weight_kg": data.get("weight"),
        }),
        "thresholds": _clean_nones({
            "max_hr": zone_data.get("maxHr") or data.get("maxHr"),
            "resting_hr": zone_data.get("rhr") or data.get("rhr"),
            "lthr": zone_data.get("lthr"),
            "ltsp": _format_ltsp(zone_data.get("ltsp")),
            "ftp": zone_data.get("ftp"),
        }),
    }

    # HR zones
    hr_zones = zone_data.get("maxHrZone") or zone_data.get("lthrZone")
    if hr_zones:
        result["hr_zones"] = _format_hr_zones(hr_zones)

    # Pace zones
    pace_zones = zone_data.get("ltspZone")
    if pace_zones:
        result["pace_zones"] = _format_pace_zones(pace_zones)

    # Power zones
    power_zones = zone_data.get("cyclePowerZone")
    if power_zones:
        result["power_zones"] = power_zones

    return result


def _format_sex(sex_code) -> str:
    if sex_code == 1:
        return "male"
    if sex_code == 2:
        return "female"
    return None


def _format_ltsp(ltsp) -> str:
    """Format LTSP (lactate threshold speed/pace) as pace string."""
    if not ltsp:
        return None
    return format_pace(ltsp)


def _format_hr_zones(boundaries: list) -> list[dict]:
    """Format HR zone boundaries to named ranges.

    boundaries is [z1_max, z2_max, z3_max, z4_max, z5_max].
    """
    if not boundaries or len(boundaries) < 2:
        return boundaries

    zones = []
    prev = 0
    for i, upper in enumerate(boundaries):
        name = _HR_ZONE_NAMES[i] if i < len(_HR_ZONE_NAMES) else f"Zone {i+1}"
        if i == 0:
            zones.append({"zone": i + 1, "name": name, "range": f"<{upper} bpm"})
        else:
            zones.append({"zone": i + 1, "name": name, "range": f"{prev}-{upper} bpm"})
        prev = upper

    return zones


def _format_pace_zones(boundaries: list) -> list[dict]:
    """Format pace zone boundaries to named ranges.

    boundaries is [z1_pace, z2_pace, ...] in sec/km (slower → faster).
    """
    if not boundaries or len(boundaries) < 2:
        return boundaries

    zones = []
    for i, pace in enumerate(boundaries):
        name = _PACE_ZONE_NAMES[i] if i < len(_PACE_ZONE_NAMES) else f"Zone {i+1}"
        pace_str = format_pace(pace)
        if i == 0:
            zones.append({"zone": i + 1, "name": name, "range": f"slower than {pace_str}"})
        elif i == len(boundaries) - 1:
            zones.append({"zone": i + 1, "name": name, "range": f"faster than {pace_str}"})
        else:
            prev_pace_str = format_pace(boundaries[i - 1])
            zones.append({"zone": i + 1, "name": name, "range": f"{prev_pace_str} to {pace_str}"})

    return zones


def _clean_nones(d):
    """Recursively remove None values from a dict."""
    if isinstance(d, dict):
        return {k: _clean_nones(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [_clean_nones(i) for i in d]
    return d
