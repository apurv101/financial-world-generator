"""The node tree: each node's role, parent, children, prompt, brief and story.

A narrator's prompt is what part of the world it tells. Its brief is what is going on in that
part now, written by its parent. Its story is the detailed account it writes of its part.
Actors are leaves: the narrator stage gives them a prompt and a brief and nothing more.
"""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

NodeRole = Literal["narrator", "actor"]

NodeStatus = Literal[
    "pending",  # a narrator that has not taken its turn yet
    "told",  # a narrator whose turn finished with its story told and every child briefed
    "unfinished",  # a narrator whose turn ended with work missing (policy unfinished_turn)
    "failed",  # a narrator whose turn failed: a model error, a refusal or the step limit
    "leaf",  # an actor
]


class Node(BaseModel):
    id: str
    role: NodeRole
    name: str
    parent: str | None = None
    prompt: str
    brief: str | None = None
    story: str | None = None
    children: list[str] = Field(default_factory=list)
    status: NodeStatus


class Tree(BaseModel):
    root: str
    nodes: dict[str, Node]

    @classmethod
    def new(
        cls,
        prompt: str,
        brief: str | None = None,
        name: str = "Root narrator",
        root_id: str = "n_root",
    ) -> "Tree":
        root = Node(
            id=root_id, role="narrator", name=name, prompt=prompt, brief=brief, status="pending"
        )
        return cls(root=root_id, nodes={root_id: root})

    def node(self, node_id: str) -> Node:
        try:
            return self.nodes[node_id]
        except KeyError:
            raise KeyError(f"No node {node_id!r} in this tree") from None

    def add_child(
        self, parent_id: str, node_id: str, role: NodeRole, name: str, prompt: str
    ) -> Node:
        parent = self.node(parent_id)
        if node_id in self.nodes:
            raise ValueError(f"Node id {node_id!r} is taken")
        child = Node(
            id=node_id,
            role=role,
            name=name,
            parent=parent_id,
            prompt=prompt,
            status="pending" if role == "narrator" else "leaf",
        )
        self.nodes[node_id] = child
        parent.children.append(node_id)
        return child

    def pending_narrators(self) -> list[str]:
        return [n.id for n in self.nodes.values() if n.role == "narrator" and n.status == "pending"]

    def save(self, path: Path) -> None:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(self.model_dump_json(indent=2) + "\n")
        tmp.replace(path)

    @classmethod
    def load(cls, path: Path) -> "Tree":
        return cls.model_validate_json(path.read_text())
