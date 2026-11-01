"""Expands the tree: a narrator takes its turn, then its narrator children take theirs.

Siblings run in parallel and never see each other: each child narrator reads only the prompt
and brief its parent wrote. Children of a failed narrator are left pending.
"""

import asyncio
from collections.abc import Callable

from worldgen.agents.roles.narrator import narrate
from worldgen.llm.base import Llm
from worldgen.policies import Policies
from worldgen.sinks.run_log import RunLog
from worldgen.tree.nodes import Tree


async def expand(
    tree: Tree,
    node_id: str,
    depth: int,
    llm: Llm,
    log: RunLog,
    policies: Policies | None = None,
    max_steps: int = 30,
    on_change: Callable[[], None] | None = None,
) -> None:
    """Runs node_id's turn, then expands its narrator children `depth` more levels down."""
    await narrate(tree, node_id, llm, log, policies, max_steps)
    if on_change:
        on_change()
    node = tree.node(node_id)
    if depth <= 0 or node.status not in ("told", "unfinished"):
        return
    children = [
        child
        for child in node.children
        if tree.node(child).role == "narrator" and tree.node(child).status == "pending"
    ]
    await asyncio.gather(
        *(
            expand(tree, child, depth - 1, llm, log, policies, max_steps, on_change)
            for child in children
        )
    )
