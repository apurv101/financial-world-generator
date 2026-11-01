"""spawn_child: a narrator creates the narrators and actors below it."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from worldgen.tools.base import Tool, ToolError
from worldgen.tools.tree.context import TreeContext

ID_PATTERN = r"^n_[a-z0-9_]+$"


class ChildSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        pattern=ID_PATTERN,
        description=(
            "A node id unique in the whole world: n_ then lowercase letters, digits and "
            "underscores, such as n_sales or n_morgan."
        ),
    )
    role: Literal["narrator", "actor"] = Field(
        description=(
            "narrator for a part with several people or parties of its own; actor for one "
            "person or business acting for itself."
        )
    )
    name: str = Field(
        min_length=1,
        description="Who or what the child is, such as 'Sales department' or 'Morgan Lee'.",
    )
    prompt: str = Field(
        min_length=1,
        description=(
            "Who the child is for the whole run: identity, role, background, temperament, "
            "habits, relationships, the accounts it uses and standing quirks. Apart from its "
            "brief, this is all the child will ever see of your world."
        ),
    )


class SpawnChildInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ChildSpec] = Field(min_length=1, description="The children to create, in order.")


class SpawnChild(Tool[TreeContext, SpawnChildInput]):
    name = "spawn_child"
    description = (
        "Creates children under you: narrators for parts of your world, actors for single people "
        "or businesses. It takes a list, so one call can create many. Ids must be unique in the "
        "whole world. After creating a child, write its brief with brief_child."
    )
    input_model = SpawnChildInput

    def run(self, ctx: TreeContext, args: SpawnChildInput) -> str:
        valid: list[ChildSpec] = []
        failures: list[str] = []
        for number, spec in enumerate(args.items, 1):
            problem = _problem(ctx, spec, valid)
            if problem:
                failures.append(f"item {number} ({spec.id}): {problem}")
            else:
                valid.append(spec)
        # policy list_calls
        if failures and (ctx.policies.list_calls == "all_or_nothing" or not valid):
            raise ToolError(
                "nothing was created. Fix these items and send the list again: "
                + "; ".join(failures)
            )
        for spec in valid:
            ctx.tree.add_child(ctx.node_id, spec.id, spec.role, spec.name, spec.prompt)
        text = "Created " + ", ".join(f"{spec.id} ({spec.role})" for spec in valid) + "."
        if failures:
            text += " Not created: " + "; ".join(failures) + "."
        return text + " Write each new child's brief with brief_child."


def _problem(ctx: TreeContext, spec: ChildSpec, earlier: list[ChildSpec]) -> str | None:
    if spec.id in ctx.tree.nodes:
        return f"the id {spec.id} is taken; choose another"
    if any(other.id == spec.id for other in earlier):
        return f"the id {spec.id} appears twice in this list"
    return None
