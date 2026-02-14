"""Tests for SDK client (HTTP transport, auth, token serialization)."""

import json
import pytest
from unittest.mock import patch, Mock

from coros_mcp.sdk.client import CorosClient, UserInfo


class TestCorosClientInit:
    def test_default_region_eu(self):
        client = CorosClient()
        assert "teameuapi.coros.com" in client._api_url

    def test_global_region(self):
        client = CorosClient(region="global")
        assert client._api_url == "https://teamapi.coros.com"

    def test_cn_region(self):
        client = CorosClient(region="cn")
        assert "coros.com.cn" in client._api_url

    def test_not_logged_in_initially(self):
        client = CorosClient()
        assert client.is_logged_in is False
        assert client.access_token is None
        assert client.user_info is None


class TestMakeRequest:
    def test_raises_when_not_logged_in(self):
        client = CorosClient()
        with pytest.raises(RuntimeError, match="Not logged in"):
            client.make_request("GET", "some/endpoint")

    def test_skips_auth_check_when_not_required(self):
        client = CorosClient()
        with patch.object(client._session, "post") as mock_post:
            mock_post.return_value = Mock(
                status_code=200,
                json=lambda: {"result": "0000", "data": {"ok": True}},
            )
            mock_post.return_value.raise_for_status = Mock()
            result = client.make_request(
                "POST", "account/login",
                json_data={"account": "test"},
                require_auth=False,
            )
            assert result["data"]["ok"] is True

    def test_raises_on_api_error(self):
        client = CorosClient()
        client._access_token = "fake"
        with patch.object(client._session, "get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {"result": "1030", "message": "Invalid token"},
            )
            mock_get.return_value.raise_for_status = Mock()
            with pytest.raises(ValueError, match="Invalid token"):
                client.make_request("GET", "some/endpoint")

    def test_sends_auth_headers(self):
        client = CorosClient()
        client._access_token = "my_token"
        client._user_info = UserInfo(
            user_id="123", nickname="Test", email="t@t.com",
            head_pic="", country_code="FR", birthday=19900101,
        )
        with patch.object(client._session, "get") as mock_get:
            mock_get.return_value = Mock(
                status_code=200,
                json=lambda: {"result": "0000", "data": {}},
            )
            mock_get.return_value.raise_for_status = Mock()
            client.make_request("GET", "test/endpoint")

            call_kwargs = mock_get.call_args
            headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers")
            assert headers["accessToken"] == "my_token"
            assert '"userId"' in headers["yfheader"]


class TestTokenSerialization:
    def test_export_import_roundtrip(self):
        client = CorosClient()
        client._access_token = "test_token"
        client._user_info = UserInfo(
            user_id="42", nickname="Runner", email="run@er.com",
            head_pic="pic.jpg", country_code="US", birthday=19850315,
        )

        exported = client.export_token()
        data = json.loads(exported)
        assert data["access_token"] == "test_token"
        assert data["user_info"]["user_id"] == "42"

        # Import into new client
        client2 = CorosClient()
        client2.load_token(exported)
        assert client2.is_logged_in is True
        assert client2.access_token == "test_token"
        assert client2.user_info.nickname == "Runner"

    def test_export_raises_when_not_logged_in(self):
        client = CorosClient()
        with pytest.raises(RuntimeError, match="Not logged in"):
            client.export_token()

    def test_logout_clears_state(self):
        client = CorosClient()
        client._access_token = "token"
        client._user_info = UserInfo(
            user_id="1", nickname="X", email="x@x.com",
            head_pic="", country_code="", birthday=0,
        )
        client.logout()
        assert client.is_logged_in is False
        assert client.access_token is None
        assert client.user_info is None


class TestMd5Hash:
    def test_known_hash(self):
        assert CorosClient.md5_hash("password") == "5f4dcc3b5aa765d61d8327deb882cf99"
