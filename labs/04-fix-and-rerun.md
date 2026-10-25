# Lab 4: Fix and rerun

## Goal

Stop the wrong booking before it happens, then prove the fix with a rerun.

## When

Part 3, straight after Lab 3. Checkpoint 4 is a rerun that prints PASS.

## Steps

1. Open `src/tripmate/guards.py` in any editor and find `WORKSHOP EDIT HERE`.
2. Make `validate_booking` raise `ValueError` if the origin, destination or date in `args` differ from `requested`. Both are dictionaries with the keys `origin`, `destination` and `date`.
3. Save the file and run:
   ```
   uv run ws case 2 --rerun
   ```
4. Expect a red `book_flight` span (your guard caught it, and that red is good), then a corrected booking, then `booking_matches_request: PASS (local check, same logic as the Langfuse evaluator)`.
5. Open the new trace and compare its root with the old one.
6. To see the original bug again, even with your fix in place:
   ```
   uv run ws case 2 --guard off
   ```

The guard prevents the wrong action before it happens. The evaluator, in Lab 5, checks the recorded outcome afterwards.

> **Soumen:** pseudo-code from the slide, and a screenshot of a successful rerun.

## Checkpoint

The rerun prints PASS. Put up a green sticky.

## If you're stuck

Read the `guard:` line the rerun prints. The guide's [Lab 4 section](../docs/troubleshooting.md#lab-4-your-guardspy-edit) explains each message. Still stuck? Ask your TA.
