# Lab 6: Alerts (optional)

## Goal

Build an alert that can tell "not measured" from "failing".

## When

Part 5. Soumen demos this with two pre-built alerts on his project: the same pass-rate alert, one on the default no-data mode and one on NO_DATA. Building your own is optional, and Hobby accounts allow 2 alerts.

If you created the alert at the start of Lab 5, it started on NO_DATA. If you create it now, your Lab 5 scores already exist, so it can go straight to ALERT.

## Steps

1. In Langfuse, go to Alerts, then New.
2. Choose Scores (boolean), average of `booking_matches_request`, below `0.9`, over the smallest window offered.
3. For no-data handling, choose **Show severity NO_DATA**, not the default.
4. Save the alert.
5. Optional second alert: the count of `booking_matches_request` scores below 10. Save it too. It doesn't silence the first alert. It flags that the pass rate rests on few scores.
6. Make some failing traffic and watch the state change:
   ```
   uv run ws load -n 40 --case 2 --guard off
   ```

> **Soumen:** screenshots of both alert states (NO_DATA and ALERT), and of the webhook payload.

## Checkpoint

You can explain the difference between NO_DATA and ALERT.

## If you're stuck

Alert evaluation is not instant. Watch Soumen's pre-built alerts on the projector.
