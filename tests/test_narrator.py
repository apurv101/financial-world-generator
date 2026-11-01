import asyncio

import pytest

from worldgen.agents.roles.narrator import TEMPLATE, first_message, narrate
from worldgen.llm.base import LlmError, LlmReply
from worldgen.llm.fake import FakeLlm, Request, text_reply, tool_reply
from worldgen.policies import Policies
from worldgen.sinks.run_log import RunLog
from worldgen.tree.nodes import Tree

STORY = ("tell_story", {"story": "Lumen Metrics, a YC-backed SaaS startup in San Francisco."})
SPAWN = (
    "spawn_child",
    {
        "items": [
            {
                "id": "n_company",
                "role": "narrator",
                "name": "Lumen Metrics",
                "prompt": "The company.",
            },
            {"id": "n_alex", "role": "actor", "name": "Alex Rivera", "prompt": "CEO."},
        ]
    },
)
BRIEF_COMPANY = ("brief_child", {"child": "n_company", "brief": "January 2021."})
BRIEF_ALEX = ("brief_child", {"child": "n_alex", "brief": "Park seed money in Treasury."})


def run(tree: Tree, llm: FakeLlm, policies: Policies | None = None, max_steps: int = 30):  # type: ignore[no-untyped-def]
    log = RunLog()
    result = asyncio.run(narrate(tree, tree.root, llm, log, policies, max_steps))
    return result, log


def test_a_full_turn_tells_the_story_spawns_and_briefs() -> None:
    tree = Tree.new("A B2B SaaS startup, 2021.")
    llm = FakeLlm([tool_reply(STORY, SPAWN, BRIEF_COMPANY, BRIEF_ALEX), text_reply()])
    result, log = run(tree, llm)
    assert result.status == "done" and result.steps == 2
    root = tree.node("n_root")
    assert root.status == "told" and root.story and root.story.startswith("Lumen Metrics")
    assert tree.node("n_company").brief == "January 2021."
    assert tree.node("n_alex").brief == "Park seed money in Treasury."
    assert [e["kind"] for e in log.entries] == (
        ["turn_started", "llm_reply"] + ["tool_call"] * 4 + ["llm_reply", "turn_finished"]
    )


def test_every_request_carries_the_template_and_the_three_tools() -> None:
    tree = Tree.new("A SaaS startup.")
    llm = FakeLlm([tool_reply(STORY), text_reply()])
    run(tree, llm)
    for request in llm.requests:
        assert request.system == TEMPLATE
        assert [t["name"] for t in request.tools] == ["tell_story", "spawn_child", "brief_child"]


def test_tool_calls_run_in_the_order_written_and_results_return_in_one_message() -> None:
    tree = Tree.new("A SaaS startup.")
    llm = FakeLlm([tool_reply(BRIEF_ALEX, SPAWN, STORY, BRIEF_COMPANY, BRIEF_ALEX), text_reply()])
    run(tree, llm)
    results = llm.requests[1].messages[-1]["content"]
    assert [r["type"] for r in results] == ["tool_result"] * 5
    assert results[0]["is_error"] is True and results[0]["content"].startswith("Rejected:")
    assert all("is_error" not in r for r in results[1:])
    assert tree.node("n_alex").brief == "Park seed money in Treasury."


def test_ask_once_reminds_then_accepts_the_finished_turn() -> None:
    tree = Tree.new("A SaaS startup.")
    llm = FakeLlm(
        [
            tool_reply(SPAWN),
            text_reply(),
            tool_reply(STORY, BRIEF_COMPANY, BRIEF_ALEX),
            text_reply(),
        ]
    )
    result, log = run(tree, llm)
    assert result.status == "done"
    reminder = llm.requests[2].messages[-1]["content"]
    assert "you have not told your story" in reminder
    assert "these children have no brief: n_company, n_alex" in reminder
    assert log.of_kind("reminder_sent")[0]["missing"]


