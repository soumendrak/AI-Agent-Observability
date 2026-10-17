import hashlib
import os
from collections.abc import Iterator
from pathlib import Path

import httpx
from langfuse.api.core.api_error import ApiError

from tripmate.agent import run_agent
from tripmate.request import EXAMPLE
from tripmate.telemetry import KEYS, Telemetry, from_env
from tripmate.tools import no_guard

REGIONS = "EU https://cloud.langfuse.com, US https://us.cloud.langfuse.com"


class Failed(Exception):
    pass


def _local(python: tuple[int, int]) -> Iterator[str]:
    if python != (3, 12):
        raise Failed(
            f"Python {python[0]}.{python[1]} is running; run `uv sync`, then `uv run ws doctor`"
        )
    yield "Python 3.12"
    if not (Path.cwd() / ".env").is_file():
        raise Failed("no .env here; copy .env.example to .env in the repo folder")
    yield ".env found"
    public, secret, base_url = (os.environ.get(key, "") for key in KEYS)
    if public.startswith("sk-lf-") and secret.startswith("pk-lf-"):
        raise Failed("the keys are swapped; LANGFUSE_PUBLIC_KEY starts with pk-lf-")
    if not public.startswith("pk-lf-") or not secret.startswith("sk-lf-") or "..." in public:
        raise Failed("paste your project's keys into .env (pk-lf-... and sk-lf-...)")
    if not base_url.startswith(("https://", "http://")):
        raise Failed(f"set LANGFUSE_BASE_URL to your region: {REGIONS}")
    yield "keys look right"


def _remote(telemetry: Telemetry, base_url: str) -> Iterator[str]:
    try:
        projects = telemetry.langfuse.api.projects.get()
    except ApiError as error:
        raise Failed(
            f"Langfuse at {base_url} rejected the keys (HTTP {error.status_code}). Keys only "
            f"work in the region where you made them: {REGIONS}"
        ) from error
    except httpx.HTTPError as error:
        raise Failed(
            f"cannot reach {base_url} ({type(error).__name__}): check wifi, proxy, VPN or "
            "TLS inspection, or work offline with --exporter console"
        ) from error
    project = projects.data[0]
    yield f"Langfuse project {project.name} at {base_url}"
    result = run_agent(EXAMPLE, 0, no_guard, telemetry, latency_scale=0)
    telemetry.langfuse.flush()
    yield f"hello trace: {telemetry.trace_url(result.trace_id)}"
    yield "READY-" + hashlib.sha256(project.id.encode()).hexdigest()[:4].upper()


def run(python: tuple[int, int]) -> int:
    try:
        for line in _local(python):
            print(f"[OK] {line}")
        for line in _remote(from_env(), os.environ["LANGFUSE_BASE_URL"]):
            print(line if line.startswith("READY-") else f"[OK] {line}")
    except Failed as error:
        print(f"[FAIL] {error}")
        return 1
    return 0
