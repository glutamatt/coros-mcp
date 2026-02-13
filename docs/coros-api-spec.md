# COROS Training Hub API Specification

> Ground truth reference for all COROS endpoints used by this MCP server.
> Verified against real HAR captures (2026-02-13) and live API responses.

## Conventions

- **Base URL:** `$BASE` = `https://teameuapi.coros.com` (EU region, default)
  - Global: `https://teamapi.coros.com`
  - China: `https://teamapi.coros.com.cn`
- **Auth headers** (all authenticated requests):
  ```
  Content-Type: application/json
  accessToken: $TOKEN
  yfheader: {"userId":"$USER_ID"}
  ```
- **Response envelope:** All responses follow:
  ```json
  {"result": "0000", "message": "OK", "apiCode": "...", "data": {...}}
  ```
  `result != "0000"` means error. Common: `"1030"` = invalid credentials.
- **Date format:** COROS uses `YYYYMMDD` integers (e.g. `20260213`). MCP tools accept `YYYY-MM-DD` strings and convert.
- **Distance:** API returns meters (or meters×1000 for pace). Display in km.

---

## 1. Auth

### POST account/login

Authenticate with COROS. No auth headers required.

**Request body:**
```json
{
  "account": "user@email.com",
  "accountType": 2,
  "pwd": "md5_hex(password)"
}
```

Password is plain MD5 hash of the password string (no salt prepended).

**Response data:**
```json
{
  "accessToken": "string",
  "userId": "string",
  "nickname": "string",
  "email": "string",
  "headPic": "url_string",
  "countryCode": "FR",
  "birthday": 19900101
}
```

**curl:**
```bash
curl -X POST "$BASE/account/login" \
  -H "Content-Type: application/json" \
  -d '{"account":"user@email.com","accountType":2,"pwd":"'$(echo -n "password" | md5sum | cut -d' ' -f1)'"}'
```

---

## 2. Profile

### GET account/query

Get full account profile including biometrics and training zones.

**Response data:**
```json
{
  "userId": "string",
  "nickname": "string",
  "email": "string",
  "birthday": 19900101,
  "sex": 1,
  "countryCode": "FR",
  "stature": 183.0,
  "weight": 75.0,
  "maxHr": 190,
  "rhr": 52,
  "unit": 0,
  "temperatureUnit": 0,
  "hrZoneType": 1,
  "zoneData": {
    "maxHr": 190,
    "rhr": 52,
    "lthr": 165,
    "ltsp": 285,
    "ftp": 250,
    "maxHrZone": [114, 133, 152, 171, 190],
    "lthrZone": [...],
    "ltspZone": [400, 350, 300, 270, 240],
    "cyclePowerZone": [...]
  },
  "runScoreList": [
    {"type": 1, "avgPace": 320, "distance": 45000, "distanceRatio": 0.8, "trainingLoadRatio": 0.7}
  ]
}
```

**curl:**
```bash
curl "$BASE/account/query" \
  -H "Content-Type: application/json" \
  -H "accessToken: $TOKEN" \
  -H "yfheader: {\"userId\":\"$USER_ID\"}"
```

---

## 3. Activities

### GET activity/query

Paginated activity list.

**Query params:**

| Param | Type | Required | Notes |
|-------|------|----------|-------|
| `size` | string | yes | Page size (e.g. "20") |
| `pageNumber` | string | yes | 1-indexed page |
| `startDay` | string | no | YYYYMMDD filter start |
| `endDay` | string | no | YYYYMMDD filter end |
| `modeList` | string | no | Activity mode filter |

**Response data:**
```json
{
  "count": 42,
  "totalPage": 3,
  "pageNumber": 1,
  "dataList": [
    {
      "labelId": "string",
      "date": 20260213,
      "name": "Morning Run",
      "sportType": 1,
      "distance": 10000.0,
      "totalTime": 3600,
      "workoutTime": 3550,
      "trainingLoad": 85,
      "startTime": 1739500800,
      "endTime": 1739504400,
      "device": "PACE 3",
      "imageUrl": "..."
    }
  ]
}
```

