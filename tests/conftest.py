"""
Shared pytest fixtures for COROS MCP testing.
"""
import json
import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
from mcp.server.fastmcp import FastMCP

from coros_mcp.coros_client import UserInfo


def get_tool_result_text(result):
    """Extract text from tool result.

    FastMCP call_tool returns a list of TextContent objects.
    This helper extracts the text from the first item.
    """
    if isinstance(result, list) and len(result) > 0:
        if hasattr(result[0], 'text'):
            return result[0].text
    return str(result)


@pytest.fixture
def mock_coros_client():
    """Create a mock COROS client with common methods stubbed."""
    client = Mock()

    # Configure mock to have all the methods we need
    client.get_account = Mock(return_value=UserInfo(
        user_id="123456",
        nickname="TestUser",
        email="test@test.com",
        head_pic="https://example.com/pic.jpg",
        country_code="US",
        birthday=19900101,
    ))

    client.get_activities_list = Mock(return_value={
        "count": 0,
        "totalPage": 1,
        "pageNumber": 1,
        "dataList": [],
    })

    client.get_activity_details = Mock(return_value={
        "summary": {},
        "lapList": [],
        "zoneList": [],
        "weather": {},
    })

    client.get_activity_download_url = Mock(return_value="https://example.com/activity.fit")

    client.login = Mock(return_value=UserInfo(
        user_id="123456",
        nickname="TestUser",
        email="test@test.com",
        head_pic="",
        country_code="US",
        birthday=19900101,
    ))

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
    client.is_logged_in = True

    return client


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
    context._state = state  # For test inspection

    return context


@pytest.fixture
def today_str():
    """Return today's date as YYYY-MM-DD string."""
    return datetime.now().strftime("%Y-%m-%d")


@pytest.fixture
def yesterday_str():
    """Return yesterday's date as YYYY-MM-DD string."""
    return (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")


@pytest.fixture
def date_range():
    """Return a tuple of (start_date, end_date) as strings."""
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    return (start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))


@pytest.fixture
def sample_activity():
    """Sample activity data matching COROS API response format."""
    return {
        "labelId": "abc123",
        "date": 20240115,
        "name": "Morning Run",
        "sportType": 1,
        "distance": 5000.0,
        "totalTime": 1800,
        "workoutTime": 1750,
        "trainingLoad": 75,
        "device": "PACE 3",
    }


@pytest.fixture
def sample_activity_details():
    """Sample activity details matching COROS API response format."""
    return {
        "summary": {
            "name": "Morning Run",
            "sportType": 1,
            "sportMode": 1,
            "startTimestamp": 1705312800,
            "endTimestamp": 1705314600,
            "totalTime": 1800,
            "workoutTime": 1750,
            "pauseTime": 50,
            "distance": 5000.0,
            "avgPace": 350,
            "avgSpeed": 2.78,
            "avgHr": 145,
            "maxHr": 165,
            "avgCadence": 175,
            "maxCadence": 185,
            "elevGain": 50,
            "totalDescent": 45,
            "avgElev": 100,
            "maxElev": 120,
            "minElev": 80,
            "avgPower": 220,
            "maxPower": 280,
            "np": 230,
            "calories": 350,
            "trainingLoad": 75,
            "aerobicEffect": 3.2,
            "anaerobicEffect": 1.5,
            "avgStepLen": 110,
            "avgGroundTime": 250,
            "avgVertRatio": 8.5,
        },
        "lapList": [
            {
                "lapItemList": [
                    {
                        "lapIndex": 1,
                        "distance": 1000,
                        "time": 360,
                        "avgPace": 360,
                        "avgHr": 140,
                        "maxHr": 155,
                        "avgCadence": 172,
                        "elevGain": 10,
                        "avgPower": 215,
                    },
                    {
                        "lapIndex": 2,
                        "distance": 1000,
                        "time": 345,
                        "avgPace": 345,
                        "avgHr": 148,
                        "maxHr": 160,
                        "avgCadence": 178,
                        "elevGain": 15,
                        "avgPower": 225,
                    },
                ]
            }
        ],
        "zoneList": [
            {
                "type": 1,  # Heart rate zones
                "zoneItemList": [
                    {"zoneIndex": 1, "leftScope": 100, "rightScope": 120, "second": 120, "percent": 7},
                    {"zoneIndex": 2, "leftScope": 120, "rightScope": 140, "second": 480, "percent": 27},
                    {"zoneIndex": 3, "leftScope": 140, "rightScope": 160, "second": 900, "percent": 50},
                    {"zoneIndex": 4, "leftScope": 160, "rightScope": 175, "second": 240, "percent": 13},
                    {"zoneIndex": 5, "leftScope": 175, "rightScope": 200, "second": 60, "percent": 3},
                ]
            }
        ],
        "weather": {
            "temperature": 15,
            "bodyFeelTemp": 14,
            "humidity": 65,
            "windSpeed": 3.5,
        },
    }


@pytest.fixture
def sample_activities_list(sample_activity):
    """Sample activities list matching COROS API response format."""
    return {
        "count": 2,
        "totalPage": 1,
        "pageNumber": 1,
        "dataList": [
            sample_activity,
            {
                "labelId": "def456",
                "date": 20240114,
                "name": "Recovery Run",
                "sportType": 1,
                "distance": 3000.0,
                "totalTime": 1200,
                "workoutTime": 1180,
                "trainingLoad": 45,
                "device": "PACE 3",
            },
        ],
    }


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
