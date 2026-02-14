"""
Tests for COROS MCP analysis tools.

Tools are thin wrappers — detailed formatting tests are in tests/api/.
"""
import json
import pytest
from unittest.mock import patch
from mcp.server.fastmcp import FastMCP

from coros_mcp import analysis
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_analysis():
    app = FastMCP("Test COROS Analysis")
    app = analysis.register_tools(app)
    return app


@patch("coros_mcp.api.status.get_training_load")
@pytest.mark.asyncio
async def test_get_training_load_analysis(mock_api, app_with_analysis):
    mock_api.return_value = {
        "recent_days": [{"date": "2026-02-10", "training_load": 85, "vo2max": 52}],
        "weekly_load": [{"week_start": "2026-02-03", "training_load": 350}],
        "periodization": [{"week_start": "2026-02-03", "stage": 2}],
    }

    result = await app_with_analysis.call_tool("get_training_load_analysis", {})
    text = get_tool_result_text(result)
    data = json.loads(text)

    assert len(data["recent_days"]) == 1
    assert data["recent_days"][0]["training_load"] == 85
    assert len(data["weekly_load"]) == 1


@patch("coros_mcp.api.status.get_sport_stats")
@pytest.mark.asyncio
async def test_get_sport_statistics(mock_api, app_with_analysis):
    mock_api.return_value = {
        "sport_breakdown": [
            {"sport": "Run", "count": 5, "distance": "45.0 km", "training_load": 350},
            {"sport": "Strength", "count": 2, "distance": "0.0 km", "training_load": 80},
        ],
        "weekly_intensity": [{"low_pct": 60, "medium_pct": 25, "high_pct": 15}],
    }

    result = await app_with_analysis.call_tool("get_sport_statistics", {})
    text = get_tool_result_text(result)
    data = json.loads(text)

    assert len(data["sport_breakdown"]) == 2
    assert data["sport_breakdown"][0]["sport"] == "Run"


def test_analysis_tools_registered(app_with_analysis):
    tools = app_with_analysis._tool_manager._tools
    tool_names = list(tools.keys())

    expected = ["get_training_load_analysis", "get_sport_statistics"]
    for name in expected:
        assert name in tool_names, f"Tool {name} not registered"
