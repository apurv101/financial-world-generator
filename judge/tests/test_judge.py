import asyncio
from pathlib import Path

from llm_judge.inputs import Document, Part
from llm_judge.judge import ATTEMPTS, Failure, Judgment, RunResult, judge
from llm_judge.llm import LlmError
from tests.support import GENERAL, FakeLlm, verdict_json

REF = Document("ref.md", (Part("ref.md", "We are a SaaS startup with five staff.", "text"),))
CAND = Document("cand.md", (Part("cand.md", "A SaaS startup with a dog.", "text"),))


def run(
    llm: FakeLlm, runs: int = 1, focus: str | None = None
) -> tuple[Judgment, list[RunResult | Failure]]:
    seen: list[RunResult | Failure] = []
    result = asyncio.run(judge(llm, REF, CAND, GENERAL, focus, runs, on_done=seen.append))
    return result, seen


def test_one_run() -> None:
    llm = FakeLlm([verdict_json(score=8)])
    judgment, seen = run(llm, focus="the cast")
    assert judgment.similarity is not None and judgment.similarity.mean == 80.0
    assert judgment.coverage is not None and judgment.coverage.mean == 75.0
    assert judgment.dimensions["facts"].mean == 8.0
    result = judgment.runs[0]
    assert (result.attempts, result.quotes.found, result.model) == (1, 4, "fake-model")
    assert isinstance(seen[0], RunResult)
    system, user = llm.calls[0]
    assert "# Dimensions" in system and "- facts (Facts and specifics, weight 2)" in system
    assert user.index("<reference") < user.index("<candidate") < user.index("<focus>")
    assert "Judge only what falls under the focus." in user


def test_bad_reply_is_asked_for_again() -> None:
    llm = FakeLlm(["not json", verdict_json()])
    judgment, _ = run(llm)
    assert judgment.runs[0].attempts == 2
    assert "could not be used: the reply holds no JSON object" in llm.calls[1][1]


def test_run_fails_after_attempts_and_others_survive() -> None:
    llm = FakeLlm(["bad"] * ATTEMPTS + [LlmError("boom")])
    judgment, seen = run(llm, runs=2)
    assert judgment.runs == []
    assert judgment.similarity is None
    errors = sorted(f.error for f in judgment.failures)
    assert errors[0] == "boom" and "no JSON object" in errors[1]
    assert all(isinstance(s, Failure) for s in seen)


def test_aggregate_over_runs() -> None:
    llm = FakeLlm([verdict_json(score=4), verdict_json(score=8)])
    judgment, _ = run(llm, runs=2)
    sim = judgment.similarity
    assert sim is not None and (sim.mean, sim.low, sim.high) == (60.0, 40.0, 80.0)
    assert judgment.reference.files == ["ref.md (text)"]


def test_judgment_serializes(tmp_path: Path) -> None:
    judgment, _ = run(FakeLlm([verdict_json()]))
    path = tmp_path / "v.json"
    path.write_text(judgment.model_dump_json())
    assert Judgment.model_validate_json(path.read_text()).judge == "fake:judge"
