"""
COROS Training Hub Low-Level SDK.

Thin typed wrapper over the COROS HTTP API.
Each function maps 1:1 to a COROS endpoint.
See docs/coros-api-spec.md for the ground truth reference.
"""

from coros_mcp.sdk.client import CorosClient
from coros_mcp.sdk.types import (
    FileType,
    STSRegion,
    SportType,
    ExerciseType,
    TargetType,
    TargetDisplayUnit,
    RestType,
    VersionStatus,
    EXERCISE_TEMPLATES,
    DEFAULT_SOURCE_ID,
    DEFAULT_SOURCE_URL,
)

__all__ = [
    "CorosClient",
    "FileType",
    "STSRegion",
    "SportType",
    "ExerciseType",
    "TargetType",
    "TargetDisplayUnit",
    "RestType",
    "VersionStatus",
    "EXERCISE_TEMPLATES",
    "DEFAULT_SOURCE_ID",
    "DEFAULT_SOURCE_URL",
]
