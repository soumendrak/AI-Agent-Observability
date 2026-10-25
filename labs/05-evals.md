# Lab 5: Build and test an evaluator

## Goal

Score every booking automatically: compare the structured request with the structured booking, not the confirmation text.

## When

Part 4. You build the evaluator, then test it, then make fresh traffic. Checkpoint 5 is the two test results. Checkpoint 6 is scores on the new traffic.

## Steps

1. Optional, for Lab 6: create the alert from [Lab 6](06-alerts.md) steps 1 to 4 first, before any score exists, so you can watch it go from NO_DATA to ALERT.
2. In Langfuse, go to Evaluators, then New, then Code evaluator, and choose Python.
3. Paste the whole of `evals/booking_matches.py`.
4. Target root observations named `tripmate`. Don't save yet.
5. Test it on your old Case 2 trace (expect false, with a comment) and on your rerun trace (expect true).
6. Save with a rule on new data, then make some traffic:
   ```
   uv run ws load -n 15 --case 0
   uv run ws load -n 15 --case 2 --guard off
   uv run ws case 2 --rerun
   ```
7. Filter traces on `booking_matches_request` = false.

> **Soumen:** screenshots of the evaluator form, the target settings and both test results. If the integration gate picks the SDK-score fallback, this lab changes: read `src/tripmate/checks.py`, then add `--score sdk` to the commands in step 6 and watch the scores arrive.

## Checkpoint

The evaluator gives false on the old Case 2 and true on the rerun (checkpoint 5), and scores appear on the new traffic (checkpoint 6).

## If you're stuck

A test error saying `missing field` means you picked the wrong observation or an old trace. Use the root `tripmate` from a fresh run. Short on time? Use `-n 5` instead of `-n 15`.
