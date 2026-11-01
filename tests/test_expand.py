import asyncio
from pathlib import Path

from worldgen.llm.base import LlmReply
from worldgen.llm.fake import FakeLlm, Request, text_reply, tool_reply
from worldgen.sinks.run_log import RunLog
from worldgen.tree.expand import expand
from worldgen.tree.nodes import Tree
from worldgen.tree.render import render

ROOT_STORY = "ROOT-ONLY SECRET: the CEO holds 40% of the company."


def child(id: str, role: str, name: str) -> dict[str, str]:
    return {"id": id, "role": role, "name": name, "prompt": f"PROMPT OF {id}"}


def turn(story: str, children: list[dict[str, str]]) -> list[LlmReply]:
    calls: list[tuple[str, dict[str, object]]] = [("tell_story", {"story": story})]
    if children:
        calls.append(("spawn_child", {"items": children}))
        calls += [
            ("brief_child", {"child": c["id"], "brief": f"BRIEF OF {c['id']}"}) for c in children
        ]
    return [tool_reply(*calls), text_reply()]


SCRIPTS = {
    "n_root": turn(
        ROOT_STORY,
        [child("n_company", "narrator", "Lumen Metrics"), child("n_alex", "actor", "Alex")],
    ),
    "n_company": turn(
        "COMPANY STORY",
        [child("n_ops", "narrator", "Operations"), child("n_sales", "narrator", "Sales")],
    ),
    "n_ops": turn("OPS STORY", [child("n_morgan", "actor", "Morgan")]),
    "n_sales": turn("SALES STORY", [child("n_jordan", "actor", "Jordan")]),
}


def responder() -> tuple[FakeLlm, dict[str, list[Request]]]:
    """Replies by node: each node's turn opens with 'You are <name> (<id>).'"""
    scripts = {node: list(replies) for node, replies in SCRIPTS.items()}
    seen: dict[str, list[Request]] = {}

    def reply(request: Request) -> LlmReply:
        node = request.first_user_text.split("(", 1)[1].split(")", 1)[0]
        seen.setdefault(node, []).append(request)
        return scripts[node].pop(0)

    return FakeLlm(reply), seen


def test_depth_zero_runs_only_the_starting_narrator() -> None:
    tree = Tree.new("Alex Rivera's life.")
    llm, seen = responder()
    asyncio.run(expand(tree, "n_root", 0, llm, RunLog()))
    assert set(seen) == {"n_root"}
    assert tree.pending_narrators() == ["n_company"]


def test_depth_expands_narrator_children_level_by_level() -> None:
    tree = Tree.new("Alex Rivera's life.")
    llm, seen = responder()
    asyncio.run(expand(tree, "n_root", 2, llm, RunLog()))
    assert set(seen) == {"n_root", "n_company", "n_ops", "n_sales"}
    assert tree.pending_narrators() == []
    assert tree.node("n_ops").children == ["n_morgan"]
    assert (
        tree.node("n_jordan").status == "leaf"
        and tree.node("n_jordan").brief == "BRIEF OF n_jordan"
    )


def test_no_depth_expands_until_no_narrator_is_pending() -> None:
    tree = Tree.new("Alex Rivera's life.")
    llm, seen = responder()
    asyncio.run(expand(tree, "n_root", None, llm, RunLog()))
    assert set(seen) == {"n_root", "n_company", "n_ops", "n_sales"}
    assert tree.pending_narrators() == []


def test_a_child_sees_only_its_own_prompt_and_brief() -> None:
    tree = Tree.new("Alex Rivera's life.")
    llm, seen = responder()
    asyncio.run(expand(tree, "n_root", 2, llm, RunLog()))
    company = str(seen["n_company"][0].messages)
    assert "PROMPT OF n_company" in company and "BRIEF OF n_company" in company
    assert ROOT_STORY not in company and "Alex Rivera's life." not in company
    sales = str(seen["n_sales"][0].messages)
    assert (
        "OPS STORY" not in sales and "PROMPT OF n_ops" not in sales and "COMPANY STORY" not in sales
    )


def test_children_of_a_failed_narrator_stay_pending() -> None:
    tree = Tree.new("Alex Rivera's life.")
    script = turn(ROOT_STORY, [child("n_company", "narrator", "Lumen Metrics")])
    cut = LlmReply(content=[], stop_reason="refusal")
    llm = FakeLlm([script[0], cut])
    asyncio.run(expand(tree, "n_root", 3, llm, RunLog()))
    assert tree.node("n_root").status == "failed"
    assert tree.pending_narrators() == ["n_company"]


def test_on_change_saves_after_each_narrator_and_tree_round_trips(tmp_path: Path) -> None:
    tree = Tree.new("Alex Rivera's life.")
    llm, _ = responder()
    saves: list[int] = []

    def save() -> None:
        saves.append(len(tree.nodes))
        tree.save(tmp_path / "tree.json")

    asyncio.run(expand(tree, "n_root", 2, llm, RunLog(), on_change=save))
    assert len(saves) == 4
    assert Tree.load(tmp_path / "tree.json") == tree


def test_render_shows_every_node_in_tree_order() -> None:
    tree = Tree.new("Alex Rivera's life.")
    llm, _ = responder()
    asyncio.run(expand(tree, "n_root", 2, llm, RunLog()))
    text = render(tree)
    order = [
        text.index(f"`{n}`")
        for n in ("n_root", "n_company", "n_ops", "n_morgan", "n_sales", "n_jordan", "n_alex")
    ]
    assert order == sorted(order)
    assert "#### Morgan (`n_morgan`, actor, under `n_ops`)" in text
    assert "> COMPANY STORY" in text