**curl:**
```bash
curl "$BASE/activity/query?size=20&pageNumber=1&startDay=20260201&endDay=20260213" \
  -H "accessToken: $TOKEN" -H "yfheader: {\"userId\":\"$USER_ID\"}"
```

### POST activity/detail/query

Full activity details.

**Query params:** `labelId`, `sportType: "100"` (always 100)

**Response data:**
```json
{
  "summary": {
    "name": "...", "sportType": 1, "sportMode": 1,
    "startTimestamp": 1739500800, "endTimestamp": 1739504400,
    "totalTime": 3600, "workoutTime": 3550, "pauseTime": 50,
    "distance": 10000.0, "avgPace": 350, "avgSpeed": 2.78,
    "avgHr": 145, "maxHr": 165, "avgCadence": 175, "maxCadence": 185,
    "elevGain": 50, "totalDescent": 45, "avgElev": 100, "maxElev": 120, "minElev": 80,
    "avgPower": 220, "maxPower": 280, "np": 230,
    "calories": 350, "trainingLoad": 85,
    "aerobicEffect": 3.2, "anaerobicEffect": 1.5,
    "avgStepLen": 110, "avgGroundTime": 250, "avgVertRatio": 8.5
  },
  "lapList": [{"lapItemList": [{"lapIndex": 1, "distance": 1000, "time": 360, "avgPace": 360, "avgHr": 140, ...}]}],
  "zoneList": [{"type": 1, "zoneItemList": [{"zoneIndex": 1, "leftScope": 100, "rightScope": 120, "second": 120, "percent": 7}]}],
  "weather": {"temperature": 15, "bodyFeelTemp": 14, "humidity": 65, "windSpeed": 3.5}
}
```

### POST activity/detail/download

Get download URL for an activity file.

**Query params:** `labelId`, `sportType: "100"`, `fileType` (0=CSV, 1=GPX, 2=KML, 3=TCX, 4=FIT)

**Response data:** `{"fileUrl": "https://..."}`

### GET activity/delete

Delete an activity.

**Query params:** `labelId`

---

## 4. Dashboard

### GET dashboard/query

Main fitness dashboard summary.

**Response data:**
```json
{
  "summaryInfo": {
    "recoveryPct": 85, "recoveryState": 2, "fullRecoveryHours": 12,
    "aerobicEnduranceScore": 72, "anaerobicCapacityScore": 45,
    "anaerobicEnduranceScore": 55, "lactateThresholdCapacityScore": 68,
    "staminaLevel": 75, "staminaLevelChange": 2, "staminaLevelRanking": 3,
    "rhr": 52, "lthr": 165, "ltsp": 285,
    "sleepHrvData": {
      "sleepHrvList": [
        {"happenDay": 20260211, "sleepHrvIntervalList": [5, 61, 69, 83]}
      ]
    }
  }
}
```

### GET dashboard/detail/query

Detailed dashboard with ATI/CTI and current week records.

**Response data:**
```json
{
  "summaryInfo": {
    "ati": 85, "cti": 72, "tiredRateNew": 0.6,
    "trainingLoadRatio": 1.1, "trainingLoadRatioState": 2,
    "recomendTlInDays": 120
  },
  "currentWeekRecord": {"distanceRecord": 25000, "durationRecord": 7200, "tlRecord": 350},
  "detailList": [], "sportDataList": []
}
```

### GET dashboard/queryCycleRecord

Personal records by period.

**Response data:**
```json
{
  "allRecordList": [
    {
      "type": 1,
      "recordList": [{"happenDay": 20260210, "sportType": 1, "type": 1, "record": 1200, "labelId": "rec1"}]
    }
  ]
}
```

Period types: 1=week, 2=month, 3=year, 4=all-time

