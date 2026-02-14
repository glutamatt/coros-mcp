"""Tests for api/workouts.py — Create/estimate/reschedule/delete flows."""

from unittest.mock import Mock, patch, call

from coros_mcp.api.workouts import (
    create_workout,
    estimate_workout,
    reschedule_workout,
    delete_workout,
)


def _mock_schedule():
    return {
        "id": "plan-1",
        "pbVersion": 5,
        "maxIdInPlan": "10",
        "entities": [
            {"idInPlan": "5", "happenDay": 20260212, "planId": "plan-1", "planProgramId": "5"},
        ],
        "programs": [
            {"idInPlan": "5", "name": "Easy Run", "sportType": 1},
        ],
    }


@patch("coros_mcp.api.workouts.sdk_training")
@patch("coros_mcp.api.workouts.sdk_workouts")
def test_create_workout(mock_workouts, mock_training):
    mock_training.get_training_schedule.return_value = _mock_schedule()
    mock_workouts.calculate_workout.return_value = {
        "planDistance": 1000000,  # centimeters → 10 km
        "planDuration": 3600,
        "planTrainingLoad": 85,
        "planPitch": 0,
        "exerciseBarChart": [],
    }
    mock_training.update_training_schedule.return_value = {"result": "0000"}

    client = Mock()
    result = create_workout(
        client,
        name="Tempo Run",
        date="2026-02-15",
        sport="running",
        exercises=[
            {"type": "warmup", "duration_minutes": 15},
            {"type": "interval", "distance_km": 5.0},
            {"type": "cooldown", "duration_minutes": 10},
        ],
    )

    assert result["success"] is True
    assert result["workout_id"] == "11"  # maxIdInPlan=10 + 1
    assert result["name"] == "Tempo Run"
    assert result["date"] == "2026-02-15"
    assert result["estimated_distance"] == "10.0 km"
    assert result["estimated_load"] == 85

    # Verify calculate was called
    mock_workouts.calculate_workout.assert_called_once()
    # Verify schedule update was called
    mock_training.update_training_schedule.assert_called_once()
    payload = mock_training.update_training_schedule.call_args[0][1]
    assert payload["versionObjects"][0]["status"] == 1  # create
    # Distance passed through as raw centimeters to API
    assert payload["programs"][0]["distance"] == "1000000.00"


@patch("coros_mcp.api.workouts.sdk_training")
@patch("coros_mcp.api.workouts.sdk_workouts")
def test_create_workout_api_error(mock_workouts, mock_training):
    mock_training.get_training_schedule.return_value = _mock_schedule()
    mock_workouts.calculate_workout.return_value = {
        "planDistance": 1000000, "planDuration": 3600, "planTrainingLoad": 85,
        "planPitch": 0, "exerciseBarChart": [],
    }
    mock_training.update_training_schedule.return_value = {
        "result": "5001", "message": "Plan version conflict",
    }

    client = Mock()
    result = create_workout(client, "Run", "2026-02-15", "running",
                            [{"type": "warmup", "duration_minutes": 30}])

    assert result["success"] is False
    assert "version conflict" in result["error"]


@patch("coros_mcp.api.workouts.sdk_training")
@patch("coros_mcp.api.workouts.sdk_workouts")
def test_estimate_workout(mock_workouts, mock_training):
    mock_training.get_training_schedule.return_value = _mock_schedule()
    mock_workouts.estimate_workout.return_value = {
        "distance": "1000000.00",  # centimeters → 10 km
        "duration": 3600,
        "trainingLoad": 85,
    }

    client = Mock()
    result = estimate_workout(
        client,
        sport="running",
        exercises=[{"type": "warmup", "duration_minutes": 30}],
        date="2026-02-15",
    )

    assert result["estimated_load"] == 85
    assert result["estimated_distance"] == "10.0 km"


@patch("coros_mcp.api.workouts.sdk_training")
def test_reschedule_workout(mock_training):
    mock_training.get_training_schedule.return_value = _mock_schedule()
    mock_training.update_training_schedule.return_value = {"result": "0000"}

    client = Mock()
    result = reschedule_workout(client, workout_id="5", new_date="2026-02-16")

    assert result["success"] is True
    assert "moved to 2026-02-16" in result["message"]

    # Verify the entity was updated
    payload = mock_training.update_training_schedule.call_args[0][1]
    assert payload["entities"][0]["happenDay"] == 20260216
    assert payload["versionObjects"][0]["status"] == 2  # move


@patch("coros_mcp.api.workouts.sdk_training")
def test_reschedule_not_found(mock_training):
    mock_training.get_training_schedule.return_value = {
        "entities": [], "programs": [], "pbVersion": 5,
    }

    client = Mock()
    result = reschedule_workout(client, workout_id="999", new_date="2026-02-16")

    assert result["success"] is False
    assert "not found" in result["error"]


@patch("coros_mcp.api.workouts.sdk_training")
def test_delete_workout(mock_training):
    mock_training.get_training_schedule.return_value = _mock_schedule()
    mock_training.update_training_schedule.return_value = {"result": "0000"}

    client = Mock()
    result = delete_workout(client, workout_id="5", date="2026-02-12")

    assert result["success"] is True
    assert "deleted" in result["message"]

    payload = mock_training.update_training_schedule.call_args[0][1]
    assert payload["versionObjects"][0]["status"] == 3  # delete
    assert payload["entities"] == []
    assert payload["programs"] == []


@patch("coros_mcp.api.workouts.sdk_training")
def test_delete_not_found(mock_training):
    mock_training.get_training_schedule.return_value = {
        "pbVersion": 5, "entities": [], "programs": [],
    }

    client = Mock()
    result = delete_workout(client, workout_id="999", date="2026-02-12")
    assert result["success"] is False


def test_invalid_sport():
    import pytest
    client = Mock()
    with pytest.raises(ValueError, match="Unknown sport"):
        create_workout(client, "Run", "2026-02-15", "badminton",
                       [{"type": "warmup", "duration_minutes": 10}])
