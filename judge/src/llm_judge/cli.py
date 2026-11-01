"""judge command line.

From the judge folder, with the repo's .env:
    uv run --env-file ../.env judge compare REFERENCE CANDIDATE --rubric world
    uv run judge extract SOME_FILE_OR_DIR
"""

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from llm_judge.inputs import Document, HtmlMode, InputError, load
from llm_judge.judge import Failure, RunResult, judge
from llm_judge.llm import AnthropicLlm, Effort, LlmConfigError, Provider, settings_for
from llm_judge.prompt import build_system, build_user
from llm_judge.report import markdown, terminal_summary
from llm_judge.rubric import RubricError, builtin_names, load_rubric

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="judge: score how similar two outputs are, whatever their format.",
)

HtmlOpt = Annotated[
    HtmlMode,
    typer.Option(
        help="HTML: 'rendered' runs the page in headless Chrome and reads its visible text; "
        "'source' reads the markup with scripts kept; 'auto' renders when Chrome is found."
    ),
]
IncludeOpt = Annotated[
    list[str] | None,
    typer.Option("--include", help="For a directory input: only files matching this glob."),
]


def default_runs_dir() -> Path:
    """judge/runs in a source checkout (where this file lives), else ./judge-runs."""
    root = Path(__file__).resolve().parents[2]
    return root / "runs" if (root / "pyproject.toml").exists() else Path("judge-runs")


def _slug(label: str) -> str:
    path = Path(label)
    name = path.stem if path.suffix else path.name
    return re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-")[:40] or "input"


def _load(path: Path, html: HtmlMode, include: list[str] | None) -> Document:
    try:
        return load(path, html, include)
    except InputError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1) from error


def _describe(role: str, doc: Document) -> None:
    typer.echo(f"{role}: {doc.label}, {len(doc.text):,} chars, ≈{doc.tokens:,} tokens")
    for part in doc.parts:
        typer.echo(f"  {part.path} ({part.how}), {len(part.text):,} chars")
    for skipped in doc.skipped:
        typer.echo(f"  skipped {skipped}")


@app.command()
def compare(
    reference: Annotated[Path, typer.Argument(help="What the candidate should resemble.")],
    candidate: Annotated[Path, typer.Argument(help="The output being judged.")],
    rubric: Annotated[
        str, typer.Option(help=f"Built-in rubric ({', '.join(builtin_names())}) or a TOML path.")
    ] = "general",
    focus: Annotated[
        str | None, typer.Option(help="Judge only this part, e.g. 'the day-0 world'.")
    ] = None,
    runs: Annotated[int, typer.Option(min=1, help="Independent judge runs, in parallel.")] = 1,
    out: Annotated[
        Path | None, typer.Option(help="Directory for the results. Default: a new one in runs/.")
    ] = None,
    provider: Annotated[
        Provider | None,
        typer.Option(help="Default: anthropic if ANTHROPIC_API_KEY is set, else deepseek."),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(help="Default: claude-opus-5-5 (anthropic), deepseek-v4-pro (deepseek)."),
    ] = None,
    effort: Annotated[Effort, typer.Option(help="How hard the judge thinks.")] = "high",
    html: HtmlOpt = "auto",
    include: IncludeOpt = None,
    max_input_tokens: Annotated[
        int, typer.Option(help="Refuse inputs estimated above this many tokens together.")
    ] = 400_000,
    dry_run: Annotated[
        bool, typer.Option(help="Write the prompt and stop, without calling the model.")
    ] = False,
) -> None:
    """Judge how similar CANDIDATE is to REFERENCE and write verdict.json and verdict.md."""
    try:
        chosen = load_rubric(rubric)
    except RubricError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1) from error
    ref_doc = _load(reference, html, include)
    cand_doc = _load(candidate, html, include)
    _describe("Reference", ref_doc)
    _describe("Candidate", cand_doc)
    total = ref_doc.tokens + cand_doc.tokens
    if total > max_input_tokens:
        typer.echo(
            f"Error: the inputs come to about {total:,} tokens, over --max-input-tokens "
            f"{max_input_tokens:,}. Nothing is truncated: pass fewer files (a single file, or "
            "--include for a directory), or raise the limit if the model's context allows it.",
            err=True,
        )
        raise typer.Exit(1)

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    folder = (
        out or default_runs_dir() / f"{stamp}-{_slug(cand_doc.label)}-vs-{_slug(ref_doc.label)}"
    )
    folder.mkdir(parents=True, exist_ok=True)
    system = build_system(chosen)
    user = build_user(ref_doc, cand_doc, focus)
    (folder / "prompt.txt").write_text(f"=== SYSTEM ===\n{system}\n=== USER ===\n{user}\n")
    if dry_run:
        typer.echo(f"Dry run: wrote {folder / 'prompt.txt'}. No model was called.")
        return

    try:
        llm = AnthropicLlm(settings_for(provider, model, effort))
    except LlmConfigError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1) from error
    typer.echo(f"\nJudging with {llm.name}, effort {effort}, rubric {chosen.name}, {runs} run(s).")

    def report(result: RunResult | Failure) -> None:
        if isinstance(result, Failure):
            typer.echo(f"  run {result.run} failed: {result.error}")
        else:
            typer.echo(f"  run {result.run} done: similarity {result.similarity:g}")

    judgment = asyncio.run(
        judge(llm, ref_doc, cand_doc, chosen, focus, runs, effort, on_done=report)
    )
    (folder / "verdict.json").write_text(judgment.model_dump_json(indent=2) + "\n")
    (folder / "verdict.md").write_text(markdown(judgment))
    typer.echo("")
    typer.echo(terminal_summary(judgment))
    typer.echo(f"\nWrote {folder / 'verdict.md'} and {folder / 'verdict.json'}.")
    if not judgment.runs:
        raise typer.Exit(1)


@app.command()
def extract(
    path: Annotated[Path, typer.Argument(help="A file or directory.")],
    html: HtmlOpt = "auto",
    include: IncludeOpt = None,
) -> None:
    """Print the text the judge would read for PATH."""
    doc = _load(path, html, include)
    typer.echo(doc.text)
    typer.echo("")
    _describe("Read", doc)


@app.command()
def rubrics() -> None:
    """List the built-in rubrics."""
    for name in builtin_names():
        r = load_rubric(name)
        dims = ", ".join(f"{d.id} ×{d.weight:g}" for d in r.dimensions)
        typer.echo(f"{name}: {r.description}\n  {dims}")
