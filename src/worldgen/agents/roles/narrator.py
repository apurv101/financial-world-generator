"""The narrator role: its system prompt, its tools, and one narrator turn on day 0.

A narrator reads only its own prompt and brief. It tells the detailed story of its part with
tell_story, creates the narrators and actors below it with spawn_child, and writes each one's
brief with brief_child. Its children will see only the prompt and brief it writes for them.
"""

from importlib import resources
from typing import Any

from worldgen.agents.loop import AgentLoop, TurnResult, TurnStatus
from worldgen.llm.base import Llm
from worldgen.policies import Policies, child_roles
from worldgen.sinks.run_log import RunLog
from worldgen.tools.base import Tool
from worldgen.tools.tree.brief_child import BriefChild
from worldgen.tools.tree.context import TreeContext
from worldgen.tools.tree.spawn_child import SpawnChild
from worldgen.tools.tree.tell_story import TellStory
from worldgen.tree.nodes import Node, NodeStatus, Tree

TEMPLATE = resources.files("worldgen.agents.templates").joinpath("narrator.md").read_text()


def system_prompt(policies: Policies) -> str:
    """The template with each policy's text filled in."""
    # policy child_roles
    return TEMPLATE.replace("{{child_roles}}", child_roles.TEXT[policies.child_roles])


TOOLS: tuple[Tool[TreeContext, Any], ...] = (TellStory(), SpawnChild(), BriefChild())

_STATUS_AFTER: dict[TurnStatus, NodeStatus] = {
    "done": "told",
    "unfinished": "unfinished",
    "failed": "failed",
}


def first_message(node: Node) -> str:
    if node.brief:
        brief = node.brief
    elif node.parent is None:
        brief = (
            "You are at the top of this world, so nobody briefs you. "
            "Your prompt is the world's main prompt."
        )
    else:
        brief = "Your narrator wrote no brief for you. Work from your prompt."
    return (
        "This is day 0: the world is being built before its clock starts. "
        f"You are {node.name} ({node.id}).\n\n"
        f"<prompt>\n{node.prompt}\n</prompt>\n\n"
        f"<brief>\n{brief}\n</brief>"
    )


def missing_work(ctx: TreeContext) -> list[str]:
    gaps = []
    if not ctx.node.story:
        gaps.append("you have not told your story with tell_story")
    unbriefed = [child for child in ctx.node.children if ctx.tree.node(child).brief is None]
    if unbriefed:
        gaps.append("these children have no brief: " + ", ".join(unbriefed))
    return gaps


async def narrate(
    tree: Tree,
    node_id: str,
    llm: Llm,
    log: RunLog,
    policies: Policies | None = None,
    max_steps: int = 30,
) -> TurnResult:
    """Runs one narrator's day-0 turn and sets its status: told, unfinished or failed."""
    policies = policies or Policies()
    node = tree.node(node_id)
    if node.role != "narrator":
        raise ValueError(f"{node_id} is an actor; only narrators tell stories")
    if node.status != "pending":
        raise ValueError(f"{node_id} has already taken its turn ({node.status})")
    ctx = TreeContext(tree, node_id, policies)
    loop = AgentLoop(llm, system_prompt(policies), TOOLS, log, max_steps)
    result = await loop.run_turn(
        ctx, node_id, first_message(node), missing_work, policies.unfinished_turn
    )
    node.status = _STATUS_AFTER[result.status]
    return result