---

## 5. Analysis

### GET analyse/query

Comprehensive training analysis.

**Response data:**
```json
{
  "dayList": [
    {"happenDay": 20260210, "trainingLoad": 85, "distance": 10000, "duration": 3600,
     "vo2max": 52, "staminaLevel": 75, "rhr": 52, "ati": 85, "cti": 72,
     "tiredRateNew": 0.6, "recomendTlMin": 80, "recomendTlMax": 130}
  ],
  "weekList": [
    {"firstDayOfWeek": 20260203, "trainingLoad": 350, "recomendTlMin": 300, "recomendTlMax": 450}
  ],
  "t7dayList": [
    {"vo2max": 52, "staminaLevel": 75, "staminaLevel7d": 74,
     "tiredRateNew": 0.6, "trainingLoadRatio": 1.1, "trainingLoadRatioState": 2}
  ],
  "sportStatistic": [
    {"sportType": 1, "count": 5, "distance": 45000, "duration": 14400, "avgHeartRate": 148, "trainingLoad": 350}
  ],
  "tlIntensity": {
    "detailList": [
      {"periodLowPct": 60, "periodLowValue": 200, "periodMediumPct": 25,
       "periodMediumValue": 100, "periodHighPct": 15, "periodHighValue": 50}
    ]
  },
  "trainingWeekStageList": [{"firstDayOfWeek": 20260203, "stage": 2}]
}
```

---

## 6. Training Schedule

### GET training/schedule/query

Get training plan for a date range. Returns entities (dates) and programs (workout content) as separate arrays, linked by `idInPlan`.

**Query params:**

| Param | Type | Notes |
|-------|------|-------|
| `startDate` | string | YYYYMMDD |
| `endDate` | string | YYYYMMDD |
| `supportRestExercise` | string | Always `"1"` |

**Response data:**
```json
{
  "id": "460904915775176706",
  "name": "My Plan",
  "pbVersion": 5,
  "maxIdInPlan": "10",
  "maxPlanProgramId": "10",
  "entities": [
    {
      "id": "entity-sys-id",
      "idInPlan": "5",
      "planId": "460904915775176706",
      "planProgramId": "5",
      "happenDay": 20260212,
      "dayNo": 626,
      "sortNo": 1,
      "sortNoInPlan": 0,
      "sortNoInSchedule": 1,
      "exerciseBarChart": [...]
    }
  ],
  "programs": [
    {
      "id": "prog-sys-id",
      "idInPlan": "5",
      "name": "Easy Run",
      "sportType": 1,
      "planDistance": 8000,
      "planDuration": 2400,
      "planTrainingLoad": 60,
      "actualDistance": 0,
      "actualDuration": 0,
      "actualTrainingLoad": 0,
      "exercises": [...]
    }
  ],
  "sportDatasNotInPlan": [
    {"name": "Extra Run", "sportType": 1, "happenDay": 20260211,
     "distance": 5000, "duration": 1800, "trainingLoad": 45, "labelId": "act1"}
  ],
  "weekStages": [
    {"firstDayInWeek": 20260209, "stage": 2, "trainSum": 300}
  ]
}
```

**Key:** Programs do NOT have `happenDay`. Dates live on entities. Link via `idInPlan`.

### GET training/schedule/querysum

Actual vs planned training summary.

**Query params:** `startDate`, `endDate` (YYYYMMDD strings)

**Response data:**
```json
{
  "todayTrainingSum": {
    "actualDistance": 5000, "planDistance": 8000,
    "actualDuration": 1800, "planDuration": 2400,
    "actualTrainingLoad": 45, "planTrainingLoad": 60,
    "actualAti": 85, "actualCti": 72, "actualTiredRateNew": 0.6
  },
  "weekTrains": [
    {"firstDayInWeek": 20260203, "weekTrainSum": {"actualDistance": 40000, "planDistance": 45000, ...}}
  ],
  "dayTrainSums": [
    {"happenDay": 20260210, "dayTrainSum": {"actualDistance": 10000, "planDistance": 10000, ...}}
  ]
}
```

