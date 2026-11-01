"""Rubrics: what "similar" means for a comparison.

A rubric is a TOML file with a name, a description, guidance on how to match elements, and the
dimensions the judge scores from 0 to 10, each with a weight. Built-in rubrics live next to this
file in `rubrics/`; any other path to a TOML file works too.
"""

import tomllib
from importlib import resources
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


class RubricError(Exception):
    """A rubric can't be found or doesn't validate."""


class Dimension(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str
    weight: float = Field(default=1.0, gt=0)
    what: str
    """What the dimension asks, as the judge reads it."""


class Rubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    guidance: str
    """How to match elements between the two outputs."""
    dimensions: list[Dimension] = Field(min_length=1)

    @field_validator("dimensions")
    @classmethod
    def _unique_ids(cls, dimensions: list[Dimension]) -> list[Dimension]:
        ids = [d.id for d in dimensions]
        if len(ids) != len(set(ids)):
            raise ValueError(f"dimension ids repeat: {ids}")
        return dimensions

    @property
    def ids(self) -> list[str]:
        return [d.id for d in self.dimensions]


def builtin_names() -> list[str]:
    folder = resources.files("llm_judge").joinpath("rubrics")
    return sorted(
        p.name.removesuffix(".toml") for p in folder.iterdir() if p.name.endswith(".toml")
    )


def load_rubric(name_or_path: str) -> Rubric:
    """A built-in rubric by name (see `builtin_names`), or a TOML file by path."""
    if name_or_path in builtin_names():
        source = resources.files("llm_judge").joinpath(f"rubrics/{name_or_path}.toml").read_text()
        where = f"built-in rubric {name_or_path}"
    else:
        path = Path(name_or_path)
        if not path.is_file():
            known = ", ".join(builtin_names())
            raise RubricError(f"no rubric {name_or_path!r}: not a file, nor one of {known}")
        source = path.read_text()
        where = str(path)
    try:
        return Rubric.model_validate(tomllib.loads(source))
    except (tomllib.TOMLDecodeError, ValidationError) as error:
        raise RubricError(f"{where} is not a valid rubric: {error}") from error
