"""Tests for api/profile.py — Profile + zones formatting."""

from unittest.mock import Mock, patch

from coros_mcp.api.profile import get_athlete_profile


@patch("coros_mcp.api.profile.sdk_auth")
def test_get_athlete_profile(mock_auth):
    mock_auth.get_account_full.return_value = {
        "userId": "123",
        "nickname": "Runner",
        "email": "runner@test.com",
        "birthday": 19900101,
        "sex": 1,
        "countryCode": "FR",
        "stature": 180,
        "weight": 72,
        "maxHr": 190,
        "rhr": 50,
        "zoneData": {
            "maxHr": 190,
            "rhr": 50,
            "lthr": 165,
            "ltsp": 285,
            "ftp": 250,
            "maxHrZone": [
                {"hr": 114, "index": 0, "ratio": 60.0},
                {"hr": 133, "index": 1, "ratio": 70.0},
                {"hr": 152, "index": 2, "ratio": 80.0},
                {"hr": 171, "index": 3, "ratio": 90.0},
                {"hr": 190, "index": 4, "ratio": 100.0},
            ],
            "ltspZone": [
                {"index": 0, "pace": 400, "ratio": 70.0},
                {"index": 1, "pace": 350, "ratio": 80.0},
                {"index": 2, "pace": 300, "ratio": 90.0},
                {"index": 3, "pace": 270, "ratio": 95.0},
                {"index": 4, "pace": 240, "ratio": 100.0},
            ],
            "cyclePowerZone": [
                {"index": 0, "power": 100, "ratio": 40.0},
                {"index": 1, "power": 150, "ratio": 60.0},
                {"index": 2, "power": 200, "ratio": 80.0},
                {"index": 3, "power": 250, "ratio": 100.0},
            ],
        },
    }

    client = Mock()
    result = get_athlete_profile(client)

    assert result["identity"]["nickname"] == "Runner"
    assert result["identity"]["sex"] == "male"
    assert result["identity"]["birthday"] == "1990-01-01"
    assert result["biometrics"]["height_cm"] == 180
    assert result["biometrics"]["weight_kg"] == 72
    assert result["thresholds"]["max_hr"] == 190
    assert result["thresholds"]["lthr"] == 165
    assert result["thresholds"]["ftp"] == 250

    # HR zones formatted
    assert len(result["hr_zones"]) == 5
    assert result["hr_zones"][0]["name"] == "Recovery"
    assert "bpm" in result["hr_zones"][0]["range"]

    # Pace zones formatted
    assert len(result["pace_zones"]) == 5
    assert result["pace_zones"][0]["name"] == "Easy"

    # Power zones formatted
    assert len(result["power_zones"]) == 4
    assert "W" in result["power_zones"][0]["range"]


@patch("coros_mcp.api.profile.sdk_auth")
def test_profile_no_zones(mock_auth):
    mock_auth.get_account_full.return_value = {
        "userId": "123",
        "nickname": "Newbie",
        "zoneData": {},
    }

    client = Mock()
    result = get_athlete_profile(client)

    assert "hr_zones" not in result
    assert "pace_zones" not in result


@patch("coros_mcp.api.profile.sdk_auth")
def test_profile_female(mock_auth):
    mock_auth.get_account_full.return_value = {
        "userId": "456",
        "sex": 2,
        "zoneData": {},
    }

    client = Mock()
    result = get_athlete_profile(client)
    assert result["identity"]["sex"] == "female"
