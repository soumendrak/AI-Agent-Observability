# Lab 3: The incident

## Goal

A customer says TripMate booked the wrong flight. Find the evidence in the traces and explain what went wrong.

## When

- Warm-up (Case 1) first.
- Then the investigation (Case 2). Work alone first, then compare with your partner, then write one sentence. Checkpoint 3 is that sentence.

## Steps

Method. Each step is a separate check, so clear the previous filter before the next one:
1. Filter on level = ERROR.
2. Filter on type = tool.
3. Sort by duration or tokens.
4. Compare what was asked (the root input) with what the tool did (the tool input and output).
5. Open the generation that chose the tool call.

Warm-up:
```
uv run ws case 1
```
Find the red span and the generation that caused it. Tell your TA your answer.

The real complaint:
```
uv run ws case 2
```
Nothing is red, so the level filter shows nothing: clear it and carry on with the other steps. Fill in worksheet part B (the evidence table) with your partner, then part C (one sentence).

> **Soumen:** the complaint letter, and screenshots of where the root input, tool input and root output are in the UI, taken from a Case 0 trace so they don't show the Case 2 answer. Hints are on the slides, one at a time.

## Checkpoint

Your sentence says what went wrong, where it shows in the trace, and why the confirmation hid it. Your TA checks it.

## If you're stuck

Go back to step 4 of the method. Offline, `uv run ws case 2 --exporter console` prints the root's requested and booking fields and every tool's arguments.
