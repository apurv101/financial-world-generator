"""Renders a tree as one Markdown file: every node's prompt, brief and story, in tree order."""

from worldgen.tree.nodes import Node, Tree


def render(tree: Tree) -> str:
    root = tree.node(tree.root)
    lines = [f"# {root.name}: story tree", ""]
    _section(tree, root, 2, lines)
    return "\n".join(lines).rstrip() + "\n"


def _section(tree: Tree, node: Node, level: int, lines: list[str]) -> None:
    kind = "actor" if node.role == "actor" else f"narrator, {node.status}"
    parent = f", under `{node.parent}`" if node.parent else ""
    lines += [f"{'#' * min(level, 6)} {node.name} (`{node.id}`, {kind}{parent})", ""]
    for label, text in (("Prompt", node.prompt), ("Brief", node.brief), ("Story", node.story)):
        if text:
            lines += [f"**{label}**", ""]
            lines += [f"> {line}" if line else ">" for line in text.strip().splitlines()]
            lines.append("")
    for child in node.children:
        _section(tree, tree.node(child), level + 1, lines)
