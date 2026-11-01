"""Policies: every modeling rule that is our preference, each switchable per run.

One file per policy. Its docstring starts "Our preference:", each option is commented, and
DEFAULT is the option used unless a run picks another (`worldgen narrate --policy name=option`).
Code that applies a policy names it in a comment.
"""

from pydantic import BaseModel, ConfigDict

from worldgen.policies import child_roles, list_calls, unfinished_turn
from worldgen.policies.child_roles import ChildRoles
from worldgen.policies.list_calls import ListCalls
from worldgen.policies.unfinished_turn import UnfinishedTurn


class Policies(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    child_roles: ChildRoles = child_roles.DEFAULT
    list_calls: ListCalls = list_calls.DEFAULT
    unfinished_turn: UnfinishedTurn = unfinished_turn.DEFAULT
