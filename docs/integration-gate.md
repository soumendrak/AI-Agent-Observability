# Integration gate runbook (plan A9)

Run this on a fresh Langfuse Cloud Hobby account, Mon 19 Oct evening. Go/no-go is due Tue 20 Oct 22:00 IST. Every command works the same in PowerShell and in a macOS or Linux terminal unless a step shows two versions.

You need three results on the real account:

| Trace | Command | `booking_matches_request` |
|---|---|---|
| Normal run | `uv run ws case 0` | true |
| Broken booking | `uv run ws case 2` | false, comment `mismatch: origin requested=HYD booked=BLR, destination requested=BLR booked=HYD` |
| Guarded rerun | reference fix applied, `uv run ws case 2 --rerun` | true |

Keep a notes file open. Each step says what to record.

## 0. Account and clean clone

1. Sign up at https://cloud.langfuse.com (EU) or https://us.cloud.langfuse.com (US). Create an organization and a project named `tripmate-workshop`.
2. Project settings > API Keys > Create new API keys. Keep the tab open; the secret key is shown once.
3. Install uv if needed:
   - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
   - Windows: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
4. Clone and install. Until the PR stack is merged, the gate kit is on branch `m6-doctor` (PR #6, the top of the stack):
   ```
   git clone https://github.com/soumendrak/AI-Agent-Observability gate-check
   cd gate-check
   git checkout m6-doctor
   uv sync
   ```
5. Create `.env`:
   - macOS/Linux: `cp .env.example .env`
   - Windows: `copy .env.example .env`

   Open `.env` and set `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` and `LANGFUSE_BASE_URL` (the region URL from step 1, no trailing slash). Leave `LLM_MODE=fake`.
6. Check the setup:
   ```
   uv run ws doctor
   ```
   Expect six `[OK]` lines (Python, `.env`, keys, `LLM_MODE`, project, hello trace URL) and a `READY-XXXX` code. A `[FAIL]` line names the cause and the fix. Record any failure message, since it feeds M11.
7. Offline smoke test, no network needed:
   ```
   uv run ws case 2 --exporter console
   ```
   Expect a tree that starts with `agent tripmate OK`, a `booking:` line with `"origin": "BLR", "destination": "HYD"`, and `TripMate: Booked TM-204 HYD to BLR on 2026-10-31. PNR B1EDC2.`

## 1. Create both alerts first (A9 step 4, part 1)

The alerts read scores only, so create them before any score exists. That gives the empty window the step needs. Hobby allows 2 alerts, and these are the two.

Alerts > New Alert, twice:

| Field | Alert A | Alert B |
|---|---|---|
| Data source | Scores (boolean) | Scores (boolean) |
| Metric | avg of the score value | avg of the score value |
| Filter | score name = `booking_matches_request` | score name = `booking_matches_request` |
| Operator | `<` | `<` |
| Alert threshold | `0.9` | `0.9` |
| Window | the smallest offered | the smallest offered |
| Advanced > No-data handling | **Show severity NO_DATA** | Treat missing data as 0 (default, leave it) |
| Name | `booking pass rate (NO_DATA mode)` | `booking pass rate (default mode)` |

No automation is needed. Save both.

Record: the time you saved each alert, and the time each one left `UNKNOWN`. The gap is the evaluation interval, which the docs don't state. Expected: A shows `NO_DATA`, B shows `ALERT` on the same empty window. Screenshot the alert list.

## 2. Traces (A9 step 1)

```
uv run ws case 0
uv run ws case 2
```

Each command prints `trace: https://.../project/<id>/traces/<trace id>`. Open both links.

Check on each trace: the root observation is `tripmate` (type agent) with no parent. Its Input shows JSON with `requested` = `{"origin": "HYD", "destination": "BLR", "date": "2026-10-31"}`. Its Output shows JSON with `booking`. For Case 0 the booking is HYD to BLR, for Case 2 it is BLR to HYD while `final_message` still says HYD to BLR.

Record: seconds from command to trace visible (target: about 1 min). Screenshot the root observation of both traces.

Now the guarded rerun. Apply the reference fix in this clone only:

- macOS/Linux: `cp tests/reference_guard.py src/tripmate/guards.py`
- Windows: `copy tests\reference_guard.py src\tripmate\guards.py`

```
uv run ws case 2 --rerun
```

Expect:
```
TripMate: Booked TM-204 HYD to BLR on 2026-10-31. PNR DE224B.
guard: caught mismatch on origin, destination
trace: https://...
booking_matches_request: PASS (local check, same logic as the Langfuse evaluator)
```
The trace has one red `book_flight` span (`does not match request: origin, destination`) and then a second, green `book_flight`. Keep the fix in place until step 4 is done.

## 3. Code evaluator test panel (A9 step 2)

1. Evaluators > New evaluator > Code evaluator > Python.
2. Replace the template with the whole of `evals/booking_matches.py`. Paste it as is: Langfuse provides `EvaluationContext`, `EvaluationResult` and `Score`.
3. On the right, filter the sample observations: Is Root Observation = true, Name = `tripmate`.
4. Run the test on each of the three roots from step 2:

| Sample | Expected result |
|---|---|
| Case 0 root | true, `all fields match` |
| Case 2 root | false, `mismatch: origin requested=HYD booked=BLR, destination requested=BLR booked=HYD` |
| Case 2 rerun root | true, `all fields match` |

Record: three screenshots. If a test says `missing field: requested.origin; ...`, you picked a non-root observation or an old trace.

## 4. Rule and live scores (A9 step 3)

1. Save the evaluator and create a rule from the filters: target observations, Is Root Observation = true, Name = `tripmate`, run on **new data only**, sampling 100%.
2. Run three fresh traces (the reference fix is still in place for the third):
   ```
   uv run ws case 0
   uv run ws case 2 --guard off
   uv run ws case 2 --rerun
   ```
   `--guard off` gives the original bug even with the fix applied.
3. Open Scores (or each trace's Scores tab).

Expected: `booking_matches_request` true, false, true, with the same comments as step 3. Record the delay from command to score.

## 5. Alerts on real scores (A9 step 4, part 2)

```
uv run ws load -n 10 --case 2 --guard off
```

It prints `run 1/10: FAIL ...` to `run 10/10` and `done: 10 runs of case 2, local check PASS 0/10`.

Wait at least one evaluation interval (from step 1) after the scores appear. Expected: alert A goes from `NO_DATA` to `ALERT`. Alert A may already show `ALERT` after step 4, because true, false, true averages 0.67, below 0.9. The load makes the result unambiguous. Screenshot the alert list.

Then restore the shipped guard:
```
git checkout -- src/tripmate/guards.py
```

## GO / NO-GO

GO only if steps 2 to 5 all pass, including true, false, true in both step 3 and step 4. Fill in:

| Item | Result |
|---|---|
| Trace visible after (s) | |
| Root input/output arrived as JSON objects | yes / no |
| Test panel: case 0, case 2, rerun | |
| Rule scores: case 0, case 2, rerun | |
| Score delay (s) | |
| Alert evaluation interval | |
| Empty window: alert A / alert B | |
| After load: alert A | |

## Fallback: scores from the app (`--score sdk`)

Use this if step 3 or 4 fails: the evaluator can't read the fields, the rule doesn't fire, or it is too slow. `--score sdk` runs the same `evals/booking_matches.py` locally (through `src/tripmate/checks.py`) and sends the result on the root `tripmate` observation with the SDK call `root.score(name="booking_matches_request", value=1.0 or 0.0, data_type="BOOLEAN", comment=...)`.

1. Pause or delete the evaluator rule from step 4, so each trace gets one score.
2. With the reference fix applied:
   ```
   uv run ws case 0 --score sdk
   uv run ws case 2 --guard off --score sdk
   uv run ws case 2 --rerun --score sdk
   uv run ws load -n 10 --case 2 --guard off --score sdk
   ```
3. Expected in Scores: true, false (with the mismatch comment), true, then ten false. The alerts don't change, since they read Scores (boolean) either way.
4. Restore the shipped guard: `git checkout -- src/tripmate/guards.py`.

`--score sdk` refuses `--exporter console`, since offline runs send nothing.

## Pre-gate API check (Sat 17 Oct 2026, US project `tripmate-workshop`)

What a fresh Langfuse Cloud organization accepts, checked with SDK 5.0.2:

- Traces from `ws case 0`, `ws case 1`, `ws case 2 --guard off` and `ws case 2 --rerun` arrive within seconds. Root `tripmate` is `AGENT` with `isRootObservation=true`. The failed `book_flight` spans have level `ERROR` with the tool's message as `statusMessage`.
- `GET /api/public/v2/observations?traceId=...&isRootObservation=true&fields=core,basic,io` returns `input` and `output` as **JSON strings**, not objects (by design in v2). `input` holds `requested` and `message`; `output` holds `booking` and `final_message`. The evaluator accepts both strings and objects, and gives the expected result on the strings it fetched.
- `--score sdk` scores show up in `GET /api/public/v3/scores?traceId=...&fields=details,subject` as `BOOLEAN` `true`/`false`, source `API`, attached to the root observation (`subject.kind = observation`), with the mismatch text as `comment`.
- Organizations created on or after 16 Sep 2026 get **HTTP 410** `LEGACY_API_UNAVAILABLE_FOR_NEW_ORGANIZATION` from `GET /api/public/traces/{id}`, `/api/public/observations` and `/api/public/scores` (v1 and v2). Use Observations v2 and Scores v3. `ws doctor` only uses the projects API and Observations v2.
- Langfuse will shut down the legacy ingestion API on 16 Nov 2026. That doesn't affect us: traces go over OTLP, and the docs say the score-create events from the SDK stay supported.
