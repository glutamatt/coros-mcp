"""
Analysis tools for COROS MCP server.

Training load analysis, sport statistics, and long-term trends.
"""

import json

from fastmcp import Context

from coros_mcp.client_factory import get_client
from coros_mcp.utils import coros_to_date, get_sport_name, format_duration, format_distance


def register_tools(app):
    """Register analysis tools with the MCP app."""

    @app.tool()
    async def get_training_load_analysis(ctx: Context) -> str:
        """
        Get comprehensive training load analysis.

        Returns daily/weekly load, ATI/CTI (acute/chronic training index),
        tired rate, VO2max trend, recommended load range, and periodization stages.

        Essential for load management and periodization decisions.

        Returns:
            JSON with training load analysis data
        """
        client = get_client(ctx)
        data = client.get_analysis()

        # Daily metrics (last 14 days for context)
        day_list = data.get("dayList", [])
        recent_days = [
            {
                "date": coros_to_date(d.get("happenDay")),
                "training_load": d.get("trainingLoad") if d.get("trainingLoad") else None,
                "distance_meters": d.get("distance"),
                "duration_seconds": d.get("duration"),
                "vo2max": d.get("vo2max"),
                "stamina_level": d.get("staminaLevel"),
                "resting_hr": d.get("rhr"),
                "ati": d.get("ati"),
                "cti": d.get("cti"),
                "tired_rate": d.get("tiredRateNew"),
                "recommended_load_min": d.get("recomendTlMin"),
                "recommended_load_max": d.get("recomendTlMax"),
            }
            for d in day_list[-14:]
        ]

        # Weekly summaries
        week_list = data.get("weekList", [])
        weeks = [
            {
                "week_start": coros_to_date(w.get("firstDayOfWeek")),
                "training_load": w.get("trainingLoad"),
                "recommended_min": w.get("recomendTlMin"),
                "recommended_max": w.get("recomendTlMax"),
            }
            for w in week_list[-8:]  # Last 8 weeks
        ]

        # 7-day rolling averages (last 4 entries)
        t7_list = data.get("t7dayList", [])
        rolling_7d = []
        for t in t7_list[-4:]:
            entry = {
                "vo2max": t.get("vo2max"),
                "stamina_level": t.get("staminaLevel"),
                "stamina_level_7d": t.get("staminaLevel7d"),
                "tired_rate": t.get("tiredRateNew"),
                "load_ratio": t.get("trainingLoadRatio"),
                "load_ratio_state": t.get("trainingLoadRatioState"),
            }
            # Add tired rate zones if available
            zones = t.get("tiredRateNewZoneList", [])
            if zones:
                entry["tired_rate_zones"] = zones
            rolling_7d.append(entry)

        # Periodization stages
        stages = data.get("trainingWeekStageList", [])
        periodization = [
            {
                "week_start": coros_to_date(s.get("firstDayOfWeek")),
                "stage": s.get("stage"),
            }
            for s in stages[-8:]
        ]

        result = {
            "recent_days": [_clean_nones(d) for d in recent_days],
            "weekly_load": [_clean_nones(w) for w in weeks],
            "rolling_7d_trend": [_clean_nones(r) for r in rolling_7d],
            "periodization": periodization,
        }

        return json.dumps(result, indent=2)

    @app.tool()
    async def get_sport_statistics(ctx: Context) -> str:
        """
        Get per-sport volume/load breakdown and intensity distribution.

        Returns sport-by-sport aggregates (count, distance, duration, load)
        and weekly training intensity breakdown (low/medium/high percentage).

        Useful for analyzing training balance across sports.

        Returns:
            JSON with sport statistics and intensity distribution
        """
        client = get_client(ctx)
        data = client.get_analysis()

        # Per-sport aggregates
        sport_stats = []
        for s in data.get("sportStatistic", []):
            sport_stats.append({
                "sport": get_sport_name(s.get("sportType", 0)),
                "sport_type": s.get("sportType"),
                "count": s.get("count"),
                "distance_meters": s.get("distance"),
                "distance_display": format_distance(s.get("distance", 0)),
                "duration_seconds": s.get("duration"),
                "duration_display": format_duration(s.get("duration", 0)),
                "avg_heart_rate": s.get("avgHeartRate"),
                "training_load": s.get("trainingLoad"),
            })

        # Intensity distribution
        tl_intensity = data.get("tlIntensity", {})
        intensity_weeks = []
        for w in tl_intensity.get("detailList", []):
            intensity_weeks.append({
                "low_pct": w.get("periodLowPct"),
                "low_load": w.get("periodLowValue"),
                "medium_pct": w.get("periodMediumPct"),
                "medium_load": w.get("periodMediumValue"),
                "high_pct": w.get("periodHighPct"),
                "high_load": w.get("periodHighValue"),
            })

        result = {
            "sport_breakdown": sport_stats,
            "weekly_intensity": intensity_weeks[-8:],  # Last 8 weeks
        }

        return json.dumps(result, indent=2)

    return app


def _clean_nones(d):
    """Recursively remove None values from a dict."""
    if isinstance(d, dict):
        return {k: _clean_nones(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [_clean_nones(i) for i in d]
    return d
