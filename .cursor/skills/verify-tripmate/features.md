# Journeys

| Journey | Command | Expected |
|---|---|---|
| Parse a request | `uv run python -c "from tripmate.request import parse_request; print(parse_request('Book HYD to BLR on 2026-10-31'))"` | `{'origin': 'HYD', 'destination': 'BLR', 'date': '2026-10-31'}` |
