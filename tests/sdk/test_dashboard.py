"""Tests for SDK dashboard functions."""

import pytest
from unittest.mock import patch

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import dashboard


@pytest.fixture
def authed_client():
    client = CorosClient()
    client._access_token = "token"
    return client


class TestGetDashboard:
    def test_returns_data(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {"summaryInfo": {"recoveryPct": 85}},
            }
            result = dashboard.get_dashboard(authed_client)
            assert result["summaryInfo"]["recoveryPct"] == 85
            assert mock_req.call_args[0][1] == "dashboard/query"


class TestGetDashboardDetail:
    def test_returns_data(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {"summaryInfo": {"ati": 85, "cti": 72}},
            }
            result = dashboard.get_dashboard_detail(authed_client)
            assert result["summaryInfo"]["ati"] == 85
            assert mock_req.call_args[0][1] == "dashboard/detail/query"


class TestGetPersonalRecords:
    def test_returns_data(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {"allRecordList": [{"type": 1, "recordList": []}]},
            }
            result = dashboard.get_personal_records(authed_client)
            assert len(result["allRecordList"]) == 1
            assert mock_req.call_args[0][1] == "dashboard/queryCycleRecord"
