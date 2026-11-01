"""A judgment as Markdown (verdict.md) and as a short terminal summary."""

from llm_judge.judge import Judgment, RunResult, Stat
from llm_judge.rubric import Dimension

_STATUS_MARK = {"match": "✅ match", "partial": "🟡 partial", "contradicted": "❌ contradicted",
                "missing": "⬜ missing"}  # fmt: skip


def _stat(stat: Stat | None, unit: str = "") -> str:
    if stat is None:
        return "n/a"
    spread = "" if stat.low == stat.high else f" (runs {stat.low:g}–{stat.high:g})"
    return f"{stat.mean:g}{unit}{spread}"


def _cell(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ").strip()


def _quote(text: str, found: bool | None) -> str:
    if found is None:
        return ""
    mark = "" if found else " ⚠ *not found in the text*"
    return f"“{_cell(text)}”{mark}"


def headline(j: Judgment) -> str:
    contradicted = sum(r.statuses.get("contradicted", 0) for r in j.runs)
    per_run = f", {round(contradicted / len(j.runs), 1):g} contradicted per run" if j.runs else ""
    return (
        f"Similarity {_stat(j.similarity, '/100')} · "
        f"coverage of the reference {_stat(j.coverage, '%')}{per_run}"
    )


def markdown(j: Judgment) -> str:
    names = {d.id: d for d in j.rubric.dimensions}
    out = [
        f"# Judgment: {j.candidate.label} against {j.reference.label}",
        "",
        f"**{headline(j)}**",
        "",
        f"Judge {j.judge}, effort {j.effort}, rubric `{j.rubric.name}`, "
        f"{len(j.runs)} run(s) done, {len(j.failures)} failed. {j.created_at}.",
    ]
    if j.focus:
        out += ["", f"Focus: {j.focus}"]
    out += [
        "",
        "| | Reference | Candidate |",
        "|---|---|---|",
        f"| Source | `{j.reference.label}` | `{j.candidate.label}` |",
        f"| Files | {_cell(', '.join(j.reference.files))} "
        f"| {_cell(', '.join(j.candidate.files))} |",
        f"| Size | {j.reference.chars:,} chars (≈{j.reference.tokens_estimate:,} tokens) "
        f"| {j.candidate.chars:,} chars (≈{j.candidate.tokens_estimate:,} tokens) |",
    ]
    skipped = [*j.reference.skipped, *j.candidate.skipped]
    if skipped:
        out += ["", "Skipped files: " + "; ".join(skipped)]
    out += [
        "",
        "Similarity is the weighted mean of the dimension scores. Coverage is the share of the "
        "reference's elements the candidate carries (match 1, partial ½), weighted by importance.",
        "",
        "## Dimensions",
        "",
        "| Dimension | Weight | Score /10 | Each run |",
        "|---|---|---|---|",
    ]
    for dim in j.rubric.dimensions:
        scores = [str(d.score) for r in j.runs for d in r.verdict.dimensions if d.id == dim.id]
        out.append(
            f"| {dim.name} | {dim.weight:g} | {_stat(j.dimensions.get(dim.id))} "
            f"| {', '.join(scores) or 'n/a'} |"
        )
    for failure in j.failures:
        out += ["", f"**Run {failure.run} failed:** {failure.error}"]
    for run in j.runs:
        out += ["", *_run_section(run, names)]
    return "\n".join(out) + "\n"


def _run_section(run: RunResult, names: dict[str, Dimension]) -> list[str]:
    v, q = run.verdict, run.quotes
    counts = ", ".join(f"{n} {status}" for status, n in run.statuses.items())
    cov = "n/a" if run.coverage is None else f"{run.coverage:g}%"
    out = [
        f"## Run {run.run}",
        "",
        f"Similarity {run.similarity:g}/100 · coverage {cov} · "
        f"{counts} · quotes found in the texts {q.found}/{q.checked} · "
        f"{run.attempts} attempt(s) · {run.model or ''}",
        "",
        f"**Summary.** {v.summary.strip()}",
        "",
        "### Why each score",
        "",
    ]
    for dim in v.dimensions:
        name = names[dim.id].name if dim.id in names else dim.id
        out.append(f"- **{name}: {dim.score}/10.** {dim.reason.strip()}")
    out += [
        "",
        "### Elements of the reference",
        "",
        "| # | Status | Importance | Element | Reference | Candidate | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for n, e in enumerate(v.elements):
        out.append(
            f"| {n + 1} | {_STATUS_MARK[e.status]} | {e.importance} | {_cell(e.description)} "
            f"| {_quote(e.reference_quote, q.reference[n])} "
            f"| {_quote(e.candidate_quote, q.candidate[n])} | {_cell(e.note)} |"
        )
    if v.extras:
        out += ["", "### What the candidate adds", ""]
        for n, x in enumerate(v.extras):
            quote = _quote(x.candidate_quote, q.extras[n])
            out.append(f"- {x.description.strip()}" + (f" {quote}" if quote else ""))
    return out


def terminal_summary(j: Judgment) -> str:
    lines = [headline(j), ""]
    width = max(len(d.name) for d in j.rubric.dimensions)
    for dim in j.rubric.dimensions:
        lines.append(f"  {dim.name:<{width}}  {_stat(j.dimensions.get(dim.id))}/10")
    for run in j.runs:
        q = run.quotes
        lines += [
            "",
            f"Run {run.run}: similarity {run.similarity:g}, coverage {run.coverage}%, "
            f"quotes found {q.found}/{q.checked}.",
            f"  {run.verdict.summary.strip()}",
        ]
    for failure in j.failures:
        lines += ["", f"Run {failure.run} failed: {failure.error}"]
    return "\n".join(lines)
