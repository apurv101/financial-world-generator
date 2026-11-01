"""The judge's verdict, how it is parsed and checked, and the scores computed from it.

The model never writes the headline numbers. It lists the reference's elements with a status and
quotes, and scores each rubric dimension 0-10. Code then computes:

- similarity: the weighted mean of the dimension scores, on 0-100.
- coverage: the share of the reference's elements the candidate carries (match 1, partial 0.5),
  weighted by importance (high 3, medium 2, low 1), on 0-100.
- quote checks: whether each quote really appears in the text it claims to come from. An
  unverified quote is a sign the judge is citing from memory rather than from the text.
"""

import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator

from llm_judge.inputs import normalize, quote_found
from llm_judge.rubric import Rubric

Status = Literal["match", "partial", "contradicted", "missing"]
Importance = Literal["high", "medium", "low"]

STATUS_CREDIT: dict[str, float] = {
    "match": 1.0,
    "partial": 0.5,
    "contradicted": 0.0,
    "missing": 0.0,
}
IMPORTANCE_WEIGHT: dict[str, int] = {"high": 3, "medium": 2, "low": 1}


class VerdictError(Exception):
    """A reply that isn't a usable verdict: not JSON, wrong shape, or wrong dimensions."""


class Element(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    importance: Importance
    reference_quote: str
    status: Status
    candidate_quote: str
    note: str


class Extra(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    candidate_quote: str


class DimensionScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    score: int
    reason: str

    @field_validator("score")
    @classmethod
    def _in_range(cls, score: int) -> int:
        # Checked here rather than with Field(ge=, le=): structured outputs reject numeric
        # bounds in the JSON schema.
        if not 0 <= score <= 10:
            raise ValueError(f"score {score} is outside 0-10")
        return score


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    elements: list[Element]
    extras: list[Extra]
    dimensions: list[DimensionScore]
    summary: str


def verdict_schema() -> dict[str, object]:
    """The JSON schema of a verdict: every object closed and every field required."""
    return Verdict.model_json_schema()


_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.S)


def parse_verdict(text: str, rubric: Rubric) -> Verdict:
    """A verdict from the model's reply text, checked against the rubric's dimensions."""
    body = text.strip()
    fenced = _FENCE.match(body)
    if fenced:
        body = fenced.group(1)
    start, end = body.find("{"), body.rfind("}")
    if start < 0 or end < start:
        raise VerdictError("the reply holds no JSON object")
    try:
        verdict = Verdict.model_validate(json.loads(body[start : end + 1]))
    except json.JSONDecodeError as error:
        raise VerdictError(f"the JSON doesn't parse: {error}") from error
    except ValidationError as error:
        raise VerdictError(f"the JSON doesn't match the verdict shape: {error}") from error
    got = [d.id for d in verdict.dimensions]
    if sorted(got) != sorted(rubric.ids):
        raise VerdictError(f"dimensions must be exactly {rubric.ids}, one entry each; got {got}")
    return verdict


def similarity(verdict: Verdict, rubric: Rubric) -> float:
    weights = {d.id: d.weight for d in rubric.dimensions}
    total = sum(weights[d.id] * d.score for d in verdict.dimensions)
    return round(100 * total / (10 * sum(weights.values())), 1)


def coverage(verdict: Verdict) -> float | None:
    """None when the judge listed no elements."""
    if not verdict.elements:
        return None
    weight = sum(IMPORTANCE_WEIGHT[e.importance] for e in verdict.elements)
    credit = sum(
        IMPORTANCE_WEIGHT[e.importance] * STATUS_CREDIT[e.status] for e in verdict.elements
    )
    return round(100 * credit / weight, 1)


def status_counts(verdict: Verdict) -> dict[str, int]:
    counts = dict.fromkeys(STATUS_CREDIT, 0)
    for element in verdict.elements:
        counts[element.status] += 1
    return counts


class QuoteCheck(BaseModel):
    """Per element: True found, False not found, None no quote to check."""

    reference: list[bool | None]
    candidate: list[bool | None]
    extras: list[bool | None]

    @property
    def checked(self) -> int:
        return sum(v is not None for v in (*self.reference, *self.candidate, *self.extras))

    @property
    def found(self) -> int:
        return sum(v is True for v in (*self.reference, *self.candidate, *self.extras))


def check_quotes(verdict: Verdict, reference_text: str, candidate_text: str) -> QuoteCheck:
    ref, cand = normalize(reference_text), normalize(candidate_text)

    def check(quote: str, text: str) -> bool | None:
        return quote_found(quote, text) if quote.strip() else None

    return QuoteCheck(
        reference=[check(e.reference_quote, ref) for e in verdict.elements],
        candidate=[check(e.candidate_quote, cand) for e in verdict.elements],
        extras=[check(x.candidate_quote, cand) for x in verdict.extras],
    )
