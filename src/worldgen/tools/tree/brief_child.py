"""brief_child: a narrator writes one child's brief, what is going on for it now."""

from pydantic import BaseModel, ConfigDict, Field

from worldgen.tools.base import Tool, ToolError
from worldgen.tools.tree.context import TreeContext


class BriefChildInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    child: str = Field(description="The child's id.")
    brief: str = Field(
        min_length=1,
        description=(
            "What is going on for this child now: the time frame, open items, upcoming dates "
            "and amounts, plans, and what to watch for."
        ),
    )


class BriefChild(Tool[TreeContext, BriefChildInput]):
    name = "brief_child"
    description = (
        "Writes one child's brief: what is going on for it now. A child sees only its prompt and "
        "this brief, so include every name, date and amount it needs. Works only for your own "
        "children. Calling it again for the same child replaces the earlier brief."
    )
    input_model = BriefChildInput

    def run(self, ctx: TreeContext, args: BriefChildInput) -> str:
        children = ctx.node.children
        if args.child not in children:
            if not children:
                raise ToolError(
                    f"{args.child} is not your child: you have no children yet. "
                    "Create it with spawn_child first."
                )
            raise ToolError(
                f"{args.child} is not your child. Your children: {', '.join(children)}."
            )
        child = ctx.tree.node(args.child)
        replaced = child.brief is not None
        child.brief = args.brief
        verb = "Replaced the brief" if replaced else "Saved the brief"
        return f"{verb} for {child.id} ({child.name})."
