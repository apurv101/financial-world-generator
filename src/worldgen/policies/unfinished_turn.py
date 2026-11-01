"""Our preference: what the engine does when a narrator ends its turn with work missing.

Work is missing when the narrator has not told its story, or a child it spawned has no brief.
"""

from typing import Literal

UnfinishedTurn = Literal[
    # Default. The engine asks once, naming what is missing. If the narrator ends again with
    # work still missing, the turn ends as unfinished and its turn_finished entry names the gaps.
    "ask_once",
    # The turn ends at once as unfinished, and its turn_finished entry names the gaps.
    "accept",
]

DEFAULT: UnfinishedTurn = "ask_once"
