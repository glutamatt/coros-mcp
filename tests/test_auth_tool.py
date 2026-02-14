"""
Tests for COROS MCP authentication tools.

Tests login, session management, and logout functionality.
"""
import json
import pytest
from unittest.mock import patch, Mock
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from coros_mcp import auth_tool
from coros_mcp.sdk.client import UserInfo
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_auth():
    """Create FastMCP app with auth tools registered."""
    app = FastMCP("Test COROS Auth")
    app = auth_tool.register_tools(app)
    return app


@patch("coros_mcp.auth_tool.sdk_auth")
@pytest.mark.asyncio
async def test_get_user_name(mock_sdk_auth, app_with_auth, mock_sdk_client):
    """Test get_user_name tool returns user info."""
    mock_sdk_auth.get_account.return_value = UserInfo(
        user_id="123456", nickname="TestUser", email="test@test.com",
        head_pic="", country_code="US", birthday=19900101,
    )

    result = await app_with_auth.call_tool("get_user_name", {})
    text = get_tool_result_text(result)
    data = json.loads(text)

    assert data["name"] == "TestUser"
    assert data["user_id"] == "123456"
    assert data["email"] == "test@test.com"


@pytest.mark.asyncio
async def test_get_available_features(app_with_auth):
    """Test get_available_features tool returns feature list."""
    result = await app_with_auth.call_tool("get_available_features", {})

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["platform"] == "COROS Training Hub"
    assert "auth" in data
    assert "activities" in data
    assert "plan_builder" in data  # New in Layer 4


@pytest.mark.asyncio
async def test_coros_login_success(app_with_auth):
    """Test successful login stores tokens."""
    mock_result = Mock()
    mock_result.success = True
    mock_result.tokens = json.dumps({"access_token": "test_token"})
    mock_result.to_dict = Mock(return_value={
        "success": True,
        "message": "Login successful",
    })

    with patch("coros_mcp.auth_tool.coros_login", return_value=mock_result) as mock_login:
        with patch("coros_mcp.auth_tool.set_session_tokens") as mock_set_tokens:
            result = await app_with_auth.call_tool(
                "coros_login_tool",
                {"email": "test@test.com", "password": "password123"}
            )

    mock_login.assert_called_once_with("test@test.com", "password123")
    mock_set_tokens.assert_called_once()


@pytest.mark.asyncio
async def test_coros_login_failure(app_with_auth):
    """Test failed login does not store tokens."""
    mock_result = Mock()
    mock_result.success = False
    mock_result.tokens = None
    mock_result.to_dict = Mock(return_value={
        "success": False,
        "error": "Invalid credentials",
    })

    with patch("coros_mcp.auth_tool.coros_login", return_value=mock_result):
        with patch("coros_mcp.auth_tool.set_session_tokens") as mock_set_tokens:
            await app_with_auth.call_tool(
                "coros_login_tool",
                {"email": "test@test.com", "password": "wrong"}
            )

    mock_set_tokens.assert_not_called()


@pytest.mark.asyncio
async def test_coros_logout(app_with_auth):
    """Test coros_logout clears session tokens."""
    with patch("coros_mcp.auth_tool.clear_session_tokens") as mock_clear:
        result = await app_with_auth.call_tool("coros_logout", {})

    mock_clear.assert_called_once()
    text = get_tool_result_text(result)
    assert "logged out" in text.lower()


@pytest.mark.asyncio
async def test_get_user_name_not_logged_in(app_with_auth, mock_get_client):
    """Test get_user_name raises error when not logged in."""
    mock_get_client.side_effect = ValueError("No COROS session. Call coros_login() first.")

    with pytest.raises(ToolError) as exc_info:
        await app_with_auth.call_tool("get_user_name", {})

    assert "session" in str(exc_info.value).lower()


def test_auth_tools_registered(app_with_auth):
    """Test that all auth tools are registered."""
    tools = app_with_auth._tool_manager._tools
    tool_names = list(tools.keys())

    expected_tools = [
        "coros_login_tool",
        "set_coros_session",
        "coros_logout",
        "get_user_name",
        "get_available_features",
    ]

    for tool_name in expected_tools:
        assert tool_name in tool_names, f"Tool {tool_name} not registered"
