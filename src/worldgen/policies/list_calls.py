"""Our preference: how a tree tool that takes a list applies it when some items fail.

There is no real-world rule here. It is how our engine treats a narrator's batch. A list that
doesn't match the tool's input schema is rejected whole under either option; this policy decides
for well-formed items that break a rule, such as a taken id.
"""

from typing import Literal

ListCalls = Literal[
    # Default. One failing item rejects the whole call, and the rejection names every failing
    # item. The narrator fixes the list and sends it again, so half a batch never lands.
    # (SPEC policy list_calls.)
    "all_or_nothing",
    # The valid items are applied, and the result names the items that failed.
    "per_item",
]

DEFAULT: ListCalls = "all_or_nothing"
