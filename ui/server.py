"""Lightweight zero-dependency web server and static bundle builder for the worldgen Story & Observability UI.

Usage:
    uv run python ui/server.py                  # starts live server at http://127.0.0.1:8765
    uv run python ui/server.py --port 8080      # custom port
    uv run python ui/server.py --build-bundle   # writes ui/static/worlds_bundle.js for serverless file:// viewing
"""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

ROOT_DIR = Path(__file__).resolve().parent.parent
WORLDS_DIR = ROOT_DIR / "worlds"
STATIC_DIR = Path(__file__).resolve().parent / "static"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def _summarize_world(world_id: str, folder: Path) -> dict[str, Any]:
    tree_path = folder / "tree.json"
    story_path = folder / "story.md"
    narrator_out_path = folder / "narrator_output.md"
    log_path = folder / "log.jsonl"

    tree_data: dict[str, Any] = {}
    if tree_path.exists():
        try:
            tree_data = json.loads(tree_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            tree_data = {}

    nodes = tree_data.get("nodes", {})
    narrator_count = sum(1 for n in nodes.values() if n.get("role") == "narrator")
    actor_count = sum(1 for n in nodes.values() if n.get("role") == "actor")
    status_counts: dict[str, int] = {}
    story_words = 0
    for n in nodes.values():
        st = n.get("status", "unknown")
        status_counts[st] = status_counts.get(st, 0) + 1
        if n.get("story"):
            story_words += len(str(n["story"]).split())

    log_entries = _read_jsonl(log_path)
    llm_name = None
    effort = None
    policies: dict[str, Any] = {}
    started_at = None
    usage_totals = {"input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0}
    llm_calls = 0
    tool_calls = 0
    tool_errors = 0

    for entry in log_entries:
        kind = entry.get("kind")
        if kind == "run_started":
            llm_name = entry.get("llm") or llm_name
            effort = entry.get("effort") or effort
            policies = entry.get("policies") or policies
            started_at = entry.get("at") or started_at
        elif kind == "llm_reply":
            llm_calls += 1
            usage = entry.get("usage") or {}
            for k in usage_totals:
                usage_totals[k] += int(usage.get(k) or 0)
        elif kind == "tool_call":
            tool_calls += 1
            if entry.get("is_error"):
                tool_errors += 1

    # Extract a short title from the root story first heading if available
    root_id = tree_data.get("root", "n_root")
    root_node = nodes.get(root_id, {})
    root_story = str(root_node.get("story") or "")
    title = world_id
    for line in root_story.splitlines():
        cleaned = line.strip().lstrip("#").strip()
        if cleaned:
            title = cleaned
            break

    return {
        "id": world_id,
        "title": title,
        "path": str(folder.relative_to(ROOT_DIR)),
        "node_count": len(nodes),
        "narrator_count": narrator_count,
        "actor_count": actor_count,
        "status_counts": status_counts,
        "story_words": story_words,
        "llm": llm_name,
        "effort": effort,
        "policies": policies,
        "started_at": started_at,
        "llm_calls": llm_calls,
        "tool_calls": tool_calls,
        "tool_errors": tool_errors,
        "usage": usage_totals,
        "files": {
            "tree": tree_path.exists(),
            "story": story_path.exists(),
            "narrator_output": narrator_out_path.exists(),
            "log": log_path.exists(),
        },
    }


def discover_worlds() -> dict[str, Path]:
    """Finds all directories under worlds/ that hold a tree.json or story.md."""
    found: dict[str, Path] = {}
    if not WORLDS_DIR.exists():
        return found
    for path in sorted(WORLDS_DIR.rglob("tree.json")):
        folder = path.parent
        rel_id = str(folder.relative_to(WORLDS_DIR)).replace("\\", "/")
        found[rel_id] = folder
    return found


def load_world_payload(world_id: str) -> dict[str, Any] | None:
    worlds = discover_worlds()
    folder = worlds.get(world_id)
    if folder is None:
        return None
    summary = _summarize_world(world_id, folder)
    tree_path = folder / "tree.json"
    story_path = folder / "story.md"
    narrator_out_path = folder / "narrator_output.md"
    log_path = folder / "log.jsonl"

    tree = json.loads(tree_path.read_text(encoding="utf-8")) if tree_path.exists() else None
    story_md = story_path.read_text(encoding="utf-8") if story_path.exists() else None
    narrator_output_md = (
        narrator_out_path.read_text(encoding="utf-8") if narrator_out_path.exists() else None
    )
    log_entries = _read_jsonl(log_path)

    return {
        "summary": summary,
        "tree": tree,
        "story_md": story_md,
        "narrator_output_md": narrator_output_md,
        "log_entries": log_entries,
    }


def build_static_bundle() -> Path:
    """Writes ui/static/worlds_bundle.js so index.html works both via file:// and HTTP server."""
    worlds = discover_worlds()
    summaries = []
    payloads = {}
    for world_id, folder in worlds.items():
        summaries.append(_summarize_world(world_id, folder))
        payloads[world_id] = load_world_payload(world_id)

    bundle = {
        "worlds": summaries,
        "payloads": payloads,
    }
    target = STATIC_DIR / "worlds_bundle.js"
    target.write_text(
        "// Auto-generated snapshot of worlds/ for direct file:// viewing.\n"
        "// Run `uv run python ui/server.py --build-bundle` or start `uv run python ui/server.py` for live updates.\n"
        f"window.__WORLDGEN_BUNDLE__ = {json.dumps(bundle, ensure_ascii=False)};\n",
        encoding="utf-8",
    )
    return target


class WorldgenUIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/worlds":
            worlds = discover_worlds()
            data = [_summarize_world(wid, folder) for wid, folder in worlds.items()]
            self._send_json({"worlds": data})
            return

        if path.startswith("/api/worlds/"):
            world_id = path.removeprefix("/api/worlds/").strip("/")
            payload = load_world_payload(world_id)
            if payload is None:
                self._send_json({"error": f"World {world_id!r} not found"}, status=404)
            else:
                self._send_json(payload)
            return

        super().do_GET()

    def _send_json(self, obj: Any, status: int = 200) -> None:
        raw = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format: str, *args: Any) -> None:
        # Keep console output clean
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="worldgen Story & Observability UI server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind (default: 8765)")
    parser.add_argument(
        "--build-bundle",
        action="store_true",
        help="Generate ui/static/worlds_bundle.js and exit",
    )
    args = parser.parse_args()

    bundle_path = build_static_bundle()
    if args.build_bundle:
        print(f"Built static bundle at {bundle_path}")
        return

    server = ThreadingHTTPServer((args.host, args.port), WorldgenUIHandler)
    print(f"worldgen UI running at http://{args.host}:{args.port}")
    print(f"Serving worlds from: {WORLDS_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        server.server_close()


if __name__ == "__main__":
    main()
