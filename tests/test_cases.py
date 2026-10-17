import json
from typing import cast

from conftest import Run, tree
from reference_guard import validate_booking as reference_fix

from tripmate.telemetry import Telemetry

REQUESTED = {"origin": "HYD", "destination": "BLR", "date": "2026-10-31"}


def root_io(telemetry: Telemetry, trace_id: str) -> tuple[dict[str, object], dict[str, object]]:
    root = next(s for s in telemetry.spans(trace_id) if s.parent is None)
    attributes = root.attributes or {}
    return (
        cast(dict[str, object], json.loads(str(attributes["langfuse.observation.input"]))),
        cast(dict[str, object], json.loads(str(attributes["langfuse.observation.output"]))),
    )


def test_case_0_books_the_requested_flight(run: Run, telemetry: Telemetry) -> None:
    result = run(0)
    booking = {"pnr": "DE224B", "flight": "TM-204", **REQUESTED}
    assert result.booking == booking
    assert result.final_message == "Booked TM-204 HYD to BLR on 2026-10-31. PNR DE224B."
    assert root_io(telemetry, result.trace_id) == (
        {"requested": REQUESTED, "message": "Book HYD to BLR on 2026-10-31"},
        {"booking": booking, "final_message": result.final_message},
    )
    nodes = tree(telemetry, result)
    assert nodes[0] == ("agent", "tripmate", "DEFAULT")
    assert nodes[1] == ("chain", "LangGraph", "DEFAULT")
    assert [name for _, name, _ in nodes if name in {"search_flights", "book_flight"}] == [
        "search_flights",
        "book_flight",
    ]
    assert [kind for kind, _, _ in nodes].count("generation") == 3
    assert all(level == "DEFAULT" for _, _, level in nodes)


def test_generations_record_model_and_usage(run: Run, telemetry: Telemetry) -> None:
    result = run(0)
    generations = [
        s.attributes or {}
        for s in telemetry.spans(result.trace_id)
        if (s.attributes or {}).get("langfuse.observation.type") == "generation"
    ]
    assert {g["langfuse.observation.model.name"] for g in generations} == {"tripmate-scripted-1"}
    usage = json.loads(str(generations[0]["langfuse.observation.usage_details"]))
    assert usage["total"] == usage["input"] + usage["output"] > 0


def test_case_1_red_tool_span_and_no_booking(run: Run, telemetry: Telemetry) -> None:
    result = run(1)
    assert result.booking is None
    assert result.final_message == "Sorry, I couldn't complete the booking."
    span = next(s for s in telemetry.spans(result.trace_id) if s.name == "book_flight")
    attributes = span.attributes or {}
    assert attributes["langfuse.observation.level"] == "ERROR"
    assert attributes["langfuse.observation.status_message"] == "date must be YYYY-MM-DD"
    assert json.loads(str(attributes["langfuse.observation.input"]))["date"] == "31/10/2026"
    assert "booking" not in root_io(telemetry, result.trace_id)[1]


def test_case_2_all_green_but_wrong_flight(run: Run, telemetry: Telemetry) -> None:
    result = run(2)
    assert result.requested == REQUESTED
    assert result.booking == {
        "pnr": "B1EDC2",
        "flight": "TM-205",
        "origin": "BLR",
        "destination": "HYD",
        "date": "2026-10-31",
    }
    assert result.final_message == "Booked TM-204 HYD to BLR on 2026-10-31. PNR B1EDC2."
    assert result.rejected == []
    assert all(level == "DEFAULT" for _, _, level in tree(telemetry, result))


def test_case_2_reference_fix_catches_and_corrects(run: Run, telemetry: Telemetry) -> None:
    result = run(2, reference_fix)
    assert result.rejected == [{"origin": "BLR", "destination": "HYD", "date": "2026-10-31"}]
    assert result.booking == {"pnr": "DE224B", "flight": "TM-204", **REQUESTED}
    assert result.final_message == "Booked TM-204 HYD to BLR on 2026-10-31. PNR DE224B."
    errors = [
        s.attributes or {}
        for s in telemetry.spans(result.trace_id)
        if (s.attributes or {}).get("langfuse.observation.level") == "ERROR"
    ]
    assert [e["langfuse.observation.status_message"] for e in errors] == [
        "does not match request: origin, destination"
    ]


def test_guard_message_gets_the_rejection_phrase(run: Run) -> None:
    def terse(requested: dict[str, str], args: dict[str, str]) -> None:
        if args != requested:
            raise ValueError("origin is wrong")

    result = run(2, terse)
    assert len(result.rejected) == 1
    assert result.booking == {"pnr": "DE224B", "flight": "TM-204", **REQUESTED}


def test_step_guard_stops_a_loop(run: Run) -> None:
    def always(requested: dict[str, str], args: dict[str, str]) -> None:
        raise ValueError("never")

    result = run(2, always)
    assert result.final_message == "Stopped: step limit of 8 reached."
    assert result.booking is None
    assert len(result.rejected) == 7


def test_unknown_route_finds_no_flights(run: Run) -> None:
    result = run(0, text="Book HYD to XYZ on 2026-10-31")
    assert result.final_message == "Sorry, I found no flights for that trip."


def test_bad_request_date_fails_the_search(run: Run) -> None:
    result = run(0, text="Book HYD to BLR on 2026-02-30")
    assert result.final_message == "Sorry, I found no flights for that trip."


def test_swapped_route_without_a_return_flight(run: Run) -> None:
    result = run(2, text="Book BLR to MAA on 2026-11-02")
    assert result.booking is None
    assert result.final_message == "Sorry, I couldn't complete the booking."
