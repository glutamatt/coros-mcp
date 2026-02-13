"""
COROS API types, enums, and constants.

All COROS-specific codes, mappings, and magic values live here.
See docs/coros-api-spec.md for the ground truth reference.
"""

from enum import Enum, IntEnum


class FileType(Enum):
    """Export file type options for activity downloads."""
    CSV = "0"
    GPX = "1"
    KML = "2"
    TCX = "3"
    FIT = "4"


class STSRegion(Enum):
    """Storage region configuration."""
    EN = "en.prod"
    CN = "cn.prod"
    EU = "eu.prod"


class SportType(IntEnum):
    """Program sport type codes (workout context).

    These differ from activity sport type codes.
    Used in workout/program payloads.
    """
    RUNNING = 1
    TRAIL = 3
    STRENGTH = 4
    HIKE = 5
    BIKE = 6
    POOL_SWIM = 9
    OPEN_WATER = 10


class ExerciseType(IntEnum):
    """Exercise type codes within a workout program."""
    GROUP = 0
    WARMUP = 1
    INTERVAL = 2
    COOLDOWN = 3
    RECOVERY = 4


class TargetType(IntEnum):
    """Exercise target type codes."""
    NONE = 0
    DURATION = 2
    DISTANCE = 5


class TargetDisplayUnit(IntEnum):
    """Display unit for exercise target values."""
    SECONDS = 0
    METERS = 1
    KILOMETERS = 2


class RestType(IntEnum):
    """Rest type between repeat sets."""
    TIMED = 0
    NO_REST = 3


class VersionStatus(IntEnum):
    """Status codes for versionObjects in schedule/update."""
    NEW = 1
    MOVE_UPDATE = 2
    DELETE = 3


# Activity sport type names (activity context, different from program sport types)
ACTIVITY_SPORT_NAMES = {
    0: "Unknown",
    1: "Run",
    2: "Indoor Run",
    3: "Trail Run",
    4: "Track Run",
    5: "Hike",
    6: "Bike",
    7: "Indoor Bike",
    8: "Mountain Bike",
    9: "Pool Swim",
    10: "Open Water Swim",
    11: "Triathlon",
    12: "Multisport",
    13: "Ski",
    14: "Snowboard",
    15: "XC Ski",
    16: "Strength",
    17: "Gym Cardio",
    18: "Rowing",
    19: "Walk",
    20: "Flatwater",
    21: "Whitewater",
    22: "Windsurfing",
    23: "Speedsurfing",
    24: "GPS Cardio",
    100: "Other",
}

# User-friendly sport name to program sport code mapping
SPORT_NAME_TO_CODE = {
    "running": SportType.RUNNING,
    "run": SportType.RUNNING,
    "trail": SportType.TRAIL,
    "strength": SportType.STRENGTH,
    "hike": SportType.HIKE,
    "bike": SportType.BIKE,
    "cycling": SportType.BIKE,
    "pool_swim": SportType.POOL_SWIM,
    "swim": SportType.POOL_SWIM,
    "open_water": SportType.OPEN_WATER,
}

# Exercise template metadata from COROS exercise library (running)
EXERCISE_TEMPLATES = {
    ExerciseType.WARMUP: {
        "name": "T1120",
        "overview": "sid_run_warm_up_dist",
        "originId": "425895398452936705",
        "createTimestamp": 1586584068,
        "defaultOrder": 1,
    },
    ExerciseType.INTERVAL: {
        "name": "T3001",
        "overview": "sid_run_training",
        "originId": "426109589008859136",
        "createTimestamp": 1587381919,
        "defaultOrder": 2,
        "isDefaultAdd": 1,
    },
    ExerciseType.COOLDOWN: {
        "name": "T1122",
        "overview": "sid_run_cool_down_dist",
        "originId": "425895456971866112",
        "createTimestamp": 1586584214,
        "defaultOrder": 3,
    },
    ExerciseType.RECOVERY: {
        "name": "T1123",
        "overview": "sid_run_cool_down_dist",
        "originId": "425895398452936705",
        "createTimestamp": 1586584214,
        "defaultOrder": 3,
    },
}

# Default source IDs (from COROS exercise library)
DEFAULT_SOURCE_ID = "425868113867882496"
DEFAULT_SOURCE_URL = "https://d31oxp44ddzkyk.cloudfront.net/source/source_default/0/5a9db1c3363348298351aaabfd70d0f5.jpg"
