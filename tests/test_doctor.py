import hashlib
from pathlib import Path

import pytest
from conftest import use_keys, ws
from fake_langfuse import BROKEN_KEY, FakeLangfuse

from tripmate import doctor

pytestmark = pytest.mark.usefixtures("workshop_shell")


def fail_line(capsys: pytest.CaptureFixture[str]) -> str:
    code, out, _ = ws(capsys, "doctor")
    assert code == 1
    return out.splitlines()[-1]


def test_ready(capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse) -> None:
    use_keys(fake_langfuse.url, "pk-lf-doctor")
    code, out, _ = ws(capsys, "doctor")
    lines = out.splitlines()
    assert code == 0
    assert lines[:4] == [
        "[OK] Python 3.12",
        "[OK] .env found",
        "[OK] keys look right",
        f"[OK] Langfuse project tripmate-workshop at {fake_langfuse.url}",
    ]
    assert lines[4].startswith(f"[OK] hello trace: {fake_langfuse.url}/project/proj-test/traces/")
    assert lines[5] == "READY-" + hashlib.sha256(b"proj-test").hexdigest()[:4].upper()


def test_wrong_python(capsys: pytest.CaptureFixture[str]) -> None:
    assert doctor.run((3, 11)) == 1
    assert "Python 3.11 is running; run `uv sync`" in capsys.readouterr().out


def test_missing_env(capsys: pytest.CaptureFixture[str]) -> None:
    assert fail_line(capsys) == "[FAIL] no .env here; copy .env.example to .env in the repo folder"


def test_example_keys(capsys: pytest.CaptureFixture[str]) -> None:
    example = Path(__file__).resolve().parents[1] / ".env.example"
    Path(".env").write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
    assert "paste your project's keys" in fail_line(capsys)


def test_swapped_keys(capsys: pytest.CaptureFixture[str]) -> None:
    use_keys("https://cloud.langfuse.com", "sk-lf-1", "pk-lf-1")
    assert "the keys are swapped" in fail_line(capsys)


def test_base_url_without_scheme(capsys: pytest.CaptureFixture[str]) -> None:
    use_keys("cloud.langfuse.com")
    assert "set LANGFUSE_BASE_URL to your region" in fail_line(capsys)


def test_rejected_keys(capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse) -> None:
    use_keys(fake_langfuse.url, BROKEN_KEY)
    line = fail_line(capsys)
    assert "rejected the keys (HTTP 401)" in line
    assert "https://us.cloud.langfuse.com" in line


def test_unreachable(capsys: pytest.CaptureFixture[str]) -> None:
    use_keys("http://127.0.0.1:9", "pk-lf-unreachable")
    assert "cannot reach http://127.0.0.1:9 (ConnectError)" in fail_line(capsys)
