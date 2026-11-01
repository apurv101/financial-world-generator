"""AnthropicLlm: the Llm interface on the Anthropic Python SDK.

Two providers speak the Anthropic Messages API, and this one class serves both:

- anthropic: Claude. The default model is claude-opus-5-5 (SPEC). Requests use adaptive thinking
  with summarized display (so log.jsonl shows why an agent acted), an explicit effort, prompt
  caching (the system prompt and tools are identical on every turn) and server-side refusal
  fallback.
- deepseek: DeepSeek's Anthropic-compatible endpoint. It accepts thinking and
  output_config.effort, ignores cache_control and a tool_result's is_error, and does not document
  betas or fallbacks, so requests carry only the shared fields.
"""

import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Literal

import anthropic

from worldgen.llm.base import LlmConfigError, LlmError, LlmReply, Message

Provider = Literal["anthropic", "deepseek"]

DEEPSEEK_BASE_URL = "https://api.deepseek.com/anthropic"

DEFAULT_MODELS: dict[Provider, str] = {
    "anthropic": "claude-opus-5-5",
    "deepseek": "deepseek-v4-pro",
}

FALLBACK_BETA = "server-side-fallback-2026-07-01"


@dataclass(frozen=True)
class LlmSettings:
    provider: Provider
    model: str
    effort: str = "high"
    max_tokens: int = 64000


def pick_provider(env: Mapping[str, str] | None = None) -> Provider:
    """Claude when ANTHROPIC_API_KEY is set, else DeepSeek when DEEPSEEK_API_KEY is set."""
    env = os.environ if env is None else env
    if env.get("ANTHROPIC_API_KEY"):
        return "anthropic"
    if env.get("DEEPSEEK_API_KEY"):
        return "deepseek"
    raise LlmConfigError(
        "No model credentials. Set ANTHROPIC_API_KEY or DEEPSEEK_API_KEY, for example in .env "
        "and run with `uv run --env-file .env ...`."
    )


def settings_for(
    provider: Provider | None = None,
    model: str | None = None,
    effort: str = "high",
    env: Mapping[str, str] | None = None,
) -> LlmSettings:
    chosen = provider or pick_provider(env)
    return LlmSettings(provider=chosen, model=model or DEFAULT_MODELS[chosen], effort=effort)


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
    def __init__(self, settings: LlmSettings, client: anthropic.AsyncAnthropic | None = None):
        self.settings = settings
        self.name = f"{settings.provider}:{settings.model}"
        self._client = client or make_client(settings.provider)

    def request_params(
        self, system: str, tools: list[dict[str, Any]], messages: list[Message]
    ) -> dict[str, Any]:
        s = self.settings
        params: dict[str, Any] = {
            "model": s.model,
            "max_tokens": s.max_tokens,
            "system": system,
            "tools": tools,
            "messages": messages,
            "output_config": {"effort": s.effort},
        }
        if s.provider == "anthropic":
            params["thinking"] = {"type": "adaptive", "display": "summarized"}
            params["cache_control"] = {"type": "ephemeral"}
            params["betas"] = [FALLBACK_BETA]
            params["fallbacks"] = "default"
            # Long tool inputs (a story, a child's prompt) stream as they are written. The API
            # then skips input validation, so every tool validates its own input.
            params["tools"] = [{**tool, "eager_input_streaming": True} for tool in tools]
        else:
            params["thinking"] = {"type": "enabled"}
        return params

    async def complete(
        self, system: str, tools: list[dict[str, Any]], messages: list[Message]
    ) -> LlmReply:
        params = self.request_params(system, tools, messages)
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
        stop_details = getattr(message, "stop_details", None)
        return LlmReply(
            content=[block.to_dict() for block in message.content],
            stop_reason=message.stop_reason or "",
            usage=message.usage.to_dict(),
            request_id=request_id,
            model=message.model,
            stop_details=stop_details.to_dict() if stop_details is not None else None,
        )
