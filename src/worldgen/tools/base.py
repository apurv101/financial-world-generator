"""Tools: what an agent can do. Each tool has a strict pydantic input and a run method.

Bad input, or a call that breaks a rule, goes back to the model as a rejection instead of
raising. Rejections start with "Rejected:" because some providers ignore a tool_result's
is_error flag, so the text alone must say the call failed.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError


class ToolError(Exception):
    """A rule the call broke. Its message goes back to the model."""


@dataclass(frozen=True)
class ToolOutcome:
    text: str
    is_error: bool = False


def rejected(message: str) -> ToolOutcome:
    return ToolOutcome(f"Rejected: {message}", is_error=True)


class Tool[C, In: BaseModel](ABC):
    name: str
    description: str
    input_model: type[In]

    def definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": input_schema(self.input_model),
        }

    def call(self, ctx: C, raw: Any) -> ToolOutcome:
        try:
            args = self.input_model.model_validate(raw)
        except ValidationError as error:
            return rejected(describe_errors(error))
        try:
            return ToolOutcome(self.run(ctx, args))
        except ToolError as error:
            return rejected(str(error))

    @abstractmethod
    def run(self, ctx: C, args: In) -> str: ...


def describe_errors(error: ValidationError) -> str:
    parts = []
    for item in error.errors():
        where = ".".join(str(part) for part in item["loc"]) or "input"
        parts.append(f"{where}: {item['msg']}")
    return "; ".join(parts)


def input_schema(model: type[BaseModel]) -> dict[str, Any]:
    """The model's JSON Schema with every $ref inlined and pydantic's title metadata dropped."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return resolve(defs[node["$ref"].rsplit("/", 1)[-1]])
            return {
                key: resolve(value)
                for key, value in node.items()
                if not (key == "title" and isinstance(value, str))
            }
        if isinstance(node, list):
            return [resolve(value) for value in node]
        return node

    resolved: dict[str, Any] = resolve(schema)
    return resolved
