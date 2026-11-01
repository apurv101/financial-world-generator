import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from llm_judge import cli
from llm_judge.llm import Settings
from llm_judge.rubric import load_rubric
from tests.support import FakeLlm, verdict_json

runner = CliRunner()


@pytest.fixture
def pair(tmp_path: Path) -> tuple[Path, Path]:
    ref = tmp_path / "lumen.md"
    cand = tmp_path / "story.json"
    ref.write_text("We are a SaaS startup with five staff.")
    cand.write_text(json.dumps({"story": "A SaaS startup\nwith a dog."}))
    return ref, cand


def fake_llm(monkeypatch: pytest.MonkeyPatch, script: list[str | Exception]) -> FakeLlm:
    llm = FakeLlm(script)

    def make(settings: Settings) -> FakeLlm:
        llm.name = f"{settings.provider}:{settings.model}"
        return llm

    monkeypatch.setattr(cli, "AnthropicLlm", make)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "d")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    return llm


def test_compare_writes_verdict(
    pair: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    world = load_rubric("world")
    fake_llm(monkeypatch, [verdict_json(world, 6), verdict_json(world, 8)])
    out = tmp_path / "out"
    args = ["compare", *map(str, pair), "--rubric", "world", "--runs", "2", "--out", str(out)]
    result = runner.invoke(cli.app, args)
    assert result.exit_code == 0, result.output
    assert "Similarity 70/100 (runs 60–80)" in result.output
    verdict = json.loads((out / "verdict.json").read_text())
    assert verdict["judge"] == "deepseek:deepseek-v4-pro"
    assert verdict["candidate"]["files"] == ["story.json (json)"]
    report = (out / "verdict.md").read_text()
    assert "## Run 2" in report and "| Cast | 2 | 7 (runs 6–8) | 6, 8 |" in report
    assert "⚠ *not found in the text*" not in report.split("### What the candidate adds")[0]
    assert "=== SYSTEM ===" in (out / "prompt.txt").read_text()


def test_dry_run_calls_no_model(pair: tuple[Path, Path], tmp_path: Path) -> None:
    out = tmp_path / "out"
    result = runner.invoke(cli.app, ["compare", *map(str, pair), "--dry-run", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "No model was called" in result.output
    assert "<candidate" in (out / "prompt.txt").read_text()
    assert not (out / "verdict.json").exists()


def test_size_limit_refuses(pair: tuple[Path, Path]) -> None:
    result = runner.invoke(cli.app, ["compare", *map(str, pair), "--max-input-tokens", "5"])
    assert result.exit_code == 1
    assert "Nothing is truncated" in result.output


def test_all_runs_failing_exits_nonzero(
    pair: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_llm(monkeypatch, ["bad", "bad", "bad"])
    result = runner.invoke(cli.app, ["compare", *map(str, pair), "--out", str(tmp_path / "o")])
    assert result.exit_code == 1
    assert "run 1 failed" in result.output
    assert "Run 1 failed" in (tmp_path / "o" / "verdict.md").read_text()


def test_bad_inputs(
    pair: tuple[Path, Path], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ref, cand = pair
    missing = runner.invoke(cli.app, ["compare", str(ref), str(tmp_path / "nope")])
    assert missing.exit_code == 1 and "does not exist" in missing.output
    rubric = runner.invoke(cli.app, ["compare", str(ref), str(cand), "--rubric", "nope"])
    assert rubric.exit_code == 1 and "no rubric" in rubric.output
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    nokey = runner.invoke(cli.app, ["compare", str(ref), str(cand), "--out", str(tmp_path / "o")])
    assert nokey.exit_code == 1 and "No model credentials" in nokey.output


def test_extract_and_rubrics(pair: tuple[Path, Path]) -> None:
    result = runner.invoke(cli.app, ["extract", str(pair[1])])
    assert result.exit_code == 0
    assert "story: |\n  A SaaS startup\n  with a dog." in result.output
    listed = runner.invoke(cli.app, ["rubrics"])
    assert "world:" in listed.output and "cast ×2" in listed.output


def test_default_runs_dir_and_slug() -> None:
    assert cli.default_runs_dir().name == "runs"
    assert cli._slug("../worlds/demo/story.md") == "story"
    assert cli._slug("../worlds/demo") == "demo"
    assert cli._slug("???.md") == "input"
