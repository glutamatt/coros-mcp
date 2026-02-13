"""
Athlete status — how are you right now?

Fitness, recovery, HRV, training load, records, race predictions.
"""

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import dashboard as sdk_dashboard
from coros_mcp.sdk import analysis as sdk_analysis
from coros_mcp.utils import coros_to_date, format_duration, format_distance, format_pace, get_sport_name


# ── Personal record type codes ──────────────────────────────────────────

_RECORD_TYPE_NAMES = {
    7: "1km", 6: "3km", 5: "5km", 4: "10km",
    8: "1 mile", 9: "2 miles", 10: "3 miles", 11: "5 miles",
    101: "Longest distance", 102: "Max elevation gain",
}

# ── Race prediction type codes ──────────────────────────────────────────

_RACE_DISTANCES = {
    5: "5K", 4: "10K", 2: "Half Marathon", 1: "Marathon",
}

# ── Period names ────────────────────────────────────────────────────────

_PERIOD_NAMES = {1: "week", 2: "month", 3: "year", 4: "all_time"}


def get_fitness_status(client: CorosClient) -> dict:
    """Full athlete status: recovery, fitness scores, stamina, HRV, training load.

    Combines dashboard + dashboard_detail SDK calls.
    """
    dashboard = sdk_dashboard.get_dashboard(client)
    detail = sdk_dashboard.get_dashboard_detail(client)

    summary = dashboard.get("summaryInfo", {})
    detail_summary = detail.get("summaryInfo", {})
    current_week = detail.get("currentWeekRecord", {})

    result = {
        "recovery": _clean_nones({
            "percent": summary.get("recoveryPct"),
            "state": summary.get("recoveryState"),
            "full_recovery_hours": summary.get("fullRecoveryHours"),
        }),
        "fitness_scores": _clean_nones({
            "aerobic_endurance": summary.get("aerobicEnduranceScore"),
            "anaerobic_capacity": summary.get("anaerobicCapacityScore"),
            "anaerobic_endurance": summary.get("anaerobicEnduranceScore"),
            "lactate_threshold": summary.get("lactateThresholdCapacityScore"),
        }),
        "stamina": _clean_nones({
            "level": summary.get("staminaLevel"),
            "change": summary.get("staminaLevelChange"),
            "ranking": summary.get("staminaLevelRanking"),
        }),
        "training_load": _clean_nones({
            "ati": detail_summary.get("ati"),
            "cti": detail_summary.get("cti"),
            "tired_rate": detail_summary.get("tiredRateNew"),
            "load_ratio": detail_summary.get("trainingLoadRatio"),
            "load_ratio_state": detail_summary.get("trainingLoadRatioState"),
            "recommended_daily_load": detail_summary.get("recomendTlInDays"),
        }),
        "current_week": _clean_nones({
            "distance": format_distance(current_week.get("distanceRecord", 0)),
            "duration": format_duration(current_week.get("durationRecord", 0)),
            "training_load": current_week.get("tlRecord"),
        }),
    }

    # HRV summary if available
    hrv_data = summary.get("sleepHrvData", {})
    hrv_list = hrv_data.get("sleepHrvList", [])
    if hrv_list:
        recent = hrv_list[-7:]
        avg_values = [h["avgSleepHrv"] for h in recent if h.get("avgSleepHrv")]
        result["hrv_summary"] = _clean_nones({
            "recent_7d_avg": round(sum(avg_values) / len(avg_values), 1) if avg_values else None,
            "current_baseline": recent[-1].get("sleepHrvBase") if recent else None,
        })

    return result


def get_race_predictions(client: CorosClient) -> dict:
    """Race time predictions for 5K, 10K, half marathon, marathon.

    From dashboard/query runScoreList.
    """
    dashboard = sdk_dashboard.get_dashboard(client)
    summary = dashboard.get("summaryInfo", {})
    run_scores = summary.get("runScoreList", [])

    predictions = []
    for rs in run_scores:
        race_type = rs.get("type")
        distance_name = _RACE_DISTANCES.get(race_type)
        if not distance_name:
            continue

        score = rs.get("score", 0)
        pace = rs.get("pace", 0)
        predictions.append(_clean_nones({
            "distance": distance_name,
            "predicted_time": format_duration(score) if score else None,
            "pace_per_km": format_pace(pace) if pace else None,
        }))

    return {"predictions": predictions}


