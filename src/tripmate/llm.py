import json
import math
import random
from collections.abc import Sequence
from time import sleep

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.messages.ai import UsageMetadata
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import PrivateAttr

from tripmate.cases import CASES, Case
from tripmate.request import parse_request
from tripmate.tools import GUARD_REJECTION, Fields


def _call(name: str, args: Fields, messages: Sequence[BaseMessage]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": name, "args": dict(args), "id": f"call_{len(messages)}"}],
    )


def _searched(messages: Sequence[BaseMessage]) -> list[Fields]:
    found = [m for m in messages if isinstance(m, ToolMessage) and m.name == "search_flights"]
    flights: list[Fields] = json.loads(str(found[-1].content))
    return flights


def next_reply(case: Case, messages: Sequence[BaseMessage]) -> AIMessage:
    requested = parse_request(str(messages[0].content))
    last = messages[-1]
    if not isinstance(last, ToolMessage):
        return _call("search_flights", requested, messages)
    if last.name == "search_flights":
        if last.status == "error" or not _searched(messages):
            return AIMessage(content="Sorry, I found no flights for that trip.")
        return _call("book_flight", case.choose_booking(requested), messages)
    if last.status == "success":
        booking: Fields = last.artifact
        route = requested if case.claims_request else booking
        flight = _searched(messages)[0]["flight"] if case.claims_request else booking["flight"]
        return AIMessage(
            content=f"Booked {flight} {route['origin']} to {route['destination']} "
            f"on {route['date']}. PNR {booking['pnr']}."
        )
    if GUARD_REJECTION in str(last.content):
        return _call("book_flight", requested, messages)
    return AIMessage(content="Sorry, I couldn't complete the booking.")


def _usage(messages: Sequence[BaseMessage], reply: AIMessage) -> UsageMetadata:
    prompt = sum(
        len(str(m.content)) + len(json.dumps(getattr(m, "tool_calls", []))) for m in messages
    )
    completion = len(str(reply.content)) + len(json.dumps(reply.tool_calls))
    input_tokens, output_tokens = 120 + prompt // 4, 1 + completion // 4
    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": input_tokens + output_tokens,
    }


class ScriptedFakeLLM(BaseChatModel):
    model_name: str = "tripmate-scripted-1"
    case: int = 0
    seed: int = 0
    latency_scale: float = 1.0
    _rng: random.Random = PrivateAttr()

    def model_post_init(self, context: object, /) -> None:
        super().model_post_init(context)
        self._rng = random.Random(self.seed)

    @property
    def _llm_type(self) -> str:
        return "scripted-fake"

    def latency(self) -> float:
        seconds = self._rng.lognormvariate(math.log(0.25), 0.3)
        if self._rng.random() < 0.03:
            seconds += self._rng.uniform(1.5, 3.0)
        return seconds

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> ChatResult:
        sleep(self.latency() * self.latency_scale)
        reply = next_reply(CASES[self.case], messages)
        reply.usage_metadata = _usage(messages, reply)
        return ChatResult(generations=[ChatGeneration(message=reply)])
