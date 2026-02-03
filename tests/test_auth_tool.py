"""
Tests for COROS MCP authentication tools.

Tests login, session management, and logout functionality.
"""
import json
import pytest
from unittest.mock import patch, Mock, AsyncMock
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from coros_mcp import auth_tool
from coros_mcp.coros_client import UserInfo
from tests.conftest import get_tool_result_text


@pytest.fixture
def app_with_auth():
    """Create FastMCP app with auth tools registered."""
    app = FastMCP("Test COROS Auth")
    app = auth_tool.register_tools(app)
    return app


@pytest.mark.asyncio
async def test_get_user_name(app_with_auth, mock_coros_client):
    """Test get_user_name tool returns user info."""

    async def mock_get_client(ctx):
        return mock_coros_client

    with patch("coros_mcp.auth_tool.get_client", mock_get_client):
        result = await app_with_auth.call_tool("get_user_name", {})

    text = get_tool_result_text(result)
    assert "TestUser" in text
    assert "123456" in text
    assert "test@test.com" in text


@pytest.mark.asyncio
async def test_get_user_name_returns_json(app_with_auth, mock_coros_client):
    """Test get_user_name tool returns valid JSON."""

    async def mock_get_client(ctx):
        return mock_coros_client

    with patch("coros_mcp.auth_tool.get_client", mock_get_client):
        result = await app_with_auth.call_tool("get_user_name", {})

    # Parse the result as JSON
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
    assert "COROS Training Hub" in text
    assert "coros_login_tool" in text
    assert "get_activities" in text


@pytest.mark.asyncio
async def test_get_available_features_returns_json(app_with_auth):
    """Test get_available_features tool returns valid JSON."""
    result = await app_with_auth.call_tool("get_available_features", {})

    text = get_tool_result_text(result)
    data = json.loads(text)
    assert data["platform"] == "COROS Training Hub"
    assert "auth" in data
    assert "user" in data
    assert "activities" in data
    assert "notes" in data


@pytest.mark.asyncio
async def test_coros_login_success(app_with_auth):
    """Test successful login stores tokens."""
    mock_result = Mock()
    mock_result.success = True
    mock_result.tokens = json.dumps({"access_token": "test_token"})
    mock_result.to_dict = Mock(return_value={
        "success": True,
        "message": "Login successful",
        "user": {"nickname": "TestUser"},
    })

    with patch("coros_mcp.auth_tool.coros_login", return_value=mock_result) as mock_login:
        with patch("coros_mcp.auth_tool.set_session_tokens", new_callable=AsyncMock) as mock_set_tokens:
            result = await app_with_auth.call_tool(
                "coros_login_tool",
                {"email": "test@test.com", "password": "password123"}
            )

    mock_login.assert_called_once_with("test@test.com", "password123")
    mock_set_tokens.assert_called_once()
    text = get_tool_result_text(result)
    assert "success" in text.lower() or "True" in text


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

    with patch("coros_mcp.auth_tool.coros_login", return_value=mock_result) as mock_login:
        with patch("coros_mcp.auth_tool.set_session_tokens", new_callable=AsyncMock) as mock_set_tokens:
            result = await app_with_auth.call_tool(
                "coros_login_tool",
                {"email": "test@test.com", "password": "wrongpassword"}
            )

    mock_login.assert_called_once()
    mock_set_tokens.assert_not_called()
    text = get_tool_result_text(result)
    assert "error" in text.lower() or "false" in text.lower()


@pytest.mark.asyncio
async def test_set_coros_session_success(app_with_auth):
    """Test set_coros_session restores session tokens."""
    # Use a simple token string that won't be parsed as JSON by FastMCP
    tokens = "token_abc123_xyz789"

    with patch("coros_mcp.auth_tool.set_session_tokens", new_callable=AsyncMock) as mock_set_tokens:
        result = await app_with_auth.call_tool(
            "set_coros_session",
            {"coros_tokens": tokens}
        )

    mock_set_tokens.assert_called_once()
    text = get_tool_result_text(result)
    assert "success" in text.lower() or "restored" in text.lower()


@pytest.mark.asyncio
async def test_set_coros_session_failure(app_with_auth):
    """Test set_coros_session handles errors."""
    tokens = "invalid_json"

    with patch("coros_mcp.auth_tool.set_session_tokens", new_callable=AsyncMock) as mock_set_tokens:
        mock_set_tokens.side_effect = Exception("Invalid token format")
        result = await app_with_auth.call_tool(
            "set_coros_session",
            {"coros_tokens": tokens}
        )

    text = get_tool_result_text(result)
    assert "error" in text.lower() or "false" in text.lower()


@pytest.mark.asyncio
async def test_coros_logout(app_with_auth):
    """Test coros_logout clears session tokens."""
    with patch("coros_mcp.auth_tool.clear_session_tokens", new_callable=AsyncMock) as mock_clear_tokens:
        result = await app_with_auth.call_tool("coros_logout", {})

    mock_clear_tokens.assert_called_once()
    text = get_tool_result_text(result)
    assert "success" in text.lower() or "logged out" in text.lower()


@pytest.mark.asyncio
async def test_get_user_name_not_logged_in(app_with_auth):
    """Test get_user_name raises error when not logged in."""

    async def mock_get_client_no_session(ctx):
        raise ValueError("No COROS session. Call coros_login() first.")

    with patch("coros_mcp.auth_tool.get_client", mock_get_client_no_session):
        # FastMCP wraps tool errors in ToolError
        with pytest.raises(ToolError) as exc_info:
            await app_with_auth.call_tool("get_user_name", {})

    assert "session" in str(exc_info.value).lower()


# Test tool registration
def test_auth_tools_registered(app_with_auth):
    """Test that all auth tools are registered."""
    # Get registered tools by checking app's tools
    # FastMCP stores tools internally
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
