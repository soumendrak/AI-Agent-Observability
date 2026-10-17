import json
from pathlib import Path
from typing import cast

import pytest
from conftest import Run
from reference_guard import validate_booking as reference_fix

from tripmate.checks import Score, booking_matches_request
from tripmate.telemetry import Telemetry

CASES = cast(
    list[dict[str, object]],
    json.loads((Path(__file__).parent / "eval_cases.json").read_text(encoding="utf-8")),
)


@pytest.mark.parametrize("case", CASES, ids=[str(c["name"]) for c in CASES])
def test_checks_matches_the_parity_table(case: dict[str, object]) -> None:
    score = booking_matches_request(case["input"], case["output"])
    assert (score.value, score.comment) == (case["expect"], case["comment"])
    assert (score.name, score.data_type) == ("booking_matches_request", "BOOLEAN")


def exported_root_score(telemetry: Telemetry, trace_id: str) -> Score:
    root = next(s for s in telemetry.spans(trace_id) if s.parent is None)
    attributes = root.attributes or {}
    return booking_matches_request(
        attributes["langfuse.observation.input"], attributes["langfuse.observation.output"]
    )


def test_exported_traces_score_like_the_gate(run: Run, telemetry: Telemetry) -> None:
    results = {
        "case 0": exported_root_score(telemetry, run(0).trace_id),
        "case 1": exported_root_score(telemetry, run(1).trace_id),
        "case 2": exported_root_score(telemetry, run(2).trace_id),
        "case 2 fixed": exported_root_score(telemetry, run(2, reference_fix).trace_id),
    }
    assert {name: score.value for name, score in results.items()} == {
        "case 0": True,
        "case 1": False,
        "case 2": False,
        "case 2 fixed": True,
    }
    assert results["case 2"].comment == (
        "mismatch: origin requested=HYD booked=BLR, destination requested=BLR booked=HYD"
    )
