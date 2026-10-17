from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from fake_langfuse import FakeLangfuse, serve

from tripmate import cli
from tripmate.agent import RunResult, run_agent
from tripmate.guards import validate_booking
from tripmate.request import EXAMPLE
from tripmate.telemetry import Telemetry, console
from tripmate.tools import Guard

Run = Callable[..., RunResult]


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


@pytest.fixture(scope="session")
def fake_langfuse() -> Iterator[FakeLangfuse]:
    fake, server = serve()
    yield fake
    server.shutdown()


@pytest.fixture
def workshop_shell(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    for key in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL", "LLM_MODE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr("tripmate.llm.sleep", lambda seconds: None)
    monkeypatch.setattr("tripmate.doctor.sleep", lambda seconds: None)


def ws(capsys: pytest.CaptureFixture[str], *argv: str) -> tuple[int, str, str]:
    code = cli.main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def use_keys(base_url: str, public_key: str = "pk-lf-test", secret_key: str = "sk-lf-test") -> None:
    Path(".env").write_text(
        f"LANGFUSE_PUBLIC_KEY={public_key}\nLANGFUSE_SECRET_KEY={secret_key}\n"
        f"LANGFUSE_BASE_URL={base_url}\nLLM_MODE=fake\n",
        encoding="utf-8",
    )
