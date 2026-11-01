from pathlib import Path

import pytest

from llm_judge.rubric import RubricError, builtin_names, load_rubric


def test_builtin_rubrics_load() -> None:
    assert builtin_names() == ["general", "world"]
    world = load_rubric("world")
    assert world.ids == ["premise", "cast", "money", "history", "stories", "friction", "specifics"]
    assert "examples" in world.guidance


def test_custom_rubric_file(tmp_path: Path) -> None:
    path = tmp_path / "mine.toml"
    path.write_text(
        'name = "mine"\ndescription = "d"\nguidance = "g"\n'
        '[[dimensions]]\nid = "tone"\nname = "Tone"\nweight = 2\nwhat = "Same tone?"\n'
    )
    rubric = load_rubric(str(path))
    assert rubric.ids == ["tone"]
    assert rubric.dimensions[0].weight == 2


@pytest.mark.parametrize(
    "body",
    [
        'name = "x"\ndescription = "d"\nguidance = "g"\ndimensions = []\n',
        'name = "x"\ndescription = "d"\nguidance = "g"\n'
        '[[dimensions]]\nid = "a"\nname = "A"\nwhat = "?"\n'
        '[[dimensions]]\nid = "a"\nname = "B"\nwhat = "?"\n',
        'name = "x"\ndescription = "d"\nguidance = "g"\n'
        '[[dimensions]]\nid = "a"\nname = "A"\nwhat = "?"\nweight = 0\n',
        "not = toml = at all",
    ],
)
def test_invalid_rubrics(tmp_path: Path, body: str) -> None:
    path = tmp_path / "bad.toml"
    path.write_text(body)
    with pytest.raises(RubricError, match="not a valid rubric"):
        load_rubric(str(path))


def test_unknown_rubric() -> None:
    with pytest.raises(RubricError, match="no rubric 'nope'"):
        load_rubric("nope")