### POST training/schedule/update

Create, move, or delete scheduled workouts. The central mutation endpoint.

**Request body:**
```json
{
  "pbVersion": 5,
  "entities": [...],
  "programs": [...],
  "versionObjects": [{"id": ..., "status": ..., ...}]
}
```

**versionObjects patterns:**

| Operation | Status | Fields |
|-----------|--------|--------|
| **Create** | `1` | `{id: idInPlan, status: 1}` |
| **Move/Update** | `2` | `{id: idInPlan, status: 2, planProgramId: idInPlan, planId: planId}` |
| **Delete** | `3` | `{id: idInPlan, status: 3, planProgramId: idInPlan, planId: planId}` |

For **Create**: entities and programs arrays contain the new workout data.
For **Move/Update**: entities and programs contain the updated workout data (full objects from server + modifications). Entity `happenDay` changed for date moves.
For **Delete**: entities and programs arrays are empty (or omitted). Only versionObjects needed.

**Response:** Standard envelope with `result: "0000"` on success.

---

## 7. Workout Builder

### POST training/program/estimate

Preview training load before creating a workout. Lean payload — no userId/authorId.

**Request body:**
```json
{
  "entity": {
    "happenDay": "20260223",
    "idInPlan": 25,
    "sortNo": 0, "dayNo": 0, "sortNoInPlan": 0, "sortNoInSchedule": 0
  },
  "program": {
    "idInPlan": 25,
    "name": "Workout Name",
    "sportType": 1,
    "subType": 0,
    "totalSets": 1,
    "sets": 1,
    "exerciseNum": "",
    "targetType": "",
    "targetValue": "",
    "version": 0,
    "simple": true,
    "exercises": [...],
    "access": 1,
    "essence": 0, "estimatedTime": 0, "originEssence": 0,
    "overview": "",
    "type": 0, "unit": 0,
    "pbVersion": 2,
    "sourceId": "425868113867882496",
    "sourceUrl": "https://d31oxp44ddzkyk.cloudfront.net/source/source_default/0/5a9db1c3363348298351aaabfd70d0f5.jpg",
    "referExercise": {"intensityType": 0, "hrType": 0, "valueType": 0},
    "poolLengthId": 1, "poolLength": 2500, "poolLengthUnit": 2
  }
}
```

**Response data:**
```json
{
  "distance": "90909.00",
  "distanceDisplayUnit": 1,
  "duration": 300,
  "pitch": 0,
  "sets": 1,
  "trainingLoad": 23
}
```

Note: `distance` is a **string** with 2 decimals, in meters.

### POST training/program/calculate

Full workout calculation with bar chart data. Flat program object (not wrapped).

**Request body (new workout):**
```json
{
  "access": 1,
  "authorId": "0",
  "createTimestamp": 0,
  "distance": 0, "duration": 0,
  "essence": 0, "estimatedType": 0, "estimatedValue": 0,
  "exerciseNum": 0,
  "exercises": [...],
  "headPic": "",
  "id": "0", "idInPlan": "0",
  "name": "Workout Name",
  "nickname": "",
  "originEssence": 0, "overview": "",
  "pbVersion": 2, "planIdIndex": 0,
  "poolLength": 2500, "profile": "",
  "referExercise": {"intensityType": 0, "hrType": 0, "valueType": 0},
  "sex": 0, "shareUrl": "",
  "simple": false,
  "sourceUrl": "...",
  "sportType": 1,
  "star": 0,
  "subType": 65535,
  "targetType": 0, "targetValue": 0,
  "thirdPartyId": 0, "totalSets": 0, "trainingLoad": 0,
  "type": 0, "unit": 0,
  "userId": "0", "version": 0,
  "videoCoverUrl": "", "videoUrl": "",
  "fastIntensityTypeName": "",
  "poolLengthId": 1, "poolLengthUnit": 2,
  "sourceId": "425868113867882496"
}
```

