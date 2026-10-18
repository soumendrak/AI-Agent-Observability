import json
import sys
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest
from conftest import Run, tree, use_keys, ws
from fake_langfuse import FakeLangfuse
from opentelemetry.sdk.trace import ReadableSpan
from stub_openai import REJECTED_KEY, TRIP, StubOpenAI, serve

from tripmate import cli, models
from tripmate.agent import RunResult, run_agent
from tripmate.request import EXAMPLE
from tripmate.telemetry import SetupError, Telemetry
from tripmate.tools import no_guard

pytestmark = pytest.mark.usefixtures("workshop_shell")


@pytest.fixture
def stub() -> Iterator[StubOpenAI]:
    found, server = serve()
    yield found
    server.shutdown()


def openai_env(base_url: str = "", key: str = "sk-test", model: str = "") -> None:
    lines = ["LLM_MODE=openai", f"OPENAI_API_KEY={key}"]
    lines += [f"OPENAI_BASE_URL={base_url}"] if base_url else []
    lines += [f"OPENAI_MODEL={model}"] if model else []
    with Path(".env").open("a", encoding="utf-8") as env:
        env.write("\n".join(lines) + "\n")


Node = tuple[str, str, str]


def shape(telemetry: Telemetry, result: RunResult) -> list[tuple[Node, Node | None]]:
    spans = telemetry.spans(result.trace_id)

    def node(span: ReadableSpan) -> Node:
        attributes = span.attributes or {}
        kind = str(attributes.get("langfuse.observation.type"))
        level = str(attributes.get("langfuse.observation.level", "DEFAULT"))
        return (kind, "model" if kind == "generation" else span.name, level)

    by_id = {s.context.span_id: s for s in spans if s.context}
    edges = [(node(s), node(by_id[s.parent.span_id]) if s.parent else None) for s in spans]
    return sorted(edges, key=repr)


def test_real_model_trace_has_the_same_tree_shape(
    run: Run, telemetry: Telemetry, stub: StubOpenAI
) -> None:
    model = models.RealModel("stub-model", "sk-test", stub.url)
    real = run_agent(EXAMPLE, 0, no_guard, telemetry, model=model)
    fake = run(0)
    assert shape(telemetry, real) == shape(telemetry, fake)
    assert len(shape(telemetry, real)) == len(tree(telemetry, fake))
    assert real.booking == {"pnr": "DE224B", "flight": "TM-204", **TRIP}
    assert real.final_message == "Booked TM-204 HYD to BLR on 2026-10-31."
    generation = next(
        s.attributes or {}
        for s in telemetry.spans(real.trace_id)
        if (s.attributes or {}).get("langfuse.observation.type") == "generation"
    )
    assert generation["langfuse.observation.model.name"] == "stub-model"
    usage = json.loads(str(generation["langfuse.observation.usage_details"]))
    assert (usage["input"], usage["output"]) == (50, 10)


def test_the_model_gets_the_tools_and_the_instructions(
    capsys: pytest.CaptureFixture[str], stub: StubOpenAI
) -> None:
    openai_env(stub.url)
    code, out, _ = ws(capsys, "run", "--exporter", "console")
    assert code == 0
    assert "TripMate: Booked TM-204 HYD to BLR on 2026-10-31." in out
    first = stub.requests[0]
    tools = cast(list[dict[str, dict[str, str]]], first["tools"])
    messages = cast(list[dict[str, str]], first["messages"])
    assert first["model"] == models.DEFAULT_MODEL
    assert first["parallel_tool_calls"] is False
    assert [t["function"]["name"] for t in tools] == ["search_flights", "book_flight"]
    assert [m["role"] for m in messages] == ["system", "user"]
    assert set(stub.keys) == {"sk-test"}


def test_openai_model_and_base_url_come_from_env(
    capsys: pytest.CaptureFixture[str], stub: StubOpenAI
) -> None:
    openai_env(stub.url, model="my-local-model")
    code, _, _ = ws(capsys, "load", "-n", "2", "--exporter", "console")
    assert code == 0
    assert {r["model"] for r in stub.requests} == {"my-local-model"}


def test_scripted_faults_need_the_fake_model(capsys: pytest.CaptureFixture[str]) -> None:
    openai_env()
    code, _, err = ws(capsys, "case", "2", "--exporter", "console")
    assert code == 2
    assert "error: LLM_MODE=openai runs only case 0; the workshop faults need LLM_MODE=fake" in err


