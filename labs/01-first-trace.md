# Lab 1: First trace

## Goal

Run TripMate once and open its trace in Langfuse.

## When

Part 1, right after the opening. Checkpoint 1 is your own trace in Langfuse.

## Steps

1. Run:
   ```
   uv run ws run "Book HYD to BLR on 2026-10-31"
   ```
2. Click the `trace:` link it prints.
3. Find the root observation `tripmate`, the `LangGraph` chain under it, the generations and the tools.
4. Compare your tree with the one on the projector.

## Checkpoint

You see your own trace with the root `tripmate`. Put up a green sticky.

## If you're stuck

No link, or a login page? Check the region and keys with `uv run ws doctor`. You can also work offline:
```
uv run ws run "Book HYD to BLR on 2026-10-31" --exporter console
```
That prints the same tree in the terminal.
