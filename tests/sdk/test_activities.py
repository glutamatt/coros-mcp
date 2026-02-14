"""Tests for SDK activities functions."""

import pytest
from datetime import date
from unittest.mock import patch, Mock

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import activities
from coros_mcp.sdk.types import FileType


@pytest.fixture
def authed_client():
    client = CorosClient()
    client._access_token = "token"
    return client


class TestGetActivitiesList:
    def test_basic_call(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {"count": 5, "totalPage": 1, "pageNumber": 1, "dataList": []},
            }
            result = activities.get_activities_list(authed_client)
            assert result["count"] == 5

            call_args = mock_req.call_args
            assert call_args[0][1] == "activity/query"
            params = call_args.kwargs.get("params") or call_args[0][2]
            assert params["size"] == "20"
            assert params["pageNumber"] == "1"

    def test_with_date_filter(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {"count": 0, "dataList": []},
            }
            activities.get_activities_list(
                authed_client,
                from_date=date(2026, 1, 1),
                to_date=date(2026, 1, 31),
            )
            params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
            assert params["startDay"] == "20260101"
            assert params["endDay"] == "20260131"

    def test_pagination(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {"count": 100, "totalPage": 5, "pageNumber": 3, "dataList": []},
            }
            activities.get_activities_list(authed_client, page=3, size=10)
            params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
            assert params["pageNumber"] == "3"
            assert params["size"] == "10"


class TestGetActivityDetails:
    def test_returns_data(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {"summary": {"name": "Run"}, "lapList": []},
            }
            result = activities.get_activity_details(authed_client, "abc123")
            assert result["summary"]["name"] == "Run"
            params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
            assert params["labelId"] == "abc123"
            assert params["sportType"] == "100"


class TestGetActivityDownloadUrl:
    def test_fit_format(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {"fileUrl": "https://dl.coros.com/file.fit"},
            }
            url = activities.get_activity_download_url(authed_client, "abc123")
            assert url == "https://dl.coros.com/file.fit"

    def test_gpx_format(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {"fileUrl": "https://dl.coros.com/file.gpx"},
            }
            url = activities.get_activity_download_url(
                authed_client, "abc123", FileType.GPX,
            )
            params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
            assert params["fileType"] == "1"


class TestDeleteActivity:
    def test_returns_true(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {"result": "0000", "data": {}}
            assert activities.delete_activity(authed_client, "abc123") is True
            params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
            assert params["labelId"] == "abc123"
