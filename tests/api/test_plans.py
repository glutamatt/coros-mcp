"""Tests for api/plans.py — Plan CRUD flows."""

from unittest.mock import Mock, patch

from coros_mcp.api.plans import (
    list_plans,
    get_plan,
    create_plan,
    add_workout_to_plan,
    activate_plan,
    delete_plans,
)


@patch("coros_mcp.api.plans.sdk_plans")
def test_list_plans_draft(mock_plans):
    mock_plans.query_plans.return_value = [
        {
            "id": "plan-1",
            "name": "N1117",
            "overview": "Marathon Prep",
            "status": 0,
            "totalDay": 84,
            "maxWeeks": 12,
            "entities": [{"idInPlan": "1"}, {"idInPlan": "2"}],
            "createTime": "2026-01-15 10:00:00",
        },
    ]

    client = Mock()
    result = list_plans(client, status="draft")

    assert len(result) == 1
    assert result[0]["id"] == "plan-1"
    assert result[0]["name"] == "Marathon Prep"
    assert result[0]["status"] == "draft"
    assert result[0]["workout_count"] == 2

    mock_plans.query_plans.assert_called_once_with(client, status_list=[0])


@patch("coros_mcp.api.plans.sdk_plans")
def test_list_plans_active(mock_plans):
    mock_plans.query_plans.return_value = []
    client = Mock()
    result = list_plans(client, status="active")
    assert result == []
    mock_plans.query_plans.assert_called_once_with(client, status_list=[1])


@patch("coros_mcp.api.plans.sdk_plans")
def test_get_plan(mock_plans):
    mock_plans.get_plan_detail.return_value = {
        "id": "plan-1",
        "name": "N1117",
        "overview": "5K Training",
        "totalDay": 28,
        "maxWeeks": 4,
        "entities": [
            {"idInPlan": "1", "dayNo": 0},
            {"idInPlan": "2", "dayNo": 3},
        ],
        "programs": [
            {"idInPlan": "1", "name": "Easy Run", "sportType": 1,
             "distance": 5000, "duration": 1800, "trainingLoad": 40, "exercises": []},
            {"idInPlan": "2", "name": "Intervals", "sportType": 1,
             "distance": 8000, "duration": 2700, "trainingLoad": 75, "exercises": []},
        ],
    }

    client = Mock()
    result = get_plan(client, "plan-1")

    assert result["id"] == "plan-1"
    assert result["name"] == "5K Training"
    assert result["total_days"] == 28
    assert len(result["workouts"]) == 2
    assert result["workouts"][0]["day"] == 0
    assert result["workouts"][1]["day"] == 3


@patch("coros_mcp.api.plans.sdk_plans")
@patch("coros_mcp.api.plans.sdk_workouts")
def test_create_plan(mock_workouts, mock_plans):
    mock_workouts.calculate_workout.return_value = {
        "planDistance": 5000,
        "planDuration": 1800,
        "planTrainingLoad": 40,
        "planPitch": 0,
        "exerciseBarChart": [],
    }
    mock_plans.add_plan.return_value = "new-plan-id"

    client = Mock()
    result = create_plan(
        client,
        name="Week 1",
        overview="Easy start week",
        workouts=[
            {"day": 0, "name": "Easy Run", "sport": "running",
             "exercises": [{"type": "warmup", "duration_minutes": 30}]},
            {"day": 3, "name": "Recovery", "sport": "running",
             "exercises": [{"type": "warmup", "duration_minutes": 20}]},
        ],
    )

    assert result["success"] is True
    assert result["plan_id"] == "new-plan-id"
    assert result["workout_count"] == 2
    assert result["total_days"] == 4  # max dayNo=3, +1
    assert result["weeks"] == 1

    # Calculate should have been called for each workout
    assert mock_workouts.calculate_workout.call_count == 2

    # Verify the add_plan payload
    add_payload = mock_plans.add_plan.call_args[0][1]
    assert len(add_payload["entities"]) == 2
    assert len(add_payload["programs"]) == 2
    assert add_payload["entities"][0]["dayNo"] == 0
    assert add_payload["entities"][1]["dayNo"] == 3


@patch("coros_mcp.api.plans.sdk_plans")
@patch("coros_mcp.api.plans.sdk_workouts")
def test_add_workout_to_plan(mock_workouts, mock_plans):
    mock_plans.get_plan_detail.return_value = {
        "id": "plan-1",
        "maxIdInPlan": "2",
        "entities": [
            {"idInPlan": "1", "dayNo": 0},
            {"idInPlan": "2", "dayNo": 3},
        ],
        "programs": [
            {"idInPlan": "1", "name": "Run 1"},
            {"idInPlan": "2", "name": "Run 2"},
        ],
        "totalDay": 4,
        "maxWeeks": 1,
        "minWeeks": 1,
    }
    mock_workouts.calculate_workout.return_value = {
        "planDistance": 8000, "planDuration": 2400, "planTrainingLoad": 60,
        "planPitch": 0, "exerciseBarChart": [],
    }
    mock_plans.update_plan.return_value = {"result": "0000"}

    client = Mock()
    result = add_workout_to_plan(
        client,
        plan_id="plan-1",
        day=7,
        name="Long Run",
        sport="running",
        exercises=[{"type": "warmup", "duration_minutes": 60}],
    )

    assert result["success"] is True
    assert result["workout_id"] == "3"
    assert result["day"] == 7

    # Verify update was called with all entities + new one
    update_payload = mock_plans.update_plan.call_args[0][1]
    assert len(update_payload["entities"]) == 3
    assert len(update_payload["programs"]) == 3
    assert update_payload["maxIdInPlan"] == "3"


@patch("coros_mcp.api.plans.sdk_plans")
def test_activate_plan(mock_plans):
    mock_plans.execute_sub_plan.return_value = {"result": "0000"}

    client = Mock()
    result = activate_plan(client, plan_id="plan-1", start_date="2026-03-01")

    assert result["success"] is True
    assert result["start_date"] == "2026-03-01"
    mock_plans.execute_sub_plan.assert_called_once_with(client, "plan-1", 20260301)


@patch("coros_mcp.api.plans.sdk_plans")
def test_delete_plans(mock_plans):
    mock_plans.delete_plans.return_value = {"result": "0000"}

    client = Mock()
    result = delete_plans(client, plan_ids=["plan-1", "plan-2"])

    assert result["success"] is True
    assert result["deleted"] == ["plan-1", "plan-2"]
    mock_plans.delete_plans.assert_called_once_with(client, ["plan-1", "plan-2"])
