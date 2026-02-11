"""
Dashboard tools for COROS MCP server.

Fitness overview, HRV trends, and personal records.
"""

import json

from fastmcp import Context

from coros_mcp.client_factory import get_client
from coros_mcp.utils import coros_to_date, format_duration, format_distance, get_sport_name


def register_tools(app):
    """Register dashboard tools with the MCP app."""

    @app.tool()
    async def get_fitness_summary(ctx: Context) -> str:
        """
        Get the athlete's current fitness overview.

        Combines dashboard summary and detail data into a unified view:
        recovery state, fitness scores, HRV baseline, stamina level,
        training load vs target, and current week records.

        This is the "how is the athlete doing right now" tool.

        Returns:
            JSON with fitness summary data
        """
        client = get_client(ctx)

        dashboard = client.get_dashboard()
        detail = client.get_dashboard_detail()

        summary_info = dashboard.get("summaryInfo", {})
        detail_summary = detail.get("summaryInfo", {})
        current_week = detail.get("currentWeekRecord", {})

        result = {
            "recovery": {
                "recovery_percent": summary_info.get("recoveryPct"),
                "recovery_state": summary_info.get("recoveryState"),
                "full_recovery_hours": summary_info.get("fullRecoveryHours"),
            },
            "fitness_scores": {
                "aerobic_endurance": summary_info.get("aerobicEnduranceScore"),
                "anaerobic_capacity": summary_info.get("anaerobicCapacityScore"),
                "anaerobic_endurance": summary_info.get("anaerobicEnduranceScore"),
                "lactate_threshold": summary_info.get("lactateThresholdCapacityScore"),
            },
            "stamina": {
                "level": summary_info.get("staminaLevel"),
                "change": summary_info.get("staminaLevelChange"),
                "ranking": summary_info.get("staminaLevelRanking"),
            },
            "physiological": {
                "resting_hr": summary_info.get("rhr"),
                "lthr": summary_info.get("lthr"),
                "ltsp": summary_info.get("ltsp"),
            },
            "training_load": {
                "ati": detail_summary.get("ati"),
                "cti": detail_summary.get("cti"),
                "tired_rate": detail_summary.get("tiredRateNew"),
                "load_ratio": detail_summary.get("trainingLoadRatio"),
                "load_ratio_state": detail_summary.get("trainingLoadRatioState"),
                "recommended_daily_load": detail_summary.get("recomendTlInDays"),
            },
            "current_week": {
                "distance_record": current_week.get("distanceRecord"),
                "duration_record": current_week.get("durationRecord"),
                "load_record": current_week.get("tlRecord"),
            },
        }

        # Add HRV data if available
        hrv_data = summary_info.get("sleepHrvData", {})
        hrv_list = hrv_data.get("sleepHrvList", [])
        if hrv_list:
            result["hrv"] = {
                "recent_values": [
                    {
                        "date": coros_to_date(h.get("happenDay")),
                        "avg_hrv": h.get("avgSleepHrv"),
                        "hrv_baseline": h.get("sleepHrvBase"),
                        "hrv_sd": h.get("sleepHrvSd"),
                    }
                    for h in hrv_list[-7:]  # Last 7 days
                ]
            }

        # Remove None values recursively
        result = _clean_nones(result)

        return json.dumps(result, indent=2)

    @app.tool()
    async def get_hrv_trend(ctx: Context) -> str:
        """
        Get HRV (Heart Rate Variability) trend data.

        Returns HRV baseline and daily values from sleep data.
        Useful for overtraining detection and recovery monitoring.

        Returns:
            JSON with HRV trend data
        """
        client = get_client(ctx)

        dashboard = client.get_dashboard()
        summary_info = dashboard.get("summaryInfo", {})

        hrv_data = summary_info.get("sleepHrvData", {})
        hrv_list = hrv_data.get("sleepHrvList", [])

        if not hrv_list:
            return json.dumps({
                "message": "No HRV data available. HRV is measured during sleep with a compatible COROS device.",
                "values": [],
            }, indent=2)

        values = [
            {
                "date": coros_to_date(h.get("happenDay")),
                "avg_hrv": h.get("avgSleepHrv"),
                "hrv_baseline": h.get("sleepHrvBase"),
                "hrv_sd": h.get("sleepHrvSd"),
            }
            for h in hrv_list
        ]

        # Calculate trend
        recent = [v["avg_hrv"] for v in values[-7:] if v.get("avg_hrv")]
        baseline_values = [v["hrv_baseline"] for v in values[-7:] if v.get("hrv_baseline")]

        result = {
            "values": values,
            "total_days": len(values),
        }

        if recent:
            result["recent_7d_avg"] = round(sum(recent) / len(recent), 1)
        if baseline_values:
            result["current_baseline"] = baseline_values[-1]

        return json.dumps(result, indent=2)

    @app.tool()
    async def get_personal_records(ctx: Context) -> str:
        """
        Get personal records by time period.

        Returns PRs for week, month, year, and all-time across sports.
        Useful for motivation and progress tracking.

        Returns:
            JSON with personal records grouped by period
        """
        client = get_client(ctx)
        data = client.get_personal_records()

        period_names = {1: "week", 2: "month", 3: "year", 4: "all_time"}

        records = {}
        for cycle in data.get("allRecordList", []):
            period = period_names.get(cycle.get("type"), f"period_{cycle.get('type')}")
            records[period] = [
                {
                    "date": coros_to_date(r.get("happenDay")),
                    "sport": get_sport_name(r.get("sportType", 0)),
                    "record_type": r.get("type"),
                    "value": r.get("record"),
                    "label_id": r.get("labelId"),
                }
                for r in cycle.get("recordList", [])
            ]

        return json.dumps(records, indent=2)

    return app


def _clean_nones(d):
    """Recursively remove None values from a dict."""
    if isinstance(d, dict):
        return {k: _clean_nones(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [_clean_nones(i) for i in d]
    return d
