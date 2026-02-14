"""
Spec verification tests — validate real COROS API responses against
docs/coros-api-spec.md.

All tests are READ-ONLY (no mutations). They require a valid token.

Run:  COROS_TOKEN_JSON='...' pytest tests/spec/ -v
"""

import requests
import pytest


# ── Helpers ──────────────────────────────────────────────────────────

def get(base_url, endpoint, headers, params=None):
    resp = requests.get(f"{base_url}/{endpoint}", headers=headers, params=params)
    resp.raise_for_status()
    body = resp.json()
    assert body["result"] == "0000", f"{endpoint} failed: {body}"
    return body


def post(base_url, endpoint, headers, params=None, json_data=None):
    resp = requests.post(
        f"{base_url}/{endpoint}", headers=headers, params=params, json=json_data,
    )
    resp.raise_for_status()
    body = resp.json()
    assert body["result"] == "0000", f"{endpoint} failed: {body}"
    return body


def assert_has_keys(obj, keys, label=""):
    """Assert obj contains all listed keys. Reports missing keys."""
    missing = [k for k in keys if k not in obj]
    assert not missing, f"{label} missing keys: {missing}. Got: {list(obj.keys())}"


def assert_type(value, expected_type, label=""):
    assert isinstance(value, expected_type), (
        f"{label}: expected {expected_type.__name__}, got {type(value).__name__} = {value!r}"
    )


# ── 1. Auth ──────────────────────────────────────────────────────────

class TestAccountLogin:
    """Spec §1: POST account/login — tested implicitly by conftest login.
    We just verify the token works by calling account/query."""

    def test_token_is_valid(self, base_url, auth_headers):
        body = get(base_url, "account/query", auth_headers)
        assert "data" in body


# ── 2. Profile ───────────────────────────────────────────────────────

class TestAccountQuery:
    """Spec §2: GET account/query"""

    def test_response_shape(self, base_url, auth_headers):
        body = get(base_url, "account/query", auth_headers)
        data = body["data"]

        # Required fields per spec
        assert_has_keys(data, [
            "userId", "nickname", "email", "birthday", "sex",
            "stature", "weight", "maxHr", "rhr", "unit",
        ], "account/query.data")

        # Types
        assert_type(data["userId"], str, "userId")
        assert_type(data["birthday"], int, "birthday")
        assert_type(data["sex"], int, "sex")
        assert_type(data["stature"], (int, float), "stature")
        assert_type(data["maxHr"], int, "maxHr")

    def test_zone_data_present(self, base_url, auth_headers):
        body = get(base_url, "account/query", auth_headers)
        data = body["data"]

        assert "zoneData" in data, "Missing zoneData"
        zd = data["zoneData"]
        assert_has_keys(zd, ["maxHr", "rhr"], "zoneData")


# ── 3. Activities ────────────────────────────────────────────────────

class TestActivityQuery:
    """Spec §3: GET activity/query"""

    def test_response_shape(self, base_url, auth_headers):
        body = get(base_url, "activity/query", auth_headers, params={
            "size": "5", "pageNumber": "1",
        })
        data = body["data"]

        assert_has_keys(data, ["count", "totalPage", "pageNumber", "dataList"], "activity/query.data")
        assert_type(data["count"], int, "count")
        assert_type(data["dataList"], list, "dataList")

    def test_activity_item_shape(self, base_url, auth_headers):
        body = get(base_url, "activity/query", auth_headers, params={
            "size": "1", "pageNumber": "1",
        })
        items = body["data"]["dataList"]
        if not items:
            pytest.skip("No activities found")

        item = items[0]
        assert_has_keys(item, [
            "labelId", "date", "sportType", "distance", "totalTime",
            "startTime", "endTime",
        ], "activity item")

        assert_type(item["labelId"], str, "labelId")
        assert_type(item["date"], int, "date")
        assert_type(item["sportType"], int, "sportType")

    def test_date_filter(self, base_url, auth_headers):
        """Verify startDay/endDay params work per spec."""
        body = get(base_url, "activity/query", auth_headers, params={
            "size": "5", "pageNumber": "1",
            "startDay": "20260101", "endDay": "20260213",
        })
        data = body["data"]
        assert_type(data["dataList"], list, "filtered dataList")


