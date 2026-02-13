"""
Tests for COROS MCP activity tools.

Tools are thin wrappers — detailed formatting tests are in tests/api/.
These tests verify the tool → api delegation and JSON serialization.
"""
import json
import pytest
from unittest.mock import patch
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from coros_mcp import activities
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_activities():
    """Create FastMCP app with activity tools registered."""
    app = FastMCP("Test COROS Activities")
    app = activities.register_tools(app)
    return app


@patch("coros_mcp.api.activities.get_activities")
@pytest.mark.asyncio
async def test_get_activities(mock_api, app_with_activities):
    mock_api.return_value = {
        "count": 2,
        "total_pages": 1,
        "current_page": 1,
        "activities": [
            {"id": "abc123", "name": "Morning Run", "sport": "Run", "distance": "10.0 km"},
            {"id": "def456", "name": "Easy Run", "sport": "Run", "distance": "5.0 km"},
        ],
    }

    result = await app_with_activities.call_tool("get_activities", {})
    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["count"] == 2
    assert len(data["activities"]) == 2
    assert data["activities"][0]["name"] == "Morning Run"
    mock_api.assert_called_once()


@patch("coros_mcp.api.activities.get_activities")
@pytest.mark.asyncio
async def test_get_activities_with_date_filter(mock_api, app_with_activities):
    mock_api.return_value = {"count": 0, "activities": []}

    await app_with_activities.call_tool(
        "get_activities",
        {"start_date": "2026-02-09", "end_date": "2026-02-15"},
    )

    args = mock_api.call_args
    assert args[0][1] == "2026-02-09"  # start_date
    assert args[0][2] == "2026-02-15"  # end_date


@patch("coros_mcp.api.activities.get_activities")
@pytest.mark.asyncio
async def test_get_activities_with_pagination(mock_api, app_with_activities):
    mock_api.return_value = {"count": 0, "activities": []}

    await app_with_activities.call_tool(
        "get_activities",
        {"page": 2, "size": 10},
    )

    args = mock_api.call_args
    assert args[0][3] == 2   # page
    assert args[0][4] == 10  # size


@patch("coros_mcp.api.activities.get_activity_detail")
@pytest.mark.asyncio
async def test_get_activity_details(mock_api, app_with_activities):
    mock_api.return_value = {
        "activity_id": "abc123",
        "name": "Tempo Run",
        "sport": "Run",
        "distance": "10.0 km",
        "avg_pace": "5:55/km",
        "avg_hr": 155,
        "training_load": 95,
        "laps": [{"lap": 1, "distance": "5.0 km"}],
        "hr_zones": [{"zone": 1, "range": "100-130 bpm"}],
        "weather": {"temperature_c": 12},
    }

    result = await app_with_activities.call_tool(
        "get_activity_details",
        {"activity_id": "abc123"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["activity_id"] == "abc123"
    assert data["name"] == "Tempo Run"
    assert data["distance"] == "10.0 km"
    assert len(data["laps"]) == 1
    assert len(data["hr_zones"]) == 1
    assert data["weather"]["temperature_c"] == 12


@patch("coros_mcp.api.activities.get_download_url")
@pytest.mark.asyncio
async def test_get_activity_download_url(mock_api, app_with_activities):
    mock_api.return_value = {
        "activity_id": "abc123",
        "format": "fit",
        "download_url": "https://cdn.coros.com/activity.fit",
    }

    result = await app_with_activities.call_tool(
        "get_activity_download_url",
        {"activity_id": "abc123"},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["download_url"] == "https://cdn.coros.com/activity.fit"
    assert data["format"] == "fit"
    mock_api.assert_called_once()


@patch("coros_mcp.api.activities.get_download_url")
@pytest.mark.asyncio
async def test_get_activity_download_url_gpx(mock_api, app_with_activities):
    mock_api.return_value = {"activity_id": "abc123", "format": "gpx", "download_url": "url"}

    await app_with_activities.call_tool(
        "get_activity_download_url",
        {"activity_id": "abc123", "file_format": "gpx"},
    )

    # Verify format is passed through
    args = mock_api.call_args
    assert args[1]["format"] == "gpx"


@patch("coros_mcp.api.activities.get_activities_summary")
@pytest.mark.asyncio
async def test_get_activities_summary(mock_api, app_with_activities):
    mock_api.return_value = {
        "period": {"start_date": "2026-02-07", "end_date": "2026-02-14", "days": 7},
        "totals": {"activity_count": 3, "distance": "18.0 km", "training_load": 200},
        "by_sport": {"Run": {"count": 2}, "Strength": {"count": 1}},
    }

    result = await app_with_activities.call_tool(
        "get_activities_summary",
        {"days": 7},
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["totals"]["activity_count"] == 3
    assert "Run" in data["by_sport"]


@pytest.mark.asyncio
async def test_get_activities_not_logged_in(app_with_activities, mock_get_client):
    mock_get_client.side_effect = ValueError("No COROS session. Call coros_login() first.")

    with pytest.raises(ToolError) as exc_info:
        await app_with_activities.call_tool("get_activities", {})

    assert "session" in str(exc_info.value).lower()


def test_activity_tools_registered(app_with_activities):
    tools = app_with_activities._tool_manager._tools
    tool_names = list(tools.keys())

    expected_tools = [
        "get_activities",
        "get_activity_details",
        "get_activity_download_url",
        "get_activities_summary",
    ]

    for tool_name in expected_tools:
        assert tool_name in tool_names, f"Tool {tool_name} not registered"
