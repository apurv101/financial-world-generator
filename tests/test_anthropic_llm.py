import asyncio
from types import SimpleNamespace
from typing import Any

import anthropic
import httpx2 as httpx
import pytest

from worldgen.llm.anthropic_llm import (
    DEEPSEEK_BASE_URL,
    AnthropicLlm,
    LlmSettings,
    make_client,
    pick_provider,
    settings_for,
)
from worldgen.llm.base import LlmConfigError, LlmError

TOOLS = [{"name": "tell_story", "description": "d", "input_schema": {"type": "object"}}]
MESSAGES = [{"role": "user", "content": "hi"}]


class Block:
    def __init__(self, data: dict[str, Any]):
        self.data = data

    def to_dict(self) -> dict[str, Any]:
        return self.data


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
    def __init__(self, error: Exception | None = None):
        self.calls: list[dict[str, Any]] = []
        self.error = error

    def stream(self, **params: Any) -> Stream:
        self.calls.append(params)
        message = SimpleNamespace(
            content=[
                Block(
                    {"type": "tool_use", "id": "t1", "name": "tell_story", "input": {"story": "x"}}
                )
            ],
            stop_reason="tool_use",
            usage=Block({"input_tokens": 10, "output_tokens": 5}),
            model="claude-opus-5-5",
            stop_details=None,
        )
        return Stream(message, self.error)


class Client:
    def __init__(self, error: Exception | None = None):
        self.messages = Messages(error)
        self.beta = SimpleNamespace(messages=Messages(error))


def complete(llm: AnthropicLlm) -> Any:
    return asyncio.run(llm.complete("system", TOOLS, MESSAGES))


def test_anthropic_requests_use_claude_features_on_the_beta_stream() -> None:
    client = Client()
    llm = AnthropicLlm(LlmSettings("anthropic", "claude-opus-5-5", "high"), client)  # type: ignore[arg-type]
    reply = complete(llm)
    assert client.messages.calls == []
    params = client.beta.messages.calls[0]
    assert params["model"] == "claude-opus-5-5" and params["max_tokens"] == 64000
    assert params["thinking"] == {"type": "adaptive", "display": "summarized"}
    assert params["output_config"] == {"effort": "high"}
    assert params["cache_control"] == {"type": "ephemeral"}
    assert params["fallbacks"] == "default" and params["betas"] == [
        "server-side-fallback-2026-07-01"
    ]
    assert params["tools"][0]["eager_input_streaming"] is True
    assert TOOLS[0].get("eager_input_streaming") is None
    assert reply.tool_uses()[0]["input"] == {"story": "x"}
    assert reply.request_id == "req_1" and reply.usage == {"input_tokens": 10, "output_tokens": 5}
    assert llm.name == "anthropic:claude-opus-5-5"


def test_deepseek_requests_carry_only_shared_fields_on_the_plain_stream() -> None:
    client = Client()
    llm = AnthropicLlm(LlmSettings("deepseek", "deepseek-v4-pro", "high"), client)  # type: ignore[arg-type]
    complete(llm)
    assert client.beta.messages.calls == []
    params = client.messages.calls[0]
    assert params["thinking"] == {"type": "enabled"}
    assert params["output_config"] == {"effort": "high"}
    for claude_only in ("cache_control", "fallbacks", "betas"):
        assert claude_only not in params
    assert params["tools"] == TOOLS


def test_api_errors_become_llm_errors() -> None:
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    error = anthropic.APIConnectionError(request=request)
    llm = AnthropicLlm(LlmSettings("deepseek", "deepseek-v4-pro"), Client(error))  # type: ignore[arg-type]
    with pytest.raises(LlmError, match="APIConnectionError"):
        complete(llm)


def test_pick_provider_prefers_anthropic_then_deepseek() -> None:
    assert pick_provider({"ANTHROPIC_API_KEY": "a", "DEEPSEEK_API_KEY": "d"}) == "anthropic"
    assert pick_provider({"DEEPSEEK_API_KEY": "d"}) == "deepseek"
    with pytest.raises(LlmConfigError, match="No model credentials"):
        pick_provider({})


def test_settings_default_models() -> None:
    assert settings_for(env={"DEEPSEEK_API_KEY": "d"}).model == "deepseek-v4-pro"
    assert settings_for("anthropic", env={}).model == "claude-opus-5-5"
    assert settings_for("deepseek", "deepseek-flash", "low", env={}).effort == "low"


def test_make_client_points_deepseek_at_its_anthropic_endpoint() -> None:
    client = make_client("deepseek", {"DEEPSEEK_API_KEY": "sk-test"})
    assert str(client.base_url).rstrip("/") == DEEPSEEK_BASE_URL
    assert client.api_key == "sk-test"
    with pytest.raises(LlmConfigError, match="DEEPSEEK_API_KEY"):
        make_client("deepseek", {})