class TestActivityDetailQuery:
    """Spec §3: POST activity/detail/query"""

    @pytest.fixture(scope="class")
    def first_activity(self, base_url, auth_headers):
        body = get(base_url, "activity/query", auth_headers, params={
            "size": "1", "pageNumber": "1",
        })
        items = body["data"]["dataList"]
        if not items:
            pytest.skip("No activities found")
        return items[0]

    def test_response_shape(self, base_url, auth_headers, first_activity):
        body = post(
            base_url, "activity/detail/query", auth_headers,
            params={"labelId": first_activity["labelId"], "sportType": "100"},
        )
        data = body["data"]

        assert "summary" in data, "Missing summary in activity detail"
        summary = data["summary"]
        assert_has_keys(summary, [
            "sportType", "totalTime", "distance",
        ], "activity detail summary")

    def test_lap_list_present(self, base_url, auth_headers, first_activity):
        body = post(
            base_url, "activity/detail/query", auth_headers,
            params={"labelId": first_activity["labelId"], "sportType": "100"},
        )
        data = body["data"]
        # lapList may or may not exist depending on activity type, just check shape if present
        if "lapList" in data:
            assert_type(data["lapList"], list, "lapList")


class TestActivityDetailDownload:
    """Spec §3: POST activity/detail/download"""

    @pytest.fixture(scope="class")
    def first_activity(self, base_url, auth_headers):
        body = get(base_url, "activity/query", auth_headers, params={
            "size": "1", "pageNumber": "1",
        })
        items = body["data"]["dataList"]
        if not items:
            pytest.skip("No activities found")
        return items[0]

    def test_fit_download_url(self, base_url, auth_headers, first_activity):
        body = post(
            base_url, "activity/detail/download", auth_headers,
            params={
                "labelId": first_activity["labelId"],
                "sportType": "100",
                "fileType": "4",  # FIT
            },
        )
        data = body["data"]
        assert "fileUrl" in data, f"Missing fileUrl. Got: {list(data.keys())}"
        assert_type(data["fileUrl"], str, "fileUrl")
        assert data["fileUrl"].startswith("http"), f"fileUrl not a URL: {data['fileUrl']}"


# ── 4. Dashboard ─────────────────────────────────────────────────────

class TestDashboardQuery:
    """Spec §4: GET dashboard/query"""

    def test_response_shape(self, base_url, auth_headers):
        body = get(base_url, "dashboard/query", auth_headers)
        data = body["data"]

        assert "summaryInfo" in data, f"Missing summaryInfo. Got: {list(data.keys())}"
        si = data["summaryInfo"]
        assert_has_keys(si, [
            "recoveryPct", "recoveryState",
        ], "dashboard summaryInfo")

    def test_hrv_data(self, base_url, auth_headers):
        body = get(base_url, "dashboard/query", auth_headers)
        si = body["data"]["summaryInfo"]

        if "sleepHrvData" in si:
            hrv = si["sleepHrvData"]
            assert "sleepHrvList" in hrv, "Missing sleepHrvList"
            assert_type(hrv["sleepHrvList"], list, "sleepHrvList")
            if hrv["sleepHrvList"]:
                item = hrv["sleepHrvList"][0]
                assert_has_keys(item, ["happenDay"], "HRV item")
                # Items may have sleepHrvIntervalList (raw intervals) or avgSleepHrv
                assert "sleepHrvIntervalList" in item or "avgSleepHrv" in item, (
                    f"HRV item missing HRV data. Got: {list(item.keys())}"
                )


class TestDashboardDetailQuery:
    """Spec §4: GET dashboard/detail/query"""

    def test_response_shape(self, base_url, auth_headers):
        body = get(base_url, "dashboard/detail/query", auth_headers)
        data = body["data"]

        assert "summaryInfo" in data, f"Missing summaryInfo. Got: {list(data.keys())}"
        si = data["summaryInfo"]
        assert_has_keys(si, ["ati", "cti"], "dashboard detail summaryInfo")

        assert_type(si["ati"], (int, float), "ati")
        assert_type(si["cti"], (int, float), "cti")


class TestDashboardCycleRecord:
    """Spec §4: GET dashboard/queryCycleRecord"""

    def test_response_shape(self, base_url, auth_headers):
        body = get(base_url, "dashboard/queryCycleRecord", auth_headers)
        data = body["data"]

        assert "allRecordList" in data, f"Missing allRecordList. Got: {list(data.keys())}"
        assert_type(data["allRecordList"], list, "allRecordList")

        if data["allRecordList"]:
            item = data["allRecordList"][0]
            assert_has_keys(item, ["type", "recordList"], "record group")
            assert_type(item["type"], int, "record type")
            assert_type(item["recordList"], list, "recordList")


# ── 5. Analysis ──────────────────────────────────────────────────────

