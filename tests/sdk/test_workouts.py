"""Tests for SDK workout builder functions."""

import pytest
from unittest.mock import patch

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk import workouts


@pytest.fixture
def authed_client():
    client = CorosClient()
    client._access_token = "token"
    return client


class TestEstimateWorkout:
    def test_returns_data(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {
                    "distance": 10000,
                    "duration": 3600,
                    "trainingLoad": 85,
                    "sets": 1,
                },
            }
            payload = {"entity": {}, "program": {}}
            result = workouts.estimate_workout(authed_client, payload)
            assert result["trainingLoad"] == 85
            assert mock_req.call_args[0][1] == "training/program/estimate"


class TestCalculateWorkout:
    def test_returns_data(self, authed_client):
        with patch.object(authed_client, "make_request") as mock_req:
            mock_req.return_value = {
                "result": "0000",
                "data": {
                    "planDistance": 10000,
                    "planDuration": 3600,
                    "planTrainingLoad": 85,
                    "exerciseBarChart": [{"exerciseId": "1", "height": 50}],
                },
            }
            payload = {"sportType": 1, "exercises": []}
            result = workouts.calculate_workout(authed_client, payload)
            assert result["planTrainingLoad"] == 85
            assert len(result["exerciseBarChart"]) == 1
            assert mock_req.call_args[0][1] == "training/program/calculate"
