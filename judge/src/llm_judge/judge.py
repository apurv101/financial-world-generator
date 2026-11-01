"""Run the judge: one or more independent runs over the same pair, then the aggregate.

Model runs are not deterministic, so a pair can be judged several times in parallel. The
judgment reports each run and the mean, lowest and highest of every score, so a spread shows how
far a single run can be trusted.
"""

import asyncio
import statistics
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from llm_judge.inputs import Document
from llm_judge.llm import Llm, LlmError
from llm_judge.prompt import build_system, build_user, retry_note
from llm_judge.rubric import Rubric
from llm_judge.verdict import (
    QuoteCheck,
    Verdict,
    VerdictError,
    check_quotes,
    coverage,
    parse_verdict,
    similarity,
    status_counts,
    verdict_schema,
)

ATTEMPTS = 3
"""Model calls per run. A reply that isn't a usable verdict, or a call that fails for a transient
reason (network, stalled stream, rate limit, server error), is tried again, twice at most."""


class Source(BaseModel):
    label: str
    files: list[str]
    skipped: list[str]
    chars: int
    tokens_estimate: int
    sha256: str

    @classmethod
    def of(cls, document: Document) -> "Source":
        return cls(
            label=document.label,
            files=[f"{p.path} ({p.how})" for p in document.parts],
            skipped=list(document.skipped),
            chars=len(document.text),
            tokens_estimate=document.tokens,
            sha256=document.sha256,
        )


class RunResult(BaseModel):
    run: int
    similarity: float
    coverage: float | None
    statuses: dict[str, int]
    quotes: QuoteCheck
    attempts: int
    model: str | None
    request_id: str | None
    usage: dict[str, Any]
    verdict: Verdict


class Failure(BaseModel):
    run: int
    error: str


class Stat(BaseModel):
    mean: float
    low: float
    high: float

    @classmethod
    def over(cls, values: list[float]) -> "Stat | None":
        if not values:
            return None
        return cls(mean=round(statistics.fmean(values), 1), low=min(values), high=max(values))


class Judgment(BaseModel):
    created_at: str
    judge: str
    effort: str
    rubric: Rubric
    focus: str | None
    reference: Source
    candidate: Source
    similarity: Stat | None
    coverage: Stat | None
    dimensions: dict[str, Stat]
    runs: list[RunResult]
    failures: list[Failure]


async def judge_once(
    llm: Llm,
    system: str,
    user: str,
    rubric: Rubric,
    reference: Document,
    candidate: Document,
    run: int,
) -> RunResult:
    schema = verdict_schema()
    note = ""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            reply = await llm.complete(system, user + note, schema)
        except LlmError as error:
            if not error.transient or attempt == ATTEMPTS:
                raise
            continue
        try:
            verdict = parse_verdict(reply.text, rubric)
        except VerdictError as error:
            if attempt == ATTEMPTS:
                raise
            note = retry_note(str(error))
            continue
        return RunResult(
            run=run,
            similarity=similarity(verdict, rubric),
            coverage=coverage(verdict),
            statuses=status_counts(verdict),
            quotes=check_quotes(verdict, reference.text, candidate.text),
            attempts=attempt,
            model=reply.model,
            request_id=reply.request_id,
            usage=reply.usage,
            verdict=verdict,
        )
    raise AssertionError("unreachable")  # pragma: no cover


async def judge(
    llm: Llm,
    reference: Document,
    candidate: Document,
    rubric: Rubric,
    focus: str | None = None,
    runs: int = 1,
    effort: str = "high",
    on_done: Callable[[RunResult | Failure], None] | None = None,
) -> Judgment:
    system = build_system(rubric)
    user = build_user(reference, candidate, focus)

    async def one(run: int) -> RunResult | Failure:
        try:
            result: RunResult | Failure = await judge_once(
                llm, system, user, rubric, reference, candidate, run
            )
        except (LlmError, VerdictError) as error:
            result = Failure(run=run, error=str(error))
        if on_done is not None:
            on_done(result)
        return result

    outcomes = await asyncio.gather(*(one(n) for n in range(1, runs + 1)))
    done = [o for o in outcomes if isinstance(o, RunResult)]
    dimensions: dict[str, Stat] = {}
    for dim in rubric.ids:
        scores = [float(d.score) for r in done for d in r.verdict.dimensions if d.id == dim]
        stat = Stat.over(scores)
        if stat is not None:
            dimensions[dim] = stat
    return Judgment(
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        judge=llm.name,
        effort=effort,
        rubric=rubric,
        focus=focus,
        reference=Source.of(reference),
        candidate=Source.of(candidate),
        similarity=Stat.over([r.similarity for r in done]),
        coverage=Stat.over([r.coverage for r in done if r.coverage is not None]),
        dimensions=dimensions,
        runs=done,
        failures=[o for o in outcomes if isinstance(o, Failure)],
    )
