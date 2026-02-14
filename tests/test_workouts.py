"""
Tests for COROS MCP workout builder tools.

Tools are thin wrappers — detailed exercise model tests are in tests/api/.
"""
import json
import pytest
from unittest.mock import patch
from mcp.server.fastmcp import FastMCP

from coros_mcp import workouts
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_workouts():
    app = FastMCP("Test COROS Workouts")
    app = workouts.register_tools(app)
    return app


@patch("coros_mcp.api.workouts.create_workout")
@pytest.mark.asyncio
async def test_create_workout(mock_api, app_with_workouts):
    mock_api.return_value = {
        "success": True,
        "workout_id": "11",
        "name": "Tempo Run",
        "date": "2026-02-15",
        "sport": "running",
        "estimated_load": 85,
    }

    result = await app_with_workouts.call_tool(
        "create_workout",
        {
            "name": "Tempo Run",
            "date": "2026-02-15",
            "sport_type": "running",
            "exercises": [
                {"type": "warmup", "duration_minutes": 15},
                {"type": "interval", "distance_km": 1.0, "repeats": 4, "rest_seconds": 90},
                {"type": "cooldown", "duration_minutes": 10},
            ],
        },
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["success"] is True
    assert data["name"] == "Tempo Run"
    assert data["estimated_load"] == 85

    # Verify correct args passed through
    mock_api.assert_called_once()
    args = mock_api.call_args
    assert args[0][1] == "Tempo Run"       # name
    assert args[0][2] == "2026-02-15"      # date
    assert args[0][3] == "running"         # sport
    assert len(args[0][4]) == 3            # exercises


@patch("coros_mcp.api.workouts.create_workout")
@pytest.mark.asyncio
async def test_create_workout_invalid_sport(mock_api, app_with_workouts):
    mock_api.side_effect = ValueError("Unknown sport 'surfing'.")

    result = await app_with_workouts.call_tool(
        "create_workout",
        {
            "name": "Test",
            "date": "2026-02-15",
            "sport_type": "surfing",
            "exercises": [{"type": "warmup", "duration_minutes": 10}],
        },
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["success"] is False
    assert "surfing" in data["error"]


@patch("coros_mcp.api.workouts.estimate_workout")
@pytest.mark.asyncio
async def test_estimate_workout_load(mock_api, app_with_workouts):
    mock_api.return_value = {
        "estimated_distance": "10.0 km",
        "estimated_duration": "1h00m00s",
        "estimated_load": 85,
    }

    result = await app_with_workouts.call_tool(
        "estimate_workout_load",
        {
            "sport_type": "running",
            "exercises": [
                {"type": "warmup", "duration_minutes": 10},
                {"type": "interval", "distance_m": 800, "repeats": 6, "rest_seconds": 90},
                {"type": "cooldown", "duration_minutes": 10},
            ],
        },
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["estimated_load"] == 85
    assert data["estimated_distance"] == "10.0 km"


@patch("coros_mcp.api.workouts.reschedule_workout")
@pytest.mark.asyncio
async def test_reschedule_workout(mock_api, app_with_workouts):
    mock_api.return_value = {
        "success": True,
        "message": "Workout 'Easy Run' moved to 2026-02-16",
    }

    result = await app_with_workouts.call_tool(
        "reschedule_workout",
        {"workout_id": "5", "new_date": "2026-02-16"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["success"] is True
    assert "2026-02-16" in data["message"]


@patch("coros_mcp.api.workouts.reschedule_workout")
@pytest.mark.asyncio
async def test_reschedule_workout_not_found(mock_api, app_with_workouts):
    mock_api.return_value = {
        "success": False,
        "error": "Workout nonexistent not found in schedule",
    }

    result = await app_with_workouts.call_tool(
        "reschedule_workout",
        {"workout_id": "nonexistent", "new_date": "2026-02-16"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert "not found" in data.get("error", "")


def test_workout_tools_registered(app_with_workouts):
    tools = app_with_workouts._tool_manager._tools
    tool_names = list(tools.keys())

    expected = ["create_workout", "estimate_workout_load", "reschedule_workout"]
    for name in expected:
        assert name in tool_names, f"Tool {name} not registered"
