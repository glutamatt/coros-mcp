"""
Tests for COROS MCP training schedule tools.

Tools are thin wrappers — detailed formatting tests are in tests/api/.
"""
import json
import pytest
from unittest.mock import patch
from mcp.server.fastmcp import FastMCP

from coros_mcp import training
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_training():
    app = FastMCP("Test COROS Training")
    app = training.register_tools(app)
    return app


@patch("coros_mcp.api.calendar.get_calendar")
@pytest.mark.asyncio
async def test_get_training_schedule(mock_api, app_with_training):
    mock_api.return_value = {
        "period": {"start_date": "2026-02-09", "end_date": "2026-02-15"},
        "plan_name": "Test Plan",
        "scheduled_workouts": [
            {"id": "5", "name": "Easy Run", "date": "2026-02-12", "status": "planned"},
        ],
        "unplanned_activities": [
            {"name": "Extra Run", "date": "2026-02-11"},
        ],
        "week_stages": [{"week_start": "2026-02-09", "stage": 2}],
    }

    result = await app_with_training.call_tool(
        "get_training_schedule",
        {"start_date": "2026-02-09", "end_date": "2026-02-15"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["plan_name"] == "Test Plan"
    assert len(data["scheduled_workouts"]) == 1
    assert data["scheduled_workouts"][0]["name"] == "Easy Run"
    assert len(data["unplanned_activities"]) == 1

    # Verify dates passed through
    mock_api.assert_called_once()
    args = mock_api.call_args
    assert args[0][1] == "2026-02-09"
    assert args[0][2] == "2026-02-15"


@patch("coros_mcp.api.calendar.get_calendar")
@pytest.mark.asyncio
async def test_get_training_schedule_defaults(mock_api, app_with_training):
    """Test schedule defaults to current week when no dates provided."""
    mock_api.return_value = {
        "period": {"start_date": "2026-02-09", "end_date": "2026-02-15"},
        "scheduled_workouts": [], "unplanned_activities": [], "week_stages": [],
    }

    result = await app_with_training.call_tool("get_training_schedule", {})
    text = get_tool_result_text(result)
    data = json.loads(text)
    assert "period" in data


@patch("coros_mcp.api.calendar.get_adherence")
@pytest.mark.asyncio
async def test_get_plan_adherence(mock_api, app_with_training):
    mock_api.return_value = {
        "period": {"start_date": "2026-01-14", "end_date": "2026-02-11"},
        "today": {"actual_distance": "5.0 km", "planned_distance": "8.0 km", "actual_load": 45},
        "weekly": [{"week_start": "2026-02-03", "actual_load": 300, "planned_load": 350}],
        "daily": [{"date": "2026-02-10", "actual_load": 85}],
    }

    result = await app_with_training.call_tool(
        "get_plan_adherence",
        {"start_date": "2026-01-14", "end_date": "2026-02-11"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["today"]["actual_distance"] == "5.0 km"
    assert data["today"]["actual_load"] == 45
    assert len(data["weekly"]) == 1
    assert len(data["daily"]) == 1


@patch("coros_mcp.api.workouts.delete_workout")
@pytest.mark.asyncio
async def test_delete_scheduled_workout(mock_api, app_with_training):
    mock_api.return_value = {"success": True, "message": "Workout 'Easy Run' deleted"}

    result = await app_with_training.call_tool(
        "delete_scheduled_workout",
        {"workout_id": "5", "date": "2026-02-12"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["success"] is True
    assert "Easy Run" in data["message"]


@patch("coros_mcp.api.workouts.delete_workout")
@pytest.mark.asyncio
async def test_delete_scheduled_workout_not_found(mock_api, app_with_training):
    mock_api.return_value = {"success": False, "error": "Workout nonexistent not found on 2026-02-12"}

    result = await app_with_training.call_tool(
        "delete_scheduled_workout",
        {"workout_id": "nonexistent", "date": "2026-02-12"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["success"] is False
    assert "not found" in data["error"]


@patch("coros_mcp.api.workouts.delete_workout")
@pytest.mark.asyncio
async def test_delete_scheduled_workout_api_error(mock_api, app_with_training):
    mock_api.side_effect = ValueError("Plan data is illegal.")

    result = await app_with_training.call_tool(
        "delete_scheduled_workout",
        {"workout_id": "5", "date": "2026-02-12"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["success"] is False
    assert "illegal" in data["error"].lower()


def test_training_tools_registered(app_with_training):
    tools = app_with_training._tool_manager._tools
    tool_names = list(tools.keys())

    expected = ["get_training_schedule", "get_plan_adherence", "delete_scheduled_workout"]
    for name in expected:
        assert name in tool_names, f"Tool {name} not registered"
