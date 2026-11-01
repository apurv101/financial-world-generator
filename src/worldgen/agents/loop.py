"""AgentLoop: one turn of one node, a tool-use loop the engine owns.

Each turn is a fresh conversation: the node's first message, then model replies and tool results
until the model replies without a tool call. Tool calls in one reply run in the order they are
written, and all their results go back in one message. The system prompt and tools are the same
on every turn of a role, so the provider can serve them from its prompt cache.
"""

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from worldgen.llm.base import Block, Llm, LlmError, Message
from worldgen.policies.unfinished_turn import UnfinishedTurn
from worldgen.sinks.run_log import RunLog
from worldgen.tools.base import Tool, rejected

TurnStatus = Literal["done", "unfinished", "failed"]


@dataclass(frozen=True)
class TurnResult:
    status: TurnStatus
    steps: int
    reason: str | None = None


class AgentLoop[C]:
    def __init__(
        self,
        llm: Llm,
        system: str,
        tools: Sequence[Tool[C, Any]],
        log: RunLog,
        max_steps: int = 30,
    ):
        self.llm = llm
        self.system = system
        self.log = log
        self.max_steps = max_steps
        self.tools = {tool.name: tool for tool in tools}
        self.definitions = [tool.definition() for tool in tools]
        fingerprint = system + json.dumps(self.definitions, sort_keys=True)
        self.prompt_sha = hashlib.sha256(fingerprint.encode()).hexdigest()[:12]

    async def run_turn(
        self,
        ctx: C,
        node_id: str,
        first_message: str,
        missing: Callable[[C], list[str]] | None = None,
        unfinished: UnfinishedTurn = "ask_once",
    ) -> TurnResult:
        """Runs the turn. `missing` names work the node still owes when it tries to stop."""
        messages: list[Message] = [{"role": "user", "content": first_message}]
        self.log.write(
            "turn_started",
            node=node_id,
            llm=self.llm.name,
            prompt_sha=self.prompt_sha,
            tools=list(self.tools),
            message=first_message,
        )
        asked = False
        for step in range(1, self.max_steps + 1):
            try:
                reply = await self.llm.complete(self.system, self.definitions, messages)
            except LlmError as error:
                return self._end(node_id, "failed", step, str(error))
            self.log.write(
                "llm_reply",
                node=node_id,
                step=step,
                model=reply.model,
                request_id=reply.request_id,
                stop_reason=reply.stop_reason,
                usage=reply.usage,
                content=reply.content,
            )
            messages.append({"role": "assistant", "content": reply.content})
            if reply.stop_reason == "refusal":
                return self._end(
                    node_id, "failed", step, f"the model refused: {reply.stop_details}"
                )
            if reply.stop_reason == "max_tokens":
                reason = "the reply hit max_tokens, so its tool calls were not run"
                return self._end(node_id, "failed", step, reason)
            uses = reply.tool_uses()
            if uses:
                results = [self._run_tool(ctx, node_id, step, use) for use in uses]
                messages.append({"role": "user", "content": results})
                continue
            gaps = missing(ctx) if missing else []
            if not gaps:
                return self._end(node_id, "done", step)
            # policy unfinished_turn
            if unfinished == "ask_once" and not asked:
                asked = True
                self.log.write("reminder_sent", node=node_id, step=step, missing=gaps)
                reminder = (
                    "You ended your turn with work missing: "
                    + "; ".join(gaps)
                    + ". Finish it with your tools, then reply without a tool call."
                )
                messages.append({"role": "user", "content": reminder})
                continue
            return self._end(node_id, "unfinished", step, "; ".join(gaps))
        reason = f"no final reply after {self.max_steps} model calls"
        return self._end(node_id, "failed", self.max_steps, reason)

    def _run_tool(self, ctx: C, node_id: str, step: int, use: Block) -> Block:
        tool = self.tools.get(use["name"])
        if tool is None:
            outcome = rejected(
                f"there is no tool named {use['name']}. Your tools: {', '.join(self.tools)}."
            )
        else:
            outcome = tool.call(ctx, use.get("input"))
        self.log.write(
            "tool_call",
            node=node_id,
            step=step,
            tool=use["name"],
            input=use.get("input"),
            result=outcome.text,
            is_error=outcome.is_error,
        )
        result: Block = {"type": "tool_result", "tool_use_id": use["id"], "content": outcome.text}
        if outcome.is_error:
            result["is_error"] = True
        return result

    def _end(
        self, node_id: str, status: TurnStatus, steps: int, reason: str | None = None
    ) -> TurnResult:
        self.log.write("turn_finished", node=node_id, status=status, steps=steps, reason=reason)
        return TurnResult(status, steps, reason)