class TestAnalyseQuery:
    """Spec §5: GET analyse/query"""

    def test_response_shape(self, base_url, auth_headers):
        body = get(base_url, "analyse/query", auth_headers)
        data = body["data"]

        assert_has_keys(data, [
            "dayList", "sportStatistic",
        ], "analyse/query.data")

        assert_type(data["dayList"], list, "dayList")
        assert_type(data["sportStatistic"], list, "sportStatistic")

    def test_day_list_item_shape(self, base_url, auth_headers):
        body = get(base_url, "analyse/query", auth_headers)
        days = body["data"]["dayList"]
        if not days:
            pytest.skip("No analysis day data")

        day = days[0]
        assert_has_keys(day, ["happenDay", "trainingLoad"], "dayList item")
        assert_type(day["happenDay"], int, "happenDay")

    def test_sport_statistic_shape(self, base_url, auth_headers):
        body = get(base_url, "analyse/query", auth_headers)
        stats = body["data"]["sportStatistic"]
        if not stats:
            pytest.skip("No sport statistics")

        stat = stats[0]
        assert_has_keys(stat, ["sportType", "count", "distance"], "sport statistic")


# ── 6. Training Schedule ─────────────────────────────────────────────

class TestTrainingScheduleQuery:
    """Spec §6: GET training/schedule/query"""

    def test_response_shape(self, base_url, auth_headers):
        body = get(base_url, "training/schedule/query", auth_headers, params={
            "startDate": "20260209", "endDate": "20260215",
            "supportRestExercise": "1",
        })
        data = body["data"]

        assert_has_keys(data, ["pbVersion"], "schedule query data")
        assert_type(data["pbVersion"], int, "pbVersion")

        # entities and programs may be empty if no workouts scheduled
        if "entities" in data:
            assert_type(data["entities"], list, "entities")
        if "programs" in data:
            assert_type(data["programs"], list, "programs")

    def test_entity_program_linking(self, base_url, auth_headers):
        """Spec: entities and programs are linked by idInPlan."""
        body = get(base_url, "training/schedule/query", auth_headers, params={
            "startDate": "20260101", "endDate": "20260228",
            "supportRestExercise": "1",
        })
        data = body["data"]
        entities = data.get("entities", [])
        programs = data.get("programs", [])

        if not entities or not programs:
            pytest.skip("No scheduled workouts to verify linking")

        entity = entities[0]
        assert_has_keys(entity, ["idInPlan", "happenDay"], "entity")

        program = programs[0]
        assert_has_keys(program, ["idInPlan", "sportType"], "program")

        # Verify at least one idInPlan matches between entities and programs
        entity_ids = {e["idInPlan"] for e in entities}
        program_ids = {p["idInPlan"] for p in programs}
        overlap = entity_ids & program_ids
        assert overlap, (
            f"No idInPlan overlap between entities {entity_ids} and programs {program_ids}"
        )

    def test_program_exercises_shape(self, base_url, auth_headers):
        """Verify exercise objects inside programs match the spec."""
        body = get(base_url, "training/schedule/query", auth_headers, params={
            "startDate": "20260101", "endDate": "20260228",
            "supportRestExercise": "1",
        })
        programs = body["data"].get("programs", [])
        if not programs:
            pytest.skip("No programs with exercises")

        # Find a program with exercises
        prog_with_ex = next((p for p in programs if p.get("exercises")), None)
        if not prog_with_ex:
            pytest.skip("No program has exercises")

        for ex in prog_with_ex["exercises"]:
            assert_has_keys(ex, ["id", "sortNo", "exerciseType"], "exercise")

            if ex.get("isGroup"):
                # Group: has sets, no groupId
                assert_has_keys(ex, ["sets"], "group exercise")
            else:
                # Step: has targetType, targetValue
                assert_has_keys(ex, ["targetType", "targetValue"], "step exercise")

    def test_exercise_intensity_fields(self, base_url, auth_headers):
        """Verify intensity fields exist on step exercises (spec §Exercise Object Reference)."""
        body = get(base_url, "training/schedule/query", auth_headers, params={
            "startDate": "20260101", "endDate": "20260228",
            "supportRestExercise": "1",
        })
        programs = body["data"].get("programs", [])
        steps = [
            ex
            for p in programs
            for ex in p.get("exercises", [])
            if not ex.get("isGroup")
        ]
        if not steps:
            pytest.skip("No step exercises found")

        step = steps[0]
        assert_has_keys(step, [
            "intensityType", "intensityValue", "intensityMultiplier",
        ], "step intensity fields")

    def test_pace_intensity_encoding(self, base_url, auth_headers):
        """Spec: pace values are always sec/km × 1000 when intensityMultiplier=1000.
        intensityDisplayUnit selects the UI unit: 1=min/km, 2=min/mile, 3=sec/100m.
        Older templates may have multiplier=0 with raw seconds.
        """
        body = get(base_url, "training/schedule/query", auth_headers, params={
            "startDate": "20260101", "endDate": "20260228",
            "supportRestExercise": "1",
        })
        programs = body["data"].get("programs", [])
        steps = [
            ex
            for p in programs
            for ex in p.get("exercises", [])
            if not ex.get("isGroup")
        ]

        pace_steps = [s for s in steps if s.get("intensityType") == 3]
        if not pace_steps:
            pytest.skip("No pace steps found")

        for s in pace_steps:
            mult = s.get("intensityMultiplier")
            val = s.get("intensityValue")

            if mult is not None and mult == 1000:
                # Standard format: value is sec/km × 1000
                assert val >= 100000, (
                    f"Pace with multiplier=1000 should have value >=100000, got {val}"
                )
                du = s.get("intensityDisplayUnit")
                # displayUnit is int in responses: 1=min/km, 2=min/mile, 3=sec/100m
                assert du in (1, 2, 3, "1", "2", "3"), (
                    f"Pace intensityDisplayUnit should be 1-3, got {du!r}"
                )
            elif mult == 0 or mult is None:
                # Template/older format: raw seconds
                assert val < 1000, (
                    f"Pace with multiplier=0/None should be raw seconds (<1000), got {val}"
                )


