"""
COROS activities SDK functions.

See docs/coros-api-spec.md § Activities.
"""

from datetime import date
from typing import Any, Dict, Optional

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk.types import FileType


def get_activities_list(
    client: CorosClient,
    page: int = 1,
    size: int = 20,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    mode_list: str = "",
) -> Dict[str, Any]:
    """
    Get paginated list of activities.

    GET activity/query

    Returns:
        {count, totalPage, pageNumber, dataList: [{labelId, date, name, sportType, ...}]}
    """
    params = {
        "size": str(size),
        "pageNumber": str(page),
    }
    if from_date:
        params["startDay"] = from_date.strftime("%Y%m%d")
    if to_date:
        params["endDay"] = to_date.strftime("%Y%m%d")
    if mode_list:
        params["modeList"] = mode_list

    response = client.make_request("GET", "activity/query", params=params)
    return response["data"]


def get_activity_details(client: CorosClient, activity_id: str) -> Dict[str, Any]:
    """
    Get detailed information about an activity.

    POST activity/detail/query

    Returns:
        {summary, lapList, zoneList, weather, frequencyList, graphList, ...}
    """
    response = client.make_request(
        "POST",
        "activity/detail/query",
        params={"labelId": activity_id, "sportType": "100"},
    )
    return response["data"]


def get_activity_download_url(
    client: CorosClient,
    activity_id: str,
    file_type: FileType = FileType.FIT,
) -> str:
    """
    Get download URL for an activity file.

    POST activity/detail/download

    Returns:
        URL string to download the activity file
    """
    response = client.make_request(
        "POST",
        "activity/detail/download",
        params={
            "labelId": activity_id,
            "sportType": "100",
            "fileType": file_type.value,
        },
    )
    return response["data"]["fileUrl"]


def delete_activity(client: CorosClient, activity_id: str) -> bool:
    """
    Delete an activity.

    GET activity/delete

    Returns:
        True if deleted successfully
    """
    client.make_request(
        "GET",
        "activity/delete",
        params={"labelId": activity_id},
    )
    return True
