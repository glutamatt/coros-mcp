"""
Tests for COROS MCP activity tools.
"""
import json
import pytest
from datetime import datetime
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from coros_mcp import activities
from coros_mcp.coros_client import FileType
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_activities():
    """Create FastMCP app with activity tools registered."""
    app = FastMCP("Test COROS Activities")
    app = activities.register_tools(app)
    return app


@pytest.mark.asyncio
async def test_get_activities_empty(app_with_activities, mock_coros_client):
    """Test get_activities returns empty list when no activities."""
    result = await app_with_activities.call_tool("get_activities", {})

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["count"] == 0
    assert data["activities"] == []


@pytest.mark.asyncio
async def test_get_activities_with_data(app_with_activities, mock_coros_client, sample_activities_list):
    """Test get_activities returns activity list."""
    mock_coros_client.get_activities_list.return_value = sample_activities_list

    result = await app_with_activities.call_tool("get_activities", {})

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["count"] == 2
    assert len(data["activities"]) == 2
    assert data["activities"][0]["name"] == "Morning Run"
    assert data["activities"][0]["id"] == "abc123"


@pytest.mark.asyncio
async def test_get_activities_with_date_filter(app_with_activities, mock_coros_client, sample_activities_list):
    """Test get_activities with date range filter."""
    mock_coros_client.get_activities_list.return_value = sample_activities_list

    result = await app_with_activities.call_tool(
        "get_activities",
        {"start_date": "2024-01-14", "end_date": "2024-01-15"}
    )

    call_args = mock_coros_client.get_activities_list.call_args
    assert call_args.kwargs["from_date"] == datetime.strptime("2024-01-14", "%Y-%m-%d").date()
    assert call_args.kwargs["to_date"] == datetime.strptime("2024-01-15", "%Y-%m-%d").date()


@pytest.mark.asyncio
async def test_get_activities_with_pagination(app_with_activities, mock_coros_client, sample_activities_list):
    """Test get_activities with pagination parameters."""
    mock_coros_client.get_activities_list.return_value = sample_activities_list

    result = await app_with_activities.call_tool(
        "get_activities",
        {"page": 2, "size": 10}
    )

    call_args = mock_coros_client.get_activities_list.call_args
    assert call_args.kwargs["page"] == 2
    assert call_args.kwargs["size"] == 10


@pytest.mark.asyncio
async def test_get_activities_size_limit(app_with_activities, mock_coros_client, sample_activities_list):
    """Test get_activities limits size to 50."""
    mock_coros_client.get_activities_list.return_value = sample_activities_list

    result = await app_with_activities.call_tool(
        "get_activities",
        {"size": 100}
    )

    call_args = mock_coros_client.get_activities_list.call_args
    assert call_args.kwargs["size"] == 50


