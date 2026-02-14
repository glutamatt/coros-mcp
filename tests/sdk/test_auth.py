"""Tests for SDK auth functions."""

import pytest
from unittest.mock import patch, Mock

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import auth


class TestLogin:
    def test_login_success(self):
        client = CorosClient(email="test@test.com", password="pass123")
        with patch.object(client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {
                    "accessToken": "new_token",
                    "userId": "456",
                    "nickname": "Runner",
                    "email": "test@test.com",
                    "headPic": "pic.jpg",
                    "countryCode": "FR",
                    "birthday": 19900101,
                },
            }
            user = auth.login(client)

            assert user.user_id == "456"
            assert user.nickname == "Runner"
            assert client.is_logged_in is True
            assert client.access_token == "new_token"

            # Verify correct endpoint call
            mock_req.assert_called_once()
            call_args = mock_req.call_args
            assert call_args[0][1] == "account/login"
            assert call_args.kwargs["require_auth"] is False

    def test_login_missing_credentials(self):
        client = CorosClient()
        with pytest.raises(ValueError, match="Missing credentials"):
            auth.login(client)


class TestGetAccount:
    def test_get_account(self):
        client = CorosClient()
        client._access_token = "token"
        with patch.object(client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {
                    "userId": "789",
                    "nickname": "Athlete",
                    "email": "a@a.com",
                    "headPic": "",
                    "countryCode": "US",
                    "birthday": 19850101,
                },
            }
            user = auth.get_account(client)
            assert user.user_id == "789"
            assert user.nickname == "Athlete"
            assert client.user_info.user_id == "789"


class TestGetAccountFull:
    def test_returns_raw_data(self):
        client = CorosClient()
        client._access_token = "token"
        with patch.object(client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {
                    "userId": "123",
                    "zoneData": {"maxHr": 190},
                    "runScoreList": [],
                },
            }
            data = auth.get_account_full(client)
            assert data["userId"] == "123"
            assert data["zoneData"]["maxHr"] == 190
