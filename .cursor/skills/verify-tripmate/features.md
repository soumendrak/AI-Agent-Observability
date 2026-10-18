# Journeys

All journeys run offline with `--exporter console`. Add `--exporter langfuse` (the default) only with real keys in `.env`.

| Journey | Command | Expected |
|---|---|---|
| Parse a request | `uv run ws run "Book DEL to BOM on 2026-11-01" --exporter console` | `TripMate: Booked TM-530 DEL to BOM on 2026-11-01. ...` |
| Case 0 | `uv run ws case 0 --exporter console` | tree with no `[ERROR]`, `booking` equals `requested` |
| Case 1 | `uv run ws case 1 --exporter console` | `tool book_flight [ERROR] date must be YYYY-MM-DD`, `booking: null` |
| Case 2 | `uv run ws case 2 --exporter console` | no `[ERROR]`, `booking` differs from `requested`, final message reads correctly (exact values: `tests/test_cases.py`) |
| Rerun, no-op guard | `uv run ws case 2 --rerun --exporter console` | `guard: no-op`, `booking_matches_request: FAIL: mismatch: ...` |
| Rerun, reference fix | copy `tests/reference_guard.py` over `src/tripmate/guards.py` in a scratch clone, then `uv run ws case 2 --rerun --exporter console` | `guard: caught mismatch on ...`, `booking_matches_request: PASS ...` |
| Guard off | same scratch clone, `uv run ws case 2 --rerun --guard off --exporter console` | `guard: off`, FAIL |
| Doctor, no setup | `uv run ws doctor` in a folder without `.env` | `[FAIL] no .env here; copy .env.example to .env in the repo folder`, exit 1 |
