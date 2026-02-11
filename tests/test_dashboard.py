"""
Tests for COROS MCP dashboard tools.
"""

import json
import pytest
from mcp.server.fastmcp import FastMCP

from coros_mcp import dashboard
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_dashboard():
    app = FastMCP("Test COROS Dashboard")
    app = dashboard.register_tools(app)
    return app


@pytest.mark.asyncio
async def test_get_fitness_summary(app_with_dashboard, mock_coros_client):
    result = await app_with_dashboard.call_tool("get_fitness_summary", {})

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["recovery"]["recovery_percent"] == 85
    assert data["fitness_scores"]["aerobic_endurance"] == 72
    assert data["stamina"]["level"] == 75
    assert data["training_load"]["ati"] == 85
    assert data["current_week"]["distance_record"] == 25000


@pytest.mark.asyncio
async def test_get_fitness_summary_includes_hrv(app_with_dashboard, mock_coros_client):
    result = await app_with_dashboard.call_tool("get_fitness_summary", {})

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert "hrv" in data
    assert len(data["hrv"]["recent_values"]) == 3
    assert data["hrv"]["recent_values"][0]["date"] == "2026-02-09"


@pytest.mark.asyncio
async def test_get_hrv_trend(app_with_dashboard, mock_coros_client):
    result = await app_with_dashboard.call_tool("get_hrv_trend", {})

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["total_days"] == 3
    assert len(data["values"]) == 3
    assert data["values"][0]["avg_hrv"] == 52
    assert "recent_7d_avg" in data


@pytest.mark.asyncio
async def test_get_hrv_trend_empty(app_with_dashboard, mock_coros_client):
    mock_coros_client.get_dashboard.return_value = {
        "summaryInfo": {"sleepHrvData": {"sleepHrvList": []}}
    }

    result = await app_with_dashboard.call_tool("get_hrv_trend", {})

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["values"] == []
    assert "No HRV data" in data["message"]


@pytest.mark.asyncio
async def test_get_personal_records(app_with_dashboard, mock_coros_client):
    result = await app_with_dashboard.call_tool("get_personal_records", {})

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert "week" in data
    assert "all_time" in data
    assert data["week"][0]["sport"] == "Run"
    assert data["week"][0]["date"] == "2026-02-10"


def test_dashboard_tools_registered(app_with_dashboard):
    tools = app_with_dashboard._tool_manager._tools
    tool_names = list(tools.keys())

    expected = ["get_fitness_summary", "get_hrv_trend", "get_personal_records"]
    for name in expected:
        assert name in tool_names, f"Tool {name} not registered"
