import base64
import gzip
import json
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest

PROJECT = {"id": "proj-test", "name": "tripmate-workshop", "organization": {"id": "o", "name": "o"}}
BROKEN_KEY = "pk-lf-broken"
BUSY_KEY = "pk-lf-busy"
DROPPED_KEY = "pk-lf-dropped"


@dataclass
class FakeLangfuse:
    url: str = ""
    spans: list[dict[str, str]] = field(default_factory=list)
    scores: list[dict[str, object]] = field(default_factory=list)

    def roots(self) -> Iterator[dict[str, str]]:
        return (s for s in self.spans if s["parent"] == "" and s["name"] == "tripmate")


def serve() -> tuple[FakeLangfuse, ThreadingHTTPServer]:
    fake = FakeLangfuse()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return None

        def reply(self, status: int, body: object) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            url = urlsplit(self.path)
            if self.public_key() == BROKEN_KEY:
                self.reply(401, {"message": "Invalid credentials"})
            elif self.public_key() == BUSY_KEY:
                self.reply(503, {"message": "Busy"})
            elif url.path.endswith("/v2/observations"):
                trace_id = parse_qs(url.query)["traceId"][0]
                roots = [
                    {
                        "id": s["span_id"],
                        "traceId": s["trace_id"],
                        "projectId": PROJECT["id"],
                        "startTime": "2026-10-31T09:00:00Z",
                        "type": "AGENT",
                    }
                    for s in fake.roots()
                    if s["trace_id"] == trace_id
                ]
                self.reply(200, {"data": roots, "meta": {}})
            else:
                self.reply(200, {"data": [{**PROJECT, "metadata": {}}]})

        def public_key(self) -> str:
            auth = self.headers.get("Authorization", "Basic ").split(" ", 1)[1]
            return base64.b64decode(auth).decode().split(":", 1)[0]

        def do_POST(self) -> None:
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            if self.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            if self.path.endswith("/otel/v1/traces"):
                if self.public_key() != DROPPED_KEY:
                    self.record_spans(body)
                self.reply(200, {})
            else:
                fake.scores += json.loads(body)
                self.reply(202, {"message": "Accepted"})

        def record_spans(self, body: bytes) -> None:
            request = ExportTraceServiceRequest.FromString(body)
            for resource in request.resource_spans:
                for scope in resource.scope_spans:
                    for span in scope.spans:
                        attributes = {a.key: a.value.string_value for a in span.attributes}
                        fake.spans.append(
                            {
                                **attributes,
                                "name": span.name,
                                "trace_id": span.trace_id.hex(),
                                "span_id": span.span_id.hex(),
                                "parent": span.parent_span_id.hex(),
                            }
                        )

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    fake.url = f"http://127.0.0.1:{server.server_address[1]}"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return fake, server
