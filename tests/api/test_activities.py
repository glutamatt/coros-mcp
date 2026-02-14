"""Tests for api/activities.py — Activity list/detail formatting."""

from unittest.mock import Mock, patch

from coros_mcp.api.activities import (
    get_activities,
    get_activity_detail,
    get_activities_summary,
    get_download_url,
)


@patch("coros_mcp.api.activities.sdk_activities")
def test_get_activities(mock_sdk):
    mock_sdk.get_activities_list.return_value = {
        "count": 2,
        "totalPage": 1,
        "pageNumber": 1,
        "dataList": [
            {
                "labelId": "abc123",
                "date": 20260210,
                "name": "Morning Run",
                "sportType": 1,
                "distance": 10000,
                "workoutTime": 3600,
                "trainingLoad": 85,
                "device": "PACE 3",
            },
            {
                "labelId": "def456",
                "date": 20260209,
                "name": "Easy Run",
                "sportType": 1,
                "distance": 5000,
                "workoutTime": 1800,
                "trainingLoad": 40,
                "device": "PACE 3",
            },
        ],
    }

    client = Mock()
    result = get_activities(client, start_date="2026-02-09", end_date="2026-02-10")

    assert result["count"] == 2
    assert len(result["activities"]) == 2
    assert result["activities"][0]["id"] == "abc123"
    assert result["activities"][0]["sport"] == "Run"
    assert result["activities"][0]["distance"] == "10.0 km"
    assert result["activities"][0]["duration"] == "1h00m00s"


@patch("coros_mcp.api.activities.sdk_activities")
def test_get_activity_detail(mock_sdk):
    mock_sdk.get_activity_details.return_value = {
        "summary": {
            "name": "Tempo Run",
            "sportType": 1,
            "startTimestamp": 1739500800,
            "totalTime": 3600,
            "workoutTime": 3550,
            "distance": 10000,
            "avgPace": 355,
            "avgHr": 155,
            "maxHr": 175,
            "avgCadence": 180,
            "elevGain": 50,
            "trainingLoad": 95,
            "calories": 600,
        },
        "lapList": [
            {
                "lapItemList": [
                    {"lapIndex": 1, "distance": 5000, "time": 1775, "avgPace": 355, "avgHr": 150, "maxHr": 165},
                    {"lapIndex": 2, "distance": 5000, "time": 1775, "avgPace": 355, "avgHr": 160, "maxHr": 175},
                ]
            }
        ],
        "zoneList": [
            {
                "type": 1,
                "zoneItemList": [
                    {"zoneIndex": 1, "leftScope": 100, "rightScope": 130, "second": 60, "percent": 2},
                    {"zoneIndex": 2, "leftScope": 130, "rightScope": 150, "second": 600, "percent": 17},
                ]
            }
        ],
        "weather": {"temperature": 12, "bodyFeelTemp": 10, "humidity": 70, "windSpeed": 4.0},
    }

    client = Mock()
    result = get_activity_detail(client, "abc123")

    assert result["activity_id"] == "abc123"
    assert result["name"] == "Tempo Run"
    assert result["sport"] == "Run"
    assert result["distance"] == "10.0 km"
    assert result["avg_pace"] == "5:55/km"
    assert result["avg_hr"] == 155
    assert result["training_load"] == 95

    # Laps
    assert len(result["laps"]) == 2
    assert result["laps"][0]["distance"] == "5.0 km"

    # HR zones
    assert len(result["hr_zones"]) == 2

    # Weather
    assert result["weather"]["temperature_c"] == 12


@patch("coros_mcp.api.activities.sdk_activities")
def test_get_activities_summary(mock_sdk):
    mock_sdk.get_activities_list.return_value = {
        "count": 3,
        "totalPage": 1,
        "pageNumber": 1,
        "dataList": [
            {"sportType": 1, "distance": 10000, "workoutTime": 3600, "trainingLoad": 85},
            {"sportType": 1, "distance": 8000, "workoutTime": 2800, "trainingLoad": 65},
            {"sportType": 16, "distance": 0, "workoutTime": 3600, "trainingLoad": 50},
        ],
    }

    client = Mock()
    result = get_activities_summary(client, days=7)

    assert result["totals"]["activity_count"] == 3
    assert result["totals"]["training_load"] == 200
    assert "Run" in result["by_sport"]
    assert "Strength" in result["by_sport"]
    assert result["by_sport"]["Run"]["count"] == 2


@patch("coros_mcp.api.activities.sdk_activities")
def test_get_download_url(mock_sdk):
    mock_sdk.get_activity_download_url.return_value = "https://cdn.coros.com/activity.fit"

    client = Mock()
    result = get_download_url(client, "abc123", format="fit")

    assert result["download_url"] == "https://cdn.coros.com/activity.fit"
    assert result["format"] == "fit"
