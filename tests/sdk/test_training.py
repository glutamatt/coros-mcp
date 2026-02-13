"""Tests for SDK training schedule functions."""

import pytest
from unittest.mock import patch

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import training


@pytest.fixture
def authed_client():
    client = CorosClient()
    client._access_token = "token"
    return client


class TestGetTrainingSchedule:
    def test_returns_data(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {
                    "id": "plan123",
                    "pbVersion": 5,
                    "entities": [],
                    "programs": [],
                },
            }
            result = training.get_training_schedule(authed_client, 20260209, 20260215)
            assert result["id"] == "plan123"

            params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
            assert params["startDate"] == "20260209"
            assert params["endDate"] == "20260215"
            assert params["supportRestExercise"] == "1"


class TestGetTrainingSummary:
    def test_returns_data(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {
                    "todayTrainingSum": {"actualDistance": 5000},
                    "weekTrains": [],
                },
            }
            result = training.get_training_summary(authed_client, 20260101, 20260131)
            assert result["todayTrainingSum"]["actualDistance"] == 5000

            params = mock_req.call_args.kwargs.get("params") or mock_req.call_args[0][2]
            assert params["startDate"] == "20260101"
            assert params["endDate"] == "20260131"


class TestUpdateTrainingSchedule:
    def test_returns_full_response(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {"result": "0000", "message": "OK"}
            payload = {
                "pbVersion": 5,
                "entities": [],
                "programs": [],
                "versionObjects": [{"id": 1, "status": 1}],
            }
            result = training.update_training_schedule(authed_client, payload)
            assert result["result"] == "0000"

            call_kwargs = mock_req.call_args.kwargs
            assert call_kwargs["json_data"] == payload
