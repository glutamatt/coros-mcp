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


def query_programs(
    client: CorosClient,
    sport_type: int = 0,
    start_no: int = 0,
    limit: int = 10,
) -> Any:
    """
    List workout templates from the workout library.

    POST training/program/query

    Args:
        sport_type: Filter by sport (0=all)
        start_no: Pagination offset
        limit: Page size

    Returns:
        List of program objects with exercises
    """
    response = client.make_request(
        "POST",
        "training/program/query",
        json_data={
            "name": "",
            "supportRestExercise": 1,
            "startNo": start_no,
            "limitSize": limit,
            "sportType": sport_type,
        },
    )
    return response["data"]


def get_program_detail(client: CorosClient, program_id: str) -> Dict[str, Any]:
    """
    Get a single workout program with full exercises.

    GET training/program/detail

    Args:
        program_id: Program ID string

    Returns:
        Program object with full exercises
    """
    response = client.make_request(
        "GET",
        "training/program/detail",
        params={"id": program_id, "supportRestExercise": "1"},
    )
    return response["data"]
