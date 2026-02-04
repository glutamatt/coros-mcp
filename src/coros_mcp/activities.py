"""
Activity management tools for COROS MCP server.

Provides tools for querying and managing COROS activities.
"""

import json
from datetime import datetime

from fastmcp import Context

from coros_mcp.client_factory import get_client
from coros_mcp.coros_client import FileType


def register_tools(app):
    """Register activity tools with the MCP app."""

    @app.tool()
    async def get_activities(
        ctx: Context,
        start_date: str = None,
        end_date: str = None,
        page: int = 1,
        size: int = 20,
    ) -> str:
        """
        Get list of COROS activities.

        Returns a paginated list of activities with summary information.
        Activities can be filtered by date range.

        Args:
            start_date: Filter start date in YYYY-MM-DD format (optional)
            end_date: Filter end date in YYYY-MM-DD format (optional)
            page: Page number, starting from 1 (default: 1)
            size: Number of activities per page (default: 20, max: 50)

        Returns:
            JSON with activity list and pagination info
        """
        client = get_client(ctx)

        from_date = None
        to_date = None

        if start_date:
            from_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if end_date:
            to_date = datetime.strptime(end_date, "%Y-%m-%d").date()

        data = client.get_activities_list(
            page=page,
            size=min(size, 50),
            from_date=from_date,
            to_date=to_date,
        )

        # Curate the activity list for cleaner output
        activities = []
        for activity in data.get("dataList", []):
            activities.append({
                "id": activity.get("labelId"),
                "date": _format_date(activity.get("date")),
                "name": activity.get("name"),
                "sport_type": activity.get("sportType"),
                "distance_meters": activity.get("distance"),
                "total_time_seconds": activity.get("totalTime"),
                "workout_time_seconds": activity.get("workoutTime"),
                "training_load": activity.get("trainingLoad"),
                "device": activity.get("device"),
            })

        result = {
            "count": data.get("count", 0),
            "total_pages": data.get("totalPage", 1),
            "current_page": data.get("pageNumber", page),
            "activities": activities,
        }

        return json.dumps(result, indent=2)

    @app.tool()
    async def get_activity_details(activity_id: str, ctx: Context) -> str:
        """
        Get detailed information about a COROS activity.

        Returns comprehensive activity data including:
        - Summary metrics (distance, time, pace, heart rate, etc.)
        - Lap data with splits
        - Heart rate zones
        - GPS track information
        - Weather conditions

        Args:
            activity_id: The activity's labelId from get_activities

        Returns:
            JSON with detailed activity data
        """
        client = get_client(ctx)
        data = client.get_activity_details(activity_id)

        # Curate the summary for cleaner output
        summary = data.get("summary", {})
        curated = {
            "activity_id": activity_id,
            "name": summary.get("name"),
            "sport_type": summary.get("sportType"),
            "sport_mode": summary.get("sportMode"),

            # Timing
            "start_time": summary.get("startTimestamp"),
            "end_time": summary.get("endTimestamp"),
            "total_time_seconds": summary.get("totalTime"),
            "workout_time_seconds": summary.get("workoutTime"),
            "pause_time_seconds": summary.get("pauseTime"),

            # Distance and pace
            "distance_meters": summary.get("distance"),
            "avg_pace_seconds_per_km": summary.get("avgPace"),
            "avg_speed_m_s": summary.get("avgSpeed"),

            # Heart rate
            "avg_heart_rate_bpm": summary.get("avgHr"),
            "max_heart_rate_bpm": summary.get("maxHr"),

            # Cadence
            "avg_cadence_spm": summary.get("avgCadence"),
            "max_cadence_spm": summary.get("maxCadence"),

            # Elevation
            "elevation_gain_meters": summary.get("elevGain"),
            "total_descent_meters": summary.get("totalDescent"),
            "avg_elevation_meters": summary.get("avgElev"),
            "max_elevation_meters": summary.get("maxElev"),
            "min_elevation_meters": summary.get("minElev"),

            # Power (for running/cycling)
            "avg_power_watts": summary.get("avgPower"),
            "max_power_watts": summary.get("maxPower"),
            "normalized_power": summary.get("np"),

            # Calories and training load
            "calories": summary.get("calories"),
            "training_load": summary.get("trainingLoad"),
            "aerobic_effect": summary.get("aerobicEffect"),
            "anaerobic_effect": summary.get("anaerobicEffect"),

            # Running dynamics
            "avg_stride_length_cm": summary.get("avgStepLen"),
            "avg_ground_time_ms": summary.get("avgGroundTime"),
            "avg_vertical_ratio_percent": summary.get("avgVertRatio"),
        }

        # Add lap data if available
        lap_list = data.get("lapList", [])
        if lap_list:
            laps = []
            for lap_data in lap_list:
                for lap_item in lap_data.get("lapItemList", []):
                    laps.append({
                        "lap_index": lap_item.get("lapIndex"),
                        "distance_meters": lap_item.get("distance"),
                        "time_seconds": lap_item.get("time"),
                        "avg_pace_seconds_per_km": lap_item.get("avgPace"),
                        "avg_heart_rate_bpm": lap_item.get("avgHr"),
                        "max_heart_rate_bpm": lap_item.get("maxHr"),
                        "avg_cadence_spm": lap_item.get("avgCadence"),
                        "elevation_gain_meters": lap_item.get("elevGain"),
                        "avg_power_watts": lap_item.get("avgPower"),
                    })
            curated["laps"] = laps

        # Add heart rate zones if available
        zone_list = data.get("zoneList", [])
        for zone_data in zone_list:
            if zone_data.get("type") == 1:  # Heart rate zones
                zones = []
                for zone_item in zone_data.get("zoneItemList", []):
                    zones.append({
                        "zone": zone_item.get("zoneIndex"),
                        "min_bpm": zone_item.get("leftScope"),
                        "max_bpm": zone_item.get("rightScope"),
                        "time_seconds": zone_item.get("second"),
                        "percent": zone_item.get("percent"),
                    })
                curated["heart_rate_zones"] = zones

        # Add weather if available
        weather = data.get("weather", {})
        if weather:
            curated["weather"] = {
                "temperature_celsius": weather.get("temperature"),
                "feels_like_celsius": weather.get("bodyFeelTemp"),
                "humidity_percent": weather.get("humidity"),
                "wind_speed_m_s": weather.get("windSpeed"),
            }

        # Remove None values for cleaner output
        curated = {k: v for k, v in curated.items() if v is not None}

        return json.dumps(curated, indent=2)

    @app.tool()
    async def get_activity_download_url(
        activity_id: str,
        file_format: str = "fit",
        ctx: Context = None,
    ) -> str:
        """
        Get download URL for a COROS activity file.

        The returned URL can be used to download the activity in the
        specified format. URLs are temporary and expire after some time.

        Args:
            activity_id: The activity's labelId
            file_format: Export format: fit, tcx, gpx, kml, or csv (default: fit)

        Returns:
            JSON with the download URL
        """
        client = get_client(ctx)

        # Map format string to FileType enum
        format_map = {
            "fit": FileType.FIT,
            "tcx": FileType.TCX,
            "gpx": FileType.GPX,
            "kml": FileType.KML,
            "csv": FileType.CSV,
        }

        file_type = format_map.get(file_format.lower(), FileType.FIT)
        url = client.get_activity_download_url(activity_id, file_type)

        return json.dumps({
            "activity_id": activity_id,
            "format": file_format,
            "download_url": url,
        }, indent=2)

    @app.tool()
    async def get_activities_summary(
        ctx: Context,
        days: int = 7,
    ) -> str:
        """
        Get a summary of recent activities.

        Provides an aggregated view of activities over the specified
        number of days, including totals for distance, time, and load.

        Args:
            days: Number of days to include (default: 7, max: 30)

        Returns:
            JSON with activity summary statistics
        """
        from datetime import timedelta

        client = get_client(ctx)

        days = min(days, 30)
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days - 1)

        data = client.get_activities_list(
            page=1,
            size=50,
            from_date=start_date,
            to_date=end_date,
        )

        activities = data.get("dataList", [])

        # Calculate summary statistics
        total_distance = sum(a.get("distance", 0) for a in activities)
        total_time = sum(a.get("workoutTime", 0) for a in activities)
        total_training_load = sum(a.get("trainingLoad", 0) for a in activities)

        # Group by sport type
        sport_counts = {}
        for activity in activities:
            sport_type = activity.get("sportType", 0)
            sport_name = _get_sport_name(sport_type)
            if sport_name not in sport_counts:
                sport_counts[sport_name] = {
                    "count": 0,
                    "distance_meters": 0,
                    "time_seconds": 0,
                }
            sport_counts[sport_name]["count"] += 1
            sport_counts[sport_name]["distance_meters"] += activity.get("distance", 0)
            sport_counts[sport_name]["time_seconds"] += activity.get("workoutTime", 0)

        summary = {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days,
            },
            "totals": {
                "activity_count": len(activities),
                "total_distance_meters": total_distance,
                "total_distance_km": round(total_distance / 1000, 2),
                "total_time_seconds": total_time,
                "total_time_hours": round(total_time / 3600, 2),
                "total_training_load": total_training_load,
            },
            "by_sport": sport_counts,
        }

        return json.dumps(summary, indent=2)

    return app


def _format_date(date_int: int) -> str:
    """Convert YYYYMMDD integer to YYYY-MM-DD string."""
    if not date_int:
        return None
    date_str = str(date_int)
    if len(date_str) == 8:
        return f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    return None


def _get_sport_name(sport_type: int) -> str:
    """Get human-readable sport name from COROS sport type code."""
    # Common COROS sport type codes
    sport_names = {
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
    return sport_names.get(sport_type, f"Sport_{sport_type}")
