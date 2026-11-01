"""worldgen command line.

uv run --env-file .env worldgen narrate --prompt-file TARGET_EXAMPLE.md --out worlds/lumen/story
uv run --env-file .env worldgen narrate --prompt "..." --out worlds/x --depth 0   # root only
uv run --env-file .env worldgen expand worlds/x n_sales
"""

import asyncio
from collections import Counter
from pathlib import Path
from typing import Annotated, Any, Literal

import typer
from pydantic import ValidationError

from worldgen.llm.anthropic_llm import AnthropicLlm, Provider, settings_for
from worldgen.llm.base import LlmConfigError
from worldgen.policies import Policies
from worldgen.sinks.run_log import RunLog
from worldgen.tree.expand import expand as expand_tree
from worldgen.tree.nodes import Node, Tree
from worldgen.tree.render import render

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="worldgen: generate financial worlds with LLM agents.",
)

Effort = Literal["low", "medium", "high", "xhigh", "max"]

ProviderOpt = Annotated[
    Provider | None,
    typer.Option(
        help="Model provider. Default: anthropic if ANTHROPIC_API_KEY is set, else deepseek."
    ),
]
ModelOpt = Annotated[
    str | None,
    typer.Option(
        help="Model id. Default: claude-opus-5-5 (anthropic), deepseek-v4-pro (deepseek)."
    ),
]
EffortOpt = Annotated[Effort, typer.Option(help="How hard the model thinks.")]
DepthOpt = Annotated[
    int | None,
    typer.Option(
        min=0,
        help=(
            "Stop after this many narrator levels below the starting one (0: only that one). "
            "Default: no limit; the narrators decide how deep the tree goes."
        ),
    ),
]
PolicyOpt = Annotated[
    list[str] | None,
    typer.Option("--policy", help="Switch a policy, as name=option. Repeatable."),
]
MaxStepsOpt = Annotated[int, typer.Option(min=1, help="Model calls allowed per narrator turn.")]


@app.command()
def narrate(
    out: Annotated[Path, typer.Option(help="New directory for tree.json, story.md and log.jsonl.")],
    prompt: Annotated[str | None, typer.Option(help="What the starting narrator tells.")] = None,
    prompt_file: Annotated[
        Path | None, typer.Option(exists=True, dir_okay=False, help="The prompt, read from a file.")
    ] = None,
    brief: Annotated[
        str | None,
        typer.Option(help="What is going on, when the prompt is one part of a larger world."),
    ] = None,
    brief_file: Annotated[
        Path | None, typer.Option(exists=True, dir_okay=False, help="The brief, read from a file.")
    ] = None,
    name: Annotated[str, typer.Option(help="The starting narrator's name.")] = "Root narrator",
    depth: DepthOpt = None,
    provider: ProviderOpt = None,
    model: ModelOpt = None,
    effort: EffortOpt = "high",
    policy: PolicyOpt = None,
    max_steps: MaxStepsOpt = 30,
) -> None:
    """Start a new story tree: one narrator expands a prompt, then optionally its children."""
    prompt_text = _text(prompt, prompt_file, "prompt")
    if prompt_text is None:
        raise typer.BadParameter("give --prompt or --prompt-file")
    if (out / "tree.json").exists():
        raise typer.BadParameter(f"{out} already holds a tree; continue it with `worldgen expand`")
    out.mkdir(parents=True, exist_ok=True)
    tree = Tree.new(prompt_text, _text(brief, brief_file, "brief"), name)
    _run(tree, [tree.root], depth, out, provider, model, effort, policy, max_steps, "narrate")


@app.command()
def expand(
    directory: Annotated[Path, typer.Argument(help="A directory written by `worldgen narrate`.")],
    node: Annotated[
        str | None, typer.Argument(help="The pending narrator to expand. Default: every one.")
    ] = None,
    depth: DepthOpt = None,
    provider: ProviderOpt = None,
    model: ModelOpt = None,
    effort: EffortOpt = "high",
    policy: PolicyOpt = None,
    max_steps: MaxStepsOpt = 30,
) -> None:
    """Continue a story tree from its pending narrators."""
    path = directory / "tree.json"
    if not path.exists():
        raise typer.BadParameter(f"no tree.json in {directory}")
    tree = Tree.load(path)
    if node is None:
        targets = tree.pending_narrators()
        if not targets:
            typer.echo("No pending narrators: every narrator in this tree has taken its turn.")
            raise typer.Exit()
    else:
        found = tree.nodes.get(node)
        if found is None or found.role != "narrator" or found.status != "pending":
            pending = ", ".join(tree.pending_narrators()) or "none"
            raise typer.BadParameter(f"{node} is not a pending narrator. Pending: {pending}")
        targets = [node]
    _run(tree, targets, depth, directory, provider, model, effort, policy, max_steps, "expand")


