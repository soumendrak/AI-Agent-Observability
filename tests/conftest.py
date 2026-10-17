from typing import Protocol

import pytest

from tripmate.agent import RunResult, run_agent
from tripmate.guards import validate_booking
from tripmate.request import EXAMPLE
from tripmate.telemetry import Telemetry, console
from tripmate.tools import Guard


class Run(Protocol):
    def __call__(self, case: int, guard: Guard = ..., text: str = ...) -> RunResult: ...


@pytest.fixture
def telemetry() -> Telemetry:
    return console()


@pytest.fixture
def run(telemetry: Telemetry) -> Run:
    def go(case: int, guard: Guard = validate_booking, text: str = EXAMPLE) -> RunResult:
        return run_agent(text, case, guard, telemetry, latency_scale=0)

    return go


def tree(telemetry: Telemetry, result: RunResult) -> list[tuple[str, str, str]]:
    return [
        (
            str((s.attributes or {}).get("langfuse.observation.type")),
            s.name,
            str((s.attributes or {}).get("langfuse.observation.level", "DEFAULT")),
        )
        for s in sorted(telemetry.spans(result.trace_id), key=lambda s: s.start_time or 0)
    ]
