"""
Shared pytest fixtures for COROS MCP testing.
"""
import json
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timedelta

# Monkey-patch: production uses fastmcp.FastMCP, tests use mcp.server.fastmcp.
# Patch fastmcp.Context to match mcp.server.fastmcp.Context so tools work
# with the test FastMCP.
import fastmcp
from mcp.server.fastmcp import server as mcp_server
fastmcp.Context = mcp_server.Context

from mcp.server.fastmcp import FastMCP

from coros_mcp.coros_client import UserInfo


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

    # Dashboard methods
    client.get_dashboard = Mock(return_value={
        "summaryInfo": {
            "recoveryPct": 85,
            "recoveryState": 2,
            "fullRecoveryHours": 12,
            "aerobicEnduranceScore": 72,
            "anaerobicCapacityScore": 45,
            "anaerobicEnduranceScore": 55,
            "lactateThresholdCapacityScore": 68,
            "staminaLevel": 75,
            "staminaLevelChange": 2,
            "staminaLevelRanking": 3,
            "rhr": 52,
            "lthr": 165,
            "ltsp": 285,
            "sleepHrvData": {
                "sleepHrvList": [
                    {"happenDay": 20260209, "avgSleepHrv": 52, "sleepHrvBase": 48, "sleepHrvSd": 8},
                    {"happenDay": 20260210, "avgSleepHrv": 55, "sleepHrvBase": 49, "sleepHrvSd": 7},
                    {"happenDay": 20260211, "avgSleepHrv": 50, "sleepHrvBase": 49, "sleepHrvSd": 9},
                ]
            },
        }
    })

    client.get_dashboard_detail = Mock(return_value={
        "summaryInfo": {
            "ati": 85,
            "cti": 72,
            "tiredRateNew": 0.6,
            "trainingLoadRatio": 1.1,
            "trainingLoadRatioState": 2,
            "recomendTlInDays": 120,
        },
        "currentWeekRecord": {
            "distanceRecord": 25000,
            "durationRecord": 7200,
            "tlRecord": 350,
        },
        "detailList": [],
        "sportDataList": [],
    })

    client.get_personal_records = Mock(return_value={
        "allRecordList": [
            {
                "type": 1,
                "recordList": [
                    {"happenDay": 20260210, "sportType": 1, "type": 1, "record": 1200, "labelId": "rec1"},
                ]
            },
            {
                "type": 4,
                "recordList": [
                    {"happenDay": 20250601, "sportType": 1, "type": 1, "record": 2400, "labelId": "rec2"},
                ]
            },
        ]
    })

    # Analysis methods
    client.get_analysis = Mock(return_value={
        "dayList": [
            {
                "happenDay": 20260210,
                "trainingLoad": 85,
                "distance": 10000,
                "duration": 3600,
                "vo2max": 52,
                "staminaLevel": 75,
                "rhr": 52,
                "ati": 85,
                "cti": 72,
                "tiredRateNew": 0.6,
                "recomendTlMin": 80,
                "recomendTlMax": 130,
            },
        ],
        "weekList": [
            {"firstDayOfWeek": 20260203, "trainingLoad": 350, "recomendTlMin": 300, "recomendTlMax": 450},
        ],
        "t7dayList": [
            {
                "vo2max": 52,
                "staminaLevel": 75,
                "staminaLevel7d": 74,
                "tiredRateNew": 0.6,
                "trainingLoadRatio": 1.1,
                "trainingLoadRatioState": 2,
            },
        ],
        "sportStatistic": [
            {"sportType": 1, "count": 5, "distance": 45000, "duration": 14400, "avgHeartRate": 148, "trainingLoad": 350},
            {"sportType": 16, "count": 2, "distance": 0, "duration": 3600, "avgHeartRate": 125, "trainingLoad": 80},
        ],
        "tlIntensity": {
            "detailList": [
                {"periodLowPct": 60, "periodLowValue": 200, "periodMediumPct": 25, "periodMediumValue": 100, "periodHighPct": 15, "periodHighValue": 50},
            ]
        },
        "trainingWeekStageList": [
            {"firstDayOfWeek": 20260203, "stage": 2},
        ],
    })

    # Profile methods
    client.get_account_full = Mock(return_value={
        "userId": "123456",
        "nickname": "TestUser",
        "email": "test@test.com",
        "birthday": 19900101,
        "sex": 1,
        "countryCode": "FR",
        "stature": 180,
        "weight": 75,
        "maxHr": 190,
        "rhr": 52,
        "unit": 0,
        "temperatureUnit": 0,
        "hrZoneType": 1,
        "zoneData": {
            "maxHr": 190,
            "rhr": 52,
            "lthr": 165,
            "ltsp": 285,
            "ftp": 250,
            "maxHrZone": [114, 133, 152, 171, 190],
            "ltspZone": [400, 350, 300, 270, 240],
        },
        "runScoreList": [
            {"type": 1, "avgPace": 320, "distance": 45000, "distanceRatio": 0.8, "trainingLoadRatio": 0.7},
        ],
    })

    # Training schedule methods
    client.get_training_schedule = Mock(return_value={
        "name": "Test Plan",
        "pbVersion": 5,
        "programs": [
            {
                "id": "prog1",
                "name": "Easy Run",
                "sportType": 1,
                "happenDay": 20260212,
                "planDistance": 8000,
                "planDuration": 2400,
                "planTrainingLoad": 60,
                "actualDistance": 0,
                "actualDuration": 0,
                "actualTrainingLoad": 0,
                "exercises": [],
            },
        ],
        "sportDatasNotInPlan": [
            {"name": "Extra Run", "sportType": 1, "happenDay": 20260211, "distance": 5000, "duration": 1800, "trainingLoad": 45, "labelId": "act1"},
        ],
        "weekStages": [
            {"firstDayInWeek": 20260209, "stage": 2, "trainSum": 300},
        ],
    })

    client.get_training_summary = Mock(return_value={
        "todayTrainingSum": {
            "actualDistance": 5000,
            "planDistance": 8000,
            "actualDuration": 1800,
            "planDuration": 2400,
            "actualTrainingLoad": 45,
            "planTrainingLoad": 60,
            "actualAti": 85,
            "actualCti": 72,
            "actualTiredRateNew": 0.6,
        },
        "weekTrains": [
            {
                "firstDayInWeek": 20260203,
                "weekTrainSum": {
                    "actualDistance": 40000,
                    "planDistance": 45000,
                    "actualDuration": 14400,
                    "planDuration": 16200,
                    "actualTrainingLoad": 300,
                    "planTrainingLoad": 350,
                    "actualTrainingLoadRatio": 1.1,
                    "planTrainingLoadRatio": 1.2,
                    "actualTiredRateNew": 0.6,
                    "planTiredRateNew": 0.7,
                },
            },
        ],
        "dayTrainSums": [
            {
                "happenDay": 20260210,
                "dayTrainSum": {
                    "actualDistance": 10000,
                    "planDistance": 10000,
                    "actualDuration": 3600,
                    "planDuration": 3600,
                    "actualTrainingLoad": 85,
                    "planTrainingLoad": 80,
                },
            },
        ],
    })

    client.update_training_schedule = Mock(return_value={"result": "0000", "message": "OK"})

    # Workout builder methods
    client.estimate_workout = Mock(return_value={
        "distance": 10000,
        "duration": 3600,
        "trainingLoad": 85,
        "sets": 1,
    })

    client.calculate_workout = Mock(return_value={
        "planDistance": 10000,
        "planDuration": 3600,
        "planTrainingLoad": 85,
        "planElevGain": 0,
        "exerciseBarChart": [{"exerciseId": "1", "height": 50, "width": 100}],
    })

    return client


@pytest.fixture(autouse=True)
def mock_get_client(mock_coros_client):
    """Auto-mock client_factory.get_client in all tool modules.

    Patches get_client at the module level so that tool functions receive
    the mock client instead of trying to extract tokens from the request context.

    Yields the mock function (not the client) so tests can set side_effect
    for error scenarios like "not logged in".
    """
    get_client_fn = Mock(return_value=mock_coros_client)

    modules_to_patch = [
        "coros_mcp.activities",
        "coros_mcp.auth_tool",
        "coros_mcp.dashboard",
        "coros_mcp.analysis",
        "coros_mcp.training",
        "coros_mcp.workouts",
        "coros_mcp.profile",
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
