import hashlib
import json
from collections.abc import Callable
from datetime import date as calendar_date
from importlib import resources
from typing import cast

from langchain_core.tools import BaseTool, StructuredTool

Fields = dict[str, str]
Guard = Callable[[Fields, Fields], None]

GUARD_REJECTION = "does not match request"
GUARD_ERROR = "error in guards.py"


def _schedule() -> list[Fields]:
    text = resources.files("tripmate").joinpath("data/flights.json").read_text(encoding="utf-8")
    return cast(list[Fields], json.loads(text))


def no_guard(requested: Fields, args: Fields) -> None:
    return None


def _check_date(date: str) -> None:
    try:
        parsed = calendar_date.fromisoformat(date)
    except ValueError:
        parsed = None
    if parsed is None or parsed.isoformat() != date:
        raise ValueError("date must be YYYY-MM-DD")


def find_flights(origin: str, destination: str, date: str) -> list[Fields]:
    _check_date(date)
    return [
        {**flight, "date": date}
        for flight in _schedule()
        if (flight["origin"], flight["destination"]) == (origin, destination)
    ]


def search_flights(origin: str, destination: str, date: str) -> str:
    return json.dumps(find_flights(origin, destination, date))


def make_tools(requested: Fields, guard: Guard) -> list[BaseTool]:
    def book_flight(origin: str, destination: str, date: str) -> tuple[str, Fields]:
        args = {"origin": origin, "destination": destination, "date": date}
        _check_date(date)
        try:
            guard(requested, args)
        except (ValueError, AssertionError) as error:
            reason = str(error) or type(error).__name__
            raise ValueError(
                reason if GUARD_REJECTION in reason else f"{GUARD_REJECTION}: {reason}"
            ) from error
        except Exception as error:
            raise RuntimeError(f"{GUARD_ERROR}: {type(error).__name__}: {error}") from error
        flights = find_flights(origin, destination, date)
        if not flights:
            raise ValueError(f"no flight from {origin} to {destination}")
        flight = flights[0]["flight"]
        pnr = hashlib.sha256(f"{flight}:{date}".encode()).hexdigest()[:6].upper()
        booking = {"pnr": pnr, "flight": flight, **args}
        return json.dumps(booking), booking

    return [
        StructuredTool.from_function(
            search_flights,
            description="Find flights for a route. date is YYYY-MM-DD.",
        ),
        StructuredTool.from_function(
            book_flight,
            description="Book the first flight on a route. date is YYYY-MM-DD.",
            response_format="content_and_artifact",
        ),
    ]
