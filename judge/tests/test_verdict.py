import json
from typing import Any

import pytest

from llm_judge.rubric import load_rubric
from llm_judge.verdict import (
    Verdict,
    VerdictError,
    check_quotes,
    coverage,
    parse_verdict,
    similarity,
    status_counts,
    verdict_schema,
)
from tests.support import GENERAL, verdict_dict, verdict_json


def test_parse_plain_and_fenced() -> None:
    assert parse_verdict(verdict_json(), GENERAL).summary == "Close enough."
    fenced = "```json\n" + verdict_json() + "\n```"
    assert parse_verdict(fenced, GENERAL).summary == "Close enough."
    chatty = "Here is my verdict:\n" + verdict_json() + "\nDone."
    assert parse_verdict(chatty, GENERAL).summary == "Close enough."


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("no json here", "no JSON object"),
        ("{bad json}", "doesn't parse"),
        ('{"elements": []}', "verdict shape"),
        (verdict_json(score=11), "outside 0-10"),
        (verdict_json(rubric=load_rubric("world")), "dimensions must be exactly"),
    ],
)
def test_parse_rejects(text: str, message: str) -> None:
    with pytest.raises(VerdictError, match=message):
        parse_verdict(text, GENERAL)


def test_parse_rejects_repeated_dimension() -> None:
    data = verdict_dict()
    data["dimensions"][1]["id"] = data["dimensions"][0]["id"]
    with pytest.raises(VerdictError, match="dimensions must be exactly"):
        parse_verdict(json.dumps(data), GENERAL)


def test_similarity_is_weighted_mean() -> None:
    data = verdict_dict()
    # general: subject 1, content 2, facts 2, structure 1, detail 1 (total 7)
    for dim, score in zip(data["dimensions"], [10, 5, 5, 0, 0], strict=True):
        dim["score"] = score
    verdict = Verdict.model_validate(data)
    assert similarity(verdict, GENERAL) == round(100 * (10 + 10 + 10) / 70, 1)


def test_coverage_weights_importance_and_status() -> None:
    verdict = Verdict.model_validate(verdict_dict())
    # high match (3 x 1) + low missing (1 x 0) over weight 4
    assert coverage(verdict) == 75.0
    assert status_counts(verdict) == {"match": 1, "partial": 0, "contradicted": 0, "missing": 1}
    partial = verdict_dict()
    partial["elements"][0]["status"] = "partial"
    assert coverage(Verdict.model_validate(partial)) == 37.5
    assert coverage(Verdict.model_validate(verdict_dict(elements=[]))) is None


def test_check_quotes() -> None:
    verdict = Verdict.model_validate(verdict_dict())
    checks = check_quotes(verdict, "We are a SaaS startup with five staff.", "A SaaS startup.")
    assert checks.reference == [True, True]
    assert checks.candidate == [True, None]  # the missing element has no candidate quote
    assert checks.extras == [False]  # "a dog" is not in the candidate
    assert (checks.found, checks.checked) == (3, 4)


def test_schema_is_closed_and_fully_required() -> None:
    schema = verdict_schema()

    def objects(node: Any) -> list[dict[str, Any]]:
        found: list[dict[str, Any]] = []
        if isinstance(node, dict):
            if node.get("type") == "object":
                found.append(node)
            for value in node.values():
                found += objects(value)
        elif isinstance(node, list):
            for value in node:
                found += objects(value)
        return found

    for obj in objects(schema):
        assert obj["additionalProperties"] is False
        assert sorted(obj["required"]) == sorted(obj["properties"])
    assert "minimum" not in json.dumps(schema)
