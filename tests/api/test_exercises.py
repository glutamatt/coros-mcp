"""Tests for api/exercises.py — COROS encoding/decoding."""

import pytest

from coros_mcp.api.exercises import to_coros, from_coros, parse_pace, parse_hr
from coros_mcp.api.model import Exercise
from coros_mcp.sdk.types import TargetType, TargetDisplayUnit, ExerciseType


class TestToCoros:
    def test_simple_warmup_duration(self):
        """Single warmup = simple workout."""
        exercises = [{"type": "warmup", "duration_minutes": 15}]
        result, is_simple = to_coros(exercises, "running")
        assert is_simple is True
        assert len(result) == 1
        ex = result[0]
        assert ex["exerciseType"] == ExerciseType.WARMUP
        assert ex["targetType"] == TargetType.DURATION
        assert ex["targetValue"] == 900  # 15 * 60
        assert ex["targetDisplayUnit"] == TargetDisplayUnit.SECONDS

    def test_distance_km_centimeters(self):
        """distance_km is encoded in centimeters."""
        exercises = [{"type": "cooldown", "distance_km": 2.5}]
        result, is_simple = to_coros(exercises, "running")
        assert is_simple is True
        ex = result[0]
        assert ex["targetType"] == TargetType.DISTANCE
        assert ex["targetValue"] == 250000  # 2.5 km × 100000 = 250000 cm
        assert ex["targetDisplayUnit"] == TargetDisplayUnit.KILOMETERS

    def test_distance_m_centimeters(self):
        """distance_m is encoded in centimeters."""
        exercises = [{"type": "interval", "distance_m": 400}]
        result, is_simple = to_coros(exercises, "running")
        # Single interval = not simple
        assert is_simple is False
        ex = result[0]
        assert ex["targetType"] == TargetType.DISTANCE
        assert ex["targetValue"] == 40000  # 400 m × 100 = 40000 cm
        assert ex["targetDisplayUnit"] == TargetDisplayUnit.METERS

    def test_complex_workout_structure(self):
        """Full warmup + intervals + cooldown workout."""
        exercises = [
            {"type": "warmup", "duration_minutes": 15},
            {"type": "interval", "distance_m": 800, "repeats": 6, "rest_seconds": 90},
            {"type": "cooldown", "duration_minutes": 10},
        ]
        result, is_simple = to_coros(exercises, "running")
        assert is_simple is False

        # Should produce: warmup, group, work, recovery, cooldown = 5 exercises
        assert len(result) == 5

        # Warmup
        assert result[0]["exerciseType"] == ExerciseType.WARMUP
        assert result[0]["isGroup"] is False
        assert result[0]["id"] == 1

        # Group
        assert result[1]["isGroup"] is True
        assert result[1]["sets"] == 6
        assert result[1]["restValue"] == 90
        assert result[1]["id"] == 2

        # Work step inside group
        assert result[2]["exerciseType"] == ExerciseType.INTERVAL
        assert result[2]["groupId"] == 2  # references group
        assert result[2]["targetValue"] == 80000  # 800m in cm
        assert result[2]["id"] == 3

        # Recovery step inside group
        assert result[3]["exerciseType"] == ExerciseType.RECOVERY
        assert result[3]["groupId"] == 2
        assert result[3]["targetValue"] == 90  # rest seconds
        assert result[3]["id"] == 4

        # Cooldown
        assert result[4]["exerciseType"] == ExerciseType.COOLDOWN
        assert result[4]["id"] == 5

    def test_pace_encoding(self):
        """Pace target: sec/km × 1000."""
        exercises = [{"type": "interval", "distance_m": 1000, "pace_per_km": "4:30-5:00"}]
        result, _ = to_coros(exercises, "running")
        ex = result[0]
        assert ex["intensityType"] == 3
        assert ex["intensityValue"] == 270000  # 4:30 = 270s × 1000
        assert ex["intensityValueExtend"] == 300000  # 5:00 = 300s × 1000
        assert ex["intensityMultiplier"] == 1000

    def test_hr_encoding(self):
        """HR target: BPM values."""
        exercises = [{"type": "interval", "distance_m": 1000, "hr_bpm": "150-160"}]
        result, _ = to_coros(exercises, "running")
        ex = result[0]
        assert ex["intensityType"] == 2
        assert ex["intensityValue"] == 150
        assert ex["intensityValueExtend"] == 160

    def test_sort_no_sharing(self):
        """Group and its first child share sortNo."""
        exercises = [{"type": "interval", "distance_m": 400, "repeats": 4, "rest_seconds": 60}]
        result, _ = to_coros(exercises, "running")
        group = result[0]
        work = result[1]
        assert group["sortNo"] == work["sortNo"]

    def test_exercise_objects(self):
        """Accepts Exercise dataclass objects."""
        exercises = [Exercise(type="warmup", duration_minutes=10)]
        result, is_simple = to_coros(exercises, "running")
        assert is_simple is True
        assert result[0]["targetValue"] == 600

    def test_unknown_sport_raises(self):
        with pytest.raises(ValueError, match="Unknown sport"):
            to_coros([{"type": "warmup", "duration_minutes": 10}], "badminton")

    def test_invalid_exercise_raises(self):
        with pytest.raises(ValueError, match="Invalid exercise type"):
            to_coros([{"type": "sprint", "duration_minutes": 5}], "running")

    def test_repeats_no_rest(self):
        """Repeat group without rest doesn't add recovery step."""
        exercises = [{"type": "interval", "distance_m": 400, "repeats": 3}]
        result, _ = to_coros(exercises, "running")
        # group + work = 2 (no recovery)
        assert len(result) == 2
        assert result[0]["restType"] == 3  # NO_REST