@pytest.mark.asyncio
async def test_get_activity_details(app_with_activities, mock_coros_client, sample_activity_details):
    """Test get_activity_details returns comprehensive data."""
    mock_coros_client.get_activity_details.return_value = sample_activity_details

    result = await app_with_activities.call_tool(
        "get_activity_details",
        {"activity_id": "abc123"}
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["activity_id"] == "abc123"
    assert data["name"] == "Morning Run"
    assert data["distance_meters"] == 5000.0
    assert data["avg_heart_rate_bpm"] == 145
    assert data["max_heart_rate_bpm"] == 165


@pytest.mark.asyncio
async def test_get_activity_details_with_laps(app_with_activities, mock_coros_client, sample_activity_details):
    """Test get_activity_details includes lap data."""
    mock_coros_client.get_activity_details.return_value = sample_activity_details

    result = await app_with_activities.call_tool(
        "get_activity_details",
        {"activity_id": "abc123"}
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert "laps" in data
    assert len(data["laps"]) == 2
    assert data["laps"][0]["lap_index"] == 1
    assert data["laps"][0]["distance_meters"] == 1000


@pytest.mark.asyncio
async def test_get_activity_details_with_hr_zones(app_with_activities, mock_coros_client, sample_activity_details):
    """Test get_activity_details includes heart rate zones."""
    mock_coros_client.get_activity_details.return_value = sample_activity_details

    result = await app_with_activities.call_tool(
        "get_activity_details",
        {"activity_id": "abc123"}
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert "heart_rate_zones" in data
    assert len(data["heart_rate_zones"]) == 5


@pytest.mark.asyncio
async def test_get_activity_details_with_weather(app_with_activities, mock_coros_client, sample_activity_details):
    """Test get_activity_details includes weather data."""
    mock_coros_client.get_activity_details.return_value = sample_activity_details

    result = await app_with_activities.call_tool(
        "get_activity_details",
        {"activity_id": "abc123"}
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert "weather" in data
    assert data["weather"]["temperature_celsius"] == 15


@pytest.mark.asyncio
async def test_get_activity_download_url_default_format(app_with_activities, mock_coros_client):
    """Test get_activity_download_url with default FIT format."""
    mock_coros_client.get_activity_download_url.return_value = "https://example.com/activity.fit"

    result = await app_with_activities.call_tool(
        "get_activity_download_url",
        {"activity_id": "abc123"}
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["activity_id"] == "abc123"
    assert data["format"] == "fit"
    assert data["download_url"] == "https://example.com/activity.fit"

    call_args = mock_coros_client.get_activity_download_url.call_args
    assert call_args[0][1] == FileType.FIT


@pytest.mark.asyncio
async def test_get_activity_download_url_gpx_format(app_with_activities, mock_coros_client):
    """Test get_activity_download_url with GPX format."""
    mock_coros_client.get_activity_download_url.return_value = "https://example.com/activity.gpx"

    result = await app_with_activities.call_tool(
        "get_activity_download_url",
        {"activity_id": "abc123", "file_format": "gpx"}
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["format"] == "gpx"

    call_args = mock_coros_client.get_activity_download_url.call_args
    assert call_args[0][1] == FileType.GPX


@pytest.mark.asyncio
async def test_get_activity_download_url_tcx_format(app_with_activities, mock_coros_client):
    """Test get_activity_download_url with TCX format."""
    mock_coros_client.get_activity_download_url.return_value = "https://example.com/activity.tcx"

    result = await app_with_activities.call_tool(
        "get_activity_download_url",
        {"activity_id": "abc123", "file_format": "tcx"}
    )

    call_args = mock_coros_client.get_activity_download_url.call_args
    assert call_args[0][1] == FileType.TCX


@pytest.mark.asyncio
async def test_get_activities_summary(app_with_activities, mock_coros_client, sample_activities_list):
    """Test get_activities_summary returns aggregated stats."""
    mock_coros_client.get_activities_list.return_value = sample_activities_list

    result = await app_with_activities.call_tool(
        "get_activities_summary",
        {"days": 7}
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert "period" in data
    assert data["period"]["days"] == 7
    assert "totals" in data
    assert data["totals"]["activity_count"] == 2
    assert data["totals"]["total_distance_meters"] == 8000.0


@pytest.mark.asyncio
async def test_get_activities_summary_by_sport(app_with_activities, mock_coros_client, sample_activities_list):
    """Test get_activities_summary groups by sport type."""
    mock_coros_client.get_activities_list.return_value = sample_activities_list

    result = await app_with_activities.call_tool(
        "get_activities_summary",
        {"days": 7}
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert "by_sport" in data
    assert "Run" in data["by_sport"]
    assert data["by_sport"]["Run"]["count"] == 2


@pytest.mark.asyncio
async def test_get_activities_summary_days_limit(app_with_activities, mock_coros_client, sample_activities_list):
    """Test get_activities_summary limits days to 30."""
    mock_coros_client.get_activities_list.return_value = sample_activities_list

    result = await app_with_activities.call_tool(
        "get_activities_summary",
        {"days": 60}
    )

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["period"]["days"] == 30


@pytest.mark.asyncio
async def test_get_activities_not_logged_in(app_with_activities, mock_get_client):
    """Test get_activities raises error when not logged in."""
    mock_get_client.side_effect = ValueError("No COROS session. Call coros_login() first.")

    with pytest.raises(ToolError) as exc_info:
        await app_with_activities.call_tool("get_activities", {})

    assert "session" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_activity_details_api_error(app_with_activities, mock_coros_client):
    """Test get_activity_details handles API errors."""
    mock_coros_client.get_activity_details.side_effect = Exception("API Error")

    with pytest.raises(ToolError) as exc_info:
        await app_with_activities.call_tool(
            "get_activity_details",
            {"activity_id": "invalid_id"}
        )

    assert "error" in str(exc_info.value).lower()


def test_activity_tools_registered(app_with_activities):
    """Test that all activity tools are registered."""
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


def test_format_date():
    """Test _format_date helper function."""
    from coros_mcp.activities import _format_date

    assert _format_date(20240115) == "2024-01-15"
    assert _format_date(20231231) == "2023-12-31"
    assert _format_date(None) is None
    assert _format_date(0) is None


def test_get_sport_name():
    """Test _get_sport_name helper function."""
    from coros_mcp.activities import _get_sport_name

    assert _get_sport_name(1) == "Run"
    assert _get_sport_name(2) == "Indoor Run"
    assert _get_sport_name(3) == "Trail Run"
    assert _get_sport_name(6) == "Bike"
    assert _get_sport_name(9) == "Pool Swim"
    assert _get_sport_name(16) == "Strength"
    assert _get_sport_name(100) == "Other"
    assert _get_sport_name(999) == "Sport_999"
