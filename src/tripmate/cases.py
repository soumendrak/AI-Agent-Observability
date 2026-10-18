from collections.abc import Callable
from dataclasses import dataclass

from tripmate.tools import Fields


@dataclass(frozen=True)
class Case:
    choose_booking: Callable[[Fields], Fields]
    claims_request: bool = False


def _as_requested(requested: Fields) -> Fields:
    return dict(requested)


def _day_first(requested: Fields) -> Fields:
    return {**requested, "date": "/".join(reversed(requested["date"].split("-")))}


def _swapped(requested: Fields) -> Fields:
    return {**requested, "origin": requested["destination"], "destination": requested["origin"]}


CASES = {
    0: Case(_as_requested),
    1: Case(_day_first),
    2: Case(_swapped, claims_request=True),
}
