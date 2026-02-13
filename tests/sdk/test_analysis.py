"""Tests for SDK analysis functions."""

import pytest
from unittest.mock import patch

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import analysis


@pytest.fixture
def authed_client():
    client = CorosClient()
    client._access_token = "token"
    return client


class TestGetAnalysis:
    def test_returns_data(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {
                    "dayList": [{"happenDay": 20260210, "trainingLoad": 85}],
                    "sportStatistic": [],
                },
            }
            result = analysis.get_analysis(authed_client)
            assert result["dayList"][0]["trainingLoad"] == 85
            assert mock_req.call_args[0][1] == "analyse/query"