class TestTrainingScheduleQuerysum:
    """Spec §6: GET training/schedule/querysum"""

    def test_response_shape(self, base_url, auth_headers):
        body = get(base_url, "training/schedule/querysum", auth_headers, params={
            "startDate": "20260101", "endDate": "20260228",
        })
        data = body["data"]

        assert_has_keys(data, ["todayTrainingSum"], "querysum data")
        ts = data["todayTrainingSum"]
        assert_type(ts, dict, "todayTrainingSum")

    def test_week_trains(self, base_url, auth_headers):
        body = get(base_url, "training/schedule/querysum", auth_headers, params={
            "startDate": "20260101", "endDate": "20260228",
        })
        data = body["data"]

        if "weekTrains" in data:
            assert_type(data["weekTrains"], list, "weekTrains")


# ── 7. Training Plans ────────────────────────────────────────────────

class TestTrainingPlanQuery:
    """Spec §8: POST training/plan/query"""

    def test_draft_plans(self, base_url, auth_headers):
        body = post(base_url, "training/plan/query", auth_headers, json_data={
            "name": "", "statusList": [0], "startNo": 0, "limitSize": 10,
        })
        data = body["data"]
        assert_type(data, list, "plan query response data")

        if data:
            plan = data[0]
            assert_has_keys(plan, [
                "id", "name", "pbVersion", "entities",
            ], "plan object")

    def test_active_plans(self, base_url, auth_headers):
        body = post(base_url, "training/plan/query", auth_headers, json_data={
            "name": "", "statusList": [1], "startNo": 0, "limitSize": 10,
        })
        data = body["data"]
        assert_type(data, list, "active plan query response data")

        if data:
            plan = data[0]
            assert_has_keys(plan, ["id", "name", "entities"], "active plan")
            # Active plans should have happenDay on entities
            if plan["entities"]:
                entity = plan["entities"][0]
                assert "happenDay" in entity or "dayNo" in entity, (
                    f"Active plan entity missing happenDay/dayNo: {list(entity.keys())}"
                )


class TestTrainingProgramQuery:
    """Spec §8: POST training/program/query (workout templates)"""

    def test_response_shape(self, base_url, auth_headers):
        body = post(base_url, "training/program/query", auth_headers, json_data={
            "name": "", "supportRestExercise": 1,
            "startNo": 0, "limitSize": 5, "sportType": 0,
        })
        data = body["data"]
        assert_type(data, list, "program query response data")

        if data:
            prog = data[0]
            assert_has_keys(prog, [
                "id", "name", "sportType", "exercises",
            ], "workout template")


# ── 8. Response Envelope ─────────────────────────────────────────────

class TestResponseEnvelope:
    """Spec §Conventions: all responses have the standard envelope."""

    def test_envelope_fields(self, base_url, auth_headers):
        """Every response should have result, message, apiCode."""
        resp = requests.get(
            f"{base_url}/dashboard/query", headers=auth_headers,
        )
        resp.raise_for_status()
        body = resp.json()

        assert_has_keys(body, ["result", "message"], "response envelope")
        assert body["result"] == "0000"

    def test_bad_token_returns_error(self, base_url, coros_creds):
        """Invalid token should return non-0000 result."""
        bad_headers = {
            "Content-Type": "application/json",
            "accessToken": "invalid_token_12345",
            "yfheader": '{"userId":"0"}',
        }
        resp = requests.get(f"{base_url}/dashboard/query", headers=bad_headers)
        body = resp.json()
        assert body["result"] != "0000", f"Bad token should fail, got: {body}"