class TestFromCoros:
    def test_basic_step(self):
        coros = [{
            "isGroup": False,
            "exerciseType": 1,
            "targetType": 2,
            "targetValue": 600,
            "targetDisplayUnit": 0,
            "intensityType": 0,
        }]
        result = from_coros(coros)
        assert len(result) == 1
        assert result[0]["type"] == "warmup"
        assert result[0]["duration_seconds"] == 600
        assert result[0]["duration_display"] == "10m00s"

    def test_distance_centimeters(self):
        """Distance values are in centimeters."""
        coros = [{
            "isGroup": False,
            "exerciseType": 2,
            "targetType": 5,
            "targetValue": 80000,  # 800m in cm
            "targetDisplayUnit": 2,
            "intensityType": 0,
        }]
        result = from_coros(coros)
        assert result[0]["distance_m"] == 800

    def test_distance_km(self):
        coros = [{
            "isGroup": False,
            "exerciseType": 2,
            "targetType": 5,
            "targetValue": 500000,  # 5km in cm
            "targetDisplayUnit": 1,
            "intensityType": 0,
        }]
        result = from_coros(coros)
        assert result[0]["distance_km"] == 5.0

    def test_group(self):
        coros = [{
            "isGroup": True,
            "id": 1,
            "exerciseType": 0,
            "sets": 5,
            "restType": 0,
            "restValue": 60,
        }]
        result = from_coros(coros)
        assert result[0]["type"] == "repeat"
        assert result[0]["repeats"] == 5
        assert result[0]["rest_seconds"] == 60

    def test_pace_from_coros(self):
        coros = [{
            "isGroup": False,
            "exerciseType": 2,
            "targetType": 5,
            "targetValue": 100000,
            "targetDisplayUnit": 1,
            "intensityType": 3,
            "intensityValue": 300000,
            "intensityValueExtend": 330000,
            "intensityMultiplier": 1000,
        }]
        result = from_coros(coros)
        assert result[0]["pace_per_km"] == "5:00-5:30"

    def test_hr_from_coros(self):
        coros = [{
            "isGroup": False,
            "exerciseType": 2,
            "targetType": 2,
            "targetValue": 300,
            "targetDisplayUnit": 0,
            "intensityType": 2,
            "intensityValue": 150,
            "intensityValueExtend": 160,
        }]
        result = from_coros(coros)
        assert result[0]["hr_bpm"] == "150-160"


class TestParsePace:
    def test_single(self):
        low, high = parse_pace("5:00")
        assert low == 300000
        assert high == 300000

    def test_range(self):
        low, high = parse_pace("4:30-5:00")
        assert low == 270000
        assert high == 300000

    def test_fast_pace(self):
        low, high = parse_pace("3:45")
        assert low == 225000


class TestParseHr:
    def test_single(self):
        low, high = parse_hr("155")
        assert low == 155
        assert high == 155

    def test_range(self):
        low, high = parse_hr("150-160")
        assert low == 150
        assert high == 160
