"""The Llm interface: one model request in, one reply out.

Content blocks and messages are plain dicts in Messages API shape, so a reply's content can be
sent back as the next assistant message unchanged, and the test double needs no SDK objects.
"""

from dataclasses import dataclass, field
from typing import Any, Protocol

Block = dict[str, Any]
"""One content block, such as {"type": "text", "text": "..."} or a tool_use block."""

Message = dict[str, Any]
"""One message: {"role": "user" | "assistant", "content": str | list[Block]}."""


class LlmError(Exception):
    """The model call failed (network, auth, rate limit, server). The turn that made it fails."""


class LlmConfigError(Exception):
    """No usable model configuration, such as a missing API key."""


@dataclass(frozen=True)
class LlmReply:
    content: list[Block]
    stop_reason: str
    usage: dict[str, Any] = field(default_factory=dict)
    request_id: str | None = None
    model: str | None = None
    stop_details: dict[str, Any] | None = None

    def tool_uses(self) -> list[Block]:
        return [block for block in self.content if block.get("type") == "tool_use"]


class Llm(Protocol):
    name: str
    """provider:model, written into every log entry about a model call."""

    async def complete(
        self, system: str, tools: list[dict[str, Any]], messages: list[Message]
    ) -> LlmReply: ...
