"""
Tests for COROS MCP profile tool.
"""

import json
import pytest
from mcp.server.fastmcp import FastMCP

from coros_mcp import profile
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_profile():
    app = FastMCP("Test COROS Profile")
    app = profile.register_tools(app)
    return app


@pytest.mark.asyncio
async def test_get_athlete_profile(app_with_profile, mock_coros_client):
    result = await app_with_profile.call_tool("get_athlete_profile", {})

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["identity"]["nickname"] == "TestUser"
    assert data["identity"]["birthday"] == "1990-01-01"

    assert data["biometrics"]["height_cm"] == 180
    assert data["biometrics"]["weight_kg"] == 75

    assert data["physiological"]["max_hr"] == 190
    assert data["physiological"]["resting_hr"] == 52
    assert data["physiological"]["lthr"] == 165
    assert data["physiological"]["ftp"] == 250

    assert "zones" in data
    assert "heart_rate" in data["zones"]
    assert "pace" in data["zones"]


@pytest.mark.asyncio
async def test_get_athlete_profile_with_run_scores(app_with_profile, mock_coros_client):
    result = await app_with_profile.call_tool("get_athlete_profile", {})

    text = get_tool_result_text(result)
    data = json.loads(text)

    assert "run_scores" in data
    assert data["run_scores"][0]["sport_type"] == 1
    assert data["run_scores"][0]["avg_pace"] == 320


@pytest.mark.asyncio
async def test_get_athlete_profile_no_zones(app_with_profile, mock_coros_client):
    mock_coros_client.get_account_full.return_value = {
        "userId": "123456",
        "nickname": "TestUser",
        "email": "test@test.com",
        "stature": 170,
        "weight": 65,
        "zoneData": {},
    }

    result = await app_with_profile.call_tool("get_athlete_profile", {})

    text = get_tool_result_text(result)
    data = json.loads(text)

    # zones dict should be absent when empty
    assert "zones" not in data


def test_profile_tools_registered(app_with_profile):
    tools = app_with_profile._tool_manager._tools
    tool_names = list(tools.keys())
    assert "get_athlete_profile" in tool_names
