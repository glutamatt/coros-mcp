"""
Tests for COROS MCP workout builder tools.
"""

import json
import pytest
from mcp.server.fastmcp import FastMCP

from coros_mcp import workouts
from coros_mcp.workouts import _build_exercises
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_workouts():
    app = FastMCP("Test COROS Workouts")
    app = workouts.register_tools(app)
    return app


# ── Exercise model building tests ─────────────────────────────────────


class TestBuildExercises:
    def test_simple_workout(self):
        exercises = [{"type": "warmup", "duration_minutes": 30}]
        result, is_simple = _build_exercises(exercises)
        assert is_simple is True
        assert len(result) == 1
        assert result[0]["exerciseType"] == 1  # warmup
        assert result[0]["targetValue"] == 1800  # 30 * 60

    def test_structured_workout(self):
        exercises = [
            {"type": "warmup", "duration_minutes": 15},
            {"type": "cooldown", "duration_minutes": 10},
        ]
        result, is_simple = _build_exercises(exercises)
        assert is_simple is False
        assert len(result) == 2

    def test_distance_exercise_km(self):
        exercises = [{"type": "interval", "distance_km": 1.0}]
        result, _ = _build_exercises(exercises)
        assert result[0]["targetType"] == 5  # Distance
        assert result[0]["targetValue"] == 1000  # 1km in meters
        assert result[0]["targetDisplayUnit"] == 2  # Kilometers

    def test_distance_exercise_meters(self):
        exercises = [{"type": "interval", "distance_m": 400}]
        result, _ = _build_exercises(exercises)
        assert result[0]["targetType"] == 5  # Distance
        assert result[0]["targetValue"] == 400
        assert result[0]["targetDisplayUnit"] == 1  # Meters

    def test_repeat_group(self):
        exercises = [
            {"type": "warmup", "duration_minutes": 10},
            {"type": "interval", "distance_m": 800, "repeats": 6, "rest_seconds": 90},
            {"type": "cooldown", "duration_minutes": 10},
        ]
        result, is_simple = _build_exercises(exercises)
        assert is_simple is False

        # warmup + group + work + recovery + cooldown = 5
        assert len(result) == 5

        # Check group
        group = result[1]
        assert group["exerciseType"] == 0  # Group
        assert group["isGroup"] is True
        assert group["sets"] == 6
        assert group["restValue"] == 90

        # Check work step references group
        work = result[2]
        assert work["exerciseType"] == 2  # Interval
        assert work["groupId"] == group["sortNo"]

        # Check recovery step
        recovery = result[3]
        assert recovery["exerciseType"] == 4  # Recovery
        assert recovery["groupId"] == group["sortNo"]
        assert recovery["targetValue"] == 90

    def test_repeat_no_rest(self):
        exercises = [
            {"type": "interval", "distance_m": 400, "repeats": 4},
        ]
        result, _ = _build_exercises(exercises)

        group = result[0]
        assert group["restType"] == 3  # No rest
        assert group["restValue"] == 0

        # No recovery step created (only group + work)
        assert len(result) == 2


# ── Tool tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_workout(app_with_workouts, mock_coros_client):
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
    assert data["date"] == "2026-02-15"
    assert data["estimated_load"] == 85

    # Verify calculate was called
    mock_coros_client.calculate_workout.assert_called_once()

    # Verify schedule update was called
    mock_coros_client.update_training_schedule.assert_called_once()


@pytest.mark.asyncio
async def test_create_workout_invalid_sport(app_with_workouts, mock_coros_client):
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
    assert "error" in data
    assert "surfing" in data["error"]


@pytest.mark.asyncio
async def test_estimate_workout_load(app_with_workouts, mock_coros_client):
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
    mock_coros_client.estimate_workout.assert_called_once()


@pytest.mark.asyncio
async def test_reschedule_workout(app_with_workouts, mock_coros_client):
    result = await app_with_workouts.call_tool(
        "reschedule_workout",
        {
            "workout_id": "prog1",
            "new_date": "2026-02-16",
            "plan_version": 5,
        },
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["success"] is True
    assert "2026-02-16" in data["message"]


@pytest.mark.asyncio
async def test_reschedule_workout_not_found(app_with_workouts, mock_coros_client):
    result = await app_with_workouts.call_tool(
        "reschedule_workout",
        {
            "workout_id": "nonexistent",
            "new_date": "2026-02-16",
            "plan_version": 5,
        },
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert "error" in data
    assert "not found" in data["error"]


def test_workout_tools_registered(app_with_workouts):
    tools = app_with_workouts._tool_manager._tools
    tool_names = list(tools.keys())

    expected = ["create_workout", "estimate_workout_load", "reschedule_workout"]
    for name in expected:
        assert name in tool_names, f"Tool {name} not registered"
