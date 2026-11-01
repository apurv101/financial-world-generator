# judge: how similar are two outputs?

An LLM judge that compares two outputs in any format and scores how similar they are. In this repo it is the "judge" step of the harness loop: run worldgen on a prompt, then score how close the output lands to a reference, such as a dry-run page.

It is its own project, separate from `worldgen`, with its own environment and tests. Nothing in `src/worldgen` imports it.

## Run it

From this folder, with the repo's `.env`:

```bash
uv run --env-file ../.env judge compare REFERENCE CANDIDATE --rubric world
```

- `REFERENCE` is what the candidate should resemble. `CANDIDATE` is the output being judged. Either can be a file or a directory.
- Results go to a new folder in `runs/` (gitignored): `verdict.md` to read, `verdict.json` with everything, and `prompt.txt` with the exact prompt sent.
- The judge uses Claude (`claude-opus-5-5`) when `ANTHROPIC_API_KEY` is set, else DeepSeek (`deepseek-v4-pro`) when `DEEPSEEK_API_KEY` is set. `--provider` and `--model` override this.

Example: the Lumen dry-run page against a narrator story told from `TARGET_EXAMPLE.md`.

```bash
# The page is a claude.ai artifact: save a local copy of its HTML first (here runs/lumen-dry-run.html).
uv run --env-file ../.env worldgen narrate --prompt-file ../TARGET_EXAMPLE.md --out ../worlds/target_example
uv run --env-file ../.env judge compare runs/lumen-dry-run.html ../worlds/target_example/narrator_output.md \
    --rubric world --runs 3
```

Judge only what the narrator wrote. worldgen's `story.md` and `tree.json` both quote the root prompt in full, so judging either file credits the narrator for text it was given. `narrator_output.md` holds the root story and every child's prompt, brief and story, without the root prompt. worldgen doesn't write this file yet: it was made from `tree.json`.

## Calibration

Measured on 2026-11-01 with `deepseek-v4-pro`, rubric `world`, the Lumen dry-run page as the reference:

| Candidate | Similarity | Coverage |
|---|---|---|
| The same page (should be 100) | 100 | 100% |
| The narrator's story from `TARGET_EXAMPLE.md`, 3 runs | 61 (53–70) | 69% (51–80%) |
| The demo story (a one-line SaaS prompt) | 44 | 39% |
| The trucking prompt (another industry) | 36 | 33% |

The order is right, but:

- A single run can move by about 15 points (53 to 70 across the three runs above). Use `--runs 3` or more before trusting a difference between two harness versions.
- DeepSeek follows the `world` rubric's "names are examples" only in part. It describes elements by role, but it still often marks an element partial because the provider, name or amount differs (Brex for Ramp, a different customer). That pushes same-industry candidates down, which is why the demo story lands only 8 points above trucking.

Other commands:

- `judge extract PATH` prints the text the judge reads for a file or directory. Use it to check that an input is read the way you expect.
- `judge rubrics` lists the built-in rubrics.

## Options

| Option | What it does |
|---|---|
| `--rubric general\|world\|PATH` | What "similar" means. Default `general`. See [Rubrics](#rubrics). |
| `--focus "..."` | Judge only one part, e.g. `--focus "the day-0 world: company, cast, accounts, history"`. Use it when one output covers more stages than the other. |
| `--runs N` | Independent judge runs, in parallel. The report gives the mean and the lowest and highest score. Use 3 or more when comparing harness versions. |
| `--effort` | How hard the judge thinks: `low` to `max`. Default `high`. |
| `--html auto\|rendered\|source` | How HTML is read. See below. |
| `--include GLOB` | For a directory input, only the files that match. Repeatable. |
| `--max-input-tokens N` | Refuse inputs estimated above N tokens together (default 400,000). Nothing is ever truncated. |
| `--dry-run` | Write `prompt.txt` and stop, without calling the model. |

## How it reads formats

- **Text** of any kind (Markdown, YAML, CSV, code): read as is.
- **JSON** and **JSON Lines**: rendered as indented `key: value` lines, so a story or prompt stored in a JSON string reads as text.
- **HTML**: `rendered` runs the page in headless Chrome and reads the visible text, which is what a JavaScript-built page like the Lumen artifacts needs. `source` reads the markup with scripts kept, since such pages keep their content in scripts. `auto` (default) renders when Chrome or Chromium is found; set `JUDGE_CHROME` to its path if it isn't. Rendering runs the page's scripts, so use `source` for a page you don't trust.
- **PDF** (text layer, via pypdf) and **Word .docx** (paragraphs).
- **Directories**: every readable file in path order, each headed by its path. Hidden files are left out, unreadable binaries are listed as skipped, and `--include` narrows the set. A worldgen output folder holds `story.md`, `tree.json` and `log.jsonl`, and the first two carry the same story, so pass the one file you mean.

## How it scores

The model doesn't write the headline numbers. It does three things, and code computes the scores:

1. **Elements.** It lists the reference's distinct facts, entities, events and rules (20 to 60 of them), rates each one's importance (high, medium, low) and finds each one's counterpart in the candidate: `match`, `partial`, `contradicted` or `missing`. Each comes with a verbatim quote from each side.
2. **Extras.** It lists what the candidate adds that the reference doesn't have.
3. **Dimensions.** It scores each rubric dimension from 0 to 10 and names the elements behind each score.

From these:

- **Similarity (0-100)** is the weighted mean of the dimension scores. This is the headline.
- **Coverage (0-100%)** is the share of the reference's elements the candidate carries: match 1, partial ½, weighted by importance (high 3, medium 2, low 1). It is directional: swap the arguments and it measures the other way.
- **Quote checks.** Every quote is looked up in the text it claims to come from. If a quote isn't found, the judge is citing from memory, and the report marks it ⚠.

A reply that isn't a valid verdict is asked for again, up to three attempts. With Claude the verdict's JSON schema is enforced as a structured output. DeepSeek has no structured output, so its reply is checked after it arrives.

## Rubrics

- **`general`**: any two outputs. Subject and scope, content coverage, facts and specifics, structure and sequence, level of detail. Names, numbers and dates count.
- **`world`**: two descriptions of a simulated financial world. Premise, cast, accounts and money channels, history before the start, stories and events, realistic friction, specifics. Names, amounts and dates are treated as examples, as `TARGET_EXAMPLE.md` says: an element matches when it plays the same role, and literal agreement counts only under "specifics".

A custom rubric is a TOML file:

```toml
name = "tone"
description = "Do two support replies sound alike?"
guidance = "Wording can differ; judge the stance and the promises made."

[[dimensions]]
id = "stance"          # lowercase, used in the JSON
name = "Stance"
weight = 2
what = "Do both take the same position toward the customer?"
```

Pass it with `--rubric path/to/tone.toml`.

## Limits

- An LLM judge is noisy. Compare harness versions on several runs (`--runs 3`), and look at the spread before trusting a small difference.
- A judge from the same model family as the generator may favor its style. When Claude is available, judge DeepSeek output with Claude, and the other way round.
- One output can reach further than the other, as a dry run that simulates days does against a day-0 story. That lowers coverage without making the worlds different. Use `--focus` to compare the shared part.

## Develop

```bash
uv run pytest -q --cov=llm_judge
uv run ruff check . && uv run ruff format --check .
uv run mypy src tests
```

The tests use a scripted fake model. Nothing in them calls an API.
