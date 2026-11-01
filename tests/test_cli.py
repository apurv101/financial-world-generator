import json
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from worldgen import cli
from worldgen.llm.fake import FakeLlm, text_reply, tool_reply
from worldgen.tree.nodes import Tree

runner = CliRunner()


def scripted(*replies: Any) -> FakeLlm:
    llm = FakeLlm(list(replies))
    llm.name = "fake:test"
    return llm


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> list[FakeLlm]:
    llms: list[FakeLlm] = []

    def make(settings: Any) -> FakeLlm:
        return llms.pop(0)

    monkeypatch.setattr(cli, "AnthropicLlm", make)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    return llms


ROOT_TURN = [
    tool_reply(
        ("tell_story", {"story": "A detailed story."}),
        (
            "spawn_child",
            {"items": [{"id": "n_sales", "role": "narrator", "name": "Sales", "prompt": "Sales."}]},
        ),
        ("brief_child", {"child": "n_sales", "brief": "Q1 renewals."}),
    ),
    text_reply(),
]
SALES_TURN = [tool_reply(("tell_story", {"story": "Sales story."})), text_reply()]


def test_narrate_then_expand(tmp_path: Path, fake_llm: list[FakeLlm]) -> None:
    out = tmp_path / "story"
    fake_llm.append(scripted(*ROOT_TURN))
    result = runner.invoke(cli.app, ["narrate", "--prompt", "A SaaS startup.", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert "Pending narrators: n_sales" in result.output
    assert "n_root  Root narrator  [told] (story 3 words, 1 children)" in result.output
    assert (out / "story.md").read_text().startswith("# Root narrator: story tree")
    kinds = [json.loads(line)["kind"] for line in (out / "log.jsonl").read_text().splitlines()]
    assert kinds[0] == "run_started" and kinds[-1] == "run_finished"

    fake_llm.append(scripted(*SALES_TURN))
    result = runner.invoke(cli.app, ["expand", str(out), "n_sales"])
    assert result.exit_code == 0, result.output
    assert Tree.load(out / "tree.json").node("n_sales").status == "told"

    result = runner.invoke(cli.app, ["expand", str(out)])
    assert result.exit_code == 0 and "No pending narrators" in result.output


def test_narrate_reads_prompt_and_brief_files_and_policies(
    tmp_path: Path, fake_llm: list[FakeLlm]
) -> None:
    prompt, brief = tmp_path / "p.md", tmp_path / "b.md"
    prompt.write_text("The sales department.")
    brief.write_text("Lumen Metrics sells analytics.")
    fake_llm.append(scripted(text_reply()))
    out = tmp_path / "s"
    args = [
        "narrate",
        "--prompt-file",
        str(prompt),
        "--brief-file",
        str(brief),
        "--out",
        str(out),
        "--policy",
        "unfinished_turn=accept",
        "--name",
        "Sales",
    ]
    result = runner.invoke(cli.app, args)
    assert result.exit_code == 0, result.output
    root = Tree.load(out / "tree.json").node("n_root")
    assert root.prompt == "The sales department." and root.brief == "Lumen Metrics sells analytics."
    assert root.status == "unfinished"
    assert "n_root unfinished: you have not told your story" in result.output


def test_narrate_rejects_bad_input(tmp_path: Path, fake_llm: list[FakeLlm]) -> None:
    out = str(tmp_path / "s")
    assert runner.invoke(cli.app, ["narrate", "--out", out]).exit_code != 0
    assert (
        runner.invoke(
            cli.app, ["narrate", "--out", out, "--prompt", "x", "--policy", "list_calls"]
        ).exit_code
        != 0
    )
    assert (
        runner.invoke(
            cli.app, ["narrate", "--out", out, "--prompt", "x", "--policy", "list_calls=some"]
        ).exit_code
        != 0
    )


def test_narrate_refuses_to_overwrite_and_expand_checks_the_node(
    tmp_path: Path, fake_llm: list[FakeLlm]
) -> None:
    out = tmp_path / "s"
    fake_llm.append(scripted(*ROOT_TURN))
    runner.invoke(cli.app, ["narrate", "--prompt", "x", "--out", str(out)])
    again = runner.invoke(cli.app, ["narrate", "--prompt", "x", "--out", str(out)])
    assert again.exit_code != 0 and "already holds a tree" in again.output
    wrong = runner.invoke(cli.app, ["expand", str(out), "n_root"])
    assert wrong.exit_code != 0 and "Pending: n_sales" in wrong.output
    missing = runner.invoke(cli.app, ["expand", str(tmp_path / "nowhere")])
    assert missing.exit_code != 0


def test_missing_credentials_exit_with_a_message(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    result = runner.invoke(cli.app, ["narrate", "--prompt", "x", "--out", str(tmp_path / "s")])
    assert result.exit_code == 1 and "No model credentials" in result.output
