"""The judge's model call: one system prompt and one user message in, reply text out.

Two providers speak the Anthropic Messages API, and one class serves both:

- anthropic: Claude (default claude-opus-5-5), with adaptive thinking, an explicit effort, the
  verdict's JSON schema as a structured output (so the reply is always valid JSON of the right
  shape), prompt caching, and server-side refusal fallback.
- deepseek: DeepSeek's Anthropic-compatible endpoint (default deepseek-v4-pro). It takes thinking
  and effort but no structured output, so the shape comes from the prompt and is checked after.

The provider is anthropic when ANTHROPIC_API_KEY is set, else deepseek when DEEPSEEK_API_KEY is.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

import anthropic

Provider = Literal["anthropic", "deepseek"]
Effort = Literal["low", "medium", "high", "xhigh", "max"]

DEEPSEEK_BASE_URL = "https://api.deepseek.com/anthropic"
DEFAULT_MODELS: dict[Provider, str] = {
    "anthropic": "claude-opus-5-5",
    "deepseek": "deepseek-v4-pro",
}
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class LlmError(Exception):
    """The model call failed or its reply can't be used (refusal, cut off, API error)."""


class LlmConfigError(Exception):
    """No usable model configuration, such as a missing API key."""


@dataclass(frozen=True)
class Settings:
    provider: Provider
    model: str
    effort: Effort = "high"
    max_tokens: int = 64000


@dataclass(frozen=True)
class Reply:
    text: str
    stop_reason: str
    usage: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    model: str | None = None


class Llm(Protocol):
    name: str
    """provider:model, recorded with every verdict."""

    async def complete(self, system: str, user: str, schema: dict[str, Any]) -> Reply: ...


def pick_provider(env: Mapping[str, str] | None = None) -> Provider:
    env = os.environ if env is None else env
    if env.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if env.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    raise LlmConfigError(
        "No model credentials. Set ANTHROPIC_API_KEY or DEEPSEEK_API_KEY, for example in .env "
        "and run with `uv run --env-file .env judge ...`."
    )


def settings_for(
    provider: Provider | None = None,
    model: str | None = None,
    effort: Effort = "high",
    env: Mapping[str, str] | None = None,
) -> Settings:
    chosen = provider or pick_provider(env)
    return Settings(provider=chosen, model=model or DEFAULT_MODELS[chosen], effort=effort)


def make_client(
    provider: Provider, env: Mapping[str, str] | None = None
) -> anthropic.AsyncAnthropic:
    env = os.environ if env is None else env
    if provider == "deepseek":
        key = env.get("DEEPSEEK_API_KEY")
        if not key:
            raise LlmConfigError("Provider deepseek needs DEEPSEEK_API_KEY.")
        return anthropic.AsyncAnthropic(api_key=key, base_url=DEEPSEEK_BASE_URL)
    # Credentials come from ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN or an `ant auth login` profile.
    return anthropic.AsyncAnthropic()


class AnthropicLlm:
    def __init__(self, settings: Settings, client: anthropic.AsyncAnthropic | None = None):
        self.settings = settings
        self.name = f"{settings.provider}:{settings.model}"
        self._client = client or make_client(settings.provider)

    def request_params(self, system: str, user: str, schema: dict[str, Any]) -> dict[str, Any]:
        s = self.settings
        params: dict[str, Any] = {
            "model": s.model,
            "max_tokens": s.max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "output_config": {"effort": s.effort},
        }
        if s.provider == "anthropic":
            params["thinking"] = {"type": "adaptive"}
            params["output_config"]["format"] = {"type": "json_schema", "schema": schema}
            params["cache_control"] = {"type": "ephemeral"}
            params["betas"] = [FALLBACK_BETA]
            params["fallbacks"] = "default"
        else:
            params["thinking"] = {"type": "enabled"}
        return params

    async def complete(self, system: str, user: str, schema: dict[str, Any]) -> Reply:
        params = self.request_params(system, user, schema)
        try:
            if self.settings.provider == "anthropic":
                async with self._client.beta.messages.stream(**params) as stream:
                    message: Any = await stream.get_final_message()
                    request_id = stream.request_id
            else:
                async with self._client.messages.stream(**params) as stream:
                    message = await stream.get_final_message()
                    request_id = stream.request_id
        except anthropic.APIError as error:
            raise LlmError(f"{type(error).__name__}: {error}") from error
        stop = message.stop_reason or ""
        if stop == "refusal":
            raise LlmError(f"the model declined to judge (request {request_id})")
        if stop == "max_tokens":
            raise LlmError(f"the reply was cut off at max_tokens (request {request_id})")
        text = "".join(block.text for block in message.content if block.type == "text")
        return Reply(
            text=text,
            stop_reason=stop,
            usage=message.usage.to_dict(),
            request_id=request_id,
            model=message.model,
        )
