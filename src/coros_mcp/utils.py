"""
Shared utility functions for COROS MCP server.

Date conversions, formatting helpers used across domain modules.
"""


def date_to_coros(date_str: str) -> int:
    """Convert YYYY-MM-DD string to COROS YYYYMMDD integer.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Date as YYYYMMDD integer (e.g. 20260211)
    """
    return int(date_str.replace("-", ""))


def coros_to_date(coros_int: int) -> str:
    """Convert COROS YYYYMMDD integer to YYYY-MM-DD string.

    Args:
        coros_int: Date as YYYYMMDD integer

    Returns:
        Date in YYYY-MM-DD format, or None if invalid
    """
    if not coros_int:
        return None
    s = str(coros_int)
    if len(s) == 8:
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return None


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "1h01m01s" or "25m30s"
    """
    if not seconds or seconds <= 0:
        return "0s"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h{m:02d}m{s:02d}s"
    if m > 0:
        return f"{m}m{s:02d}s"
    return f"{s}s"


def format_pace(avg_pace: int) -> str:
    """Format COROS pace value to min:sec/km.

    COROS stores pace as seconds per km.

    Args:
        avg_pace: Pace in seconds per km

    Returns:
        Formatted string like "5:30/km"
    """
    if not avg_pace or avg_pace <= 0:
        return None
    minutes = avg_pace // 60
    secs = avg_pace % 60
    return f"{minutes}:{secs:02d}/km"


def format_distance(meters: float) -> str:
    """Format distance in meters to human-readable string.

    Args:
        meters: Distance in meters

    Returns:
        Formatted string like "10.0 km" or "800 m"
    """
    if not meters or meters <= 0:
        return "0 m"
    if meters >= 1000:
        return f"{meters / 1000:.1f} km"
    return f"{int(meters)} m"


# Sport type code mapping (COROS activity context)
SPORT_NAMES = {
    0: "Unknown",
    1: "Run",
    2: "Indoor Run",
    3: "Trail Run",
    4: "Track Run",
    5: "Hike",
    6: "Bike",
    7: "Indoor Bike",
    8: "Mountain Bike",
    9: "Pool Swim",
    10: "Open Water Swim",
    11: "Triathlon",
    12: "Multisport",
    13: "Ski",
    14: "Snowboard",
    15: "XC Ski",
    16: "Strength",
    17: "Gym Cardio",
    18: "Rowing",
    19: "Walk",
    20: "Flatwater",
    21: "Whitewater",
    22: "Windsurfing",
    23: "Speedsurfing",
    24: "GPS Cardio",
    100: "Other",
}


def get_sport_name(sport_type: int) -> str:
    """Get human-readable sport name from COROS sport type code."""
    return SPORT_NAMES.get(sport_type, f"Sport_{sport_type}")
