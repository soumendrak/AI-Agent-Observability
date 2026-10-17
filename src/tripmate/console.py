import json
from collections import defaultdict
from collections.abc import Iterator, Sequence

from opentelemetry.sdk.trace import ReadableSpan

_TYPE = "langfuse.observation.type"
_LEVEL = "langfuse.observation.level"
_STATUS = "langfuse.observation.status_message"
_INPUT = "langfuse.observation.input"
_OUTPUT = "langfuse.observation.output"


def _field(span: ReadableSpan, key: str) -> dict[str, object]:
    raw = (span.attributes or {}).get(key)
    value = json.loads(str(raw)) if raw else {}
    return value if isinstance(value, dict) else {}


def _details(span: ReadableSpan, kind: str, root: bool) -> Iterator[str]:
    if root:
        inputs, outputs = _field(span, _INPUT), _field(span, _OUTPUT)
        yield f"requested: {json.dumps(inputs.get('requested'))}"
        yield f"booking: {json.dumps(outputs.get('booking'))}"
        yield f"final_message: {json.dumps(outputs.get('final_message'))}"
    if kind == "tool":
        yield f"args: {json.dumps(_field(span, _INPUT))}"


def render(spans: Sequence[ReadableSpan]) -> str:
    children: dict[int | None, list[ReadableSpan]] = defaultdict(list)
    for span in sorted(spans, key=lambda s: s.start_time or 0):
        children[span.parent.span_id if span.parent else None].append(span)
    lines: list[str] = []

    def walk(span: ReadableSpan, depth: int) -> None:
        attributes = span.attributes or {}
        kind = str(attributes.get(_TYPE, "span"))
        error = attributes.get(_LEVEL) == "ERROR"
        status = f"[ERROR] {attributes.get(_STATUS, '')}".rstrip() if error else "OK"
        lines.append(f"{'  ' * depth}{kind} {span.name} {status}")
        lines.extend(f"{'  ' * (depth + 2)}{line}" for line in _details(span, kind, depth == 0))
        for child in children[span.context.span_id if span.context else None]:
            walk(child, depth + 1)

    for root in children[None]:
        walk(root, 0)
    return "\n".join(lines)
