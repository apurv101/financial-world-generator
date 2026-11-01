"""RunLog: the append-only log.jsonl of every model call, tool call and turn.

Each line is one JSON object with `at` (UTC time), `kind` and the entry's fields. Lines are
flushed as they are written, so `tail -f log.jsonl` follows a live run.
"""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class RunLog:
    def __init__(self, path: Path | None = None):
        self.path = path
        self.entries: list[dict[str, Any]] = []

    def write(self, kind: str, **fields: Any) -> None:
        entry = {"at": datetime.now(UTC).isoformat(timespec="milliseconds"), "kind": kind, **fields}
        self.entries.append(entry)
        if self.path is not None:
            with self.path.open("a") as f:
                f.write(json.dumps(entry, default=str) + "\n")

    def of_kind(self, kind: str) -> list[dict[str, Any]]:
        return [entry for entry in self.entries if entry["kind"] == kind]
