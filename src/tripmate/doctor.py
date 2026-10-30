import hashlib
import os
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import sleep

import httpx
from langfuse.api.core.api_error import ApiError

from tripmate import checkout, models
from tripmate.telemetry import KEYS, SetupError, Telemetry, from_env, load_env

REGIONS = {"EU": "https://cloud.langfuse.com", "US": "https://us.cloud.langfuse.com"}
ARRIVAL_CHECKS = 16


class Failed(Exception):
    pass


def _local(python: tuple[int, int]) -> Iterator[str]:
    if python != (3, 12):
        raise Failed(
            f"Python {python[0]}.{python[1]} is running; run `uv sync`, then `uv run ws doctor`"
        )
    yield "Python 3.12"
    env = Path.cwd() / ".env"
    if not env.is_file():
        raise Failed("no .env here; copy .env.example to .env in the repo folder")
    try:
        load_env(env)
    except SetupError as error:
        raise Failed(str(error)) from error
    yield ".env found"
    public, secret, base_url = (os.environ.get(key, "") for key in KEYS)
    if public.startswith("sk-lf-") and secret.startswith("pk-lf-"):
        raise Failed("the keys are swapped; LANGFUSE_PUBLIC_KEY starts with pk-lf-")
    if (
        not public.startswith("pk-lf-")
        or not secret.startswith("sk-lf-")
        or "..." in public + secret
    ):
        raise Failed("paste your project's keys into .env (pk-lf-... and sk-lf-...)")
    _check_url(base_url)
    yield "keys look right"
    mode = os.environ.get("LLM_MODE", "fake")
    if mode == "openai":
        try:
            model = models.from_env()
        except SetupError as error:
            raise Failed(str(error)) from error
        yield f"LLM_MODE=openai, model {model.model} at {model.base_url or 'the OpenAI API'}"
    elif mode != "fake":
        raise Failed(f"LLM_MODE={mode} is not supported; set LLM_MODE=fake in .env")
    else:
        yield "LLM_MODE=fake"


def _regions() -> str:
    return ", ".join(f"{name} {url}" for name, url in REGIONS.items())


def _check_url(text: str) -> None:
    try:
        url = httpx.URL(text)
    except httpx.InvalidURL as error:
        raise Failed(f"set LANGFUSE_BASE_URL to your region: {_regions()}") from error
    if url.scheme not in ("http", "https") or not url.host:
        raise Failed(f"set LANGFUSE_BASE_URL to your region: {_regions()}")
    if url.path.rstrip("/"):
        raise Failed(
            "LANGFUSE_BASE_URL must stop after the host, like https://us.cloud.langfuse.com; "
            f"remove {url.path.rstrip('/')}"
        )


def _keys_work(base_url: str) -> bool:
    public, secret = os.environ[KEYS[0]], os.environ[KEYS[1]]
    try:
        response = httpx.get(f"{base_url}/api/public/projects", auth=(public, secret), timeout=10)
    except httpx.HTTPError:
        return False
    return response.status_code == 200


def _arrived(telemetry: Telemetry, trace_id: str) -> bool:
    since = datetime.now(UTC) - timedelta(minutes=10)
    for attempt in range(ARRIVAL_CHECKS):
        if attempt:
            sleep(2)
        roots = telemetry.langfuse.api.observations.get_many(
            trace_id=trace_id, is_root_observation=True, from_start_time=since
        )
        if roots.data:
            return True
    return False


def _hello(telemetry: Telemetry) -> str:
    with telemetry.langfuse.start_as_current_observation(
        name="hello-workshop", input={"mic_check": "Is this thing on?"}
    ) as root:
        with telemetry.langfuse.start_as_current_observation(
            name="coffee_check", input={"cups": 1}
        ) as coffee:
            coffee.update(output={"verdict": "sufficient for observability"})
        root.update(output={"reply": "Loud and clear. Langfuse can hear you."})
    return root.trace_id


def _remote(telemetry: Telemetry, base_url: str) -> Iterator[str]:
    project = telemetry.langfuse.api.projects.get().data[0]
    yield f"Langfuse project {project.name} at {base_url}"
    trace_id = _hello(telemetry)
    telemetry.langfuse.flush()
    if not _arrived(telemetry, trace_id):
        raise Failed(
            "the hello trace has not shown up in Langfuse after 30 s; ingestion may be slow "
            "right now, so run `uv run ws doctor` again in a minute"
        )
    yield f"hello trace: {base_url.rstrip('/')}/project/{project.id}/traces/{trace_id}"
    yield "READY-" + hashlib.sha256(project.id.encode()).hexdigest()[:4].upper()


def _explain(error: Exception, base_url: str) -> str:
    if not isinstance(error, ApiError):
        return (
            f"cannot reach {base_url} ({type(error).__name__}): check wifi, proxy, VPN or "
            "TLS inspection, or work offline with `uv run ws case 0 --exporter console`"
        )
    if error.status_code in (401, 403):
        cloud = base_url.rstrip("/") in REGIONS.values()
        for name, url in REGIONS.items():
            if cloud and url != base_url.rstrip("/") and _keys_work(url):
                return (
                    f"these keys belong to the {name} region: set LANGFUSE_BASE_URL={url} in .env"
                )
        return (
            f"Langfuse at {base_url} rejected the keys (HTTP {error.status_code}). Keys only "
            f"work in the region where you made them: {_regions()}"
        )
    return (
        f"Langfuse at {base_url} answered HTTP {error.status_code}; the service may be busy, "
        "try again in a minute or work offline with `uv run ws case 0 --exporter console`"
    )


def run(python: tuple[int, int]) -> int:
    try:
        for line in _local(python):
            print(f"[OK] {line}")
        for line in checkout.review(checkout.GUARDS):
            print(line)
        base_url = os.environ["LANGFUSE_BASE_URL"]
        for line in _remote(from_env(), base_url):
            print(line if line.startswith("READY-") else f"[OK] {line}")
    except (ApiError, httpx.HTTPError) as error:
        print(f"[FAIL] {_explain(error, base_url)}")
        return 1
    except Failed as error:
        print(f"[FAIL] {error}")
        return 1
    return 0
