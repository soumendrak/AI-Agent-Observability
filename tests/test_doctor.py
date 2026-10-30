import hashlib
from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import use_keys, ws
from fake_langfuse import BROKEN_KEY, BUSY_KEY, DROPPED_KEY, FakeLangfuse, serve

from tripmate import checkout, doctor

pytestmark = pytest.mark.usefixtures(
    "workshop_shell", "offline_regions", "workshop_clone", "before_freeze"
)
UNREACHABLE = "http://127.0.0.1:9"


@pytest.fixture
def offline_regions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "REGIONS", {"EU": UNREACHABLE, "US": UNREACHABLE})


@pytest.fixture
def workshop_clone(clone: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(checkout, "GUARDS", clone / "guards.py")
    return clone


@pytest.fixture
def other_region() -> Iterator[str]:
    fake, server = serve(accepts_keys=False)
    yield fake.url
    server.shutdown()


def fail_line(capsys: pytest.CaptureFixture[str]) -> str:
    code, out, _ = ws(capsys, "doctor")
    assert code == 1
    return out.splitlines()[-1]


def test_ready(capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse) -> None:
    use_keys(fake_langfuse.url, "pk-lf-doctor")
    code, out, _ = ws(capsys, "doctor")
    lines = out.splitlines()
    assert code == 0
    assert lines[:6] == [
        "[OK] Python 3.12",
        "[OK] .env found",
        "[OK] keys look right",
        "[OK] LLM_MODE=fake",
        "[OK] guards.py is the original",
        f"[OK] Langfuse project tripmate-workshop at {fake_langfuse.url}",
    ]
    assert lines[6].startswith(f"[OK] hello trace: {fake_langfuse.url}/project/proj-test/traces/")
    assert lines[7] == "READY-" + hashlib.sha256(b"proj-test").hexdigest()[:4].upper()


def test_wrong_python(capsys: pytest.CaptureFixture[str]) -> None:
    assert doctor.run((3, 11)) == 1
    assert "Python 3.11 is running; run `uv sync`" in capsys.readouterr().out


def test_missing_env(capsys: pytest.CaptureFixture[str]) -> None:
    assert fail_line(capsys) == "[FAIL] no .env here; copy .env.example to .env in the repo folder"


def test_example_keys(capsys: pytest.CaptureFixture[str]) -> None:
    example = Path(__file__).resolve().parents[1] / ".env.example"
    Path(".env").write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    assert "paste your project's keys" in fail_line(capsys)


def test_secret_key_placeholder(capsys: pytest.CaptureFixture[str]) -> None:
    use_keys("https://cloud.langfuse.com", "pk-lf-1234", "sk-lf-...")
    assert "paste your project's keys" in fail_line(capsys)


def test_swapped_keys(capsys: pytest.CaptureFixture[str]) -> None:
    use_keys("https://cloud.langfuse.com", "sk-lf-1", "pk-lf-1")
    assert "the keys are swapped" in fail_line(capsys)


def test_unsupported_llm_mode(capsys: pytest.CaptureFixture[str]) -> None:
    use_keys("https://cloud.langfuse.com")
    with Path(".env").open("a", encoding="utf-8") as env:
        env.write("LLM_MODE=ollama\n")
    assert fail_line(capsys) == "[FAIL] LLM_MODE=ollama is not supported; set LLM_MODE=fake in .env"


def test_base_url_without_scheme(capsys: pytest.CaptureFixture[str]) -> None:
    use_keys("cloud.langfuse.com")
    assert "set LANGFUSE_BASE_URL to your region" in fail_line(capsys)


def test_base_url_with_bad_port(capsys: pytest.CaptureFixture[str]) -> None:
    use_keys("https://cloud.langfuse.com:notaport")
    assert "set LANGFUSE_BASE_URL to your region" in fail_line(capsys)


def test_base_url_with_a_path(capsys: pytest.CaptureFixture[str]) -> None:
    use_keys("https://us.cloud.langfuse.com/project/abc")
    assert fail_line(capsys) == (
        "[FAIL] LANGFUSE_BASE_URL must stop after the host, like https://us.cloud.langfuse.com; "
        "remove /project/abc"
    )


def test_rejected_keys(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(doctor, "REGIONS", {"EU": fake_langfuse.url, "US": UNREACHABLE})
    use_keys(fake_langfuse.url, BROKEN_KEY)
    line = fail_line(capsys)
    assert "rejected the keys (HTTP 401)" in line
    assert f"US {UNREACHABLE}" in line


def test_keys_from_the_other_region_are_detected(
    capsys: pytest.CaptureFixture[str],
    fake_langfuse: FakeLangfuse,
    other_region: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "REGIONS", {"EU": other_region, "US": fake_langfuse.url})
    use_keys(other_region, "pk-lf-region")
    assert fail_line(capsys) == (
        f"[FAIL] these keys belong to the US region: set LANGFUSE_BASE_URL={fake_langfuse.url} "
        "in .env"
    )


def test_env_saved_as_utf16_by_powershell(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse
) -> None:
    use_keys(fake_langfuse.url, "pk-lf-utf16")
    text = Path(".env").read_text(encoding="utf-8")
    Path(".env").write_text(text, encoding="utf-16")
    code, out, _ = ws(capsys, "doctor")
    assert code == 0
    assert out.splitlines()[-1].startswith("READY-")


def test_unreachable(capsys: pytest.CaptureFixture[str]) -> None:
    use_keys(UNREACHABLE, "pk-lf-unreachable")
    line = fail_line(capsys)
    assert f"cannot reach {UNREACHABLE} (ConnectError)" in line
    assert line.endswith("work offline with `uv run ws case 0 --exporter console`")


def test_busy_service_is_not_blamed_on_the_keys(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse
) -> None:
    use_keys(fake_langfuse.url, BUSY_KEY)
    line = fail_line(capsys)
    assert "answered HTTP 503; the service may be busy" in line
    assert "rejected" not in line


def test_hello_trace_must_arrive(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("tripmate.doctor.ARRIVAL_CHECKS", 2)
    use_keys(fake_langfuse.url, DROPPED_KEY)
    assert fail_line(capsys) == (
        "[FAIL] the hello trace has not shown up in Langfuse after 30 s; ingestion may be slow "
        "right now, so run `uv run ws doctor` again in a minute"
    )


def test_env_in_another_encoding_fails_like_any_other_check(
    capsys: pytest.CaptureFixture[str],
) -> None:
    Path(".env").write_bytes(b"LANGFUSE_BASE_URL=https://caf\xe9.example\n")
    assert fail_line(capsys) == (
        "[FAIL] .env is not UTF-8 text; open it in an editor and save it as UTF-8"
    )


def test_hello_trace_is_checked_again_at_30_seconds(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "tripmate.doctor.sleep", lambda seconds: fake_langfuse.events.append(f"wait {seconds}")
    )
    fake_langfuse.events.clear()
    use_keys(fake_langfuse.url, DROPPED_KEY)
    fail_line(capsys)
    assert fake_langfuse.events == ["check"] + ["wait 2", "check"] * 15


def test_keys_for_a_self_hosted_server_never_go_to_the_cloud(
    capsys: pytest.CaptureFixture[str],
    fake_langfuse: FakeLangfuse,
    other_region: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(doctor, "REGIONS", {"EU": UNREACHABLE, "US": fake_langfuse.url})
    use_keys(other_region, "pk-lf-self-hosted")
    line = fail_line(capsys)
    assert f"Langfuse at {other_region} rejected the keys (HTTP 401)" in line
    assert "belong to" not in line


def test_edited_guards_warns_but_stays_ready(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse, workshop_clone: Path
) -> None:
    (workshop_clone / "guards.py").write_text("def validate_booking(r, a):\n    1\n", "utf-8")
    use_keys(fake_langfuse.url, "pk-lf-edited")
    code, out, _ = ws(capsys, "doctor")
    lines = out.splitlines()
    assert code == 0
    assert lines[4].startswith("[WARN] guards.py differs from the workshop version")
    assert lines[-1].startswith("READY-")
