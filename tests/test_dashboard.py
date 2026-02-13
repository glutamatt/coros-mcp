"""
Tests for COROS MCP dashboard tools.

Tools are thin wrappers — detailed formatting tests are in tests/api/.
"""
import json
import pytest
from unittest.mock import patch
from mcp.server.fastmcp import FastMCP

from coros_mcp import dashboard
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_dashboard():
    app = FastMCP("Test COROS Dashboard")
    app = dashboard.register_tools(app)
    return app


@patch("coros_mcp.api.status.get_fitness_status")
@pytest.mark.asyncio
async def test_get_fitness_summary(mock_api, app_with_dashboard):
    mock_api.return_value = {
        "recovery": {"percent": 85, "state": 2},
        "fitness_scores": {"aerobic_endurance": 72},
        "stamina": {"level": 75},
        "training_load": {"ati": 85, "cti": 72},
        "current_week": {"distance": "25.0 km", "training_load": 350},
    }

    result = await app_with_dashboard.call_tool("get_fitness_summary", {})
    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["recovery"]["percent"] == 85
    assert data["fitness_scores"]["aerobic_endurance"] == 72
    assert data["stamina"]["level"] == 75
    assert data["training_load"]["ati"] == 85


@patch("coros_mcp.api.status.get_race_predictions")
@pytest.mark.asyncio
async def test_get_race_predictions(mock_api, app_with_dashboard):
    mock_api.return_value = {
        "predictions": [
            {"distance": "5K", "predicted_time": "27m06s", "pace_per_km": "5:25/km"},
            {"distance": "Marathon", "predicted_time": "4h45m33s", "pace_per_km": "6:46/km"},
        ],
    }

    result = await app_with_dashboard.call_tool("get_race_predictions", {})
    text = get_tool_result_text(result)
    data = json.loads(text)

    assert len(data["predictions"]) == 2
    assert data["predictions"][0]["distance"] == "5K"


@patch("coros_mcp.api.status.get_hrv_trend")
@pytest.mark.asyncio
async def test_get_hrv_trend(mock_api, app_with_dashboard):
    mock_api.return_value = {
        "values": [
            {"date": "2026-02-09", "avg_hrv": 52, "baseline": 48},
            {"date": "2026-02-10", "avg_hrv": 55, "baseline": 49},
        ],
        "total_days": 2,
        "recent_7d_avg": 53.5,
        "current_baseline": 49,
    }

    result = await app_with_dashboard.call_tool("get_hrv_trend", {})
    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["total_days"] == 2
    assert data["recent_7d_avg"] == 53.5


@patch("coros_mcp.api.status.get_hrv_trend")
@pytest.mark.asyncio
async def test_get_hrv_trend_empty(mock_api, app_with_dashboard):
    mock_api.return_value = {"message": "No HRV data available.", "values": []}

    result = await app_with_dashboard.call_tool("get_hrv_trend", {})
    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["values"] == []
    assert "No HRV data" in data["message"]


@patch("coros_mcp.api.status.get_personal_records")
@pytest.mark.asyncio
async def test_get_personal_records(mock_api, app_with_dashboard):
    mock_api.return_value = {
        "week": [{"record": "5km", "date": "2026-02-10", "sport": "Run"}],
        "all_time": [{"record": "10km", "date": "2025-06-01", "sport": "Run"}],
    }

    result = await app_with_dashboard.call_tool("get_personal_records", {})
    text = get_tool_result_text(result)
    data = json.loads(text)

    assert "week" in data
    assert "all_time" in data
    assert data["week"][0]["sport"] == "Run"


def test_dashboard_tools_registered(app_with_dashboard):
    tools = app_with_dashboard._tool_manager._tools
    tool_names = list(tools.keys())

    expected = ["get_fitness_summary", "get_race_predictions", "get_hrv_trend", "get_personal_records"]
    for name in expected:
        assert name in tool_names, f"Tool {name} not registered"
