"""
Athlete profile tool for COROS MCP server.

Biometrics, training zones, and physiological data.
"""

import json

from fastmcp import Context

from coros_mcp.client_factory import get_client
from coros_mcp.utils import coros_to_date


def register_tools(app):
    """Register profile tools with the MCP app."""

    @app.tool()
    async def get_athlete_profile(ctx: Context) -> str:
        """
        Get the athlete's full profile with biometrics and training zones.

        Returns height, weight, max HR, resting HR, LTHR, FTP,
        and all training zones (HR, pace, power). Essential context
        for all coaching decisions.

        Returns:
            JSON with athlete profile and training zones
        """
        client = get_client(ctx)
        data = client.get_account_full()

        zone_data = data.get("zoneData", {})

        result = {
            "identity": {
                "user_id": data.get("userId"),
                "nickname": data.get("nickname"),
                "email": data.get("email"),
                "birthday": coros_to_date(data.get("birthday")),
                "sex": data.get("sex"),
                "country": data.get("countryCode"),
            },
            "biometrics": {
                "height_cm": data.get("stature"),
                "weight_kg": data.get("weight"),
                "unit_system": data.get("unit"),
                "temperature_unit": data.get("temperatureUnit"),
            },
            "physiological": {
                "max_hr": zone_data.get("maxHr") or data.get("maxHr"),
                "resting_hr": zone_data.get("rhr") or data.get("rhr"),
                "lthr": zone_data.get("lthr"),
                "ltsp": zone_data.get("ltsp"),
                "ftp": zone_data.get("ftp"),
                "hr_zone_type": data.get("hrZoneType"),
            },
            "zones": {},
        }

        # HR zones
        hr_zones = zone_data.get("maxHrZone") or zone_data.get("lthrZone")
        if hr_zones:
            result["zones"]["heart_rate"] = hr_zones

        # Pace zones
        pace_zones = zone_data.get("ltspZone")
        if pace_zones:
            result["zones"]["pace"] = pace_zones

        # Power zones
        power_zones = zone_data.get("cyclePowerZone")
        if power_zones:
            result["zones"]["power"] = power_zones

        # Zone ranges
        for key in ("maxHrRange", "rhrRange", "lthrRange", "ltspRange", "ftpRange"):
            val = zone_data.get(key)
            if val:
                result["zones"][key] = val

        # Run scores (per-sport performance)
        run_scores = data.get("runScoreList", [])
        if run_scores:
            result["run_scores"] = [
                {
                    "sport_type": rs.get("type"),
                    "avg_pace": rs.get("avgPace"),
                    "distance": rs.get("distance"),
                    "distance_ratio": rs.get("distanceRatio"),
                    "training_load_ratio": rs.get("trainingLoadRatio"),
                }
                for rs in run_scores
            ]

        # Remove empty zones dict if nothing populated
        if not result["zones"]:
            del result["zones"]

        # Clean None values
        result = _clean_nones(result)

        return json.dumps(result, indent=2)

    return app


def _clean_nones(d):
    """Recursively remove None values from a dict."""
    if isinstance(d, dict):
        return {k: _clean_nones(v) for k, v in d.items() if v is not None}
    if isinstance(d, list):
        return [_clean_nones(i) for i in d]
    return d
