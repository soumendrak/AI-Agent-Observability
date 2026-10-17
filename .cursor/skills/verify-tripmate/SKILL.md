---
name: verify-tripmate
description: Use before opening or updating a PR in AI-Agent-Observability. Runs the standards gate and the workshop journeys offline.
---
# Verify TripMate

1. `uv sync --locked`
2. `uv run python scripts/standards.py > standards.log`. The last line must be `STANDARDS OK`.
3. Drive every journey in `features.md` that the change touches and keep the printed output as evidence.
