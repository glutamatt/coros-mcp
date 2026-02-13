"""
COROS workout builder SDK functions.

See docs/coros-api-spec.md § Workout Builder.
"""

from typing import Any, Dict

from coros_mcp.sdk.client import CorosClient


def estimate_workout(
    client: CorosClient, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Estimate training load for a workout before saving.

    POST training/program/estimate

    Args:
        payload: {entity: {...}, program: {...}}

    Returns:
        {distance, duration, trainingLoad, sets}
    """
    response = client.make_request(
        "POST",
        "training/program/estimate",
        json_data=payload,
    )
    return response["data"]


def calculate_workout(
    client: CorosClient, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Full workout calculation with bar chart data.

    POST training/program/calculate

    Args:
        payload: Flat program object with exercises

    Returns:
        {planDistance, planDuration, planTrainingLoad, planElevGain,
         planPitch, exerciseBarChart[]}
    """
    response = client.make_request(
        "POST",
        "training/program/calculate",
        json_data=payload,
    )
    return response["data"]
