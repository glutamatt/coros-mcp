"""
COROS dashboard SDK functions.

See docs/coros-api-spec.md § Dashboard.
"""

from typing import Any, Dict

from coros_mcp.sdk.client import CorosClient


def get_dashboard(client: CorosClient) -> Dict[str, Any]:
    """
    Get main fitness dashboard summary.

    GET dashboard/query

    Returns:
        {summaryInfo: {recoveryPct, fitnessScores, staminaLevel, sleepHrvData, ...}}
    """
    response = client.make_request("GET", "dashboard/query")
    return response["data"]


def get_dashboard_detail(client: CorosClient) -> Dict[str, Any]:
    """
    Get detailed dashboard data.

    GET dashboard/detail/query

    Returns:
        {summaryInfo: {ati, cti, tiredRateNew, ...}, currentWeekRecord, detailList, ...}
    """
    response = client.make_request("GET", "dashboard/detail/query")
    return response["data"]


def get_personal_records(client: CorosClient) -> Dict[str, Any]:
    """
    Get personal records by time period.

    GET dashboard/queryCycleRecord

    Returns:
        {allRecordList: [{type (1=week,2=month,3=year,4=all-time), recordList}]}
    """
    response = client.make_request("GET", "dashboard/queryCycleRecord")
    return response["data"]
