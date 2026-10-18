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
4. When the load finishes, its last line reads `latency over 50 runs: mean ..., p50 ..., p95 ..., p99 ...`. Copy those four numbers into the percentile table on the worksheet: the p99 there is this line's p99. Then open the latency view in Langfuse for the same runs. Its numbers can differ a little, because Langfuse times each trace on its own and may use another percentile method ([maths appendix B0](../docs/maths-appendix.md#b0-percentiles-on-small-samples)).

> **Soumen:** where to find the latency view and percentiles in Langfuse, with a screenshot.

## Checkpoint

You can read your own p50, p95 and p99. The runs are seeded, so everyone's numbers should be close, but laptops differ a little, so don't expect an exact match.

## If you're stuck

Answer Q1 to Q3 only and move on. Offline? `uv run ws load -n 50 --exporter console` prints the same latency line, so you can still fill in the percentile table.
