"""Tests for SDK types and constants."""

from coros_mcp.sdk.types import (
    SportType,
    ExerciseType,
    TargetType,
    TargetDisplayUnit,
    RestType,
    VersionStatus,
    FileType,
    ACTIVITY_SPORT_NAMES,
    SPORT_NAME_TO_CODE,
    EXERCISE_TEMPLATES,
    DEFAULT_SOURCE_ID,
)


class TestEnums:
    def test_sport_type_values(self):
        assert SportType.RUNNING == 1
        assert SportType.BIKE == 6
        assert SportType.POOL_SWIM == 9

    def test_exercise_type_values(self):
        assert ExerciseType.GROUP == 0
        assert ExerciseType.WARMUP == 1
        assert ExerciseType.INTERVAL == 2
        assert ExerciseType.COOLDOWN == 3
        assert ExerciseType.RECOVERY == 4

    def test_target_type_values(self):
        assert TargetType.DURATION == 2
        assert TargetType.DISTANCE == 5

    def test_version_status_values(self):
        assert VersionStatus.NEW == 1
        assert VersionStatus.MOVE_UPDATE == 2
        assert VersionStatus.DELETE == 3

    def test_file_type_values(self):
        assert FileType.FIT.value == "4"
        assert FileType.GPX.value == "1"


class TestMappings:
    def test_sport_name_to_code(self):
        assert SPORT_NAME_TO_CODE["running"] == SportType.RUNNING
        assert SPORT_NAME_TO_CODE["bike"] == SportType.BIKE
        assert SPORT_NAME_TO_CODE["cycling"] == SportType.BIKE
        assert SPORT_NAME_TO_CODE["swim"] == SportType.POOL_SWIM

    def test_activity_sport_names(self):
        assert ACTIVITY_SPORT_NAMES[1] == "Run"
        assert ACTIVITY_SPORT_NAMES[6] == "Bike"
        assert ACTIVITY_SPORT_NAMES[100] == "Other"

    def test_exercise_templates(self):
        warmup = EXERCISE_TEMPLATES[ExerciseType.WARMUP]
        assert warmup["name"] == "T1120"
        assert "originId" in warmup

    def test_default_source_id(self):
        assert DEFAULT_SOURCE_ID == "425868113867882496"
