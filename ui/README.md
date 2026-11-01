# worldgen Story & World Observatory (`ui/`)

A standalone zero-dependency web UI for browsing `worldgen` narrator trees, stories, prompts, briefs, and `log.jsonl` execution traces.

## Quick Start

### 1. Live Server Mode (recommended)
Auto-discovers every world under `worlds/` (`demo`, `target_example`, and any new worlds you generate):

```bash
uv run python ui/server.py
```

Then open **http://127.0.0.1:8765** in your browser.

### 2. Direct Static File Mode
If you want to open [`ui/static/index.html`](static/index.html) directly in a browser without running the Python server, refresh the static bundle snapshot whenever you generate new worlds:

```bash
uv run python ui/server.py --build-bundle
```

You can also click **Open JSON/Log** in the top bar at any time to load any `tree.json`, `story.md`, or `log.jsonl` directly from disk.