def get_hrv_trend(client: CorosClient) -> dict:
    """HRV trend with 7-day average and baseline."""
    dashboard = sdk_dashboard.get_dashboard(client)
    summary = dashboard.get("summaryInfo", {})
    hrv_data = summary.get("sleepHrvData", {})
    hrv_list = hrv_data.get("sleepHrvList", [])

    if not hrv_list:
        return {"message": "No HRV data available.", "values": []}

    values = [
        _clean_nones({
            "date": coros_to_date(h.get("happenDay")),
            "avg_hrv": h.get("avgSleepHrv"),
            "baseline": h.get("sleepHrvBase"),
        })
        for h in hrv_list
    ]

    recent = [v["avg_hrv"] for v in values[-7:] if v.get("avg_hrv")]
    baselines = [h.get("sleepHrvBase") for h in hrv_list[-7:] if h.get("sleepHrvBase")]

    result = {"values": values, "total_days": len(values)}
    if recent:
        result["recent_7d_avg"] = round(sum(recent) / len(recent), 1)
    if baselines:
        result["current_baseline"] = baselines[-1]

    return result


def get_training_load(client: CorosClient) -> dict:
    """Training load analysis: daily/weekly, ATI/CTI, VO2max, recommended load."""
    data = sdk_analysis.get_analysis(client)

    # Recent daily metrics
    day_list = data.get("dayList", [])
    recent_days = [
        _clean_nones({
            "date": coros_to_date(d.get("happenDay")),
            "training_load": d.get("trainingLoad") or None,
            "distance": format_distance(d.get("distance", 0)),
            "duration": format_duration(d.get("duration", 0)),
            "vo2max": d.get("vo2max"),
            "ati": d.get("ati"),
            "cti": d.get("cti"),
            "tired_rate": d.get("tiredRateNew"),
            "recommended_load_range": f"{d.get('recomendTlMin', 0)}-{d.get('recomendTlMax', 0)}",
        })
        for d in day_list[-14:]
    ]

    # Weekly summaries
    week_list = data.get("weekList", [])
    weeks = [
        _clean_nones({
            "week_start": coros_to_date(w.get("firstDayOfWeek")),
            "training_load": w.get("trainingLoad"),
            "recommended_range": f"{w.get('recomendTlMin', 0)}-{w.get('recomendTlMax', 0)}",
        })
        for w in week_list[-8:]
    ]

    # Periodization
    stages = data.get("trainingWeekStageList", [])
    periodization = [
        {"week_start": coros_to_date(s.get("firstDayOfWeek")), "stage": s.get("stage")}
        for s in stages[-8:]
    ]

    return {
        "recent_days": recent_days,
        "weekly_load": weeks,
        "periodization": periodization,
    }


def get_sport_stats(client: CorosClient) -> dict:
    """Per-sport breakdown and intensity distribution."""
    data = sdk_analysis.get_analysis(client)

    sport_breakdown = [
        _clean_nones({
            "sport": get_sport_name(s.get("sportType", 0)),
            "count": s.get("count"),
            "distance": format_distance(s.get("distance", 0)),
            "duration": format_duration(s.get("duration", 0)),
            "avg_hr": s.get("avgHeartRate"),
            "training_load": s.get("trainingLoad"),
        })
        for s in data.get("sportStatistic", [])
    ]

    # Intensity distribution
    tl_intensity = data.get("tlIntensity", {})
    intensity_weeks = [
        {
            "low_pct": w.get("periodLowPct"),
            "medium_pct": w.get("periodMediumPct"),
            "high_pct": w.get("periodHighPct"),
        }
        for w in tl_intensity.get("detailList", [])[-8:]
    ]

    return {"sport_breakdown": sport_breakdown, "weekly_intensity": intensity_weeks}


def get_personal_records(client: CorosClient) -> dict:
    """PRs by period (week/month/year/all-time)."""
    data = sdk_dashboard.get_personal_records(client)

    records = {}
    for cycle in data.get("allRecordList", []):
        period = _PERIOD_NAMES.get(cycle.get("type"), f"period_{cycle.get('type')}")
        records[period] = [
            _clean_nones({
                "record": _RECORD_TYPE_NAMES.get(r.get("type"), f"type_{r.get('type')}"),
                "date": coros_to_date(r.get("happenDay")),
                "sport": get_sport_name(r.get("sportType", 0)),
                "value": r.get("record"),
                "name": r.get("name"),
                "site": r.get("site"),
                "activity_id": r.get("labelId"),
            })
            for r in cycle.get("recordList", [])
        ]

    return records


def _clean_nones(d):
    """Recursively remove None values from a dict."""
    if isinstance(d, dict):
        return {k: _clean_nones(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [_clean_nones(i) for i in d]
    return d
