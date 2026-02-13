"""
COROS training plan SDK functions.

See docs/coros-api-spec.md § Training Plans.
"""

from typing import Any, Dict, List

from coros_mcp.sdk.client import CorosClient


def query_plans(
    client: CorosClient,
    status_list: List[int] = None,
    start_no: int = 0,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    List training plans.

    POST training/plan/query

    Args:
        status_list: [0]=draft, [1]=active. Default [0].
        start_no: Pagination offset
        limit: Page size

    Returns:
        List of plan objects
    """
    if status_list is None:
        status_list = [0]
    response = client.make_request(
        "POST",
        "training/plan/query",
        json_data={
            "name": "",
            "statusList": status_list,
            "startNo": start_no,
            "limitSize": limit,
        },
    )
    return response["data"]


def get_plan_detail(
    client: CorosClient, plan_id: str, region: int = 3
) -> Dict[str, Any]:
    """
    Get full plan with all workouts and exercises.

    GET training/plan/detail

    Args:
        plan_id: Plan ID string
        region: 1=global, 2=CN, 3=EU (default)

    Returns:
        Full plan object with entities, programs, exercises
    """
    response = client.make_request(
        "GET",
        "training/plan/detail",
        params={"id": plan_id, "supportRestExercise": "1"},
    )
    return response["data"]


def add_plan(client: CorosClient, payload: Dict[str, Any]) -> str:
    """
    Create a new training plan template.

    POST training/plan/add

    Args:
        payload: Full plan object (entities, programs, versionObjects, etc.)

    Returns:
        New plan ID as string
    """
    response = client.make_request(
        "POST",
        "training/plan/add",
        json_data=payload,
    )
    return response["data"]


def update_plan(client: CorosClient, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update an existing plan template.

    POST training/plan/update

    Args:
        payload: Full plan object with modifications

    Returns:
        API response
    """
    response = client.make_request(
        "POST",
        "training/plan/update",
        json_data=payload,
    )
    return response


def delete_plans(client: CorosClient, plan_ids: List[str]) -> Dict[str, Any]:
    """
    Delete one or more plans.

    POST training/plan/delete

    Args:
        plan_ids: List of plan ID strings

    Returns:
        API response
    """
    response = client.make_request(
        "POST",
        "training/plan/delete",
        json_data=plan_ids,
    )
    return response


def execute_sub_plan(
    client: CorosClient, plan_id: str, start_date: int
) -> Dict[str, Any]:
    """
    Apply a plan template to the calendar starting on a specific date.

    POST training/schedule/executeSubPlan

    Args:
        plan_id: Plan ID to activate
        start_date: Start date as YYYYMMDD integer

    Returns:
        API response
    """
    response = client.make_request(
        "POST",
        "training/schedule/executeSubPlan",
        params={"startDay": str(start_date), "subPlanId": plan_id},
        json_data={},
    )
    return response
