"""
Tests for COROS MCP workout builder tools.
"""

import json
import pytest
from mcp.server.fastmcp import FastMCP

from coros_mcp import workouts
from coros_mcp.workouts import _build_exercises, _group_defaults, _step_defaults
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
        assert result[0]["id"] == 1
        assert result[0]["sortNo"] == 1
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
        assert result[0]["id"] == 1
        assert result[1]["id"] == 2

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

        # Check group: id=2, sortNo=2 (sequential), sportType=0
        group = result[1]
        assert group["id"] == 2
        assert group["sortNo"] == 2  # Sequential (not id << 24)
        assert group["sportType"] == 0  # Groups have sportType 0
        assert group["exerciseType"] == 0  # Group
        assert group["isGroup"] is True
        assert group["sets"] == 6
        assert group["restValue"] == 90
        # Group targetType is empty string, targetValue is 0 (HAR pattern)
        assert group["targetType"] == ""
        assert group["targetValue"] == 0

        # Check work step references group's id, shares sortNo with group
        work = result[2]
        assert work["id"] == 3
        assert work["sortNo"] == 2  # Shares sortNo with its group
        assert work["exerciseType"] == 2  # Interval
        assert work["groupId"] == group["id"]  # References group's id

        # Check recovery step
        recovery = result[3]
        assert recovery["id"] == 4
        assert recovery["sortNo"] == 3
        assert recovery["exerciseType"] == 4  # Recovery
        assert recovery["groupId"] == group["id"]
        assert recovery["targetValue"] == 90

        # Check cooldown
        cooldown = result[4]
        assert cooldown["id"] == 5
        assert cooldown["sortNo"] == 4

    def test_repeat_no_rest(self):
        exercises = [
            {"type": "interval", "distance_m": 400, "repeats": 4},
        ]
        result, _ = _build_exercises(exercises)

        group = result[0]
        assert group["id"] == 1
        assert group["sortNo"] == 1  # Sequential (not id << 24)
        assert group["restType"] == 3  # No rest
        assert group["restValue"] == 0

        # No recovery step created (only group + work)
        assert len(result) == 2
        assert result[1]["groupId"] == 1  # References group id


class TestGroupDefaults:
    """Test that group exercises have the correct HAR-matching field set."""

    def test_group_has_correct_fields(self):
        group = _group_defaults(2, 33554432)
        # Fields that groups MUST have (from HAR)
        assert group["exerciseType"] == 0
        assert group["isGroup"] is True
        assert group["sportType"] == 0
        assert group["intensityMultiplier"] == 0  # Groups use 0, not 1000
        assert group["programId"] == ""
        assert group["originId"] == ""
        assert group["overview"] == ""
        # Fields that groups must NOT have (only steps have these)
        assert "hrType" not in group
        assert "userId" not in group
        assert "isIntensityPercent" not in group
        assert "targetDisplayUnit" not in group
        assert "groupId" not in group
        assert "equipment" not in group
        assert "part" not in group
        assert "createTimestamp" not in group
        assert "intensityDisplayUnit" not in group


class TestStepDefaults:
    """Test that step exercises have the correct HAR-matching field set."""

    def test_step_has_correct_fields(self):
        step = _step_defaults(1, 1, 1, sport_type=1)
        # Fields that steps MUST have (from HAR)
        assert step["equipment"] == [1]
        assert step["part"] == [0]
        assert step["intensityDisplayUnit"] == 0  # Integer 0 (HAR pattern)
        assert step["intensityMultiplier"] == 0   # 0 (not 1000, which is pace-specific)
        # Template metadata for exercise type 1 (warmup)
        assert step["originId"] == "425895398452936705"
        assert step["overview"] == "sid_run_warm_up_dist"
        assert step["createTimestamp"] == 1586584068
        assert step["name"] == "T1120"
        assert step["hrType"] == 0
        assert step["userId"] == 0
        assert step["isIntensityPercent"] is False
        assert step["groupId"] == ""
        # Fields that steps must NOT have (only groups have these)
        assert "programId" not in step


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

    # Verify calculate was called with zeroed identity (HAR pattern for new workouts)
    calc_args = mock_coros_client.calculate_workout.call_args[0][0]
    assert "sportType" in calc_args  # flat program, not {entity, program}
    assert calc_args["idInPlan"] == "0"  # STRING "0" for calculate
    assert calc_args["id"] == "0"
    assert calc_args["userId"] == "0"
    assert calc_args["authorId"] == "0"
    assert calc_args["access"] == 1
    assert all("id" in ex for ex in calc_args["exercises"])

    # Verify schedule update has real idInPlan (integer)
    update_args = mock_coros_client.update_training_schedule.call_args[0][0]
    # versionObjects for new workouts: just id + status (no planId/planProgramId)
    assert update_args["versionObjects"][0]["id"] == 11  # integer idInPlan
    assert update_args["versionObjects"][0]["status"] == 1  # 1 = new
    assert update_args["entities"][0]["idInPlan"] == 11  # integer


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

    # Verify estimate payload structure (lean, no userId/authorId — HAR pattern)
    est_args = mock_coros_client.estimate_workout.call_args[0][0]
    assert est_args["entity"]["idInPlan"] == 11  # int
    assert est_args["program"]["idInPlan"] == 11  # int
    assert est_args["program"]["exerciseNum"] == ""  # empty string for estimate
    assert est_args["program"]["access"] == 1
    assert est_args["program"]["pbVersion"] == 2
    # Estimate has NO userId, authorId, cardType (lean payload)
    assert "userId" not in est_args["program"]
    assert "authorId" not in est_args["program"]
    assert "cardType" not in est_args["program"]


@pytest.mark.asyncio
async def test_reschedule_workout(app_with_workouts, mock_coros_client):
    result = await app_with_workouts.call_tool(
        "reschedule_workout",
        {
            "workout_id": "5",
            "new_date": "2026-02-16",
        },
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["success"] is True
    assert "2026-02-16" in data["message"]

    # Verify versionObjects has planId and planProgramId
    call_args = mock_coros_client.update_training_schedule.call_args
    payload = call_args[0][0]
    vo = payload["versionObjects"][0]
    assert vo["id"] == "5"
    assert vo["planProgramId"] == "5"
    assert vo["planId"] == "460904915775176706"
    assert vo["status"] == 2  # status 2 = move/update


@pytest.mark.asyncio
async def test_reschedule_workout_not_found(app_with_workouts, mock_coros_client):
    result = await app_with_workouts.call_tool(
        "reschedule_workout",
        {
            "workout_id": "nonexistent",
            "new_date": "2026-02-16",
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