For **existing workout** recalculation: same structure but with real `authorId`, `createTimestamp`, `distance`, `duration`, `exerciseBarChart`, `exerciseNum`, `estimatedDistance`, `estimatedTime`, `estimatedType`, `estimatedValue`.

**Response data:**
```json
{
  "actualDistance": "0", "actualDuration": 0,
  "actualElevGain": 0, "actualPitch": 0, "actualTrainingLoad": 0,
  "distanceDisplayUnit": 1,
  "exerciseBarChart": [
    {"exerciseId": "1", "exerciseType": 2, "height": 103.0, "name": "T3001",
     "targetType": 2, "targetValue": 300, "value": 300.0, "width": 100.0, "widthFill": 0.0}
  ],
  "planDistance": "90909.00",
  "planDuration": 300,
  "planElevGain": 0,
  "planPitch": 0,
  "planSets": 1,
  "planTrainingLoad": 23
}
```

---

## 8. Training Plans

Plans are templates that can be "executed" (applied to the calendar). A plan contains entities (which day a workout falls on, as relative `dayNo` offsets) and programs (the workout content).

### POST training/plan/query

List training plans.

**Request body:**
```json
{
  "name": "",
  "statusList": [0],
  "startNo": 0,
  "limitSize": 10
}
```

| statusList | Meaning |
|------------|---------|
| `[0]` | Draft/template plans (not yet scheduled) |
| `[1]` | Active/scheduled plans (applied to calendar) |

**Response data:** Array of plan objects:
```json
[
  {
    "id": "475403419167932916",
    "name": "My Training Plan",
    "overview": "Plan description",
    "access": 1,
    "authorId": "460904900742627333",
    "category": 0,
    "createTime": "2026-02-13 20:49:06",
    "updateTime": "2026-02-13 20:49:06",
    "pbVersion": 2,
    "planIcon": 1,
    "status": 0,
    "totalDay": 42,
    "maxWeeks": 1,
    "minWeeks": 1,
    "maxIdInPlan": "4",
    "maxPlanProgramId": "4",
    "executeStatus": 0,
    "inSchedule": 0,
    "entities": [
      {
        "dayNo": 10,
        "executeStatus": 0,
        "id": "...",
        "idInPlan": "1",
        "planId": "475403419167932916",
        "planProgramId": "1",
        "sortNo": 1,
        "sortNoInSchedule": 1
      }
    ],
    "weekStages": [],
    "competitions": [],
    "eventTags": [],
    "sportDatasInPlan": [],
    "sportDatasNotInPlan": []
  }
]
```

**Active plans** (statusList: [1]) additionally have:
- `endDay: 20260327` — end date
- `originId: "..."` — reference to original template
- `planIdIndex: 4` — offset index
- `programs: [...]` — full program objects with exercises
- Entities have `happenDay` populated (absolute dates, not just relative dayNo)

### GET training/plan/detail

Get full plan with all workouts and exercises.

**Query params:** `id` (plan ID), `supportRestExercise: "1"`

**Response data:**
```json
{
  "id": "475403462392332588",
  "name": "N1117",
  "overview": "2nd plan test",
  "access": 1,
  "authorId": "460904900742627333",
  "pbVersion": 2,
  "planIcon": 1,
  "maxIdInPlan": "1",
  "maxPlanProgramId": "1",
  "maxWeeks": 1,
  "minWeeks": 1,
  "totalDay": 3,
  "executeStatus": 0,
  "inSchedule": 0,
  "entities": [
    {
      "dayNo": 2,
      "executeStatus": 0,
      "exerciseBarChart": [...],
      "id": "475403462392332591",
      "idInPlan": "1",
      "planId": "475403462392332588",
      "planProgramId": "1",
      "sortNo": 1
    }
  ],
  "programs": [
    {
      "access": 1,
      "authorId": "460904900742627333",
      "createTimestamp": 1771015907,
      "distance": 78875.0,
      "duration": 300,
      "exercises": [...],
      "id": "475403462392332589",
      "idInPlan": "1",
      "name": "...",
      "sportType": 1,
      "trainingLoad": 14
    }
  ],
  "weekStages": [],
  "competitions": [],
  "eventTags": []
}
```

