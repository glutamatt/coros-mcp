"""
Tests for COROS MCP analysis tools.
"""

import json
import pytest
from mcp.server.fastmcp import FastMCP

from coros_mcp import analysis
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_analysis():
    app = FastMCP("Test COROS Analysis")
    app = analysis.register_tools(app)
    return app


@pytest.mark.asyncio
async def test_get_training_load_analysis(app_with_analysis, mock_coros_client):
    result = await app_with_analysis.call_tool("get_training_load_analysis", {})

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert "recent_days" in data
    assert len(data["recent_days"]) == 1
    assert data["recent_days"][0]["date"] == "2026-02-10"
    assert data["recent_days"][0]["training_load"] == 85
    assert data["recent_days"][0]["vo2max"] == 52

    assert "weekly_load" in data
    assert data["weekly_load"][0]["week_start"] == "2026-02-03"
    assert data["weekly_load"][0]["training_load"] == 350

    assert "rolling_7d_trend" in data
    assert data["rolling_7d_trend"][0]["vo2max"] == 52

    assert "periodization" in data
    assert data["periodization"][0]["stage"] == 2


@pytest.mark.asyncio
async def test_get_sport_statistics(app_with_analysis, mock_coros_client):
    result = await app_with_analysis.call_tool("get_sport_statistics", {})

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert "sport_breakdown" in data
    assert len(data["sport_breakdown"]) == 2
    assert data["sport_breakdown"][0]["sport"] == "Run"
    assert data["sport_breakdown"][0]["count"] == 5
    assert data["sport_breakdown"][0]["distance_display"] == "45.0 km"
    assert data["sport_breakdown"][1]["sport"] == "Strength"

    assert "weekly_intensity" in data
    assert data["weekly_intensity"][0]["low_pct"] == 60
    assert data["weekly_intensity"][0]["high_pct"] == 15


def test_analysis_tools_registered(app_with_analysis):
    tools = app_with_analysis._tool_manager._tools
    tool_names = list(tools.keys())

    expected = ["get_training_load_analysis", "get_sport_statistics"]
    for name in expected:
        assert name in tool_names, f"Tool {name} not registered"
