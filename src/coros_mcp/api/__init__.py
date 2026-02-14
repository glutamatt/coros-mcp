"""
High-Level API — Domain Model for COROS athlete coaching.

Every function returns a clean dict the LLM can reason about.
Composes with the Layer 2 SDK internally.

Modules:
    profile    — Who are you?       (biometrics, zones, thresholds)
    status     — How are you now?   (fitness, HRV, load, records)
    activities — What have you done? (past sessions, laps, totals)
    calendar   — What's coming up?  (scheduled workouts, adherence)
    workouts   — Build a session    (create, estimate, reschedule, delete)
    plans      — Build a plan       (create, activate, delete)
"""

# Model
from coros_mcp.api.model import Exercise

# Exercise translation
from coros_mcp.api.exercises import to_coros, from_coros, parse_pace, parse_hr

# Profile
from coros_mcp.api.profile import get_athlete_profile

# Status
from coros_mcp.api.status import (
    get_fitness_status,
    get_race_predictions,
    get_hrv_trend,
    get_training_load,
    get_sport_stats,
    get_personal_records,
)

# Activities
from coros_mcp.api.activities import (
    get_activities,
    get_activity_detail,
    get_activities_summary,
    get_download_url,
)

# Calendar
from coros_mcp.api.calendar import get_calendar, get_adherence

# Workouts
from coros_mcp.api.workouts import (
    create_workout,
    estimate_workout,
    reschedule_workout,
    delete_workout,
)

# Plans
from coros_mcp.api.plans import (
    list_plans,
    get_plan,
    create_plan,
    add_workout_to_plan,
    activate_plan,
    delete_plans,
)

__all__ = [
    # Model
    "Exercise",
    # Exercises
    "to_coros", "from_coros", "parse_pace", "parse_hr",
    # Profile
    "get_athlete_profile",
    # Status
    "get_fitness_status", "get_race_predictions", "get_hrv_trend",
    "get_training_load", "get_sport_stats", "get_personal_records",
    # Activities
    "get_activities", "get_activity_detail", "get_activities_summary", "get_download_url",
    # Calendar
    "get_calendar", "get_adherence",
    # Workouts
    "create_workout", "estimate_workout", "reschedule_workout", "delete_workout",
    # Plans
    "list_plans", "get_plan", "create_plan", "add_workout_to_plan", "activate_plan", "delete_plans",
]
