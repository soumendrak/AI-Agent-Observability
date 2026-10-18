# Lab 5: Build and test an evaluator

## Goal

Score every booking automatically: compare the structured request with the structured booking, not the confirmation text.

## When

01:40 to 02:15. You build from 01:50 to 02:05. Checkpoint 5 is at 02:00 and checkpoint 6 at 02:05.

## Steps

1. In Langfuse, go to Evaluators, then New, then Code evaluator, and choose Python.
2. Paste the whole of `evals/booking_matches.py`.
3. Target root observations named `tripmate`. Don't save yet.
4. Test it on your old Case 2 trace (expect false, with a comment) and on your rerun trace (expect true).
5. Save with a rule on new data, then make some traffic:
   ```
   uv run ws load -n 15 --case 0
   uv run ws load -n 15 --case 2 --guard off
   uv run ws case 2 --rerun
   ```
6. Filter traces on `booking_matches_request` = false.

> **Soumen:** screenshots of the evaluator form, the target settings and both test results. If the integration gate picks the SDK-score fallback, this lab changes: read `src/tripmate/checks.py`, then add `--score sdk` to the commands in step 5 and watch the scores arrive.

## Checkpoint

The evaluator gives false on the old Case 2 and true on the rerun (checkpoint 5), and scores appear on the new traffic (checkpoint 6).

## If you're stuck

A test error saying `missing field` means you picked the wrong observation or an old trace. Use the root `tripmate` from a fresh run. Short on time? Use `-n 5` instead of `-n 15`.
