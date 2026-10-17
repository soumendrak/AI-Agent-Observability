import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from fake_langfuse import BROKEN_KEY, FakeLangfuse, serve

from tripmate import cli

REFERENCE = Path(__file__).with_name("reference_guard.py")
PASS = "booking_matches_request: PASS (local check, same logic as the Langfuse evaluator)"


@pytest.fixture(scope="session")
def fake_langfuse() -> Iterator[FakeLangfuse]:
    fake, server = serve()
    yield fake
    server.shutdown()


@pytest.fixture(autouse=True)
def workshop_shell(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL", "LLM_MODE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("tripmate.llm.sleep", lambda seconds: None)


def ws(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def use_keys(fake: FakeLangfuse, public_key: str = "pk-lf-test") -> None:
    Path(".env").write_text(
        f"LANGFUSE_PUBLIC_KEY={public_key}\nLANGFUSE_SECRET_KEY=sk-lf-test\n"
        f"LANGFUSE_BASE_URL={fake.url}\nLLM_MODE=fake\n",
        encoding="utf-8",
    )


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
    monkeypatch.setattr(cli, "GUARDS_FILE", REFERENCE)
    _, out, _ = ws(capsys, "case", "2", "--rerun", "--exporter", "console")
    lines = out.splitlines()
    assert "guard: caught mismatch on origin, destination" in lines
    assert "tool book_flight [ERROR] does not match request: origin, destination" in out
    assert lines[-1] == PASS


def test_guard_off_brings_the_bug_back(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli, "GUARDS_FILE", REFERENCE)
    _, out, _ = ws(capsys, "case", "2", "--rerun", "--guard", "off", "--exporter", "console")
    assert "guard: off" in out.splitlines()
    assert "booking_matches_request: FAIL" in out


def test_rerun_of_a_clean_case(capsys: pytest.CaptureFixture[str]) -> None:
    _, out, _ = ws(capsys, "case", "0", "--rerun", "--exporter", "console")
    assert "guard: did not reject anything" in out.splitlines()
    assert out.splitlines()[-1] == PASS


def test_broken_guards_file_is_reported(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    broken = tmp_path / "guards.py"
    broken.write_text("def validate_booking(requested, args)\n    return\n", encoding="utf-8")
    monkeypatch.setattr(cli, "GUARDS_FILE", broken)
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
    Path(".env").write_text("LLM_MODE=openai\n", encoding="utf-8")
    code, _, err = ws(capsys, "case", "0", "--exporter", "console")
    assert code == 2
    assert "LLM_MODE=openai is not supported" in err


def test_langfuse_mode_sends_the_trace_and_prints_its_url(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse
) -> None:
    use_keys(fake_langfuse)
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
    use_keys(fake_langfuse, BROKEN_KEY)
    code, out, _ = ws(capsys, "case", "0")
    assert code == 0
    assert "trace: unavailable (UnauthorizedError); trace id " in out
