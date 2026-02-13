"""
Domain types for the COROS coaching API.

Only Exercise needs a dataclass — it's the structure the LLM builds
and needs validation. Workouts and plans stay as plain dicts.
"""

from dataclasses import dataclass, field
from typing import Optional


VALID_EXERCISE_TYPES = {"warmup", "interval", "cooldown", "recovery"}


@dataclass
class Exercise:
    """A single exercise block in a workout.

    The LLM builds these; we validate and convert to COROS protocol.
    Exactly one target (duration, distance_m, or distance_km) must be set
    unless the exercise is a recovery inside a repeat group.
    """
    type: str
    duration_minutes: Optional[float] = None
    distance_m: Optional[int] = None
    distance_km: Optional[float] = None
    repeats: Optional[int] = None
    rest_seconds: Optional[int] = None
    pace_per_km: Optional[str] = None
    hr_bpm: Optional[str] = None

    @classmethod
    def from_dict(cls, d: dict) -> "Exercise":
        """Create an Exercise from a plain dict (as the LLM would provide)."""
        return cls(
            type=d.get("type", "interval"),
            duration_minutes=d.get("duration_minutes"),
            distance_m=d.get("distance_m"),
            distance_km=d.get("distance_km"),
            repeats=d.get("repeats"),
            rest_seconds=d.get("rest_seconds"),
            pace_per_km=d.get("pace_per_km"),
            hr_bpm=d.get("hr_bpm"),
        )

    def validate(self):
        """Validate the exercise definition.

        Raises:
            ValueError: If the exercise is invalid.
        """
        if self.type not in VALID_EXERCISE_TYPES:
            raise ValueError(
                f"Invalid exercise type '{self.type}'. "
                f"Must be one of: {', '.join(sorted(VALID_EXERCISE_TYPES))}"
            )

        targets = sum(
            1 for t in (self.duration_minutes, self.distance_m, self.distance_km)
            if t is not None
        )
        if targets > 1:
            raise ValueError(
                "Exercise must have at most one target: "
                "duration_minutes, distance_m, or distance_km"
            )
        if targets == 0 and self.type != "recovery":
            raise ValueError(
                f"Exercise type '{self.type}' requires a target "
                "(duration_minutes, distance_m, or distance_km)"
            )

        if self.duration_minutes is not None and self.duration_minutes <= 0:
            raise ValueError("duration_minutes must be positive")
        if self.distance_m is not None and self.distance_m <= 0:
            raise ValueError("distance_m must be positive")
        if self.distance_km is not None and self.distance_km <= 0:
            raise ValueError("distance_km must be positive")

        if self.repeats is not None and self.repeats < 1:
            raise ValueError("repeats must be >= 1")
        if self.rest_seconds is not None and self.rest_seconds < 0:
            raise ValueError("rest_seconds must be >= 0")

        if self.pace_per_km is not None:
            _validate_pace_format(self.pace_per_km)
        if self.hr_bpm is not None:
            _validate_hr_format(self.hr_bpm)


def _validate_pace_format(s: str):
    """Validate pace format: 'M:SS' or 'M:SS-M:SS'."""
    parts = s.split("-")
    if len(parts) > 2:
        raise ValueError(f"Invalid pace format '{s}'. Use 'M:SS' or 'M:SS-M:SS'")
    for part in parts:
        part = part.strip()
        if ":" not in part:
            raise ValueError(f"Invalid pace '{part}'. Use 'M:SS' format")
        mins, secs = part.split(":", 1)
        try:
            int(mins)
            int(secs)
        except ValueError:
            raise ValueError(f"Invalid pace '{part}'. Use 'M:SS' format")


def _validate_hr_format(s: str):
    """Validate HR format: 'BPM' or 'BPM-BPM'."""
    parts = s.split("-")
    if len(parts) > 2:
        raise ValueError(f"Invalid HR format '{s}'. Use 'BPM' or 'BPM-BPM'")
    for part in parts:
        try:
            int(part.strip())
        except ValueError:
            raise ValueError(f"Invalid HR '{part}'. Must be an integer BPM")
