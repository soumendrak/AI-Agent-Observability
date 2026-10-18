import os
from dataclasses import dataclass

import httpx
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from tripmate.telemetry import SetupError

DEFAULT_MODEL = "gpt-5.4-mini"
SYSTEM = (
    "You are TripMate, a travel booking agent. Make one tool call at a time. First call "
    "search_flights with the origin, destination and date the user asked for (3-letter airport "
    "codes, date as YYYY-MM-DD) and wait for its result. Then call book_flight with the same "
    "three values. Then confirm the booking in one sentence that names the flight, the route, "
    "the date and the PNR."
)


@dataclass(frozen=True)
class RealModel:
    model: str
    api_key: str
    base_url: str | None

    def bind(self, tools: list[BaseTool]) -> Runnable[LanguageModelInput, AIMessage]:
        chat = ChatOpenAI(
            model=self.model,
            api_key=SecretStr(self.api_key),
            base_url=self.base_url,
            use_responses_api=False,
            max_retries=1,
            timeout=60,
        )
        return chat.bind_tools(tools, parallel_tool_calls=False)


def from_env() -> RealModel:
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or "..." in key:
        raise SetupError(
            "LLM_MODE=openai needs OPENAI_API_KEY in .env (a key for OpenAI or any "
            "OpenAI-compatible provider)"
        )
    base_url = os.environ.get("OPENAI_BASE_URL") or None
    if base_url is not None:
        try:
            url = httpx.URL(base_url)
        except httpx.InvalidURL:
            url = httpx.URL()
        if url.scheme not in ("http", "https") or not url.host:
            raise SetupError(
                "OPENAI_BASE_URL must be a full URL like https://api.openai.com/v1, or leave it out"
            )
    return RealModel(os.environ.get("OPENAI_MODEL") or DEFAULT_MODEL, key, base_url)