def test_ask_once_asks_only_once_then_ends_unfinished() -> None:
    tree = Tree.new("A SaaS startup.")
    llm = FakeLlm([tool_reply(STORY, SPAWN), text_reply(), text_reply()])
    result, log = run(tree, llm)
    assert result.status == "unfinished"
    assert result.reason == "these children have no brief: n_company, n_alex"
    assert tree.node("n_root").status == "unfinished"
    assert len(log.of_kind("reminder_sent")) == 1


def test_accept_ends_unfinished_without_a_reminder() -> None:
    tree = Tree.new("A SaaS startup.")
    llm = FakeLlm([text_reply()])
    result, log = run(tree, llm, Policies(unfinished_turn="accept"))
    assert result.status == "unfinished" and log.of_kind("reminder_sent") == []
    assert len(llm.requests) == 1


def test_unknown_tool_and_bad_input_are_rejected_not_raised() -> None:
    tree = Tree.new("A SaaS startup.")
    llm = FakeLlm(
        [
            tool_reply(("move_money", {}), ("tell_story", {"words": 3})),
            tool_reply(STORY),
            text_reply(),
        ]
    )
    result, log = run(tree, llm)
    assert result.status == "done"
    first, second = log.of_kind("tool_call")[:2]
    assert first["result"].startswith("Rejected: there is no tool named move_money")
    assert second["is_error"] and "story: Field required" in second["result"]


def test_a_model_error_fails_the_turn() -> None:
    class Broken(FakeLlm):
        async def complete(self, system, tools, messages):  # type: ignore[no-untyped-def]
            raise LlmError("RateLimitError: slow down")

    tree = Tree.new("A SaaS startup.")
    result, log = run(tree, Broken([]))
    assert result.status == "failed" and result.reason == "RateLimitError: slow down"
    assert tree.node("n_root").status == "failed"


def test_a_refusal_fails_the_turn() -> None:
    refusal = LlmReply(content=[], stop_reason="refusal", stop_details={"category": "cyber"})
    tree = Tree.new("A SaaS startup.")
    result, _ = run(tree, FakeLlm([refusal]))
    assert result.status == "failed" and "refused" in (result.reason or "")


def test_a_reply_cut_at_max_tokens_runs_no_tools() -> None:
    cut = LlmReply(content=tool_reply(STORY).content, stop_reason="max_tokens")
    tree = Tree.new("A SaaS startup.")
    result, log = run(tree, FakeLlm([cut]))
    assert result.status == "failed" and log.of_kind("tool_call") == []
    assert tree.node("n_root").story is None


def test_the_step_limit_fails_the_turn() -> None:
    tree = Tree.new("A SaaS startup.")
    result, _ = run(tree, FakeLlm(lambda request: tool_reply(STORY)), max_steps=3)
    assert result.status == "failed" and result.steps == 3


def test_only_a_pending_narrator_can_narrate() -> None:
    tree = Tree.new("A SaaS startup.")
    run(tree, FakeLlm([tool_reply(STORY, SPAWN, BRIEF_COMPANY, BRIEF_ALEX), text_reply()]))
    with pytest.raises(ValueError, match="already taken its turn"):
        asyncio.run(narrate(tree, "n_root", FakeLlm([]), RunLog()))
    with pytest.raises(ValueError, match="is an actor"):
        asyncio.run(narrate(tree, "n_alex", FakeLlm([]), RunLog()))


def test_first_message_holds_prompt_and_brief() -> None:
    tree = Tree.new(
        "The sales department of Lumen Metrics.", brief="Contoso renews in March.", name="Sales"
    )
    text = first_message(tree.node("n_root"))
    assert "<prompt>\nThe sales department of Lumen Metrics.\n</prompt>" in text
    assert "<brief>\nContoso renews in March.\n</brief>" in text
    assert "You are Sales (n_root)." in text
    top = first_message(Tree.new("A SaaS startup.").node("n_root"))
    assert "nobody briefs you" in top


def test_first_user_text_helper() -> None:
    request = Request("s", [], [{"role": "user", "content": "hello"}])
    assert request.first_user_text == "hello"
