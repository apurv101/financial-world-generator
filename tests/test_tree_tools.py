from worldgen.policies import Policies
from worldgen.tools.base import input_schema
from worldgen.tools.tree.brief_child import BriefChild
from worldgen.tools.tree.context import TreeContext
from worldgen.tools.tree.spawn_child import SpawnChild, SpawnChildInput
from worldgen.tools.tree.tell_story import TellStory
from worldgen.tree.nodes import Tree


def ctx(policies: Policies | None = None) -> TreeContext:
    return TreeContext(Tree.new("A B2B SaaS startup."), "n_root", policies or Policies())


def child(id: str, role: str = "actor", name: str = "Someone") -> dict[str, str]:
    return {"id": id, "role": role, "name": name, "prompt": f"{name}'s prompt"}


def test_tell_story_saves_and_replaces() -> None:
    c = ctx()
    first = TellStory().call(c, {"story": "Lumen Metrics was founded in 2020."})
    assert first.text == "Saved your story (6 words)." and not first.is_error
    second = TellStory().call(c, {"story": "Rewritten."})
    assert second.text.startswith("Replaced your story")
    assert c.node.story == "Rewritten."


def test_tell_story_rejects_empty_story() -> None:
    outcome = TellStory().call(ctx(), {"story": ""})
    assert outcome.is_error and outcome.text.startswith("Rejected: story:")


def test_spawn_child_creates_narrators_pending_and_actors_as_leaves() -> None:
    c = ctx()
    outcome = SpawnChild().call(
        c, {"items": [child("n_company", "narrator", "Lumen Metrics"), child("n_alex")]}
    )
    assert not outcome.is_error
    assert c.node.children == ["n_company", "n_alex"]
    assert c.tree.node("n_company").status == "pending"
    assert c.tree.node("n_alex").status == "leaf"
    assert c.tree.node("n_alex").parent == "n_root"


def test_spawn_child_all_or_nothing_rejects_whole_list_and_names_every_failure() -> None:
    c = ctx()
    SpawnChild().call(c, {"items": [child("n_alex")]})
    outcome = SpawnChild().call(
        c, {"items": [child("n_morgan"), child("n_alex"), child("n_jordan"), child("n_jordan")]}
    )
    assert outcome.is_error
    assert "nothing was created" in outcome.text
    assert "item 2 (n_alex): the id n_alex is taken" in outcome.text
    assert "item 4 (n_jordan): the id n_jordan appears twice" in outcome.text
    assert c.node.children == ["n_alex"]


def test_spawn_child_per_item_applies_the_valid_items() -> None:
    c = ctx(Policies(list_calls="per_item"))
    SpawnChild().call(c, {"items": [child("n_alex")]})
    outcome = SpawnChild().call(c, {"items": [child("n_morgan"), child("n_alex")]})
    assert not outcome.is_error
    assert "Created n_morgan (actor)." in outcome.text
    assert "Not created: item 2 (n_alex)" in outcome.text
    assert c.node.children == ["n_alex", "n_morgan"]


def test_spawn_child_per_item_with_nothing_valid_is_a_rejection() -> None:
    c = ctx(Policies(list_calls="per_item"))
    SpawnChild().call(c, {"items": [child("n_alex")]})
    outcome = SpawnChild().call(c, {"items": [child("n_alex")]})
    assert outcome.is_error and "nothing was created" in outcome.text


def test_spawn_child_rejects_malformed_items_under_either_policy() -> None:
    for policy in ("all_or_nothing", "per_item"):
        c = ctx(Policies(list_calls=policy))  # type: ignore[arg-type]
        outcome = SpawnChild().call(c, {"items": [child("n_ok"), child("Bad Id")]})
        assert outcome.is_error and "items.1.id" in outcome.text
        assert c.node.children == []


def test_brief_child_only_for_own_children() -> None:
    c = ctx()
    none_yet = BriefChild().call(c, {"child": "n_alex", "brief": "Q1."})
    assert none_yet.is_error and "you have no children yet" in none_yet.text
    SpawnChild().call(c, {"items": [child("n_alex")]})
    wrong = BriefChild().call(c, {"child": "n_root", "brief": "Q1."})
    assert wrong.is_error and "Your children: n_alex" in wrong.text
    ok = BriefChild().call(c, {"child": "n_alex", "brief": "Q1 fundraising."})
    assert ok.text == "Saved the brief for n_alex (Someone)."
    again = BriefChild().call(c, {"child": "n_alex", "brief": "Changed."})
    assert again.text.startswith("Replaced the brief")
    assert c.tree.node("n_alex").brief == "Changed."


def test_input_schema_inlines_refs_and_drops_titles() -> None:
    schema = input_schema(SpawnChildInput)
    assert "$defs" not in schema and "title" not in schema
    item = schema["properties"]["items"]["items"]
    assert set(item["required"]) == {"id", "role", "name", "prompt"}
    assert item["additionalProperties"] is False
    assert "title" not in item["properties"]["id"]
