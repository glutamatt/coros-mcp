"""
Tests for COROS MCP profile tool.

Tools are thin wrappers — detailed formatting tests are in tests/api/.
"""
import json
import pytest
from unittest.mock import patch
from mcp.server.fastmcp import FastMCP

from coros_mcp import profile
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_profile():
    app = FastMCP("Test COROS Profile")
    app = profile.register_tools(app)
    return app


@patch("coros_mcp.api.profile.get_athlete_profile")
@pytest.mark.asyncio
async def test_get_athlete_profile(mock_api, app_with_profile):
    mock_api.return_value = {
        "identity": {"nickname": "TestUser", "birthday": "1990-01-01"},
        "biometrics": {"height_cm": 180, "weight_kg": 75},
        "thresholds": {"max_hr": 190, "resting_hr": 52, "lthr": 165, "ftp": 250},
        "hr_zones": [{"zone": 1, "name": "Recovery", "range": "<114 bpm"}],
        "pace_zones": [{"zone": 1, "name": "Easy", "range": "slower than 6:40/km"}],
    }

    result = await app_with_profile.call_tool("get_athlete_profile", {})
    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["identity"]["nickname"] == "TestUser"
    assert data["biometrics"]["height_cm"] == 180
    assert data["thresholds"]["max_hr"] == 190
    assert len(data["hr_zones"]) == 1
    assert len(data["pace_zones"]) == 1


def test_profile_tools_registered(app_with_profile):
    tools = app_with_profile._tool_manager._tools
    tool_names = list(tools.keys())
    assert "get_athlete_profile" in tool_names
