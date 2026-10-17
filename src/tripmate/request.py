import re

FIELDS = ("origin", "destination", "date")
EXAMPLE = "Book HYD to BLR on 2026-10-31"

_PATTERN = re.compile(
    r"(?:please\s+)?(?:book\s+)?(?:a\s+flight\s+)?(?:from\s+)?"
    r"([a-z]{3})\s+to\s+([a-z]{3})\s+on\s+(\S+?)[.!?]?",
    re.IGNORECASE,
)


def parse_request(text: str) -> dict[str, str]:
    match = _PATTERN.fullmatch(text.strip())
    if match is None:
        raise ValueError(f'could not read the trip from {text!r}; try "{EXAMPLE}"')
    origin, destination, date = match.groups()
    return {"origin": origin.upper(), "destination": destination.upper(), "date": date}