def _run(
    tree: Tree,
    targets: list[str],
    depth: int | None,
    out: Path,
    provider: Provider | None,
    model: str | None,
    effort: Effort,
    policy: list[str] | None,
    max_steps: int,
    command: str,
) -> None:
    policies = _policies(policy or [])
    try:
        llm = AnthropicLlm(settings_for(provider, model, effort))
    except LlmConfigError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1) from error
    log = RunLog(out / "log.jsonl")
    start = len(log.entries)
    log.write(
        "run_started",
        command=command,
        targets=targets,
        depth=depth,
        llm=llm.name,
        effort=effort,
        policies=policies.model_dump(),
    )
    levels = "every level" if depth is None else f"depth {depth}"
    typer.echo(f"Using {llm.name}, effort {effort}. Narrating {', '.join(targets)} ({levels}).")

    def save() -> None:
        tree.save(out / "tree.json")
        (out / "story.md").write_text(render(tree))

    save()

    async def go() -> None:
        await asyncio.gather(
            *(expand_tree(tree, t, depth, llm, log, policies, max_steps, save) for t in targets)
        )

    asyncio.run(go())
    log.write("run_finished", command=command)
    save()
    _summary(tree, log.entries[start:], out)


def _summary(tree: Tree, entries: list[dict[str, Any]], out: Path) -> None:
    typer.echo("")
    _outline(tree, tree.node(tree.root), 0)
    failures = [e for e in entries if e["kind"] == "turn_finished" and e["status"] != "done"]
    for entry in failures:
        typer.echo(f"  ! {entry['node']} {entry['status']}: {entry['reason']}")
    usage: Counter[str] = Counter()
    calls = 0
    for entry in entries:
        if entry["kind"] == "llm_reply":
            calls += 1
            for key in ("input_tokens", "output_tokens", "cache_read_input_tokens"):
                usage[key] += entry["usage"].get(key) or 0
    typer.echo(
        f"\nModel calls: {calls}. Tokens in: {usage['input_tokens']}, "
        f"cached: {usage['cache_read_input_tokens']}, out: {usage['output_tokens']}."
    )
    pending = tree.pending_narrators()
    if pending:
        typer.echo(
            f"Pending narrators: {', '.join(pending)}. Continue with: worldgen expand {out} [NODE]"
        )
    typer.echo(f"Wrote {out / 'tree.json'}, {out / 'story.md'} and {out / 'log.jsonl'}.")


def _outline(tree: Tree, node: Node, indent: int) -> None:
    status = "actor" if node.role == "actor" else node.status
    extras = []
    if node.story:
        extras.append(f"story {len(node.story.split())} words")
    if node.children:
        extras.append(f"{len(node.children)} children")
    detail = f" ({', '.join(extras)})" if extras else ""
    typer.echo(f"{'  ' * indent}{node.id}  {node.name}  [{status}]{detail}")
    for child in node.children:
        _outline(tree, tree.node(child), indent + 1)


def _text(value: str | None, path: Path | None, label: str) -> str | None:
    if value is not None and path is not None:
        raise typer.BadParameter(f"give --{label} or --{label}-file, not both")
    if path is not None:
        return path.read_text()
    return value


def _policies(pairs: list[str]) -> Policies:
    values: dict[str, str] = {}
    for pair in pairs:
        key, sep, value = pair.partition("=")
        if not sep:
            raise typer.BadParameter(f"--policy takes name=option, got {pair!r}")
        values[key.strip()] = value.strip()
    try:
        return Policies.model_validate(values)
    except ValidationError as error:
        raise typer.BadParameter(str(error)) from error
