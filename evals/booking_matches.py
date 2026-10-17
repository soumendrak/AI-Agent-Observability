import json
import re
from datetime import date

FIELDS = ("origin", "destination", "date")
IATA = re.compile(r"^[A-Z]{3}$")
ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SPACE = " \t\n\r"


def _reject_constant(name: str) -> object:
    raise ValueError(f"not JSON: {name}")


def _obj(value: object) -> dict[str, object]:
    if isinstance(value, str):
        try:
            value = json.loads(value, parse_constant=_reject_constant)
        except ValueError:
            return {}
    return value if isinstance(value, dict) else {}


def _clean(record: dict[str, object], field: str) -> tuple[str | None, str | None]:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip(SPACE):
        return None, "missing"
    value = value.strip(SPACE).upper()
    if field == "date":
        if not ISO_DATE.match(value):
            return None, "invalid"
        try:
            date.fromisoformat(value)
        except ValueError:
            return None, "invalid"
    elif not IATA.match(value):
        return None, "invalid"
    return value, None


def evaluate(ctx: EvaluationContext) -> EvaluationResult:
    sides = {
        "requested": _obj(_obj(ctx.observation.input).get("requested")),
        "booking": _obj(_obj(ctx.observation.output).get("booking")),
    }
    clean: dict[tuple[str, str], str | None] = {}
    problems: list[str] = []
    for side, record in sides.items():
        for field in FIELDS:
            value, error = _clean(record, field)
            if error:
                problems.append(f"{error} field: {side}.{field}")
            clean[(side, field)] = value
    if problems:
        ok, comment = False, "; ".join(problems)
    else:
        wrong = [f for f in FIELDS if clean[("requested", f)] != clean[("booking", f)]]
        ok = not wrong
        comment = (
            "all fields match"
            if ok
            else "mismatch: "
            + ", ".join(
                f"{f} requested={clean[('requested', f)]} booked={clean[('booking', f)]}"
                for f in wrong
            )
        )
    return EvaluationResult(
        scores=[
            Score(name="booking_matches_request", value=ok, data_type="BOOLEAN", comment=comment)
        ]
    )
