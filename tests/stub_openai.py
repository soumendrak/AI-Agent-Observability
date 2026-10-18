import json
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TRIP = {"origin": "HYD", "destination": "BLR", "date": "2026-10-31"}
REJECTED_KEY = "sk-rejected"


@dataclass
class StubOpenAI:
    url: str = ""
    requests: list[dict[str, object]] = field(default_factory=list)
    keys: list[str] = field(default_factory=list)


def _reply(tool_results: int) -> dict[str, object]:
    if tool_results < 2:
        name = "search_flights" if tool_results == 0 else "book_flight"
        message: dict[str, object] = {
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": f"call_{tool_results}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(TRIP)},
                }
            ],
        }
    else:
        message = {"role": "assistant", "content": "Booked TM-204 HYD to BLR on 2026-10-31."}
    return {
        "id": f"chatcmpl-{tool_results}",
        "object": "chat.completion",
        "created": 1793000000,
        "model": "stub-model",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 50, "completion_tokens": 10, "total_tokens": 60},
    }


def serve() -> tuple[StubOpenAI, ThreadingHTTPServer]:
    stub = StubOpenAI()

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: object) -> None:
            return None

        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            key = self.headers.get("Authorization", "").removeprefix("Bearer ")
            stub.requests.append(body)
            stub.keys.append(key)
            status, reply = (
                (401, {"error": {"message": "Incorrect API key", "type": "invalid_request_error"}})
                if key == REJECTED_KEY
                else (200, _reply(sum(m["role"] == "tool" for m in body["messages"])))
            )
            data = json.dumps(reply).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    stub.url = f"http://127.0.0.1:{server.server_address[1]}/v1"
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return stub, server
