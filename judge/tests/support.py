"""Test helpers: a scripted Llm and verdict builders."""

import json
from dataclasses import dataclass, field
from typing import Any

from llm_judge.llm import LlmError, Reply
from llm_judge.rubric import Rubric, load_rubric

GENERAL = load_rubric("general")


def verdict_dict(rubric: Rubric = GENERAL, score: int = 7, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "elements": [
            {
                "description": "the company is a SaaS startup",
                "importance": "high",
                "reference_quote": "a SaaS startup",
                "status": "match",
                "candidate_quote": "SaaS startup",
                "note": "",
            },
            {
                "description": "five staff",
                "importance": "low",
                "reference_quote": "five staff",
                "status": "missing",
                "candidate_quote": "",
                "note": "",
            },
        ],
        "extras": [{"description": "a dog", "candidate_quote": "a dog"}],
        "dimensions": [
            {"id": d.id, "score": score, "reason": "because"} for d in rubric.dimensions
        ],
        "summary": "Close enough.",
    }
    data.update(overrides)
    return data


def verdict_json(rubric: Rubric = GENERAL, score: int = 7, **overrides: Any) -> str:
    return json.dumps(verdict_dict(rubric, score, **overrides))


@dataclass
class FakeLlm:
    """Replies from a script, in order. A script item that is an exception is raised."""

    script: list[str | Exception]
    name: str = "fake:judge"
    calls: list[tuple[str, str]] = field(default_factory=list)

    async def complete(self, system: str, user: str, schema: dict[str, Any]) -> Reply:
        self.calls.append((system, user))
        if not self.script:
            raise LlmError("script exhausted")
        item = self.script.pop(0)
        if isinstance(item, Exception):
            raise item
        return Reply(text=item, stop_reason="end_turn", model="fake-model", request_id="req_x")