**Key:** `dayNo` is relative (day offset from plan start). `happenDay` is only set on entities in active/scheduled plans.

### POST training/schedule/executeSubPlan

Apply a plan template to the calendar starting on a specific date.

**Query params:** `startDay` (YYYYMMDD), `subPlanId` (plan ID)

**Request body:** `{}` (empty)

**Response:** Standard envelope.

This converts a template plan into an active scheduled plan. After execution, the plan appears in `statusList: [1]` queries with `happenDay` populated on entities.

### POST training/plan/delete

Delete one or more plans.

**Request body:** Array of plan IDs:
```json
["475403419167932916"]
```

**Response:** Standard envelope.

### POST training/program/query

List workout templates (the workout library).

**Request body:**
```json
{
  "name": "",
  "supportRestExercise": 1,
  "startNo": 0,
  "limitSize": 10,
  "sportType": 0
}
```

**Response data:** Array of program objects (same structure as programs in plans, with full exercises).

---

## Exercise Object Reference

Each exercise in the `exercises[]` array has different fields depending on whether it's a **group** (repeat container) or a **step** (actual exercise).

### Group Exercise (`isGroup: true`)

```json
{
  "access": 0,
  "defaultOrder": 0,
  "exerciseType": 0,
  "id": 2,
  "intensityCustom": 0,
  "intensityMultiplier": 0,
  "intensityType": 0,
  "intensityValue": 0,
  "intensityValueExtend": 0,
  "isDefaultAdd": 0,
  "isGroup": true,
  "name": "",
  "originId": "",
  "overview": "",
  "programId": "",
  "restType": 0,
  "restValue": 30,
  "sets": 3,
  "sortNo": 2,
  "sourceId": "0",
  "sourceUrl": "",
  "sportType": 0,
  "subType": 0,
  "targetType": "",
  "targetValue": 0,
  "videoUrl": ""
}
```

Groups do **NOT** have: `hrType`, `userId`, `isIntensityPercent`, `targetDisplayUnit`, `groupId`, `equipment`, `part`, `createTimestamp`, `intensityDisplayUnit`, `intensityPercent`, `intensityPercentExtend`.

### Step Exercise (`isGroup: false`)

```json
{
  "access": 0,
  "createTimestamp": 1587381919,
  "defaultOrder": 2,
  "equipment": [1],
  "exerciseType": 2,
  "groupId": 2,
  "hrType": 0,
  "id": 3,
  "intensityCustom": 0,
  "intensityDisplayUnit": "1",
  "intensityMultiplier": 1000,
  "intensityPercent": 94000,
  "intensityPercentExtend": 113000,
  "intensityType": 3,
  "intensityValue": 300000,
  "intensityValueExtend": 360000,
  "isDefaultAdd": 1,
  "isGroup": false,
  "isIntensityPercent": false,
  "name": "T3001",
  "originId": "426109589008859136",
  "overview": "sid_run_training",
  "part": [0],
  "restType": 3,
  "restValue": 0,
  "sets": 1,
  "sortNo": 2,
  "sourceId": "0",
  "sourceUrl": "",
  "sportType": 1,
  "subType": 0,
  "targetDisplayUnit": 0,
  "targetType": 2,
  "targetValue": 300,
  "userId": 0,
  "videoUrl": ""
}
```

Steps do **NOT** have: `programId`.

### Exercise Type Codes

