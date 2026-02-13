"""
Tests for COROS MCP training plan tools.

Tools are thin wrappers — detailed plan logic tests are in tests/api/.
"""
import json
import pytest
from unittest.mock import patch
from mcp.server.fastmcp import FastMCP

from coros_mcp import plans
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_plans():
    app = FastMCP("Test COROS Plans")
    app = plans.register_tools(app)
    return app


@patch("coros_mcp.api.plans.list_plans")
@pytest.mark.asyncio
async def test_list_training_plans(mock_api, app_with_plans):
    mock_api.return_value = [
        {"id": "plan-1", "name": "Marathon Prep", "status": "draft", "weeks": 12, "workout_count": 36},
    ]

    result = await app_with_plans.call_tool("list_training_plans", {})
    text = get_tool_result_text(result)
    data = json.loads(text)

    assert len(data) == 1
    assert data[0]["name"] == "Marathon Prep"
    mock_api.assert_called_once()


@patch("coros_mcp.api.plans.get_plan")
@pytest.mark.asyncio
async def test_get_training_plan(mock_api, app_with_plans):
    mock_api.return_value = {
        "id": "plan-1",
        "name": "5K Training",
        "total_days": 28,
        "weeks": 4,
        "workouts": [
            {"id": "1", "name": "Easy Run", "day": 0, "sport": "Run"},
            {"id": "2", "name": "Intervals", "day": 3, "sport": "Run"},
        ],
    }

    result = await app_with_plans.call_tool(
        "get_training_plan",
        {"plan_id": "plan-1"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["name"] == "5K Training"
    assert len(data["workouts"]) == 2


@patch("coros_mcp.api.plans.create_plan")
@pytest.mark.asyncio
async def test_create_training_plan(mock_api, app_with_plans):
    mock_api.return_value = {
        "success": True,
        "plan_id": "new-plan-id",
        "name": "Easy start week",
        "total_days": 4,
        "weeks": 1,
        "workout_count": 2,
    }

    result = await app_with_plans.call_tool(
        "create_training_plan",
        {
            "name": "Week 1",
            "overview": "Easy start week",
            "workouts": [
                {"day": 0, "name": "Easy Run", "sport": "running",
                 "exercises": [{"type": "warmup", "duration_minutes": 30}]},
                {"day": 3, "name": "Recovery", "sport": "running",
                 "exercises": [{"type": "warmup", "duration_minutes": 20}]},
            ],
        },
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["success"] is True
    assert data["plan_id"] == "new-plan-id"
    assert data["workout_count"] == 2


@patch("coros_mcp.api.plans.add_workout_to_plan")
@pytest.mark.asyncio
async def test_add_workout_to_plan(mock_api, app_with_plans):
    mock_api.return_value = {
        "success": True,
        "plan_id": "plan-1",
        "workout_id": "prog-42",
        "day": 5,
        "name": "Tempo Run",
    }

    result = await app_with_plans.call_tool(
        "add_workout_to_plan",
        {
            "plan_id": "plan-1",
            "day": 5,
            "name": "Tempo Run",
            "sport": "running",
            "exercises": [
                {"type": "warmup", "duration_minutes": 10},
                {"type": "interval", "duration_minutes": 20},
                {"type": "cooldown", "duration_minutes": 10},
            ],
        },
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["success"] is True
    assert data["workout_id"] == "prog-42"
    assert data["day"] == 5
    mock_api.assert_called_once()
    # Verify args passed through correctly
    call_args = mock_api.call_args
    assert call_args[0][1] == "plan-1"  # plan_id
    assert call_args[0][2] == 5          # day
    assert call_args[0][3] == "Tempo Run"  # name
    assert call_args[0][4] == "running"   # sport
    assert len(call_args[0][5]) == 3      # exercises


@patch("coros_mcp.api.plans.add_workout_to_plan")
@pytest.mark.asyncio
async def test_add_workout_to_plan_error(mock_api, app_with_plans):
    mock_api.side_effect = ValueError("Plan not found")

    result = await app_with_plans.call_tool(
        "add_workout_to_plan",
        {
            "plan_id": "bad-id",
            "day": 0,
            "name": "Run",
            "sport": "running",
            "exercises": [{"type": "warmup", "duration_minutes": 10}],
        },
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["success"] is False
    assert "Plan not found" in data["error"]


@patch("coros_mcp.api.plans.activate_plan")
@pytest.mark.asyncio
async def test_activate_training_plan(mock_api, app_with_plans):
    mock_api.return_value = {
        "success": True,
        "plan_id": "plan-1",
        "start_date": "2026-03-01",
    }

    result = await app_with_plans.call_tool(
        "activate_training_plan",
        {"plan_id": "plan-1", "start_date": "2026-03-01"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["success"] is True
    assert data["start_date"] == "2026-03-01"


@patch("coros_mcp.api.plans.delete_plans")
@pytest.mark.asyncio
async def test_delete_training_plans(mock_api, app_with_plans):
    mock_api.return_value = {"success": True, "deleted": ["plan-1", "plan-2"]}

    result = await app_with_plans.call_tool(
        "delete_training_plans",
        {"plan_ids": ["plan-1", "plan-2"]},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["success"] is True
    assert data["deleted"] == ["plan-1", "plan-2"]


@patch("coros_mcp.api.plans.create_plan")
@pytest.mark.asyncio
async def test_create_training_plan_error(mock_api, app_with_plans):
    mock_api.side_effect = Exception("API timeout")

    result = await app_with_plans.call_tool(
        "create_training_plan",
        {
            "name": "Test",
            "overview": "Test",
            "workouts": [{"day": 0, "name": "Run", "sport": "running",
                         "exercises": [{"type": "warmup", "duration_minutes": 10}]}],
        },
    )

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["success"] is False
    assert "timeout" in data["error"].lower()


def test_plan_tools_registered(app_with_plans):
    tools = app_with_plans._tool_manager._tools
    tool_names = list(tools.keys())

    expected = [
        "list_training_plans",
        "get_training_plan",
        "create_training_plan",
        "add_workout_to_plan",
        "activate_training_plan",
        "delete_training_plans",
    ]
    for name in expected:
        assert name in tool_names, f"Tool {name} not registered"
