"""Tests for api/model.py — Exercise validation edge cases."""

import pytest

from coros_mcp.api.model import Exercise


class TestExerciseFromDict:
    def test_basic(self):
        ex = Exercise.from_dict({"type": "warmup", "duration_minutes": 10})
        assert ex.type == "warmup"
        assert ex.duration_minutes == 10

    def test_defaults(self):
        ex = Exercise.from_dict({"type": "interval"})
        assert ex.distance_m is None
        assert ex.distance_km is None
        assert ex.repeats is None

    def test_all_fields(self):
        ex = Exercise.from_dict({
            "type": "interval",
            "distance_m": 800,
            "repeats": 6,
            "rest_seconds": 90,
            "pace_per_km": "4:00-4:30",
            "hr_bpm": "160-170",
        })
        assert ex.distance_m == 800
        assert ex.repeats == 6
        assert ex.rest_seconds == 90
        assert ex.pace_per_km == "4:00-4:30"
        assert ex.hr_bpm == "160-170"


class TestValueUnitsAlias:
    """LLMs sometimes use {value, units} instead of canonical field names."""

    def test_value_units_minutes(self):
        ex = Exercise.from_dict({"type": "interval", "value": 2, "units": "minutes", "repeats": 8})
        assert ex.duration_minutes == 2
        assert ex.distance_m is None

    def test_value_units_meters(self):
        ex = Exercise.from_dict({"type": "interval", "value": 800, "units": "meters", "repeats": 6})
        assert ex.distance_m == 800
        assert ex.duration_minutes is None

    def test_value_units_km(self):
        ex = Exercise.from_dict({"type": "interval", "value": 1.5, "units": "km"})
        assert ex.distance_km == 1.5

    def test_canonical_takes_precedence(self):
        """If canonical field is already set, {value, units} is ignored."""
        ex = Exercise.from_dict({"type": "interval", "duration_minutes": 5, "value": 2, "units": "minutes"})
        assert ex.duration_minutes == 5


class TestExerciseValidation:
    def test_valid_warmup(self):
        ex = Exercise(type="warmup", duration_minutes=10)
        ex.validate()  # should not raise

    def test_valid_interval_distance(self):
        ex = Exercise(type="interval", distance_m=800, repeats=6, rest_seconds=90)
        ex.validate()

    def test_valid_cooldown_km(self):
        ex = Exercise(type="cooldown", distance_km=2.0)
        ex.validate()

    def test_valid_recovery_no_target(self):
        """Recovery is allowed without a target."""
        ex = Exercise(type="recovery")
        ex.validate()

    def test_invalid_type(self):
        ex = Exercise(type="sprint", duration_minutes=5)
        with pytest.raises(ValueError, match="Invalid exercise type"):
            ex.validate()

    def test_multiple_targets(self):
        ex = Exercise(type="interval", duration_minutes=10, distance_m=800)
        with pytest.raises(ValueError, match="at most one target"):
            ex.validate()

    def test_no_target_non_recovery(self):
        ex = Exercise(type="warmup")
        with pytest.raises(ValueError, match="requires a target"):
            ex.validate()

    def test_negative_duration(self):
        ex = Exercise(type="warmup", duration_minutes=-5)
        with pytest.raises(ValueError, match="duration_minutes must be positive"):
            ex.validate()

    def test_zero_distance_m(self):
        ex = Exercise(type="interval", distance_m=0)
        with pytest.raises(ValueError, match="distance_m must be positive"):
            ex.validate()

    def test_negative_distance_km(self):
        ex = Exercise(type="interval", distance_km=-1.0)
        with pytest.raises(ValueError, match="distance_km must be positive"):
            ex.validate()

    def test_invalid_repeats(self):
        ex = Exercise(type="interval", distance_m=400, repeats=0)
        with pytest.raises(ValueError, match="repeats must be >= 1"):
            ex.validate()

    def test_negative_rest(self):
        ex = Exercise(type="interval", distance_m=400, repeats=3, rest_seconds=-10)
        with pytest.raises(ValueError, match="rest_seconds must be >= 0"):
            ex.validate()

    def test_invalid_pace_format(self):
        ex = Exercise(type="interval", distance_m=400, pace_per_km="five minutes")
        with pytest.raises(ValueError, match="Invalid pace"):
            ex.validate()

    def test_valid_pace_range(self):
        ex = Exercise(type="interval", distance_m=400, pace_per_km="4:30-5:00")
        ex.validate()

    def test_invalid_hr_format(self):
        ex = Exercise(type="interval", distance_m=400, hr_bpm="high")
        with pytest.raises(ValueError, match="Invalid HR"):
            ex.validate()

    def test_valid_hr_range(self):
        ex = Exercise(type="interval", distance_m=400, hr_bpm="150-160")
        ex.validate()

    def test_valid_hr_single(self):
        ex = Exercise(type="interval", distance_m=400, hr_bpm="155")
        ex.validate()