def test_rejected_key_is_reported_without_a_traceback(
    capsys: pytest.CaptureFixture[str], stub: StubOpenAI
) -> None:
    openai_env(stub.url, key=REJECTED_KEY)
    code, _, err = ws(capsys, "run", "--exporter", "console")
    assert code == 2
    assert err == (
        "error: the model call failed (OpenAIAuthenticationError); check OPENAI_API_KEY, "
        "OPENAI_BASE_URL and OPENAI_MODEL in .env\n"
    )
    assert REJECTED_KEY not in err


@pytest.mark.parametrize(
    ("env", "message"),
    [
        (
            {"OPENAI_API_KEY": "sk-test", "OPENAI_BASE_URL": "https://api.openai.com:notaport/v1"},
            "OPENAI_BASE_URL must be a full URL like https://api.openai.com/v1, or leave it out",
        ),
        ({}, "LLM_MODE=openai needs OPENAI_API_KEY in .env"),
        ({"OPENAI_API_KEY": "sk-..."}, "LLM_MODE=openai needs OPENAI_API_KEY in .env"),
        (
            {"OPENAI_API_KEY": "sk-test", "OPENAI_BASE_URL": "api.openai.com/v1"},
            "OPENAI_BASE_URL must be a full URL like https://api.openai.com/v1, or leave it out",
        ),
    ],
)
def test_settings_are_checked(
    monkeypatch: pytest.MonkeyPatch, env: dict[str, str], message: str
) -> None:
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(SetupError, match=message):
        models.from_env()


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert models.from_env() == models.RealModel(models.DEFAULT_MODEL, "sk-test", None)


def test_doctor_checks_the_openai_settings(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse
) -> None:
    use_keys(fake_langfuse.url, "pk-lf-openai-doctor")
    openai_env(model="gpt-test")
    code, out, _ = ws(capsys, "doctor")
    assert code == 0
    assert "[OK] LLM_MODE=openai, model gpt-test at the OpenAI API" in out.splitlines()
    assert out.splitlines()[-1].startswith("READY-")


def test_doctor_names_a_custom_base_url(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse
) -> None:
    use_keys(fake_langfuse.url, "pk-lf-openai-doctor-2")
    openai_env("http://localhost:11434/v1")
    _, out, _ = ws(capsys, "doctor")
    assert (
        f"[OK] LLM_MODE=openai, model {models.DEFAULT_MODEL} at http://localhost:11434/v1"
    ) in out.splitlines()


def test_doctor_fails_without_the_key(
    capsys: pytest.CaptureFixture[str], fake_langfuse: FakeLangfuse
) -> None:
    use_keys(fake_langfuse.url, "pk-lf-openai-doctor-3")
    openai_env(key="")
    code, out, _ = ws(capsys, "doctor")
    assert code == 1
    assert out.splitlines()[-1].startswith("[FAIL] LLM_MODE=openai needs OPENAI_API_KEY in .env")


def test_the_api_key_stays_out_of_repr() -> None:
    model = models.RealModel("stub-model", "sk-hidden-123", None)
    assert "sk-hidden-123" not in repr(model)
    assert repr(model) == "RealModel(model='stub-model', base_url=None)"


def test_openai_mode_without_the_extra_says_how_to_install_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(sys.modules, "langchain_openai", None)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    with pytest.raises(SetupError, match=r"run: uv sync --extra openai"):
        models.from_env()


def test_other_errors_still_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(*_: object) -> None:
        raise RuntimeError("not a model error")

    monkeypatch.setattr(cli, "report", broken)
    with pytest.raises(RuntimeError, match="not a model error"):
        cli.main(["run", "--exporter", "console"])


def installed_by_default() -> set[str]:
    lock = tomllib.loads(Path(__file__).parents[1].joinpath("uv.lock").read_text("utf-8"))
    packages = {p["name"]: p for p in lock["package"]}
    root = packages["tripmate"]
    todo = list(root["dependencies"]) + [d for g in root["dev-dependencies"].values() for d in g]
    seen: set[str] = set()
    while todo:
        dependency = todo.pop()
        package = packages[dependency["name"]]
        for extra in dependency.get("extra", []):
            todo += package["optional-dependencies"][extra]
        if dependency["name"] not in seen:
            seen.add(dependency["name"])
            todo += package.get("dependencies", [])
    return seen


def test_a_plain_locked_sync_leaves_out_the_openai_extra() -> None:
    default = installed_by_default()
    assert "langfuse" in default
    assert {"langchain-openai", "openai", "tiktoken"}.isdisjoint(default)
