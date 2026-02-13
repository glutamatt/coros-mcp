"""
COROS training schedule SDK functions.

See docs/coros-api-spec.md § Training Schedule.
"""

from typing import Any, Dict

from coros_mcp.sdk.client import CorosClient


def get_training_schedule(
    client: CorosClient, start_date: int, end_date: int
) -> Dict[str, Any]:
    """
    Get training plan for a date range.

    GET training/schedule/query

    Args:
        start_date: Start date as YYYYMMDD integer
        end_date: End date as YYYYMMDD integer

    Returns:
        {id, name, pbVersion, maxIdInPlan, entities[], programs[],
         sportDatasNotInPlan[], weekStages[]}
    """
    response = client.make_request(
        "GET",
        "training/schedule/query",
        params={
            "startDate": str(start_date),
            "endDate": str(end_date),
            "supportRestExercise": "1",
        },
    )
    return response["data"]


def get_training_summary(
    client: CorosClient, start_date: int, end_date: int
) -> Dict[str, Any]:
    """
    Get actual vs planned training summary.

    GET training/schedule/querysum

    Args:
        start_date: Start date as YYYYMMDD integer
        end_date: End date as YYYYMMDD integer

    Returns:
        {todayTrainingSum, weekTrains[], dayTrainSums[]}
    """
    response = client.make_request(
        "GET",
        "training/schedule/querysum",
        params={
            "startDate": str(start_date),
            "endDate": str(end_date),
        },
    )
    return response["data"]


def update_training_schedule(
    client: CorosClient, payload: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create, move, or delete scheduled workouts.

    POST training/schedule/update

    Args:
        payload: {pbVersion, entities[], programs[], versionObjects[]}

    Returns:
        Full API response (including result code)
    """
    response = client.make_request(
        "POST",
        "training/schedule/update",
        json_data=payload,
    )
    return response
