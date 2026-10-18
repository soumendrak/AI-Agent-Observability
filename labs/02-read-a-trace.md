# Lab 2: Read a trace

## Goal

Read a trace as data: spans, types, arguments and tokens, plus latency percentiles from your own runs.

## When

00:20 to 00:45. You work on the worksheet from 00:28 to 00:38, and checkpoint 2 is at 00:45.

## Steps

1. Open the root `tripmate` from Lab 1. Look at its input and its output.
2. Start 50 runs in a second terminal. They take a few minutes:
   ```
   uv run ws load -n 50
   ```
3. With a partner if you have one, answer worksheet part A (Q1 to Q5) from your Lab 1 trace.
4. When the load finishes, open the latency view for the 50 runs and fill in the percentile table on the worksheet.

> **Soumen:** where to find the latency view and percentiles in Langfuse, with a screenshot.

## Checkpoint

You can read your own p50, p95 and p99. Everyone's numbers match, because the runs are seeded.

## If you're stuck

Answer Q1 to Q3 only and move on. Offline? `uv run ws load -n 50 --exporter console` still runs, but the percentiles come from Langfuse, so copy them from the projector.
