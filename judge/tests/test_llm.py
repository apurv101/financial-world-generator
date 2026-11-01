import asyncio
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2 as httpx
import pytest

from llm_judge.llm import (
    DEEPSEEK_BASE_URL,
    AnthropicLlm,
    LlmConfigError,
    LlmError,
    Settings,
    make_client,
    pick_provider,
    settings_for,
)

SCHEMA = {"type": "object"}


class Usage:
    def to_dict(self) -> dict[str, Any]:
        return {"input_tokens": 10, "output_tokens": 5}


class Stream:
    def __init__(self, message: Any, error: Exception | None):
        self.message, self.error = message, error

    async def __aenter__(self) -> "Stream":
        if self.error:
            raise self.error
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def get_final_message(self) -> Any:
        return self.message

    @property
    def request_id(self) -> str:
        return "req_1"


class Messages:
    def __init__(self, stop: str = "end_turn", error: Exception | None = None):
        self.calls: list[dict[str, Any]] = []
        self.stop, self.error = stop, error

    def stream(self, **params: Any) -> Stream:
        self.calls.append(params)
        message = SimpleNamespace(
            content=[
                SimpleNamespace(type="thinking", thinking="hmm"),
                SimpleNamespace(type="text", text='{"a": '),
                SimpleNamespace(type="text", text="1}"),
            ],
            stop_reason=self.stop,
            usage=Usage(),
            model="m",
        )
        return Stream(message, self.error)


class Client:
    def __init__(self, stop: str = "end_turn", error: Exception | None = None):
        self.messages = Messages(stop, error)
        self.beta = SimpleNamespace(messages=Messages(stop, error))


def test_pick_provider() -> None:
    assert pick_provider({"ANTHROPIC_API_KEY": "a", "DEEPSEEK_API_KEY": "d"}) == "anthropic"
    assert pick_provider({"DEEPSEEK_API_KEY": "d"}) == "deepseek"
    with pytest.raises(LlmConfigError):
        pick_provider({})
    assert settings_for(env={"DEEPSEEK_API_KEY": "d"}).model == "deepseek-v4-pro"
    assert settings_for("anthropic", effort="max").model == "claude-opus-5-5"


def test_make_client() -> None:
    client = make_client("deepseek", {"DEEPSEEK_API_KEY": "d"})
    assert str(client.base_url).rstrip("/") == DEEPSEEK_BASE_URL
    with pytest.raises(LlmConfigError):
        make_client("deepseek", {})


def test_anthropic_request_uses_structured_output() -> None:
    client = Client()
    llm = AnthropicLlm(Settings("anthropic", "claude-opus-5-5"), client)  # type: ignore[arg-type]
    reply = asyncio.run(llm.complete("sys", "user", SCHEMA))
    params = client.beta.messages.calls[0]
    assert params["output_config"] == {
        "effort": "high",
        "format": {"type": "json_schema", "schema": SCHEMA},
    }
    assert params["thinking"] == {"type": "adaptive"}
    assert params["fallbacks"] == "default"
    assert (reply.text, reply.request_id, reply.usage["input_tokens"]) == ('{"a": 1}', "req_1", 10)
    assert llm.name == "anthropic:claude-opus-5-5"


def test_deepseek_request_has_only_shared_fields() -> None:
    client = Client()
    llm = AnthropicLlm(Settings("deepseek", "deepseek-v4-pro", "low"), client)  # type: ignore[arg-type]
    asyncio.run(llm.complete("sys", "user", SCHEMA))
    params = client.messages.calls[0]
    assert params["output_config"] == {"effort": "low"}
    assert params["thinking"] == {"type": "enabled"}
    assert "fallbacks" not in params and "betas" not in params


@pytest.mark.parametrize(("stop", "message"), [("refusal", "declined"), ("max_tokens", "cut off")])
def test_unusable_stop_reasons(stop: str, message: str) -> None:
    llm = AnthropicLlm(Settings("deepseek", "m"), Client(stop=stop))  # type: ignore[arg-type]
    with pytest.raises(LlmError, match=message):
        asyncio.run(llm.complete("s", "u", SCHEMA))


def test_api_error_becomes_llm_error() -> None:
    request = httpx.Request("POST", "https://example.com")
    error = anthropic.APIConnectionError(request=request)
    llm = AnthropicLlm(Settings("anthropic", "m"), Client(error=error))  # type: ignore[arg-type]
    with pytest.raises(LlmError, match="APIConnectionError"):
        asyncio.run(llm.complete("s", "u", SCHEMA))


def status_error(code: int) -> anthropic.APIStatusError:
    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(code, request=request)
    return anthropic.APIStatusError("status", response=response, body=None)


@pytest.mark.parametrize(
    ("error", "transient"),
    [
        (anthropic.APIConnectionError(request=httpx.Request("POST", "https://x")), True),
        (httpx.ReadTimeout("stalled mid-stream"), True),
        (status_error(529), True),
        (status_error(429), True),
        (status_error(400), False),
    ],
)
def test_errors_are_marked_transient_or_not(error: Exception, transient: bool) -> None:
    llm = AnthropicLlm(Settings("deepseek", "m"), Client(error=error))  # type: ignore[arg-type]
    with pytest.raises(LlmError) as caught:
        asyncio.run(llm.complete("s", "u", SCHEMA))
    assert caught.value.transient is transient
