"""FakeLlm: a test double that replies from a script and records every request."""

import copy
import itertools
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

from worldgen.llm.base import LlmReply, Message

_ids = itertools.count(1)


@dataclass(frozen=True)
class Request:
    system: str
    tools: list[dict[str, Any]]
    messages: list[Message]

    @property
    def first_user_text(self) -> str:
        content = self.messages[0]["content"]
        return content if isinstance(content, str) else ""


Responder = Callable[[Request], LlmReply]


class FakeLlm:
    """Replies in order from a list, or by calling a responder with each request.

    A responder suits parallel turns, where the order of requests across nodes is not fixed:
    it can look at the request (for example the node's first message) to pick its reply.
    """

    name = "fake:scripted"

    def __init__(self, script: Sequence[LlmReply] | Responder):
        self._responder = script if callable(script) else None
        self._replies = [] if callable(script) else list(script)
        self.requests: list[Request] = []

    async def complete(
        self, system: str, tools: list[dict[str, Any]], messages: list[Message]
    ) -> LlmReply:
        request = Request(system, copy.deepcopy(tools), copy.deepcopy(messages))
        self.requests.append(request)
        if self._responder is not None:
            return self._responder(request)
        if not self._replies:
            raise AssertionError("FakeLlm ran out of scripted replies")
        return self._replies.pop(0)


def text_reply(text: str = "Done.") -> LlmReply:
    return LlmReply(content=[{"type": "text", "text": text}], stop_reason="end_turn")


def tool_reply(*calls: tuple[str, dict[str, Any]]) -> LlmReply:
    """A reply that calls tools in the order given: tool_reply(("tell_story", {...}), ...)."""
    blocks = [
        {"type": "tool_use", "id": f"toolu_{next(_ids)}", "name": name, "input": tool_input}
        for name, tool_input in calls
    ]
    return LlmReply(content=blocks, stop_reason="tool_use")
