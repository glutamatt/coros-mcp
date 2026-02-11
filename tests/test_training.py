"""
Tests for COROS MCP training schedule tools.
"""

import json
import pytest
from mcp.server.fastmcp import FastMCP

from coros_mcp import training
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_training():
    app = FastMCP("Test COROS Training")
    app = training.register_tools(app)
    return app


@pytest.mark.asyncio
async def test_get_training_schedule(app_with_training, mock_coros_client):
    result = await app_with_training.call_tool(
        "get_training_schedule",
        {"start_date": "2026-02-09", "end_date": "2026-02-15"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["plan_name"] == "Test Plan"
    assert data["period"]["start_date"] == "2026-02-09"
    assert len(data["scheduled_workouts"]) == 1
    assert data["scheduled_workouts"][0]["name"] == "Easy Run"
    assert data["scheduled_workouts"][0]["status"] == "planned"

    assert len(data["unplanned_activities"]) == 1
    assert data["unplanned_activities"][0]["name"] == "Extra Run"

    assert len(data["week_stages"]) == 1


@pytest.mark.asyncio
async def test_get_training_schedule_defaults(app_with_training, mock_coros_client):
    """Test schedule defaults to current week when no dates provided."""
    result = await app_with_training.call_tool("get_training_schedule", {})

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert "period" in data
    assert data["period"]["start_date"] is not None


@pytest.mark.asyncio
async def test_get_plan_adherence(app_with_training, mock_coros_client):
    result = await app_with_training.call_tool(
        "get_plan_adherence",
        {"start_date": "2026-01-14", "end_date": "2026-02-11"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["today"]["actual_distance"] == 5000
    assert data["today"]["planned_distance"] == 8000
    assert data["today"]["actual_load"] == 45

    assert len(data["weekly"]) == 1
    assert data["weekly"][0]["actual_load"] == 300
    assert data["weekly"][0]["planned_load"] == 350

    assert len(data["daily"]) == 1
    assert data["daily"][0]["date"] == "2026-02-10"


@pytest.mark.asyncio
async def test_get_plan_adherence_defaults(app_with_training, mock_coros_client):
    """Test adherence defaults to last 4 weeks."""
    result = await app_with_training.call_tool("get_plan_adherence", {})

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert "period" in data


@pytest.mark.asyncio
async def test_delete_scheduled_workout(app_with_training, mock_coros_client):
    result = await app_with_training.call_tool(
        "delete_scheduled_workout",
        {"workout_id": "prog1", "plan_version": 5, "happen_day": 20260212},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["success"] is True

    # Verify the API was called correctly
    call_args = mock_coros_client.update_training_schedule.call_args
    payload = call_args[0][0]
    assert payload["pbVersion"] == 5
    assert payload["versionObjects"][0]["id"] == "prog1"
    assert payload["versionObjects"][0]["status"] == 2


@pytest.mark.asyncio
async def test_delete_scheduled_workout_failure(app_with_training, mock_coros_client):
    mock_coros_client.update_training_schedule.return_value = {
        "result": "1001", "message": "Plan version conflict"
    }

    result = await app_with_training.call_tool(
        "delete_scheduled_workout",
        {"workout_id": "prog1", "plan_version": 3, "happen_day": 20260212},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["success"] is False
    assert "conflict" in data["error"].lower()


def test_training_tools_registered(app_with_training):
    tools = app_with_training._tool_manager._tools
    tool_names = list(tools.keys())

    expected = ["get_training_schedule", "get_plan_adherence", "delete_scheduled_workout"]
    for name in expected:
        assert name in tool_names, f"Tool {name} not registered"
