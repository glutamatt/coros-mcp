"""
Activity history — what have you done?

Past sessions, laps, zones, totals.
"""

from datetime import datetime, timedelta

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import activities as sdk_activities
from coros_mcp.sdk.types import FileType
from coros_mcp.utils import coros_to_date, format_duration, format_distance, format_pace, get_sport_name


def get_activities(
    client: CorosClient,
    start_date: str = None,
    end_date: str = None,
    page: int = 1,
    size: int = 20,
) -> dict:
    """Paginated activity list with formatted fields."""
    from_date = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None
    to_date = datetime.strptime(end_date, "%Y-%m-%d").date() if end_date else None

    data = sdk_activities.get_activities_list(
        client, page=page, size=min(size, 50),
        from_date=from_date, to_date=to_date,
    )

    activities = [
        _clean_nones({
            "id": a.get("labelId"),
            "date": coros_to_date(a.get("date")),
            "name": a.get("name"),
            "sport": get_sport_name(a.get("sportType", 0)),
            "distance": format_distance(a.get("distance", 0)),
            "duration": format_duration(a.get("workoutTime", 0)),
            "training_load": a.get("trainingLoad"),
            "device": a.get("device"),
        })
        for a in data.get("dataList", [])
    ]

    return {
        "count": data.get("count", 0),
        "total_pages": data.get("totalPage", 1),
        "current_page": data.get("pageNumber", page),
        "activities": activities,
    }


def get_activity_detail(client: CorosClient, activity_id: str) -> dict:
    """Full activity: summary, laps, HR zones, weather."""
    data = sdk_activities.get_activity_details(client, activity_id)
    summary = data.get("summary", {})

    result = _clean_nones({
        "activity_id": activity_id,
        "name": summary.get("name"),
        "sport": get_sport_name(summary.get("sportType", 0)),

        # Timing
        "start_time": summary.get("startTimestamp"),
        "total_time": format_duration(summary.get("totalTime", 0)),
        "workout_time": format_duration(summary.get("workoutTime", 0)),

        # Distance and pace
        "distance": format_distance(summary.get("distance", 0)),
        "avg_pace": format_pace(summary.get("avgPace", 0)),

        # Heart rate
        "avg_hr": summary.get("avgHr"),
        "max_hr": summary.get("maxHr"),

        # Cadence
        "avg_cadence": summary.get("avgCadence"),

        # Elevation
        "elevation_gain": summary.get("elevGain"),
        "total_descent": summary.get("totalDescent"),

        # Power
        "avg_power": summary.get("avgPower"),
        "normalized_power": summary.get("np"),

        # Training effect
        "training_load": summary.get("trainingLoad"),
        "calories": summary.get("calories"),
        "aerobic_effect": summary.get("aerobicEffect"),
        "anaerobic_effect": summary.get("anaerobicEffect"),
    })

    # Laps
    lap_list = data.get("lapList", [])
    if lap_list:
        laps = []
        for lap_data in lap_list:
            for item in lap_data.get("lapItemList", []):
                laps.append(_clean_nones({
                    "lap": item.get("lapIndex"),
                    "distance": format_distance(item.get("distance", 0)),
                    "time": format_duration(item.get("time", 0)),
                    "avg_pace": format_pace(item.get("avgPace", 0)),
                    "avg_hr": item.get("avgHr"),
                    "max_hr": item.get("maxHr"),
                    "elevation_gain": item.get("elevGain"),
                }))
        if laps:
            result["laps"] = laps

    # HR zones
    for zone_data in data.get("zoneList", []):
        if zone_data.get("type") == 1:
            zones = [
                _clean_nones({
                    "zone": z.get("zoneIndex"),
                    "range": f"{z.get('leftScope')}-{z.get('rightScope')} bpm",
                    "time": format_duration(z.get("second", 0)),
                    "percent": z.get("percent"),
                })
                for z in zone_data.get("zoneItemList", [])
            ]
            if zones:
                result["hr_zones"] = zones

    # Weather
    weather = data.get("weather", {})
    if weather and weather.get("temperature") is not None:
        result["weather"] = _clean_nones({
            "temperature_c": weather.get("temperature"),
            "feels_like_c": weather.get("bodyFeelTemp"),
            "humidity_pct": weather.get("humidity"),
            "wind_speed_ms": weather.get("windSpeed"),
        })

    return result


def get_activities_summary(client: CorosClient, days: int = 7) -> dict:
    """Aggregated view: totals + per-sport breakdown."""
    days = min(days, 30)
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days - 1)

    data = sdk_activities.get_activities_list(
        client, page=1, size=50,
        from_date=start_date, to_date=end_date,
    )

    activities = data.get("dataList", [])

    total_distance = sum(a.get("distance", 0) for a in activities)
    total_time = sum(a.get("workoutTime", 0) for a in activities)
    total_load = sum(a.get("trainingLoad", 0) for a in activities)

    # Group by sport
    by_sport = {}
    for a in activities:
        sport = get_sport_name(a.get("sportType", 0))
        if sport not in by_sport:
            by_sport[sport] = {"count": 0, "distance_m": 0, "time_s": 0}
        by_sport[sport]["count"] += 1
        by_sport[sport]["distance_m"] += a.get("distance", 0)
        by_sport[sport]["time_s"] += a.get("workoutTime", 0)

    sport_breakdown = {
        name: {
            "count": v["count"],
            "distance": format_distance(v["distance_m"]),
            "duration": format_duration(v["time_s"]),
        }
        for name, v in by_sport.items()
    }

    return {
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "days": days,
        },
        "totals": {
            "activity_count": len(activities),
            "distance": format_distance(total_distance),
            "duration": format_duration(total_time),
            "training_load": total_load,
        },
        "by_sport": sport_breakdown,
    }


def get_download_url(
    client: CorosClient, activity_id: str, format: str = "fit",
) -> dict:
    """Get temporary download URL for activity file."""
    format_map = {
        "fit": FileType.FIT, "tcx": FileType.TCX,
        "gpx": FileType.GPX, "kml": FileType.KML, "csv": FileType.CSV,
    }
    file_type = format_map.get(format.lower(), FileType.FIT)
    url = sdk_activities.get_activity_download_url(client, activity_id, file_type)

    return {"activity_id": activity_id, "format": format, "download_url": url}


def _clean_nones(d):
    """Recursively remove None values from a dict."""
    if isinstance(d, dict):
        return {k: _clean_nones(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [_clean_nones(i) for i in d]
    return d
