"""
COROS analysis SDK functions.

See docs/coros-api-spec.md § Analysis.
"""

from typing import Any, Dict

from coros_mcp.sdk.client import CorosClient


def get_analysis(client: CorosClient) -> Dict[str, Any]:
    """
    Get comprehensive training analysis.

    GET analyse/query

    Returns:
        {dayList, weekList, t7dayList, sportStatistic, tlIntensity, trainingWeekStageList}
    """
    response = client.make_request("GET", "analyse/query")
    return response["data"]
