import json
from pathlib import Path

import pytest
from conftest import use_keys, ws
from fake_langfuse import BROKEN_KEY, FakeLangfuse

from tripmate import checkout, cli
from tripmate.checks import Score, booking_matches_request

REFERENCE = Path(__file__).with_name("reference_guard.py")
PASS = "booking_matches_request: PASS (local check, same logic as the Langfuse evaluator)"


pytestmark = pytest.mark.usefixtures("workshop_shell")


def test_case_2_console_tree_solves_offline(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = ws(capsys, "case", "2", "--exporter", "console")
    assert code == 0
    lines = out.splitlines()
    assert lines[0] == "agent tripmate OK"
    assert lines[1].strip() == (
        'requested: {"origin": "HYD", "destination": "BLR", "date": "2026-10-31"}'
    )
    assert '"origin": "BLR", "destination": "HYD"' in lines[2]
    assert "tool book_flight OK" in out
    assert 'args: {"origin": "BLR", "destination": "HYD", "date": "2026-10-31"}' in out
    assert "[ERROR]" not in out
    assert "TripMate: Booked TM-204 HYD to BLR on 2026-10-31. PNR B1EDC2." in lines
    assert "trace: offline (--exporter console), nothing was sent to Langfuse" in lines
    assert "guard:" not in out


def test_case_1_shows_the_error_as_text(capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = ws(capsys, "case", "1", "--exporter", "console")
    assert "tool book_flight [ERROR] date must be YYYY-MM-DD" in out
    assert "booking: null" in out


def test_rerun_with_the_no_op_guard_fails(capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = ws(capsys, "case", "2", "--rerun", "--exporter", "console")
    assert "guard: no-op" in out.splitlines()
    assert (
        "booking_matches_request: FAIL: mismatch: origin requested=HYD booked=BLR, "
        "destination requested=BLR booked=HYD (local check, same logic as the Langfuse evaluator)"
    ) in out.splitlines()


def test_rerun_with_the_reference_fix_passes(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(checkout, "GUARDS", REFERENCE)
    _, out, _ = ws(capsys, "case", "2", "--rerun", "--exporter", "console")
    lines = out.splitlines()
    assert "guard: caught mismatch on origin, destination" in lines
    assert "tool book_flight [ERROR] does not match request: origin, destination" in out
    assert lines[-1] == PASS


def test_guard_off_brings_the_bug_back(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(checkout, "GUARDS", REFERENCE)
    _, out, _ = ws(capsys, "case", "2", "--rerun", "--guard", "off", "--exporter", "console")
    assert "guard: off" in out.splitlines()
    assert "booking_matches_request: FAIL" in out


def test_rerun_of_a_clean_case(capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = ws(capsys, "case", "0", "--rerun", "--exporter", "console")
    assert "guard: did not reject anything" in out.splitlines()
    assert out.splitlines()[-1] == PASS


def attendee_guard(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, source: str) -> None:
    guards = tmp_path / "guards.py"
    guards.write_text(source, encoding="utf-8")
    monkeypatch.setattr(checkout, "GUARDS", guards)


def test_an_assert_in_the_guard_counts_as_a_rejection(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    attendee_guard(
        monkeypatch,
        tmp_path,
        "def validate_booking(requested, args):\n    assert args == requested\n",
    )
    _, out, _ = ws(capsys, "case", "2", "--rerun", "--exporter", "console")
    lines = out.splitlines()
    assert "tool book_flight [ERROR] does not match request: assert failed" in out
    assert "guard: caught mismatch on origin, destination" in lines
    assert lines[-1] == PASS


def test_a_crashing_guard_is_reported_as_an_error(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    attendee_guard(
        monkeypatch,
        tmp_path,
        "def validate_booking(requested, args):\n    return args.origin\n",
    )
    _, out, _ = ws(capsys, "case", "2", "--rerun", "--exporter", "console")
    lines = out.splitlines()
    crash = "error in guards.py: AttributeError: 'dict' object has no attribute 'origin'"
    assert f"tool book_flight [ERROR] {crash}" in out
    assert f"guard: {crash}" in lines
    assert "guard: did not reject anything" not in lines
    assert lines[-1] == "booking_matches_request: not checked; fix the error in guards.py first"


@pytest.mark.parametrize(
    ("source", "message"),
    [
        (
            "import tripmate_helpers\n",
            "error: guards.py could not be loaded: ModuleNotFoundError: "
            "No module named 'tripmate_helpers'",
        ),
        (
            "LIMIT = 1 / 0\n",
            "error: guards.py could not be loaded: ZeroDivisionError: division by zero",
        ),
        (
            "def check_booking(requested, args):\n    return\n",
            "error: guards.py must define validate_booking(requested, args)",
        ),
        (
            "validate_booking = None\n",
            "error: guards.py must define validate_booking(requested, args)",
        ),
    ],
)
def test_guards_file_that_cannot_be_used(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    attendee_guard(monkeypatch, tmp_path, source)
    code, _, err = ws(capsys, "case", "2", "--rerun", "--exporter", "console")
    assert code == 2
    assert err.strip() == message


def test_broken_guards_file_is_reported(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    broken = tmp_path / "guards.py"
    broken.write_text("def validate_booking(requested, args)\n    return\n", encoding="utf-8")
    monkeypatch.setattr(checkout, "GUARDS", broken)
    code, _, err = ws(capsys, "case", "2", "--rerun", "--exporter", "console")
    assert code == 2
    assert err.startswith("error: guards.py line 1: ")


def test_run_your_own_request(capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = ws(capsys, "run", "Book DEL to BOM on 2026-11-01", "--exporter", "console")
    assert "TripMate: Booked TM-530 DEL to BOM on 2026-11-01." in out


def test_unreadable_request(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = ws(capsys, "run", "take me somewhere", "--exporter", "console")
    assert code == 2
    assert "could not read the trip" in err


def test_missing_env_file(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = ws(capsys, "case", "0")
    assert code == 2
    assert "missing LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_BASE_URL" in err
    assert "--exporter console" in err


def test_only_the_fake_llm_is_supported(capsys: pytest.CaptureFixture[str]) -> None:
    Path(".env").write_text("LLM_MODE=ollama\n", encoding="utf-8")
    code, _, err = ws(capsys, "case", "0", "--exporter", "console")
    assert code == 2
    assert "LLM_MODE=ollama is not supported" in err


def test_langfuse_mode_sends_the_trace_and_prints_its_url(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse
) -> None:
    use_keys(fake_langfuse.url)
    code, out, _ = ws(capsys, "case", "2")
    assert code == 0
    url = next(line for line in out.splitlines() if line.startswith("trace: "))
    trace_id = url.rsplit("/", 1)[1]
    assert url == f"trace: {fake_langfuse.url}/project/proj-test/traces/{trace_id}"
    root = next(r for r in fake_langfuse.roots() if r["trace_id"] == trace_id)
    assert json.loads(root["langfuse.observation.input"])["requested"] == {
        "origin": "HYD",
        "destination": "BLR",
        "date": "2026-10-31",
    }
    booking = json.loads(root["langfuse.observation.output"])["booking"]
    assert (booking["origin"], booking["destination"]) == ("BLR", "HYD")


def test_trace_url_unavailable_with_bad_keys(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse
) -> None:
    use_keys(fake_langfuse.url, BROKEN_KEY)
    code, out, _ = ws(capsys, "case", "0")
    assert code == 0
    assert (
        "trace: unavailable (UnauthorizedError), check the keys and LANGFUSE_BASE_URL in .env"
    ) in out.splitlines()


def test_load_runs_a_case_many_times(capsys: pytest.CaptureFixture[str]) -> None:
    code, out, _ = ws(
        capsys, "load", "-n", "3", "--case", "2", "--guard", "off", "--exporter", "console"
    )
    lines = out.splitlines()
    assert code == 0
    assert [line.split(" in ")[0] for line in lines[:3]] == [
        "run 1/3: FAIL",
        "run 2/3: FAIL",
        "run 3/3: FAIL",
    ]
    assert lines[3] == "done: 3 runs of case 2, local check PASS 0/3"
    assert lines[4].startswith("latency over 3 runs: mean ")
    assert lines[4].endswith("(nearest rank; under 100 runs p99 is just the slowest run)")


def scores_for(fake: FakeLangfuse, out: str) -> list[dict[str, object]]:
    trace_ids = [line.rsplit("/", 1)[1] for line in out.splitlines() if line.startswith("trace: ")]
    return [s for t in trace_ids for s in fake.scores if s["traceId"] == t]


def test_sdk_score_fallback_gives_the_gate_triad(
    capsys: pytest.CaptureFixture[str],
    fake_langfuse: FakeLangfuse,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_keys(fake_langfuse.url)
    _, case_0, _ = ws(capsys, "case", "0", "--score", "sdk")
    _, case_2, _ = ws(capsys, "case", "2", "--score", "sdk")
    monkeypatch.setattr(checkout, "GUARDS", REFERENCE)
    _, rerun, _ = ws(capsys, "case", "2", "--rerun", "--score", "sdk")
    scores = [scores_for(fake_langfuse, out) for out in (case_0, case_2, rerun)]
    assert [[s["value"] for s in found] for found in scores] == [[1.0], [0.0], [1.0]]
    assert {s["name"] for found in scores for s in found} == {"booking_matches_request"}
    assert {s["dataType"] for found in scores for s in found} == {"BOOLEAN"}
    assert scores[1][0]["comment"] == (
        "mismatch: origin requested=HYD booked=BLR, destination requested=BLR booked=HYD"
    )
    trace_id = str(scores[1][0]["traceId"])
    root = next(r for r in fake_langfuse.roots() if r["trace_id"] == trace_id)
    assert scores[1][0]["observationId"] == root["span_id"]


def test_load_with_sdk_scores(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse
) -> None:
    use_keys(fake_langfuse.url)
    before = len(fake_langfuse.scores)
    code, _, _ = ws(capsys, "load", "-n", "2", "--case", "2", "--guard", "off", "--score", "sdk")
    assert code == 0
    assert [s["value"] for s in fake_langfuse.scores[before:]] == [0.0, 0.0]


def test_sdk_score_needs_langfuse(capsys: pytest.CaptureFixture[str]) -> None:
    code, _, err = ws(capsys, "case", "0", "--exporter", "console", "--score", "sdk")
    assert code == 2
    assert "--score sdk sends scores to Langfuse" in err


@pytest.mark.parametrize("count", ["0", "-3"])
def test_load_needs_at_least_one_run(capsys: pytest.CaptureFixture[str], count: str) -> None:
    with pytest.raises(SystemExit) as stopped:
        cli.main(["load", "-n", count])
    assert stopped.value.code == 2
    assert "must be 1 or more" in capsys.readouterr().err


@pytest.mark.parametrize("encoding", ["utf-16-le", "utf-16-be", "utf-8"])
def test_env_saved_with_a_byte_order_mark_is_read(
    capsys: pytest.CaptureFixture[str], encoding: str
) -> None:
    Path(".env").write_bytes("\ufeffLLM_MODE=ollama\n".encode(encoding))
    code, _, err = ws(capsys, "case", "0", "--exporter", "console")
    assert code == 2
    assert "LLM_MODE=ollama is not supported" in err


def test_env_in_another_encoding_asks_for_utf8(capsys: pytest.CaptureFixture[str]) -> None:
    Path(".env").write_bytes(b"LANGFUSE_BASE_URL=https://caf\xe9.example\n")
    code, _, err = ws(capsys, "case", "0", "--exporter", "console")
    assert code == 2
    assert err.strip() == "error: .env is not UTF-8 text; open it in an editor and save it as UTF-8"


def test_load_times_the_run_not_the_local_check(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    clock = [0.0]

    def slow_check(requested: dict[str, object], output: dict[str, object]) -> Score:
        clock[0] += 5.0
        return booking_matches_request(requested, output)

    monkeypatch.setattr("time.perf_counter", lambda: clock[0])
    monkeypatch.setattr("tripmate.cli.booking_matches_request", slow_check)
    _, out, _ = ws(capsys, "load", "-n", "1", "--exporter", "console")
    assert "run 1/1: PASS in 0.00s" in out.splitlines()
    assert "done: 1 run of case 0, local check PASS 1/1" in out.splitlines()