| Code | Type |
|------|------|
| 0 | Group (repeat container) |
| 1 | Warmup |
| 2 | Interval / Work |
| 3 | Cooldown |
| 4 | Recovery |

### Target Type Codes

| Code | Type | Value unit |
|------|------|------------|
| 0 | None | — |
| 2 | Duration | Seconds |
| 5 | Distance | Meters |

### Target Display Unit

| Code | Unit |
|------|------|
| 0 | Seconds |
| 1 | Meters |
| 2 | Kilometers |

### Rest Type

| Code | Meaning |
|------|---------|
| 0 | Timed rest (use `restValue` seconds) |
| 3 | No rest |

### Intensity Fields (HAR-verified)

Intensity defines the target effort for a step.

#### intensityType codes

| Code | Mode | Notes |
|------|------|-------|
| `0` | None | No intensity target |
| `2` | Heart rate | BPM range, uses `hrType` for zone system |
| `3` | Pace | Seconds/km × 1000, uses `intensityDisplayUnit` for UI unit |
| `8` | Speed/pace (other sports) | Same encoding as type 3 (×1000), seen on cycling/swim templates |
| `1` | Cadence/speed? | Seen on strength templates, values 0 or 4536 |
| `10` | Open/RPE? | Seen on some templates, values always 0 |

For running workouts, we only use types `0`, `2`, and `3`.

#### No intensity (default)

```json
{
  "intensityType": 0,
  "intensityValue": 0,
  "intensityValueExtend": 0,
  "intensityMultiplier": 0,
  "intensityDisplayUnit": 0,
  "intensityCustom": 0,
  "intensityPercent": 0,
  "intensityPercentExtend": 0,
  "isIntensityPercent": false,
  "hrType": 0
}
```

#### HR zone target (intensityType=2)

Set a heart rate range for the step.

```json
{
  "intensityType": 2,
  "intensityValue": 150,
  "intensityValueExtend": 158,
  "intensityMultiplier": 0,
  "intensityDisplayUnit": 0,
  "intensityCustom": 2,
  "intensityPercent": 91000,
  "intensityPercentExtend": 95000,
  "isIntensityPercent": true,
  "hrType": 3
}
```

| Field | Value | Notes |
|-------|-------|-------|
| `intensityType` | `2` | HR mode |
| `intensityValue` | BPM low | e.g. 150 |
| `intensityValueExtend` | BPM high | e.g. 158 |
| `intensityMultiplier` | `0` | No multiplier for HR |
| `intensityDisplayUnit` | `0` | Always 0 for HR |
| `intensityCustom` | `2` | See below |
| `intensityPercent` | % × 1000 | e.g. 91000 = 91% |
| `intensityPercentExtend` | % × 1000 | e.g. 95000 = 95% |
| `isIntensityPercent` | `true` | Display as percentage |
| `hrType` | zone system | See below |

**`hrType` — HR zone system (HAR-verified):**

| hrType | Zone system | Example |
|--------|------------|---------|
| `1` | % of max HR | value=114 (60% of 190 maxHR), intensityPercent=61000 |
| `2` | % of HR reserve | value=154 (75% HRR), intensityPercent=75000 |
| `3` | LTHR zones | value=150 (LTHR-based zone boundary) |

**`intensityCustom` for HR:**
- `1` = zone 1 (low)
- `2` = zone 2 (moderate) / custom range
- `3` = zone 3 (high)
- `6` = seen with LTHR zones (hrType=3)

#### Pace target (intensityType=3)

Set a pace range for the step.

```json
{
  "intensityType": 3,
  "intensityValue": 300000,
  "intensityValueExtend": 360000,
  "intensityMultiplier": 1000,
  "intensityDisplayUnit": "1",
  "intensityCustom": 0,
  "intensityPercent": 94000,
  "intensityPercentExtend": 113000,
  "isIntensityPercent": false,
  "hrType": 0
}
```

