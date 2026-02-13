"""Tests for api/calendar.py — Calendar + adherence formatting."""

from unittest.mock import Mock, patch

from coros_mcp.api.calendar import get_calendar, get_adherence


@patch("coros_mcp.api.calendar.sdk_training")
def test_get_calendar(mock_training):
    mock_training.get_training_schedule.return_value = {
        "id": "plan-1",
        "name": "My Plan",
        "pbVersion": 5,
        "entities": [
            {"idInPlan": "1", "happenDay": 20260212, "planId": "plan-1"},
            {"idInPlan": "2", "happenDay": 20260214, "planId": "plan-1"},
        ],
        "programs": [
            {
                "idInPlan": "1",
                "name": "Easy Run",
                "sportType": 1,
                "planDistance": 8000,
                "planDuration": 2400,
                "planTrainingLoad": 60,
                "actualDistance": 0,
                "actualDuration": 0,
                "actualTrainingLoad": 0,
                "exercises": [],
            },
            {
                "idInPlan": "2",
                "name": "Tempo Run",
                "sportType": 1,
                "planDistance": 10000,
                "planDuration": 3000,
                "planTrainingLoad": 85,
                "actualDistance": 10200,
                "actualDuration": 2950,
                "actualTrainingLoad": 88,
                "exercises": [],
            },
        ],
        "sportDatasNotInPlan": [
            {"name": "Extra Jog", "sportType": 1, "happenDay": 20260213,
             "distance": 3000, "duration": 1200, "trainingLoad": 25, "labelId": "act1"},
        ],
        "weekStages": [
            {"firstDayInWeek": 20260209, "stage": 2, "trainSum": 300},
        ],
        "eventTags": [
            {"name": "Spring 10K", "type": 2, "happenDay": 20260315},
        ],
    }

    client = Mock()
    result = get_calendar(client, start_date="2026-02-09", end_date="2026-02-15")

    assert result["plan_name"] == "My Plan"
    assert len(result["scheduled_workouts"]) == 2
    assert result["scheduled_workouts"][0]["name"] == "Easy Run"
    assert result["scheduled_workouts"][0]["date"] == "2026-02-12"
    assert result["scheduled_workouts"][0]["status"] == "planned"
    assert result["scheduled_workouts"][1]["status"] == "completed"

    assert len(result["unplanned_activities"]) == 1
    assert result["unplanned_activities"][0]["name"] == "Extra Jog"

    assert len(result["week_stages"]) == 1

    # Event tags
    assert "events" in result
    assert result["events"][0]["name"] == "Spring 10K"
    assert result["events"][0]["type"] == "competition"
    assert result["events"][0]["date"] == "2026-03-15"


@patch("coros_mcp.api.calendar.sdk_training")
def test_get_calendar_no_events(mock_training):
    mock_training.get_training_schedule.return_value = {
        "entities": [], "programs": [],
        "sportDatasNotInPlan": [], "weekStages": [],
    }

    client = Mock()
    result = get_calendar(client, start_date="2026-02-09", end_date="2026-02-15")
    assert "events" not in result


@patch("coros_mcp.api.calendar.sdk_training")
def test_get_adherence(mock_training):
    mock_training.get_training_summary.return_value = {
        "todayTrainingSum": {
            "actualDistance": 5000, "planDistance": 8000,
            "actualDuration": 1800, "planDuration": 2400,
            "actualTrainingLoad": 45, "planTrainingLoad": 60,
        },
        "weekTrains": [
            {
                "firstDayInWeek": 20260203,
                "weekTrainSum": {
                    "actualDistance": 40000, "planDistance": 45000,
                    "actualDuration": 14400, "planDuration": 16200,
                    "actualTrainingLoad": 300, "planTrainingLoad": 350,
                },
            },
        ],
        "dayTrainSums": [
            {
                "happenDay": 20260210,
                "dayTrainSum": {
                    "actualDistance": 10000, "planDistance": 10000,
                    "actualTrainingLoad": 85, "planTrainingLoad": 80,
                },
            },
        ],
    }

    client = Mock()
    result = get_adherence(client, start_date="2026-02-03", end_date="2026-02-13")

    assert result["today"]["actual_distance"] == "5.0 km"
    assert result["today"]["planned_distance"] == "8.0 km"
    assert len(result["weekly"]) == 1
    assert result["weekly"][0]["actual_load"] == 300
    assert len(result["daily"]) == 1
