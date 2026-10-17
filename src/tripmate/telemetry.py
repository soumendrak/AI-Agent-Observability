import codecs
import io
import os
from dataclasses import dataclass
from pathlib import Path

import httpx
from dotenv import load_dotenv
from langfuse import Langfuse
from langfuse.api.core.api_error import ApiError
from langfuse.langchain import CallbackHandler
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

KEYS = ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL")
_CONSOLE_KEY = "pk-lf-console"
_CONSOLE_EXPORTER = InMemorySpanExporter()


class SetupError(Exception):
    pass


@dataclass(frozen=True)
class Telemetry:
    langfuse: Langfuse
    handler: CallbackHandler
    memory: InMemorySpanExporter | None = None

    def spans(self, trace_id: str) -> list[ReadableSpan]:
        self.langfuse.flush()
        finished = self.memory.get_finished_spans() if self.memory else ()
        return [s for s in finished if s.context and format(s.context.trace_id, "032x") == trace_id]

    def trace_url(self, trace_id: str) -> str:
        if self.memory is not None:
            return "offline (--exporter console), nothing was sent to Langfuse"
        try:
            url = self.langfuse.get_trace_url(trace_id=trace_id)
        except (ApiError, httpx.HTTPError) as error:
            return f"unavailable ({type(error).__name__}); trace id {trace_id}"
        return url or f"unavailable; trace id {trace_id}"


def load_env(path: Path) -> None:
    if not path.is_file():
        return
    data = path.read_bytes()
    utf16 = data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE))
    try:
        text = data.decode("utf-16" if utf16 else "utf-8-sig")
    except UnicodeDecodeError as error:
        raise SetupError(
            ".env is not UTF-8 text; open it in an editor and save it as UTF-8"
        ) from error
    load_dotenv(stream=io.StringIO(text))


def console() -> Telemetry:
    langfuse = Langfuse(
        public_key=_CONSOLE_KEY,
        secret_key="sk-lf-console",
        base_url="http://127.0.0.1:9",
        span_exporter=_CONSOLE_EXPORTER,
    )
    return Telemetry(langfuse, CallbackHandler(public_key=_CONSOLE_KEY), _CONSOLE_EXPORTER)


def from_env() -> Telemetry:
    missing = [key for key in KEYS if not os.environ.get(key)]
    if missing:
        raise SetupError(
            f"missing {', '.join(missing)}. Copy .env.example to .env and paste your "
            "Langfuse keys, or add --exporter console to work offline."
        )
    public_key, secret_key, base_url = (os.environ[key] for key in KEYS)
    langfuse = Langfuse(public_key=public_key, secret_key=secret_key, base_url=base_url)
    return Telemetry(langfuse, CallbackHandler(public_key=public_key))