**Value encoding is always seconds/km × 1000**, regardless of display unit.
The COROS UI converts min/mile and sec/100m inputs to sec/km internally.

| Field | Value | Notes |
|-------|-------|-------|
| `intensityType` | `3` | Pace mode |
| `intensityValue` | sec/km × 1000 | 300000 = 5:00/km |
| `intensityValueExtend` | sec/km × 1000 | 360000 = 6:00/km |
| `intensityMultiplier` | `1000` | Always 1000 for pace |
| `intensityDisplayUnit` | display unit | See table below |
| `intensityCustom` | `0` | |
| `intensityPercent` | % of LTSP × 1000 | 94000 = 94% of threshold pace |
| `intensityPercentExtend` | % of LTSP × 1000 | |
| `isIntensityPercent` | `false` | Display as absolute pace |
| `hrType` | `0` | Not HR mode |

**`intensityDisplayUnit` — pace unit selector (HAR-verified with labeled workouts):**

| Value | Unit | Example: 5:00/km entered as... | Stored as |
|-------|------|-------------------------------|-----------|
| `"1"` | **min/km** | 5:00/km | 300000 |
| `"2"` | **min/mile** | 8:02/mi → converted | 497000 (≈497s/km) |
| `"3"` | **sec/100m** | 30s/100m → converted | 300000 (=300s/km) |

**Note:** In request payloads this is a **string** (`"1"`, `"2"`, `"3"`). In API responses it comes back as **int** (`1`, `2`, `3`). When creating workouts, send as string.

**Reading pace from older/template workouts:** Some workout templates from the library (`training/program/query`) have `intensityMultiplier=0` and store `intensityValue` as raw seconds (not ×1000). Detect via:
- `intensityMultiplier == 1000`: value is sec/km × 1000 → divide by 1000
- `intensityMultiplier == 0` or absent: value is raw sec/km

**When creating workouts**, always use multiplier=1000, displayUnit=`"1"` (min/km).

### Exercise Templates (Running)

| ExerciseType | name | overview | originId | createTimestamp | defaultOrder |
|-------------|------|----------|----------|-----------------|-------------|
| 1 (warmup) | T1120 | sid_run_warm_up_dist | 425895398452936705 | 1586584068 | 1 |
| 2 (interval) | T3001 | sid_run_training | 426109589008859136 | 1587381919 | 2 |
| 3 (cooldown) | T1122 | sid_run_cool_down_dist | 425895456971866112 | 1586584214 | 3 |
| 4 (recovery) | T1123 | sid_run_cool_down_dist | 425895398452936705 | 1586584214 | 3 |

### Program Sport Type Codes (workout context)

| Code | Sport |
|------|-------|
| 1 | Running |
| 3 | Trail |
| 4 | Strength |
| 5 | Hike |
| 6 | Bike / Cycling |
| 9 | Pool Swim |
| 10 | Open Water |

### Default Source

- `sourceId`: `"425868113867882496"`
- `sourceUrl`: `"https://d31oxp44ddzkyk.cloudfront.net/source/source_default/0/5a9db1c3363348298351aaabfd70d0f5.jpg"`

### ID Sequencing Rules (new workouts)

- `exercise_id`: sequential across ALL exercises (groups + steps), starting at 1
- `sortNo`: sequential; group shares `sortNo` with its first child step
- `groupId` on child steps: references the parent group's `id` (integer)
- For **new** workouts: use simple sequential IDs
- For **existing** workouts (from server): groups may have `sortNo = id << 24` (server-side encoding)

### Workout Creation Flow

1. `GET training/schedule/query` — get `pbVersion`, `maxIdInPlan`
2. Build exercises, compute `nextIdInPlan = maxIdInPlan + 1`
3. `POST training/program/calculate` — get metrics (zeroed identity for new)
4. Build schedule payload from calculate results + real identity
5. `POST training/schedule/update` — push with `versionObjects: [{id: nextIdInPlan, status: 1}]`
