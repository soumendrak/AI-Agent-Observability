from dataclasses import dataclass

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

_CONSOLE_KEY = "pk-lf-console"
_CONSOLE_EXPORTER = InMemorySpanExporter()


@dataclass(frozen=True)
class Telemetry:
    langfuse: Langfuse
    handler: CallbackHandler
    memory: InMemorySpanExporter

    def spans(self, trace_id: str) -> list[ReadableSpan]:
        self.langfuse.flush()
        finished = self.memory.get_finished_spans()
        return [s for s in finished if s.context and format(s.context.trace_id, "032x") == trace_id]


def console() -> Telemetry:
    langfuse = Langfuse(
        public_key=_CONSOLE_KEY,
        secret_key="sk-lf-console",
        base_url="http://127.0.0.1:9",
        span_exporter=_CONSOLE_EXPORTER,
    )
    return Telemetry(langfuse, CallbackHandler(public_key=_CONSOLE_KEY), _CONSOLE_EXPORTER)
