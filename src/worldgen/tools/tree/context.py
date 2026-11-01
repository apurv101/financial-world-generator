"""TreeContext: what a tree tool acts on: the tree, the calling narrator and the run's policies."""

from dataclasses import dataclass

from worldgen.policies import Policies
from worldgen.tree.nodes import Node, Tree


@dataclass
class TreeContext:
    tree: Tree
    node_id: str
    policies: Policies

    @property
    def node(self) -> Node:
        return self.tree.node(self.node_id)
