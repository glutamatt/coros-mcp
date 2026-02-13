"""Tests for api/status.py — Fitness status formatting."""

from unittest.mock import Mock, patch

from coros_mcp.api.status import (
    get_fitness_status,
    get_hrv_trend,
    get_training_load,
    get_sport_stats,
    get_personal_records,
    get_race_predictions,
)


def _mock_dashboard():
    return {
        "summaryInfo": {
            "recoveryPct": 85,
            "recoveryState": 2,
            "fullRecoveryHours": 12,
            "aerobicEnduranceScore": 72,
            "anaerobicCapacityScore": 45,
            "anaerobicEnduranceScore": 55,
            "lactateThresholdCapacityScore": 68,
            "staminaLevel": 75,
            "staminaLevelChange": 2,
            "staminaLevelRanking": 3,
            "sleepHrvData": {
                "sleepHrvList": [
                    {"happenDay": 20260210, "avgSleepHrv": 52, "sleepHrvBase": 48},
                    {"happenDay": 20260211, "avgSleepHrv": 55, "sleepHrvBase": 49},
                ]
            },
            "runScoreList": [
                {"type": 5, "score": 1626, "pace": 325},
                {"type": 1, "score": 17133, "pace": 406},
            ],
        }
    }


def _mock_dashboard_detail():
    return {
        "summaryInfo": {
            "ati": 85, "cti": 72, "tiredRateNew": 0.6,
            "trainingLoadRatio": 1.1, "trainingLoadRatioState": 2,
            "recomendTlInDays": 120,
        },
        "currentWeekRecord": {
            "distanceRecord": 25000, "durationRecord": 7200, "tlRecord": 350,
        },
    }


@patch("coros_mcp.api.status.sdk_dashboard")
def test_get_fitness_status(mock_dash):
    mock_dash.get_dashboard.return_value = _mock_dashboard()
    mock_dash.get_dashboard_detail.return_value = _mock_dashboard_detail()

    client = Mock()
    result = get_fitness_status(client)

    assert result["recovery"]["percent"] == 85
    assert result["fitness_scores"]["aerobic_endurance"] == 72
    assert result["stamina"]["level"] == 75
    assert result["training_load"]["ati"] == 85
    assert result["current_week"]["training_load"] == 350
    assert result["hrv_summary"]["recent_7d_avg"] == 53.5


@patch("coros_mcp.api.status.sdk_dashboard")
def test_get_hrv_trend(mock_dash):
    mock_dash.get_dashboard.return_value = _mock_dashboard()

    client = Mock()
    result = get_hrv_trend(client)

    assert len(result["values"]) == 2
    assert result["recent_7d_avg"] == 53.5
    assert result["current_baseline"] == 49


@patch("coros_mcp.api.status.sdk_dashboard")
def test_get_hrv_trend_empty(mock_dash):
    mock_dash.get_dashboard.return_value = {"summaryInfo": {"sleepHrvData": {"sleepHrvList": []}}}

    client = Mock()
    result = get_hrv_trend(client)
    assert result["values"] == []


@patch("coros_mcp.api.status.sdk_analysis")
def test_get_training_load(mock_analysis):
    mock_analysis.get_analysis.return_value = {
        "dayList": [
            {"happenDay": 20260210, "trainingLoad": 85, "distance": 10000,
             "duration": 3600, "vo2max": 52, "ati": 85, "cti": 72,
             "tiredRateNew": 0.6, "recomendTlMin": 80, "recomendTlMax": 130},
        ],
        "weekList": [
            {"firstDayOfWeek": 20260203, "trainingLoad": 350, "recomendTlMin": 300, "recomendTlMax": 450},
        ],
        "trainingWeekStageList": [
            {"firstDayOfWeek": 20260203, "stage": 2},
        ],
    }

    client = Mock()
    result = get_training_load(client)

    assert len(result["recent_days"]) == 1
    assert result["recent_days"][0]["training_load"] == 85
    assert len(result["weekly_load"]) == 1
    assert len(result["periodization"]) == 1


@patch("coros_mcp.api.status.sdk_analysis")
def test_get_sport_stats(mock_analysis):
    mock_analysis.get_analysis.return_value = {
        "sportStatistic": [
            {"sportType": 1, "count": 5, "distance": 45000, "duration": 14400,
             "avgHeartRate": 148, "trainingLoad": 350},
        ],
        "tlIntensity": {
            "detailList": [
                {"periodLowPct": 60, "periodMediumPct": 25, "periodHighPct": 15},
            ]
        },
    }

    client = Mock()
    result = get_sport_stats(client)

    assert len(result["sport_breakdown"]) == 1
    assert result["sport_breakdown"][0]["sport"] == "Run"
    assert result["sport_breakdown"][0]["count"] == 5
    assert len(result["weekly_intensity"]) == 1


@patch("coros_mcp.api.status.sdk_dashboard")
def test_get_personal_records(mock_dash):
    mock_dash.get_personal_records.return_value = {
        "allRecordList": [
            {
                "type": 4,
                "recordList": [
                    {"happenDay": 20250601, "sportType": 1, "type": 5, "record": 1200, "labelId": "rec1"},
                ]
            },
        ]
    }

    client = Mock()
    result = get_personal_records(client)
    assert "all_time" in result
    assert result["all_time"][0]["record"] == "5km"


@patch("coros_mcp.api.status.sdk_dashboard")
def test_get_race_predictions(mock_dash):
    mock_dash.get_dashboard.return_value = _mock_dashboard()

    client = Mock()
    result = get_race_predictions(client)
    assert len(result["predictions"]) == 2
    assert result["predictions"][0]["distance"] == "5K"
    assert result["predictions"][1]["distance"] == "Marathon"
