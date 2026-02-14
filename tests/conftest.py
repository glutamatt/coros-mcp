"""
Shared pytest fixtures for COROS MCP testing.
"""
import json
import pytest
from unittest.mock import Mock, patch

# Monkey-patch: production uses fastmcp.FastMCP, tests use mcp.server.fastmcp.
# Patch fastmcp.Context to match mcp.server.fastmcp.Context so tools work
# with the test FastMCP.
import fastmcp
from mcp.server.fastmcp import server as mcp_server
fastmcp.Context = mcp_server.Context

from mcp.server.fastmcp import FastMCP

from coros_mcp.sdk.client import UserInfo


def get_tool_result_text(result):
    """Extract text from tool result.

    FastMCP call_tool returns a tuple (list_of_TextContent, metadata_dict).
    This helper extracts the text from the first TextContent item.
    """
    # Handle tuple return: (content_list, metadata)
    if isinstance(result, tuple) and len(result) > 0:
        result = result[0]
    if isinstance(result, list) and len(result) > 0:
        if hasattr(result[0], 'text'):
            return result[0].text
    return str(result)


@pytest.fixture
def mock_sdk_client():
    """Create a mock SDK client with common methods stubbed."""
    client = Mock()

    # Token serialization
    client.export_token = Mock(return_value=json.dumps({
        "access_token": "test_access_token",
        "user_info": {
            "user_id": "123456",
            "nickname": "TestUser",
            "email": "test@test.com",
            "head_pic": "",
            "country_code": "US",
            "birthday": 19900101,
        }
    }))
    client.load_token = Mock()
    client.logout = Mock()

    # Make_request is the core SDK method — api/ functions call SDK functions
    # which call client.make_request(). For tool tests we mock at the api/ level instead.
    client.make_request = Mock()

    client.user_info = UserInfo(
        user_id="123456",
        nickname="TestUser",
        email="test@test.com",
        head_pic="",
        country_code="US",
        birthday=19900101,
    )
    client.is_logged_in = True

    return client


# Keep backward compat alias — some tests reference mock_coros_client
@pytest.fixture
def mock_coros_client(mock_sdk_client):
    return mock_sdk_client


@pytest.fixture(autouse=True)
def mock_get_client(mock_sdk_client):
    """Auto-mock client_factory.get_client in all tool modules.

    Patches get_client at the module level so that tool functions receive
    the mock client instead of trying to extract tokens from the request context.

    Yields the mock function (not the client) so tests can set side_effect
    for error scenarios like "not logged in".
    """
    get_client_fn = Mock(return_value=mock_sdk_client)

    modules_to_patch = [
        "coros_mcp.activities",
        "coros_mcp.auth_tool",
        "coros_mcp.dashboard",
        "coros_mcp.analysis",
        "coros_mcp.training",
        "coros_mcp.workouts",
        "coros_mcp.profile",
        "coros_mcp.plans",
    ]

    patchers = []
    for module in modules_to_patch:
        p = patch(f"{module}.get_client", get_client_fn)
        p.start()
        patchers.append(p)

    yield get_client_fn

    for p in patchers:
        p.stop()


def create_test_app(module):
    """Helper to create a FastMCP app with a specific module registered."""
    app = FastMCP(f"Test COROS {module.__name__}")
    app = module.register_tools(app)
    return app


@pytest.fixture
def mock_context():
    """Create a mock MCP context with state management."""
    context = Mock()
    state = {}

    async def get_state(key):
        return state.get(key)

    async def set_state(key, value):
        state[key] = value

    async def delete_state(key):
        if key in state:
            del state[key]

    context.get_state = get_state
    context.set_state = set_state
    context.delete_state = delete_state
    context._state = state

    return context


@pytest.fixture
def coros_tokens():
    """Sample COROS tokens for session restoration."""
    return json.dumps({
        "access_token": "test_access_token",
        "user_info": {
            "user_id": "123456",
            "nickname": "TestUser",
            "email": "test@test.com",
            "head_pic": "",
            "country_code": "US",
            "birthday": 19900101,
        }
    })
