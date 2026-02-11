"""
Tests for COROS MCP utility functions.
"""

from coros_mcp.utils import (
    date_to_coros,
    coros_to_date,
    format_duration,
    format_pace,
    format_distance,
    get_sport_name,
)


class TestDateConversions:
    def test_date_to_coros(self):
        assert date_to_coros("2026-02-11") == 20260211

    def test_date_to_coros_start_of_year(self):
        assert date_to_coros("2026-01-01") == 20260101

    def test_date_to_coros_end_of_year(self):
        assert date_to_coros("2025-12-31") == 20251231

    def test_coros_to_date(self):
        assert coros_to_date(20260211) == "2026-02-11"

    def test_coros_to_date_none(self):
        assert coros_to_date(None) is None

    def test_coros_to_date_zero(self):
        assert coros_to_date(0) is None

    def test_coros_to_date_invalid_length(self):
        assert coros_to_date(2026) is None

    def test_roundtrip(self):
        assert coros_to_date(date_to_coros("2026-02-11")) == "2026-02-11"


class TestFormatDuration:
    def test_hours_minutes_seconds(self):
        assert format_duration(3661) == "1h01m01s"

    def test_minutes_seconds(self):
        assert format_duration(1530) == "25m30s"

    def test_seconds_only(self):
        assert format_duration(45) == "45s"

    def test_zero(self):
        assert format_duration(0) == "0s"

    def test_none(self):
        assert format_duration(None) == "0s"

    def test_exact_hour(self):
        assert format_duration(3600) == "1h00m00s"

    def test_large_duration(self):
        assert format_duration(7265) == "2h01m05s"


class TestFormatPace:
    def test_normal_pace(self):
        assert format_pace(330) == "5:30/km"

    def test_fast_pace(self):
        assert format_pace(210) == "3:30/km"

    def test_slow_pace(self):
        assert format_pace(420) == "7:00/km"

    def test_zero(self):
        assert format_pace(0) is None

    def test_none(self):
        assert format_pace(None) is None


class TestFormatDistance:
    def test_kilometers(self):
        assert format_distance(10000) == "10.0 km"

    def test_meters(self):
        assert format_distance(800) == "800 m"

    def test_decimal_km(self):
        assert format_distance(5500) == "5.5 km"

    def test_zero(self):
        assert format_distance(0) == "0 m"

    def test_none(self):
        assert format_distance(None) == "0 m"

    def test_exact_1km(self):
        assert format_distance(1000) == "1.0 km"


class TestGetSportName:
    def test_run(self):
        assert get_sport_name(1) == "Run"

    def test_bike(self):
        assert get_sport_name(6) == "Bike"

    def test_swim(self):
        assert get_sport_name(9) == "Pool Swim"

    def test_strength(self):
        assert get_sport_name(16) == "Strength"

    def test_unknown(self):
        assert get_sport_name(999) == "Sport_999"

    def test_other(self):
        assert get_sport_name(100) == "Other"
