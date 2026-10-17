import re

FIELDS = ("origin", "destination", "date")
EXAMPLE = "Book HYD to BLR on 2026-10-31"

_PATTERN = re.compile(r"\b([A-Za-z]{3})\s+to\s+([A-Za-z]{3})\b.*?\bon\s+([\w/.-]*\w)", re.DOTALL)


def parse_request(text: str) -> dict[str, str]:
    match = _PATTERN.search(text)
    if match is None:
        raise ValueError(f'could not read the trip from {text!r}; try "{EXAMPLE}"')
    origin, destination, date = match.groups()
    return {"origin": origin.upper(), "destination": destination.upper(), "date": date}
