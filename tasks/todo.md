# Tasks: Financial World Generator

Plan: `tasks/plan.md` (decisions D1-D6, architecture, risks). Spec: `SPEC.md`.

**Rules for every task**

- **Gate.** All three must pass before a task is checked off:
  ```
  uv run pytest -q --cov=worldgen --cov-fail-under=90
  uv run ruff check . && uv run ruff format --check .
  uv run mypy --strict worldgen
  ```
- Files under `validators/`, `institutions/mechanisms/`, `engine/clearinghouse.py` and `agents/loop.py` keep 100% line coverage from the task that creates them.
- Every source file listed gets a mirrored test under `tests/`. Test files are not listed separately.
- **Sizing.** SPEC's one-class-per-file convention makes model, tool and log-entry files a few lines each. A task's size counts the files that hold real logic, and no task has more than about five of those.
- Tests use `FakeLlm` (scripted or replaying fixtures) or the `tests/support/as_agreed.py` policy. Live tests live in `tests/live/` and run only with `WORLDGEN_LIVE=1`.
- A task that changes the manifest schema updates `docs/manifest-reference.md`. From Task 3 on, a test fails if any model field is undocumented.
- Engine code never names an institution, industry, payment method or relationship type. From Task 2 on, the neutrality test enforces this.
- **Preferences are policies (D7).** A task that builds a rule from SPEC's Policies table, or finds a new rule that is our preference, builds it as a policy:
  - a file in `worldgen/policies/` whose docstring starts "Our preference:", with a comment on every option
  - a field on `Policies`, defaulting to our preference, and a docs entry
  - a test for every option, and a comment naming the policy where the code applies it
  A new policy is added to SPEC's table. Changing a default needs the user (SPEC: ask first). `tasks/plan.md` maps each policy to the task that builds it.
- Commit after each task. Commit messages carry no Claude attribution lines.

---

## Phase 0: Decisions and the declaration language

## Task 0: Confirm D1-D6 and sync SPEC.md

**Description:** Get the user's answers to D1-D6 in `tasks/plan.md` and write them into SPEC.md as current design:
- **Tech Stack:** `jsonschema` as a runtime dependency (D4d).
- **Core Concepts:**
  - receiving accounts (D5a)
  - which institution's rules settle a payment and hear its dispute (D5b)
  - the Event fields `memo` and `details`, the Entity field `fields`, and zero-amount record events (D5c)
- **Manifest Shape:** `nodes[].brief`.
- **Commands:** `worldgen prompts history|revert` (D5i).
- **Simulation Model:**
  - the `default_chapter` values (D5j)
  - escalations read within a review under way (D5k)
  - what a report turn can do (D5l)
  - day-0-only tools (D5n)
  - catalog prices (D5o)
  - all-or-nothing list calls (D5p)
- **Run history:** `run_started` lists the starting tree, and what a spawned node is (D6), as answered.
- **Open Questions:** resolved as in D3.
- **Success Criterion 1:** as answered in D4e, plus unknown policies and policy options.
- **Policies (D7):** the Policies section and table, the policy convention in Code Style, Testing Strategy and Boundaries, and each rule's policy named where SPEC states it.

Update TARGET_EXAMPLE.md only where an answer touches it. Write only the current design, with no mention of removed alternatives.

**Acceptance criteria:**
- [x] D1-D7 each have a recorded answer in `tasks/plan.md`
- [x] SPEC.md and TARGET_EXAMPLE.md agree with each other and with the answers
- [x] Both files describe only the current design

**Verification:**
- [x] Manual: the user reads both diffs and approves them

**Dependencies:** None
**Files likely touched:** `SPEC.md`, `TARGET_EXAMPLE.md`, `tasks/plan.md`
**Estimated scope:** S

## Task 1: The institution declaration language, on paper

**Description:** Before any mechanism code exists, write out how institutions are declared, and test the language against the four SaaS institutions. This task writes no code. Task 1b then tests the language on another industry.

**`docs/declaring-an-institution.md`** covers:
- **Declaration fields:**
  - `calendar`
  - `methods`, with each method's settlement rules
  - `mechanisms`, with each mechanism's config
  - `tables`
- **The column-source vocabulary:**
  - event fields, including `event.settled`, `event.memo` and `event.details.<key>` (D5b, D5c)
  - account fields
  - party fields, such as `payer.descriptor`, `actor.name` and `<party>.fields.<key>`
  - `statement.*` and `counter.<name>`
  - constants, and value maps (for example, from a payment method to a `transaction_type`)
- **Rows:**
  - each table's row source: one row per movement, per statement, per record event or per split leg
  - its filter, on action, payment method and account
  - the sign convention
  - which rows update later, and on what (settlement, a sweep, a statement closing, an annotation)
- **Two coverage tables:**
  - every column of every SaaS table, with its source
  - every money flow in TARGET_EXAMPLE section 4, with the act tool, staff tool or mechanism that produces it

**The SaaS declarations:**
- `examples/saas_startup/manifest.yaml` holds only its `institutions:` section for now: Mercury, Ramp, Stripe and Rippling. Later tasks complete the manifest.
- `examples/saas_startup/schemas/` holds one JSON Schema per table, split from TARGET_EXAMPLE section 5 with no column changed, plus `common.schema.json`.

**Acceptance criteria:**
- [x] Every column of every SaaS table has a source from the vocabulary, and none is left as custom
- [x] Every institution behavior and money flow in TARGET_EXAMPLE sections 3.4 and 4 maps to a mechanism's config, an act tool or a staff decision:
  - Stripe's fee, availability delay, daily payouts and negative-balance pulls
  - Ramp's cutoff and autopay
  - Rippling's numbered, balanced journal entries and their Mercury debits
  - Mercury's statements and interest
- [x] Anything that does not fit is written up as a proposed change to the mechanism set or the act tools, for the user to decide (SPEC: ask first)

**Verification:**
- [ ] Manual: the user reviews the doc and the declarations at Checkpoint 0

**Dependencies:** Task 0
**Files likely touched:** `docs/declaring-an-institution.md`, `examples/saas_startup/{manifest.yaml,schemas/}`
**Estimated scope:** M (design files only)

## Task 1b: The language tested on trucking

**Description:** Test the language from Task 1 on an industry it wasn't written for. This task writes no code.
- `examples/trucking/PROMPT.md` is a one-page main prompt: a small trucking company, its shippers and drivers, a bank, a fuel-card issuer and a factoring company.
- `examples/trucking/manifest.yaml` holds only its `institutions:` section: the bank, the fuel-card issuer and the factoring company.
- `examples/trucking/schemas/` holds those institutions' table schemas.
- The doc's two coverage tables gain the trucking tables and money flows.

**Acceptance criteria:**
- [x] Every column of every trucking table has a source from the vocabulary. Any addition the vocabulary needs is written up for the user, not quietly added.
- [x] Each trucking behavior maps to a mechanism's config, an act tool or a staff decision: factoring advances, factoring fees, reserve releases, and fuel-card statements and autopay
- [x] The coverage tables cover both industries

**Verification:**
- [ ] Manual: the user reviews the trucking declarations at Checkpoint 0

**Dependencies:** Task 1
**Files likely touched:** `examples/trucking/{PROMPT.md,manifest.yaml,schemas/}`, `docs/declaring-an-institution.md`
**Estimated scope:** S (design files only)

## Checkpoint 0: Decisions and language (after Tasks 0-1b)
- [ ] The user has approved the SPEC diff and the declaration language
- [ ] The user has decided each trucking addition T1-T6 (`docs/declaring-an-institution.md` section 8)
- [ ] Any mechanism or act-tool change the user accepted is written into SPEC.md, and into the tasks that build it (D8: P1-P8, including the market prompt in SPEC's manifest excerpt for P7 and the `receiving_account` default for P8; and each accepted T1-T6, with a new Phase 5 task for the advance mechanism before Task 47 if T5 is accepted)
- [ ] SPEC's Manifest Shape excerpt for `institutions` matches the language

---

## Phase 1: Foundation and tracer bullet

## Task 2: Project scaffold, CLI and the neutrality test

**Description:** Set up a uv project for Python 3.12.
- **Runtime dependencies:** `pydantic` v2, `PyYAML`, `typer`, and `jsonschema` if D4d is confirmed.
- **Dev dependencies:** `pytest`, `pytest-cov`, `pytest-asyncio`, `hypothesis`, `ruff`, `mypy` and `types-PyYAML`.
- **CLI:** a `worldgen` console script backed by an empty typer app.
- **Tooling:** ruff and `mypy --strict` configured in `pyproject.toml`.
- **`.gitignore`:** replace the stale `worlds/*/out/` with `worlds/*/runs/` and `worlds/*/authoring/`.

`tests/test_engine_neutral.py` reads every YAML file under `examples/` with PyYAML. It collects these names:
- institution ids, and the names of institution entities
- payment method names
- relationship kinds

The test fails if any of these appears as a whole word in an identifier or string literal under `worldgen/`.

**Acceptance criteria:**
- [ ] `uv sync` succeeds from a clean checkout, and `uv run worldgen --help` exits 0
- [ ] The gate passes, with the 90% coverage threshold active from the start
- [ ] The neutrality test passes on the empty package, and fails on a planted string literal that names a payment method from `examples/`

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/test_cli.py tests/test_engine_neutral.py`
- [ ] Gate passes
- [ ] Manual: `uv run worldgen --help`

**Dependencies:** Checkpoint 0
**Files likely touched:** `pyproject.toml`, `worldgen/__init__.py`, `worldgen/cli.py`, `.gitignore`, `tests/test_engine_neutral.py`
**Estimated scope:** S

## Task 3: Manifest models: world, config, nodes, entities, accounts, access

**Description:** Define frozen pydantic v2 models:
- `World`: name, start, end, currency, `schema_version`, optional `rng_seed`.
- `Config`: model, effort, `max_tool_calls_per_turn` and `policies`.
- `Policies` (D7): one field per policy, typed by that policy's options and defaulting to our preference. This task adds `default_chapter` (`worldgen/policies/default_chapter.py`, D5j); later tasks add theirs. A test fails if a file in `worldgen/policies/` has no docstring starting "Our preference:" or no field on `Policies`.
- `Node`: id, role (narrator, actor, staff or market), parent, `stands_for`, prompt, brief (D5e), `next_review`.
- `Entity`: id, kind, name, descriptors, `fields` (D5c).
- `Account`: id, holder, `at`, kind, name, methods, opening, limit, rate, linked.
- `Access`: node, account, methods.
- `Manifest`: the root, loaded from YAML.

Money fields parse from 2dp strings to `Decimal` and reject floats. Unknown fields are rejected.

Start `docs/manifest-reference.md`, and add a test that fails if any model field is undocumented.

Write `examples/tracer/manifest.yaml`, over 2021-03-22..2021-04-05:
- **Narrators:** `n_root`, the founder's life, and under it `n_company`, which stands for `co_self` and has `next_review: 2021-03-29`. `n_root` sets no review date, so its first review is the default, 2021-04-01.
- **Actors:**
  - under `n_company`: `n_morgan`, the ops manager, with `ach` and `wire` access on X0666; and `n_acme`, a customer
  - under `n_root`: `n_landlord`
- **Staff:** `n_mercury`, outside the tree.
- **Entities:** `co_self`, `p_morgan`, `cust_acme`, `ent_landlord` and `inst_mercury`.
- **Accounts:** `a_x0666` at Mercury, plus Acme's and the landlord's banks, which are tracked but not rendered.

**Acceptance criteria:**
- [ ] The tracer manifest loads and survives a YAML round trip
- [ ] A float amount, an unknown field or a wrong type fails with an error naming the YAML path, and an undocumented model field fails the docs test
- [ ] mypy strict passes with no `Any` leaking out of the YAML layer

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/manifest tests/docs`
- [ ] Gate passes

**Dependencies:** Task 2
**Files likely touched:** `worldgen/manifest/{world,config,policies,node,entity,account,access,manifest}.py`, `worldgen/policies/default_chapter.py`, `examples/tracer/manifest.yaml`, `docs/manifest-reference.md`
**Estimated scope:** M (small model files)

## Task 4: Manifest models: tables and column sources

**Description:** Model a declared table in the language approved at Checkpoint 0:
- its schema path
- its row source: per movement, per statement, per record event or per split leg
- its filter, on action, payment method and account
- its columns

Each column source is parsed into a typed source from the vocabulary: event fields, account fields, party fields, statement fields, counters, constants and value maps. Each typed source knows its value type, which Task 8 checks against the table's schema.

**Acceptance criteria:**
- [ ] Every table declaration in `examples/saas_startup` and `examples/trucking` loads as a table model and round-trips
- [ ] A column source outside the vocabulary, or a filter on an unknown field, fails with a pointer
- [ ] Every source kind is documented in the manifest reference

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/manifest tests/docs`
- [ ] Gate passes

**Dependencies:** Task 3
**Files likely touched:** `worldgen/manifest/{table_decl,row_source,column_source}.py`
**Estimated scope:** S

## Task 4b: Manifest models: institutions

**Description:** Model an institution declaration:
- **The institution:** its id (its entity), `calendar`, `methods` (the settlement rules per payment method), `mechanisms`, and `tables` made of Task 4's table models.
- **Mechanism configs:** one config model per generic mechanism, under `worldgen/manifest/mechanisms/`. Their behavior lands in the mechanism tasks. Defining every config now lets every declaration from Tasks 1 and 1b load from the start.

The tracer declares Mercury with three payment methods (`ach`, `wire` and `book`), the settlement and descriptors mechanisms, and one table, `mercury_transactions`, whose schema is copied into `examples/tracer/schemas/`.

**Acceptance criteria:**
- [ ] The `institutions` sections of `examples/saas_startup` and `examples/trucking`, and the tracer's, load and round-trip
- [ ] An unknown mechanism or an unknown calendar fails with a pointer
- [ ] Every mechanism config model is documented in the manifest reference

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/manifest tests/docs`
- [ ] Gate passes

**Dependencies:** Task 4
**Files likely touched:** `worldgen/manifest/{institution,method_rules}.py`, `worldgen/manifest/mechanisms/*.py`, `examples/tracer/{manifest.yaml,schemas/}`
**Estimated scope:** M (small model files)

## Checkpoint 1a: The declarations load (after Tasks 2-4b)
- [ ] Gate passes
- [ ] Every declaration from Tasks 1 and 1b loads as a model, and the neutrality test reads its names

## Task 5: Manifest models: relationships, terms, catalog, stories, noise

**Description:**
- **`Relationship`:** id, parties, kind, `written_by`, handlers, prompt, and optional terms.
- **`Terms`:**
  - payer and payee
  - direction: `push` or `pull`
  - payment method
  - amount: fixed, or omitted so the prompt decides
  - schedule: a list of dates, or a recurrence (`every: day|week|month|quarter|year`, with `day` as one day or a list such as `[10, 26]`, plus `from` and an optional `until`)
  - optional `to_account`: the payee's receiving account, read under policy `receiving_account: named`
- **`CatalogEntry`:** id, category, price range and descriptors. Each entry is also an entity.
- **`Story`:** id, `written_by` and steps. Each step has a day, an actor and an intent, and optionally a counterparty and an amount.
- **`Noise`:** a scope (world, node, relationship, story or step) plus a prompt.

The tracer manifest gains two relationships:
- `r_lease`: `co_self` pays `ent_landlord` $7,000.00 by `ach` (push) on the 1st of each month. `n_morgan` handles it, and `n_root` wrote it.
- `r_acme`: `cust_acme` pays `co_self` $1,200.00 by `ach` (push) on the 25th of each month. `n_company` wrote it.

**Acceptance criteria:**
- [ ] The extended tracer manifest loads and round-trips, and a terms block with no amount loads
- [ ] A schedule with both dates and a recurrence, or a direction other than `push` or `pull`, fails with a pointer
- [ ] A handler entry for an entity that isn't a party to the relationship fails with a pointer

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/manifest tests/docs`
- [ ] Gate passes

**Dependencies:** Task 3
**Files likely touched:** `worldgen/manifest/{relationship,terms,schedule,catalog_entry,story,noise}.py`, `examples/tracer/manifest.yaml`
**Estimated scope:** M (small model files)

## Task 6: Manifest models: seed and mandates

**Description:** The `Seed` model holds the world's state at `start`:
- **`in_transit`:** seed events, each with an id, day, action, source, destination, payment method, amount, arrival date and cause.
- **`open_obligations`:** each with a relationship, due date, amount and cause.
- **`history`:** per relationship, `since`, `paid_through` and `cycles_billed`.
- **`mandates`:** each `Mandate` names a payer account, a payee and its payment methods.
- **`institutions`:** each institution's state, keyed by mechanism, in the shapes Task 1 set: counters, unpaid statements, pending balances.

The tracer gains a seed:
- An ACH from Acme's bank to X0666, initiated 2021-03-19 and arriving 2021-03-23, with the cause "Acme's late February payment".
- History for `r_lease` (since 2020-07-01, paid through 2021-03-31) and for `r_acme` (since 2020-10-25, 5 cycles billed).

**Acceptance criteria:**
- [ ] The tracer manifest with its seed loads and round-trips
- [ ] Seeded institution state for a mechanism the institution doesn't declare fails with a pointer
- [ ] A mandate that names no payment method fails with a pointer

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/manifest tests/docs`
- [ ] Gate passes

**Dependencies:** Tasks 4b, 5
**Files likely touched:** `worldgen/manifest/{seed,mandate}.py`, `examples/tracer/manifest.yaml`
**Estimated scope:** S

## Task 7: `worldgen validate`: references, tree, time range

**Description:** Three validators, one file each:
- **manifest_refs** checks references from:
  - node parents and `stands_for`
  - account holders, `at` and `linked`
  - access nodes and accounts
  - mandate accounts and payees
  - relationship parties, handlers and `written_by`
  - catalog parties
  - story actors and `written_by`
  - noise scopes
  - institution ids, which must name entities of kind `institution`
- **tree** checks that:
  - there is exactly one root, and it is a narrator
  - there are no cycles
  - every parent is a narrator, and every actor is a leaf
  - every staff node stands for an institution and has either no parent or a narrator parent
  - there is at most one market node, and it has no parent
  - only narrators have a `next_review`
- **time_range** checks that story steps and term dates fall inside the world range, and that each `next_review` falls after the start day and no later than the end.

`worldgen validate <manifest>` prints one error per problem, each with a pointer (for example `relationships[3].handlers.co_self: unknown node 'n_jordn'`), and exits 1 if there are any.

**Acceptance criteria:**
- [ ] One fixture manifest per error class fails with the exact pointer in its message
- [ ] The tracer manifest validates with exit code 0
- [ ] `worldgen/validators/` has 100% line coverage

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/validators tests/test_cli.py`
- [ ] Gate passes
- [ ] Manual: `uv run worldgen validate examples/tracer/manifest.yaml`

**Dependencies:** Task 6
**Files likely touched:** `worldgen/validators/{manifest_refs,tree,time_range}.py`, `worldgen/cli.py`, `tests/fixtures/manifests/`
**Estimated scope:** M

## Task 8: `worldgen validate`: payment methods and table columns

**Description:** Two more validators that `validate` runs:
- **methods** checks that:
  - every payment method named by an account, access grant, mandate or terms block is declared by some institution
  - an account at an institution supports only methods that institution declares
  - an access grant's methods are a subset of its account's methods
- **table_columns** checks that every declared column's source exists in the vocabulary, that its type fits the column in the table's JSON Schema, and that every required column has a source (SC1).

**Acceptance criteria:**
- [ ] A method no institution declares, or an access grant wider than its account, fails with a pointer
- [ ] A column whose source type doesn't fit its schema column (a date source for a money column), or a required column with no source, fails with a pointer
- [ ] The tracer and every declaration from Tasks 1 and 1b pass

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/validators`
- [ ] Gate passes

**Dependencies:** Task 7
**Files likely touched:** `worldgen/validators/{methods,table_columns}.py`, `tests/fixtures/manifests/`
**Estimated scope:** S

## Checkpoint 1b: The manifest validates (after Tasks 5-8)
- [ ] Gate passes
- [ ] `validate` passes the tracer and fails every error fixture with a pointer
- [ ] Every declaration from Tasks 1 and 1b passes `table_columns`

## Task 9: Clock, calendars, Rng and money

**Description:**
- **`Clock`:**
  - Maps dates to day indices from the world start, negative for the seed's past.
  - Answers business-day questions for a named calendar (D5m). `us_federal` holds the Federal Reserve holidays, computed in code with no added dependency; on it, a Saturday holiday does not close the preceding Friday. `every_day` has no closed days.
  - Gives the default review date for each option of policy `default_chapter` (D5j).
- **`Rng`:** wraps `random.Random` with the optional best-effort `rng_seed`. It is the only source of randomness for mechanisms, and it also generates UUIDs.
- **`money`:** helpers that quantize `Decimal` to cents, parse and format 2dp strings, and raise on float input.

**Acceptance criteria:**
- [ ] hypothesis: on `us_federal`, `add_business_days(d, n)` never lands on a weekend or holiday and is at least d+n calendar days; a pre-start date maps to a negative index and back
- [ ] Known dates hold:
  - 2021-01-01 and 2021-07-05 are closed, 2021-12-24 is open and 2022-06-20 is closed
  - the `month` default after 2021-03-22 is 2021-04-01, and after 2021-04-01 is 2021-05-01
  - the `week` default after Friday 2021-03-26 is Monday 2021-03-29
- [ ] `format(Decimal("-642.2")) == "-642.20"`, and float input raises `TypeError`

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/engine/test_clock.py tests/engine/test_rng.py tests/test_money.py`
- [ ] Gate passes

**Dependencies:** Task 2
**Files likely touched:** `worldgen/engine/{clock,calendars,rng}.py`, `worldgen/money.py`
**Estimated scope:** S

## Task 10: Accounts, events and ledger

**Description:**
- **The account registry** is built from the manifest's accounts, plus:
  - an implicit receiving account for each entity with none (D5a)
  - one clearing account per declared payment method (D5b)
  - `world_boundary`

  An account with a limit can go negative, down to its limit.
- **`Event`** is frozen, with SPEC's fields plus `memo` and `details` (D5c): id, day, action, `source_account`, `dest_account`, amount, method, cause, turn (or mechanism name), links, memo and details. The amount is a non-negative `Decimal`, and it is zero only for record events.
- **`EventLog`** appends to `events.jsonl` and flushes after every write.
- **`Ledger`** derives each account's balance from events.

**Acceptance criteria:**
- [ ] hypothesis: for any sequence of events, the balances of all accounts (including clearing accounts and `world_boundary`) sum to 0
- [ ] `events.jsonl` round-trips exactly, with amounts as 2dp strings and seed days as negative indices
- [ ] An event with a negative or float amount is rejected

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/events tests/engine/test_accounts.py`
- [ ] Gate passes

**Dependencies:** Tasks 3, 9
**Files likely touched:** `worldgen/engine/accounts.py`, `worldgen/events/{event,event_log,ledger}.py`
**Estimated scope:** S

## Task 11: Run directory, `run.json` and `log.jsonl`

**Description:**
- **`run_id`:** a sortable UTC timestamp plus a 3-character suffix.
- **`RunMeta`** (`run.json`): status (running, done, failed or cancelled), start and end times, pid, counts, manifest sha256 and `parent_run`.
- **`RunLog`:** appends `{seq, ts, day, kind, ...}` to `log.jsonl` and flushes after every entry.
- **`RunStore`:** creates the run directory with a copy of `manifest.yaml` and a `prompts.json` snapshot (every prompt keyed by owner, with its content-hash revision id), and lists and opens runs.

A run context sets `done` on success and `failed` on any exception. This task adds two log entries:
- `run_started`, which lists every node of the starting tree (id, role, parent, `stands_for`), so a followed log opens with the seed agents (D6)
- `run_finished`

**Acceptance criteria:**
- [ ] An exception inside a run leaves a readable partial `log.jsonl` and `status: failed`
- [ ] Two runs of one manifest create two sibling directories, and editing the source manifest afterward leaves both byte-identical (hash test)
- [ ] `seq` is strictly increasing, and the file is valid JSONL after every append

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/runs tests/sinks`
- [ ] Gate passes

**Dependencies:** Task 3
**Files likely touched:** `worldgen/runs/{run_id,run_meta,run_store}.py`, `worldgen/sinks/run_log.py`, `worldgen/runs/entries/{run_started,run_finished}.py`
**Estimated scope:** M

## Task 12: Llm interface and `FakeLlm`

**Description:**
- **The `Llm` protocol:** async `create(LlmRequest) -> LlmResponse`. The types mirror the Messages API with tool use:
  - **Request:** system, tools (name, description, input schema), and messages made of text, `tool_use` and `tool_result` blocks.
  - **Response:** content blocks, stop reason, and usage including cache read and write tokens.
- **`TurnMeta`:** each request carries one (node id, role, day, turn id, call index), so fakes can answer without parsing prose.
- **`FakeLlm`:** either runs a scripted callable or replays recorded whole-turn fixtures keyed by `TurnMeta`. It records every call and raises on a fixture miss.

**Acceptance criteria:**
- [ ] Replay returns the recorded response for a matching request and raises on a miss
- [ ] A scripted fake can return several `tool_use` blocks in one response
- [ ] No module outside the CLI and simulation wiring imports a concrete `Llm` (import test)

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/llm`
- [ ] Gate passes

**Dependencies:** Task 2
**Files likely touched:** `worldgen/llm/{base,fake}.py`
**Estimated scope:** S

## Checkpoint 1c: Engine types (after Tasks 9-12)
- [ ] Gate passes
- [ ] The core types read cleanly together before the loop builds on them: `Event`, the account registry, `LlmRequest` and `LlmResponse`, and the log entry shape

## Task 13: Tool base class and `AgentLoop`

**Description:**
- **`Tool`:** name, description, a strict pydantic input model exported as JSON schema, and `run(input, view) -> result`, which returns what the model sees. Invalid input comes back to the model as an error result; it does not raise.
- **`AgentLoop.run_turn(node, role, brief)`:**
  1. Send the role's system prompt and tools, then the brief.
  2. Execute every `tool_use` block in the response, and send all the results back together, in order, in one message.
  3. Repeat until a response has no tool call, or the turn reaches `max_tool_calls_per_turn`.

  An optional follow-up hook can continue the turn once with an extra message; Task 18 uses it. Each turn is a fresh conversation.
- **Logging:** `turn_started`, `turn_finished`, `llm_call` (request, response, prompt revision ids) and `tool_call` (tool, input, result).

**Acceptance criteria:**
- [ ] Parallel tool calls produce one result message, and the turn stops at exactly `max_tool_calls_per_turn` (hypothesis over scripted fakes)
- [ ] The system prompt and tools are byte-identical across two turns of the same role, and they come before the brief
- [ ] `agents/loop.py` has 100% line coverage

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/agents tests/tools`
- [ ] Gate passes

**Dependencies:** Tasks 11, 12
**Files likely touched:** `worldgen/agents/loop.py`, `worldgen/tools/tool.py`, `worldgen/runs/entries/{turn_started,turn_finished,llm_call,tool_call}.py`
**Estimated scope:** M

## Task 14: Compiler: obligations and story steps

**Description:** `Compiler` turns a `Manifest` into a `Schedule` with two parts.

**Obligations by day,** expanded from relationship terms. Each obligation has:
- an id, its relationship and its direction
- the payer and payee
- an amount, or none if the prompt decides
- a due day and a payment method
- a handler:
  - push obligations go to the payer's handler, and pull obligations to the payee's handler
  - the handler comes from the relationship's `handlers`, or else is the node that stands for the party
  - a catalog party's handler is the market node

Seed history removes obligations already met: those on or before `paid_through`, and those within `cycles_billed`. Seed `open_obligations` are added on their due dates.

**Story steps by day,** grouped by actor.

The date-list and recurrence expanders are one file each. Obligations are clipped to the world range. The compiler can also add a single relationship to an existing schedule, which Task 30 needs.

**Acceptance criteria:**
- [ ] In the tracer, `r_lease` yields one obligation on 2021-04-01, handled by `n_morgan`, and `r_acme` yields one on 2021-03-25, handled by `n_acme`
- [ ] A pull term gives its obligation to the payee's handler, or to the market node for a catalog payee, and `day: [10, 26]` yields two obligations a month
- [ ] A monthly term from 2020-07-01 with `paid_through: 2021-03-31` yields its first obligation on 2021-04-01, and a seed open obligation appears on its due date

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/compiler`
- [ ] Gate passes

**Dependencies:** Tasks 6, 9
**Files likely touched:** `worldgen/compiler/{compiler,obligation,schedule}.py`, `worldgen/compiler/expanders/{dates,recurrence}.py`
**Estimated scope:** M

## Task 15: Clearinghouse and the settlement mechanism

**Description:**
- **`institutions/mechanisms/settlement.py`** reads each payment method's rules from the declaration: the settlement range in days, whether it counts business days or calendar days, whether it settles on weekends, and its calendar. It picks a settle day with `Rng`.
- **`engine/clearinghouse.py`** handles money in flight:
  - `enqueue` emits the initiation event from the source account to the method's clearing account, under the rules of the institution that policy `settlement_rules` picks (D5b; build and test all three options).
  - `settle(day)` emits a linked settlement event, from the clearing account to the destination, for everything due that day.
  - `in_flight(day)` reports what is still pending.
  - A held item (Task 38) settles only after it is released.

**Acceptance criteria:**
- [ ] hypothesis: nothing settles before initiation plus the minimum delay or after the maximum, and nothing settles on a closed day unless the method allows it
- [ ] Clearing accounts net to zero once everything has settled, and a payment with no institution on either side settles the same day
- [ ] `engine/clearinghouse.py` and `institutions/mechanisms/settlement.py` have 100% line coverage

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/engine/test_clearinghouse.py tests/institutions/mechanisms`
- [ ] Gate passes

**Dependencies:** Tasks 4b, 10
**Files likely touched:** `worldgen/engine/clearinghouse.py`, `worldgen/institutions/mechanisms/settlement.py`
**Estimated scope:** S

## Checkpoint 1d: A scripted turn, a schedule and settlement (after Tasks 13-15)
- [ ] Gate passes
- [ ] A scripted `FakeLlm` turn runs through `AgentLoop` with parallel tool calls, and every call is logged
- [ ] The tracer compiles into its obligations, and the settlement suite is green

## Task 16: Act tools, part 1: validation, reservation and `pay`

**Description:** An act tool is a `Tool` whose input always includes `cause`, with optional `memo` and `details` (D5c). `ActMenu` discovers the act tools in `tools/act/`, so adding one needs no registry edit.

Every call is checked on the spot:
- The tool is in the role's set, and its input parses.
- The actor's entity holds the source account, or the actor has access to it with that payment method.
- The account supports the method.
- Funds are available under policy `available_funds` (D5d; build and test both options).

A call that passes reserves its funds and is enqueued in the clearinghouse within one synchronous step. A call that fails returns its reason as the tool result, logs `action_rejected`, and emits nothing.

`pay` pushes money from an account the actor can use, by a payment method, to one or more parties, with an amount for each. Each payment lands in the account policy `receiving_account` picks (D5a): by default the party's first account that supports the method; under `named`, the `to_account` the call gives, with a refund going back to the account it came from, and a call that names none when several fit is rejected with the choices. It may point to an obligation, or to an earlier event it returns (a refund), which it links.

**Acceptance criteria:**
- [ ] An overdraft attempt, or a payment by a method the actor's access doesn't grant, returns its reason within the same turn, logs `action_rejected` and leaves no event
- [ ] Two concurrent turns spending from one account cannot overdraw it (`asyncio.gather` test), and an account with a limit stops at its limit
- [ ] A payment to three parties emits three movements, and a refund links the event it returns

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tools/act`
- [ ] Gate passes

**Dependencies:** Tasks 8, 13, 15
**Files likely touched:** `worldgen/tools/act/{act_tool,act_menu,pay}.py`, `worldgen/engine/reservations.py`, `worldgen/runs/entries/action_rejected.py`
**Estimated scope:** M

## Task 17: Node tree, `NodeView` and read tools

**Description:**
- **`tree/nodes.py`** is the live tree: parent, children, role, the entity each node stands for, and subtree queries.
- **`NodeView`** is the only path from a brief or a read tool to world state. It covers the node's entity's accounts, the accounts it has access to, its obligations and its own history.
- **Two read tools:**
  - `my_balances` shows posted and available balances.
  - `my_obligations` shows due, overdue, and upcoming items within policy `obligation_horizon_days` (D3).

**Acceptance criteria:**
- [ ] `n_morgan`'s `my_obligations` on 2021-04-01 lists the rent obligation, and `n_landlord`'s doesn't
- [ ] `n_morgan`'s `my_balances` shows Acme's 03-25 payment, made with `pay` and settled by the clearinghouse, only after it settles
- [ ] A read tool cannot reach an account the node has no access to (test through `NodeView`)

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tree tests/agents tests/tools/read`
- [ ] Gate passes

**Dependencies:** Tasks 14, 16
**Files likely touched:** `worldgen/tree/nodes.py`, `worldgen/agents/node_view.py`, `worldgen/tools/read/{my_balances,my_obligations}.py`
**Estimated scope:** M

## Task 17b: Actor briefs and the actor role

**Description:**
- **`briefs.py`** builds an actor's brief from ordered sections:
  1. the prompt, with its revision id
  2. the chapter brief
  3. noise in scope (empty until Task 36)
  4. today's items: obligations as policy `obligations_in_brief` picks (D3; due today and overdue by default, plus upcoming under `with_upcoming`), story steps, and balance changes since the last turn

  `turn_started` logs the brief along with its revision ids.
- **The actor role** is a system template plus a tool set: the act tools from Task 16 and the read tools from Task 17. Later tasks add tools to it.

**Acceptance criteria:**
- [ ] `n_morgan`'s brief on 2021-04-01 lists the rent obligation among today's items, and `n_landlord`'s brief that day doesn't
- [ ] The sections come in order, and `turn_started` records the brief with its prompt revision id
- [ ] Two actors' turns send byte-identical system prompts and tools, and differ only in their briefs

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tree/test_briefs.py tests/agents`
- [ ] Gate passes

**Dependencies:** Task 17
**Files likely touched:** `worldgen/tree/briefs.py`, `worldgen/agents/roles/actor.py`, `worldgen/agents/templates/actor.md`
**Estimated scope:** S

## Task 18: Answering obligations

**Description:** The `answer_obligation` act tool answers one or many obligations in a single call. Each answer has a decision (`pay`, `collect`, `pay_late` with a new day, `short_pay` with an amount, `skip`, `dispute`, `cancel` or `change`) and a `cause`.
- A paying answer runs `pay` from an account the handler names, with the obligation's payment method, validated like any act tool. `collect` answers arrive in Task 33.
- `pay_late` moves the obligation to the new day, where it returns to the handler's brief.
- The tool call records whether the answer is a deviation (D5g).

`engine/obligations.py` tracks open obligations per handler. If a turn ends with a due obligation unanswered, the loop continues once with a message listing only the missing items. If they are still unanswered, the engine logs `obligation_unanswered` and renders nothing for them. This is policy `unanswered_obligation`'s default, `ask_once`; under `log_only` the engine logs at once. Payment under a relationship whose terms give a `to_account` lands there under `receiving_account: named`.

Also add `tests/support/as_agreed.py`, the scripted policy described in the plan. It is the offline driver for whole worlds.

**Acceptance criteria:**
- [ ] A missing item gets exactly one follow-up listing only that item, then an `obligation_unanswered` entry naming the obligation and the handler
- [ ] `pay_late` by 3 days brings the item back to the brief 3 days later, and it is paid then
- [ ] No event pays an obligation without an `answer_obligation` call (unit form of SC12)

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/engine/test_obligations.py tests/tools/act`
- [ ] Gate passes

**Dependencies:** Tasks 16, 17b
**Files likely touched:** `worldgen/engine/obligations.py`, `worldgen/tools/act/answer_obligation.py`, `worldgen/runs/entries/obligation_unanswered.py`, `tests/support/as_agreed.py`
**Estimated scope:** M

## Checkpoint 1e: An obligation answered (after Tasks 16-18)
- [ ] Gate passes
- [ ] In a test without the day loop, `n_morgan`'s scripted turn on 2021-04-01 reads its brief, answers the rent obligation with `pay`, and the payment settles through the clearinghouse

## Task 19: Day loop

**Description:** `engine/day.py` runs one simulated day in the order set in the plan:
1. The reviews due that day (an empty step until Task 26).
2. Build briefs.
3. Run every turn in parallel, in a `TaskGroup`. Only actors take turns for now; the market and staff start in Tasks 37 and 38.
4. Close the day: settle the clearinghouse, run each institution's day-close hook (empty until Task 20), and move tomorrow's items into place.

`engine/engine.py` loops over the world range. Policy `idle_turns` (D3) is read from `config.policies`, and both options are built and tested.

This task adds two log entries: `event`, one per event, by id; and `day_closed`.

**Acceptance criteria:**
- [ ] Two actors' turns on the same day are in flight at the same time (barrier test with `FakeLlm`)
- [ ] An event created on day d is visible to another node no earlier than d+1
- [ ] Every event names its turn or a mechanism

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/engine/test_day.py tests/engine/test_engine.py`
- [ ] Gate passes

**Dependencies:** Tasks 11, 18
**Files likely touched:** `worldgen/engine/{day,engine}.py`, `worldgen/runs/entries/{event,day_closed}.py`
**Estimated scope:** M

## Task 20: Institutions and tables: movement rows

**Description:**
- **`institutions/institution.py`** runs one declared institution at day close, on its own accounts: its mechanisms in one fixed engine order, written down here so the Phase 5 lanes don't conflict, then its tables.
- **`institutions/tables.py`** builds a declared table's rows from events, in the Task 1 language. This task supports movement rows: one row per initiation and settlement pair, rendered at settlement. It also handles filters, column sources, value maps and the sign convention. Every row is checked against the table's JSON Schema as it renders (D4d).
- **`mechanisms/descriptors.py`** is the class in SPEC's Code Style. It renders a party's statement name from its `descriptors` and fills `{ref}` from `Rng`.
- **The `JsonFiles` sink** keeps each table keyed by row id (re-rendering an id replaces the row) and writes `<institution>/<table>.json` at each day close. Every render logs `row_rendered` with its linked event ids.

In the tracer, Mercury renders `mercury_transactions` entirely from declared columns:
- `transaction_date` is the initiation day and `posted_date` is the settlement day.
- The amount is signed.
- `transaction_type` is a value map on the payment method.
- `description` and `counterparty_name` come from descriptors.

**Acceptance criteria:**
- [ ] With `Rng` stubbed, the tracer renders Acme's 03-25 ACH and the 04-01 rent ACH, each posted on a business day no earlier than its initiation, with descriptions from the counterparty's descriptors
- [ ] Every row validates against its schema and has a `row_rendered` entry linking at least one event, and a row that fails its schema fails the run with the table, row and column named
- [ ] The neutrality test still passes, so `worldgen/` names no institution, payment method or table

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/institutions tests/sinks`
- [ ] Gate passes

**Dependencies:** Tasks 8, 19
**Files likely touched:** `worldgen/institutions/{institution,tables}.py`, `worldgen/institutions/mechanisms/descriptors.py`, `worldgen/sinks/json_files.py`, `worldgen/runs/entries/row_rendered.py`
**Estimated scope:** M

## Task 21: Loading the seed

**Description:** `engine/seed.py` loads the seed before day 0:
- **Seed events** go into `events.jsonl` first, with negative days. In-transit items open in their method's clearing account, since opening balances already include them, and they settle on their arrival dates.
- **Seed open obligations** appear in their handlers' briefs from day 0.
- **Seed mandates** are in force. `collect` uses them from Task 33.
- **Seeded institution state** goes to each mechanism as it lands.

A seeded movement that settles on or after `start` renders a row that keeps its seed id and its pre-start initiation date. One that settled before `start` renders none.

`validators/seed.py` (run by `validate`) checks that:
- seed events are dated before `start` and arrive on or after it (SC1)
- their accounts exist
- open obligations name relationships

The engine logs `seed_loaded` with the counts of seed events, open obligations and mandates.

**Acceptance criteria:**
- [ ] The tracer's seeded ACH from Acme renders in `mercury_transactions` with `transaction_date` 2021-03-19, `posted_date` 2021-03-23 and its seed id
- [ ] Conservation holds from `start`, counting the in-transit money opening in the clearing account
- [ ] A seed event dated on or after `start`, or arriving before it, fails `validate` with a pointer

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/engine/test_seed.py tests/validators`
- [ ] Gate passes

**Dependencies:** Task 20
**Files likely touched:** `worldgen/engine/seed.py`, `worldgen/validators/seed.py`, `worldgen/runs/entries/seed_loaded.py`
**Estimated scope:** M

## Checkpoint 1f: The tracer runs from its seed (after Tasks 19-21)
- [ ] Gate passes
- [ ] In a test, the tracer runs day by day with `as_agreed` from its seed and writes `mercury_transactions`, with one row per settled movement, the seeded ACH included

## Task 22: `worldgen simulate`

**Description:** `Simulation` connects the manifest, seed, compiler, engine, institutions and sinks inside a `RunStore` run context. `worldgen simulate <manifest> --llm fake:<fixture_dir>` creates `worlds/<world>/runs/<run_id>/` (or a directory set by `--world-dir`) and prints the run directory. The Anthropic backend becomes the default in Task 24.

**Acceptance criteria:**
- [ ] Simulating the tracer with the `as_agreed` policy produces a complete run directory: `run.json`, `manifest.yaml`, `prompts.json`, `log.jsonl`, `events.jsonl` and `inst_mercury/mercury_transactions.json`
- [ ] The run ends with `status: done` and a `run_finished` entry with counts
- [ ] Running it twice gives two separate run directories

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/runs/test_simulation.py`
- [ ] Gate passes
- [ ] Manual: run it and read `log.jsonl`

**Dependencies:** Task 21
**Files likely touched:** `worldgen/runs/simulation.py`, `worldgen/llm/factory.py`, `worldgen/cli.py`
**Estimated scope:** S

## Task 23: `worldgen verify`

**Description:** Validators, one file each:
- **conservation:** for every account, opening balance + sum of its events from `start` = closing balance, and the rendered rows give the same closing balance. All events from `start` sum to zero, counting clearing accounts and `world_boundary`.
- **event_links:** every row links at least one event, with 0 orphans.
- **log_consistency:** every `row_rendered` entry matches a row and vice versa, and every `event` entry matches `events.jsonl` and vice versa.
- **schema:** every row validates against its table's JSON Schema.
- **obligations_answered:** every obligation due within the run has an `answer_obligation` call or an `obligation_unanswered` entry, and no event pays or collects an obligation without such a call (SC12).

`worldgen verify <run_dir>` runs these and the seed validator, prints a report, and exits 1 on any failure.

**Acceptance criteria:**
- [ ] The tracer run verifies clean
- [ ] Each validator catches its corrupted-run fixture: a deleted row, an extra row, a tampered amount, an orphan event, a paid obligation with no answer
- [ ] `worldgen/validators/` has 100% line coverage

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/validators`
- [ ] Gate passes
- [ ] Manual: `uv run worldgen verify <tracer run dir>`

**Dependencies:** Task 22
**Files likely touched:** `worldgen/validators/{conservation,event_links,log_consistency,schema,obligations_answered}.py`, `worldgen/cli.py`
**Estimated scope:** M

## Checkpoint 1: Tracer bullet (after Tasks 22-23)
- [ ] Gate passes
- [ ] `simulate` then `verify` on the tracer world is clean offline, starting from its seed
- [ ] The user has read one run directory and agrees with the log, event, row and brief shapes

---

## Phase 2: Live loop

## Task 24: `AnthropicLlm`, recorder and live tracer smoke test

**Description:** Load the `claude-api` skill before writing this. `AnthropicLlm` uses the async Anthropic client:
- The model and effort come from `config`.
- The system prompt and tools are marked for prompt caching.
- Transient errors (rate limits, overload, 5xx, connection errors) are retried with capped exponential backoff and no cap on attempts, so they never fail a run on their own. Non-transient errors, such as a bad request or failed auth, fail the run.
- Credentials come only from the environment.

`RecordingLlm` wraps any `Llm` and writes whole-turn fixtures for `FakeLlm`. The live smoke test runs the tracer over its full range. This task adds the `anthropic` dependency.

**Acceptance criteria:**
- [ ] `WORLDGEN_LIVE=1 uv run pytest -q tests/live` runs the tracer live, with a clean `verify` and 0 `obligation_unanswered`
- [ ] The recorded fixtures replay the run offline through `FakeLlm`, and the replayed run also verifies clean
- [ ] Simulated 529 and connection errors are retried until the turn completes, and the API key never appears in `log.jsonl`, `run.json` or fixtures

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/llm`, plus the live test above
- [ ] Gate passes

**Dependencies:** Tasks 0 (D4a), 23
**Files likely touched:** `pyproject.toml`, `worldgen/llm/{anthropic_llm,recording,factory}.py`, `tests/live/test_tracer_live.py`
**Estimated scope:** M

## Task 25: `worldgen runs list|show` with a loop-quality summary

**Description:** `runs list <world_dir>` prints every run: time, status, prompt revisions (from `prompts.json` and `prompt_revisions.json`), row counts and deviation counts (D5g).

`runs show <run_dir>` opens with the run's tree (D6): every node at the start, with its role, parent, `stands_for` and prompt revision, then the nodes spawned or retired during the run and the narrator that did it. It then summarises the run:
- turns and LLM calls, by role
- tool calls per turn (mean and max), and turns that hit the cap
- rejected actions by reason
- follow-ups and unanswered obligations
- deviations, messages and spawns
- reviews by trigger, chapter lengths per narrator, and escalations
- report and brief lengths
- rows per table
- tokens (input, output, cache read, cache write) and latency
- wall-clock time per simulated day

These numbers are how the loop gets judged.

**Acceptance criteria:**
- [ ] The tree and the summary are computed from run files alone and work on a copied run directory
- [ ] A run marked `running` whose pid is gone is listed as `failed`
- [ ] The summary numbers match hand-counted values on a fixture run

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/runs/test_run_summary.py`
- [ ] Gate passes

**Dependencies:** Task 22
**Files likely touched:** `worldgen/runs/{run_summary,run_store}.py`, `worldgen/cli.py`
**Estimated scope:** S

## Checkpoint 2: Live loop (after Tasks 24-25)
- [ ] Gate passes
- [ ] A live tracer run reviewed with the user, using `runs show` and `log.jsonl`
- [ ] Decide whether the actor template or tool schemas need changes before building on them

---

## Phase 3: Narrator tree

## Task 26: Reviews, part 1: review dates and reports up

**Description:**
- **Review dates:** `tree/reviews.py` keeps each narrator's next review date. It starts from the manifest's `next_review`, or else from the `default_chapter` date after the start day. Until Task 27, a narrator's next date after a review is the default date after that review day. Each day, before briefs are built, the day loop asks which narrators are due:
  - A narrator due on the same day as one of its ancestors is reviewed as part of the ancestor's review.
  - Reviews of separate subtrees run in parallel.
- **Report turns:** a review starts with a report turn for every actor, and every staff node inside the tree, in the subtree, all in parallel. The report brief asks what happened since the node's last report, and lists the node's own events and obligation answers since then, read through `NodeView`. The node answers with `report_up`. Act tools are rejected in a report turn under policy `report_turn_tools` (D5l); under `all` they run.
- **Reports up:** narrators below the reviewing narrator then take turns level by level, starting from the deepest, with narrators on the same level running in parallel. Each reads `children_reports` and gives its own `report_up`. A child that didn't report shows as "no report" to its parent.
- **Narrator role:** add the narrator system template and tool set. A narrator sees its own prompt and brief, and its children's prompts and reports. `as_agreed` learns to write stock reports.

Log entries: `review_started` (narrator and trigger, `scheduled` or `default`) and `report_written`.

**Acceptance criteria:**
- [ ] In the tracer, `n_company` reviews on 2021-03-29 (trigger `scheduled`) and `n_root` on 2021-04-01 (trigger `default`), each before that day's turns, and `n_morgan`'s report comes before `n_company`'s
- [ ] On 04-01, `n_company`'s default review runs inside `n_root`'s, with one `review_started` entry. On a fixture tree, two sibling narrators due on the same day review in parallel (barrier test).
- [ ] `children_reports` returns only the narrator's own children's reports, and an act tool called in a report turn is rejected with a reason

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tree/test_reviews.py tests/tools`
- [ ] Gate passes

**Dependencies:** Task 19, Checkpoint 2
**Files likely touched:** `worldgen/tree/reviews.py`, `worldgen/engine/day.py`, `worldgen/tools/tree/report_up.py`, `worldgen/tools/read/children_reports.py`, `worldgen/agents/{roles/narrator.py,templates/narrator.md}`, `worldgen/runs/entries/{review_started,report_written}.py`
**Estimated scope:** M (small tool files)

## Task 27: Reviews, part 2: briefs down and `schedule_review`

**Description:** After the reports go up, the reviewing narrator reads its children's reports. It then writes each child's next brief with `brief_child`, and sets its own next review with `schedule_review`, which takes a date and a reason. Briefs then go down the subtree level by level, with narrators on the same level in parallel. Each narrator below writes its children's next briefs and sets its own next review.
- A narrator that sets no date gets the `default_chapter` date after the review day. This is logged as `review_scheduled` with reason `default`.
- A child that gets no new brief keeps its old one. A new brief replaces the old one in an actor's brief from its next turn, which is that same day's turn.
- `my_chapters` returns a narrator's own past chapters: the reports it read and wrote, the briefs it wrote and the review dates it set.
- `as_agreed` writes stock briefs and sets no review date.

Log entries: `brief_written` and `review_scheduled`.

**Acceptance criteria:**
- [ ] In `n_root`'s review on 04-01, the root writes its briefs before `n_company` writes any, and each actor's turn that day carries the brief its parent has just written
- [ ] A date set with `schedule_review` brings a `review_started` on that date (trigger `scheduled`), and a narrator that sets none reviews on the default date (trigger `default`). A date that isn't after today, or that falls past the world end, is rejected with a reason.
- [ ] `brief_child` to a node that isn't the caller's child is rejected with a reason

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tree tests/tools`
- [ ] Gate passes

**Dependencies:** Task 26
**Files likely touched:** `worldgen/tree/reviews.py`, `worldgen/tools/tree/{brief_child,schedule_review}.py`, `worldgen/tools/read/my_chapters.py`, `worldgen/runs/entries/{brief_written,review_scheduled}.py`
**Estimated scope:** M (small tool files)

## Task 28: Escalation

**Description:** `escalate` takes a reason and is a tool for every node with a parent: actors, narrators and staff inside the tree. The reason reaches the caller's parent as an urgent report, which `children_reports` lists first and marks as urgent. Delivery follows policy `escalation_in_review` (D5k). Its default, `read_in_review`:
- If a review that covers the parent is under way, and the parent hasn't read its children's reports yet, the parent reads the escalation in that review.
- Otherwise the parent's next review moves to the next day if it was later, with trigger `escalated` naming the escalating node. Several escalations to one parent bring one review.
- Under `next_day`, every escalation takes the second path.

In that review the parent handles the escalation or escalates to its own parent. The root's call is rejected because it has no parent. The `escalated` entry records the reason and which delivery applied, so `verify` can check SC14 from the log (Task 31).

**Acceptance criteria:**
- [ ] `n_morgan` escalating in its turn on 03-30 brings `n_company`'s review to 03-31, with trigger `escalated` naming `n_morgan`. An escalation to a parent already due the next day changes no date.
- [ ] An escalation in a report turn on 03-29 is read in that same review of `n_company`, and `n_company` escalating in it brings `n_root`'s review to 03-30
- [ ] The root's `escalate` is rejected with a reason, and the urgent report reaches no node other than the parent

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tree/test_reviews.py tests/tools/tree`
- [ ] Gate passes

**Dependencies:** Task 27
**Files likely touched:** `worldgen/tools/tree/escalate.py`, `worldgen/tree/reviews.py`, `worldgen/tools/read/children_reports.py`, `worldgen/agents/roles/{actor,narrator}.py`, `worldgen/runs/entries/escalated.py`
**Estimated scope:** M

## Checkpoint 3a: Reviews offline (after Tasks 26-28)
- [ ] Gate passes
- [ ] Offline with `as_agreed`, the tracer's reviews run in order: report turns, reports up, briefs down, a scheduled and a default date, and an escalation that moves a review

## Task 29: Growing the tree

**Description:** Narrator tools, each taking a list of items and validated on the spot. A call is applied all or nothing, and a rejection names every failing item (D5p). This is policy `list_calls`; build and test `per_item` too.
- `spawn_child`: role, prompt, brief, and optionally `stands_for`. A staff child must stand for an institution.
- `retire_child`: rejected while the node still handles active relationships.
- `create_entity`: includes descriptors and `fields`.
- `open_account`: the holder must be an entity that a node in the caller's subtree stands for, and the methods must be declared by the account's institution.
- `grant_access`: the grantee must be a node in the caller's subtree.

`tree/spawn.py` applies these changes to the live tree, the account registry and the `NodeView`s. When spawned nodes start taking turns:
- A spawned actor or staff node takes its first turn the next day.
- A narrator spawned during a review takes its turn at the next level of that review's briefs-down pass, so it can brief and spawn its own children and set its first review.
- A retired node takes no more turns.

Log entries: `node_spawned` and `node_retired`, each naming the narrator.

**Acceptance criteria:**
- [ ] A hire spawned on day d, with its entity, card account and access in one review, takes its first turn on d+1 with the brief it was given and can pay from that account. A narrator spawned in a review briefs its own children in that same review.
- [ ] Retiring a node that still handles an active relationship is rejected with those relationships listed, and a list call with one bad item applies nothing and names that item
- [ ] Every node added during a run has a `node_spawned` entry naming the narrator

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tree tests/tools/tree`
- [ ] Gate passes

**Dependencies:** Task 27
**Files likely touched:** `worldgen/tree/spawn.py`, `worldgen/tools/tree/{spawn_child,retire_child,create_entity,open_account,grant_access}.py`, `worldgen/runs/entries/{node_spawned,node_retired}.py`
**Estimated scope:** M (small tool files)

## Task 30: Relationships, stories and catalog entries written during a run

**Description:** Three narrator tools, each taking a list under policy `list_calls` (D5p):
- **`write_relationship`** creates, amends (terms, handlers, prompt) or ends a relationship. Every party that is neither an institution nor a catalog party must have a node in the writer's subtree. A new or amended relationship is compiled into obligations from the next day.
- **`write_story`** writes steps for actors in the writer's subtree, dated from the next day and within the world range.
- **`write_catalog`** adds catalog entries, each with a category, a price range and descriptors. They are in the catalog from the next day.

**Acceptance criteria:**
- [ ] A relationship written on day d produces obligations from d+1, never on d
- [ ] A relationship or story that names a node outside the writer's subtree is rejected with a reason
- [ ] Ending a relationship drops its future obligations, and the retire rule from Task 29 then allows retiring the node

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tools/tree tests/compiler`
- [ ] Gate passes

**Dependencies:** Task 29
**Files likely touched:** `worldgen/tools/tree/{write_relationship,write_story,write_catalog}.py`, `worldgen/compiler/compiler.py`
**Estimated scope:** S

## Task 31: Tree-rule and isolation validators

**Description:** Two validators that `worldgen verify` runs on every run.

**tree_rules** (SC14):
- every node except the root has exactly one parent
- every node added during a run has a `node_spawned` entry
- every relationship and story, whether from day 0 or written during the run, was written by a narrator whose subtree holds the nodes it names
- every review has a `review_started` entry naming its trigger
- every escalation is followed, no later than the next day, by a review of its parent: either the review under way that its `escalated` entry names, or a later review whose subtree holds the parent

**isolation** (SC13): no node's `llm_call` requests contain another node's private text. Private text means prompt revisions, notes and chapter briefs. The exceptions are:
- messages sent to the node
- for a narrator, its children's prompts and reports, escalations included

The isolation test plants a unique canary in every node's prompt, notes and brief, then runs the tracer through the `as_agreed` policy.

**Acceptance criteria:**
- [ ] The canary tracer run passes isolation, and a planted leak (one node's brief containing another node's prompt) fails it
- [ ] Each tree rule catches its corrupted-run fixture, including an escalation with no review of its parent by the next day
- [ ] Both validators have 100% line coverage

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/validators`
- [ ] Gate passes

**Dependencies:** Tasks 23, 28, 30
**Files likely touched:** `worldgen/validators/{tree_rules,isolation}.py`, `tests/support/canaries.py`
**Estimated scope:** M

## Checkpoint 3: Narrator tree (after Tasks 29-31)
- [ ] Gate passes
- [ ] A live tracer run over its full range is reviewed with the user. It covers the review dates narrators chose and why, any escalations, the reports and briefs, and any spawns or relationships written.
- [ ] Decide on changes to the narrator template before actor life and institutions build on it

---

## Phase 4: Actor life, the market and staff

## Task 32: Messages and inbox

**Description:** `send_message` takes a recipient node, text, and an optional reference to a relationship, an obligation or a payment. It follows the contact rule. A node can message:
- the handlers on the other side of the relationships it handles
- the market, about a payment it made to a catalog party
- anyone who has messaged it

Messages reach the recipient's inbox the next day and appear among its items. `send_message` is rejected in a report turn under policy `report_turn_tools` (D5l). `my_inbox` reads the inbox, and `message_sent` is logged. The isolation validator learns that delivered messages are an allowed channel.

**Acceptance criteria:**
- [ ] A message sent on day d appears in the recipient's brief on d+1 and not on d
- [ ] A message to a node outside the contact rule is rejected with a reason, and a reply to a node that has messaged the sender is allowed
- [ ] Isolation still passes on a run where nodes exchange messages that quote their own prompts

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/engine/test_inbox.py tests/tools tests/validators`
- [ ] Gate passes

**Dependencies:** Task 31
**Files likely touched:** `worldgen/engine/inbox.py`, `worldgen/tools/talk/send_message.py`, `worldgen/tools/read/my_inbox.py`, `worldgen/runs/entries/message_sent.py`, `worldgen/validators/isolation.py`
**Estimated scope:** M

## Task 33: Mandates and `collect`

**Description:** Three act tools:
- **`authorize`** gives a payee a mandate on one of the actor's accounts, for named payment methods.
- **`revoke`** ends a mandate.
- **`collect`** pulls money under a mandate from a payer's account into an account the caller can use. It is validated like `pay` plus the mandate check, and its settlement rules come from the payee's side under policy `settlement_rules`'s default (D5b).

`authorize` and `revoke` emit record events (D5c). Seed mandates are in force from day 0. `answer_obligation` gains the `collect` decision for pull obligations, and `as_agreed` answers pull obligations with it.

**Acceptance criteria:**
- [ ] A `collect` without a mandate is rejected with a reason and logged as `action_rejected` (SC10)
- [ ] A pull obligation answered with `collect` under a seeded mandate moves the money from the payer's account
- [ ] After `revoke`, the next `collect` under that mandate is rejected

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tools/act tests/engine/test_mandates.py`
- [ ] Gate passes

**Dependencies:** Tasks 18, 21
**Files likely touched:** `worldgen/engine/mandates.py`, `worldgen/tools/act/{authorize,revoke,collect,answer_obligation}.py`, `tests/support/as_agreed.py`
**Estimated scope:** M

## Task 34: Record tools: `bill`, `record_activity` and `annotate`

**Description:** Three act tools that move no money and each emit a zero-amount record event (D5c):
- **`bill`** asks a party for payment under a relationship the caller handles, with an amount, a due day, a memo, `details` and an optional `to_account` (read under policy `receiving_account: named`). The bill goes to the payer's handler as a message, and opens an obligation for that handler on the due day.
- **`record_activity`** records something delivered or used under a relationship (hours, loads, ad spend), with `details`. It reaches the other party's handler the next day, so a vendor can bill from what was used.
- **`annotate`** adds or changes the memo on one of the actor's own past transactions. Its event links the one it changes, and that event's rows re-render with the new memo.

**Acceptance criteria:**
- [ ] A bill sent on day d reaches the payer as a message on d+1 and as an obligation on its due day. Paying it closes it, and a bill on a relationship the sender doesn't handle is rejected.
- [ ] Recorded activity reaches the other party's handler on d+1, and a later bill can cite it
- [ ] An `annotate` re-renders the transaction's row with the new memo, linked to the record event, and annotating another node's transaction is rejected

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tools/act tests/engine/test_obligations.py tests/institutions`
- [ ] Gate passes

**Dependencies:** Tasks 20, 32
**Files likely touched:** `worldgen/tools/act/{bill,record_activity,annotate}.py`, `worldgen/engine/obligations.py`
**Estimated scope:** M

## Checkpoint 4a: Talking and billing (after Tasks 32-34)
- [ ] Gate passes
- [ ] Offline, a Net-30 vendor bills the tracer company. The bill arrives as a message and as an obligation, and `n_morgan` pays it. A landlord on a pull lease collects rent under a seeded mandate.

## Task 35: Timers, notes, history and statements

**Description:**
- `set_timer` (day, note) adds an item to the node's brief on that day.
- `note_to_self` appends to the node's notes.
- `search_my_history` searches the node's own past turns, tool calls, events, messages and notes, by text or date range. It includes the seed's past: seed events on its accounts, and the history of the relationships it handles.
- `my_statement` lists the events on an account the node can use, over a date range, seed events included.

What a node remembers between turns is reached only through these tools.

**Acceptance criteria:**
- [ ] A timer set on day d for d+k fires on exactly d+k
- [ ] A note written on day d is found by `search_my_history` on a later day, and the tracer's `n_morgan` finds Acme's seeded payment in `my_statement`
- [ ] Neither `search_my_history` nor `my_statement` ever returns another node's entries, or an account without access

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tools tests/engine/test_timers.py`
- [ ] Gate passes

**Dependencies:** Tasks 19, 21
**Files likely touched:** `worldgen/engine/timers.py`, `worldgen/tools/self/{set_timer,note_to_self}.py`, `worldgen/tools/read/{search_my_history,my_statement}.py`
**Estimated scope:** M (small tool files)

## Task 36: Noise in briefs

**Description:** Noise prompts are added to the brief of every agent in their scope:

| Scope | Whose briefs |
|---|---|
| world | everyone, including staff and the market |
| node | that node's subtree |
| relationship | the relationship's handlers |
| story | briefs that carry a step of the story |
| step | the brief that carries that step |

Every `turn_started` entry lists the revision ids of the noise in its brief (SC6, first part).

**Acceptance criteria:**
- [ ] Noise scoped to `n_company` appears in the brief of every node under it and of no other node
- [ ] Step-scoped noise appears only on that step's day, in that actor's brief
- [ ] Every `turn_started` entry lists its noise revision ids

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tree/test_briefs.py`
- [ ] Gate passes

**Dependencies:** Task 17b
**Files likely touched:** `worldgen/tree/{briefs,noise_scope}.py`
**Estimated scope:** S

## Task 37: The catalog and the market node

**Description:**
- **`catalog`** searches the catalog by name or category. It is a read tool for actors and the market.
- **`pay` to a catalog party:**
  - It lands in that party's implicit account (D5a).
  - A payment outside the party's price range goes through, and the result says it was unusual (D5o). This is policy `catalog_price_range`; build and test `reject` too.
  - A `pay` to a party that is neither in the world nor in the catalog is rejected, and the reason points to `catalog`.
- **The market role** has its own system template and tools:
  - read: `catalog`, the payments made to catalog parties, `my_inbox` and `my_obligations`
  - act: `pay`, `collect` and `answer_obligation`
  - talk: `send_message`
- **The market's daily turn:** its brief lists the payments made to catalog parties since its last turn, the obligations where a catalog party is the handler's side, and its messages. With this, merchants refund returns, double-charge and reverse, and collect under cards on file.

The isolation validator adds the market's exception: it may see payments made to catalog parties.

**Acceptance criteria:**
- [ ] A pull relationship with a catalog payee gives the market the obligation, and its `collect` under the seeded mandate moves the money
- [ ] The market's briefs and tool results show payments to catalog parties and nothing else of other nodes' state (isolation test with canaries)
- [ ] A payment to an unknown party is rejected, pointing to `catalog`, and an out-of-range payment succeeds with the note

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tools tests/agents tests/validators`
- [ ] Gate passes

**Dependencies:** Tasks 30, 32, 33
**Files likely touched:** `worldgen/tools/read/{catalog,catalog_payments}.py`, `worldgen/agents/{roles/market.py,templates/market.md}`, `worldgen/tools/act/pay.py`, `worldgen/validators/isolation.py`
**Estimated scope:** M

## Checkpoint 4b: Memory, noise and the market (after Tasks 35-37)
- [ ] Gate passes
- [ ] Offline, a catalog merchant collects under a card on file through the market, scoped noise reaches exactly the briefs in its scope, and a timer fires on its day
- [ ] Isolation passes with canaries, the market included

## Task 38: Staff nodes: `flag`, `hold` and `release`

**Description:**
- **The staff role** has its own system template. A staff node sits outside the tree, or, when its institution is at the center of the story, as a leaf under a narrator. A staff node inside the tree also takes report turns and can `report_up` and `escalate`.
- **Daily turn:** the staff brief lists the movements on its institution's accounts since its last turn, its flagged items and open disputes.
- **Tools:**
  - `institution_accounts` reads balances and recent activity on the accounts its institution holds.
  - `flag` marks an item for review.
  - `hold` delays a movement in flight, or a balance, through the clearinghouse hold.
  - `release` frees it.
  - `send_message`.

Staff tools are validated like any act tool.

**Acceptance criteria:**
- [ ] A held movement settles only after its release, on a business day, and conservation holds
- [ ] A staff tool on an account at another institution is rejected
- [ ] On a fixture tree, a staff leaf under a narrator reports up in that narrator's review, and isolation holds for it

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tools/staff tests/agents tests/tree`
- [ ] Gate passes

**Dependencies:** Tasks 20, 32
**Files likely touched:** `worldgen/agents/{roles/staff.py,templates/staff.md}`, `worldgen/tools/staff/{institution_accounts,flag,hold,release}.py`
**Estimated scope:** M

## Task 39: Disputes, `reverse` and `adjust`

**Description:**
- **`dispute`** (actor act tool) contests a past payment the actor made or received. The next day it reaches the staff of the institution policy `dispute_venue` picks (D5b; by default the one whose rules settled the payment, under `payer` the payer's; build and test both), as a flagged item with the actor's reason.
- **`reverse`** (staff) returns a movement, such as a returned wire or a chargeback, as a new movement linked to the original.
- **`adjust`** (staff) posts a fee, a correction, or a duplicate and its reversal, each linked to the item it concerns.

**Acceptance criteria:**
- [ ] A returned wire sends the funds back with a fee posted by `adjust`, both linked to the original, and conservation holds
- [ ] A dispute reaches the right staff node's brief the next day, and reversing it returns the money to the disputer
- [ ] A duplicate posted with `adjust` and later reversed renders two rows, each linked to the original movement

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tools/staff tests/tools/act tests/institutions`
- [ ] Gate passes

**Dependencies:** Task 38
**Files likely touched:** `worldgen/tools/act/dispute.py`, `worldgen/tools/staff/{reverse,adjust}.py`
**Estimated scope:** S

## Checkpoint 4: Staff (after Tasks 38-39)
- [ ] Gate passes
- [ ] The tracer, extended with a Net-30 vendor that bills, a catalog merchant with a card on file, and a large wire held by staff, runs offline and verifies clean, including tree rules and isolation

---

## Phase 5: Mechanisms and institutions

Each mechanism task implements one file in `worldgen/institutions/mechanisms/`, configured by the model from Task 4b. Each runs in the day-close order fixed in Task 20 and is shown on a fixture world, built in the test, that uses one or more of the SaaS declarations from Task 1. Each must keep the neutrality test passing. The payouts lane (Tasks 40-42) and the statements lane (Tasks 43-45) can run in parallel, and Checkpoints 5a and 5b close them.

## Task 40: The split mechanism

**Description:** Splits a movement into legs as the declaration configures them, rounding each leg half up to the cent:
- **Deducting legs** take a fixed amount plus a percentage to the institution's own account (fees), or to a named party (withholding).
- **Add-on legs** are charged on top to the payer (employer contributions).

Each leg links its movement, so tables can render one row per leg. The fixture world shows two splits: Stripe's 2.9% + $0.30 fee on collections into the Stripe balance, and a payroll split with withholding and an employer add-on. Rippling's journal entries also need numbering, so they come together in Task 46.

**Acceptance criteria:**
- [ ] hypothesis over amounts: deducting legs plus the net equal the movement exactly, each fee equals its formula, and money is conserved
- [ ] `stripe_charges` renders `amount`, `fee_amount` and `net_amount` from the split, and every row validates
- [ ] A payroll split renders one row per leg in a fixture table, and its debit and credit legs balance

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/institutions/mechanisms/test_split.py tests/institutions`
- [ ] Gate passes

**Dependencies:** Tasks 33, 34, Checkpoint 4
**Files likely touched:** `worldgen/institutions/mechanisms/split.py`, `worldgen/institutions/tables.py`
**Estimated scope:** M

## Task 41: The hold mechanism

**Description:** Holds funds that arrive in an institution's account, as the declaration configures:
- an availability delay in business days, before funds can be swept or paid out
- a reserve: a percentage held for a period

Seeded pending balances become available on their dates. The fixture world shows Stripe's availability delay.

**Acceptance criteria:**
- [ ] Funds collected on day d are unavailable until d plus the delay in business days, and then become available
- [ ] A reserve is held and released on its date, and conservation holds
- [ ] A seeded pending balance becomes available on its seeded date

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/institutions/mechanisms/test_hold.py`
- [ ] Gate passes

**Dependencies:** Checkpoint 4
**Files likely touched:** `worldgen/institutions/mechanisms/hold.py`
**Estimated scope:** S

## Task 42: The sweep mechanism

**Description:** Moves a balance between linked accounts, by a declared payment method, on one of three triggers:
- a schedule (each business day, or weekly on a given weekday)
- a delay after a statement closes (autopay)
- a balance going negative, which pulls the difference from the linked account

One sweep movement links every movement it carries (charges, fees, refunds), so rows can backfill `payout_id`. A sweep's row updates from `in_transit` to `paid` when it settles. The fixture world shows Stripe payouts into Mercury.

**Acceptance criteria:**
- [ ] Phenomenon 2: N charges, fees and refunds produce one `stripe_payouts` row and one Mercury row (`Deposit - STRIPE`), and the sums agree
- [ ] Phenomenon 1, with `Rng` stubbed: charges on 2021-03-29..31 give `payout_date` 2021-03-30 and `arrival_date` 2021-04-01, and the Mercury row posts on 04-01. A payout still in flight at run end stays `in_transit`.
- [ ] Refunds beyond the balance produce a negative `net_payout_amount` and a Mercury `ACH Debit` pull. A stubbed statement-close signal triggers an autopay sweep after its delay. Conservation holds throughout.

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/institutions/mechanisms/test_sweep.py tests/institutions`
- [ ] Gate passes

**Dependencies:** Tasks 40, 41
**Files likely touched:** `worldgen/institutions/mechanisms/sweep.py`, `worldgen/institutions/tables.py`
**Estimated scope:** M

## Checkpoint 5a: Payouts lane (after Tasks 40-42)
- [ ] Gate passes
- [ ] Phenomena 1 and 2 hold on a fixture world, and conservation holds across fees, holds, payouts and pulls

## Task 43: The statement mechanism

**Description:** Closes statements on a cycle (for example monthly), counting movements by settled or posted date. Each statement has its totals and a running balance per line, and renders statement rows and line rows. It backfills `statement_id` on the movements it covers, signals the close for sweeps, and continues from a seeded unpaid statement. The fixture world shows two tables:
- Ramp's `ramp_statements`
- Mercury's `mercury_statement_line_items`

The tracer gains a Mercury statement.

**Acceptance criteria:**
- [ ] For every statement, `ending_balance = opening_balance + new_charges - payments_and_credits`, and a swipe that settles after the cutoff lands on the next statement (phenomenon 5 at row level)
- [ ] `running_balance` carries over continuously between months and equals the ledger balance at each line
- [ ] The tracer's March statement excludes a payment posted on 04-01

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/institutions/mechanisms/test_statement.py tests/institutions`
- [ ] Gate passes

**Dependencies:** Checkpoint 4
**Files likely touched:** `worldgen/institutions/mechanisms/statement.py`, `worldgen/institutions/tables.py`, `examples/tracer/manifest.yaml`
**Estimated scope:** M

## Task 44: The interest mechanism

**Description:** Credits interest on an account's balance at its annual `rate`, on the basis its declaration sets (the average daily balance or the closing balance), at the end of each cycle. The interest is paid as a movement from the institution's account. The fixture world shows Mercury checking and Treasury. With interest in place, it also renders `mercury_treasury_records`, whose rows are statements with an interest column. The tracer gains interest on X0666.

**Acceptance criteria:**
- [ ] hypothesis: the interest equals the configured formula to the cent
- [ ] Interest posts on the cycle's last day, or on the next open day if the calendar requires it
- [ ] Each Treasury record satisfies `ending = beginning + deposits - withdrawals + interest`

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/institutions/mechanisms/test_interest.py tests/institutions`
- [ ] Gate passes

**Dependencies:** Task 43
**Files likely touched:** `worldgen/institutions/mechanisms/interest.py`, `examples/tracer/manifest.yaml`
**Estimated scope:** S

## Task 45: The numbering mechanism

**Description:** Keeps counters an institution declares:
- a global sequence (journal numbers)
- a sequence per party, with that party's prefix (invoice numbers such as `#FF308C68-0007`)

Counters continue from their seeded values. A number is assigned when its row first renders and is never reused, even when the row re-renders. The fixture world shows Rippling's journal numbers and Stripe's invoice numbers.

**Acceptance criteria:**
- [ ] A per-party counter seeded at `#FF308C68-0007` gives `#FF308C68-0008` next, and a global counter seeded at 17 gives 18
- [ ] Numbers rise without gaps, and re-rendering a row keeps its number
- [ ] Two parties' sequences never interfere

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/institutions/mechanisms/test_numbering.py`
- [ ] Gate passes

**Dependencies:** Checkpoint 4
**Files likely touched:** `worldgen/institutions/mechanisms/numbering.py`
**Estimated scope:** S

## Checkpoint 5b: Statements lane (after Tasks 43-45)
- [ ] Gate passes
- [ ] Over two month ends on a fixture world, statements, statement lines and Treasury records reconcile to the ledger, and counters continue from the seed

## Task 46: The four SaaS institutions in full

**Description:** A fixture world, built in the test, from the `institutions` section of `examples/saas_startup` plus a small cast:
- two subscribers with cards on file at Stripe
- a cardholder with a Ramp card
- a vendor that collects from a stored Ramp card through the market
- two employees paid through Rippling
- a landlord

It runs offline with `as_agreed` from 2021-03-22 to 2021-04-05, across a month end, with a seed that includes Rippling's and Stripe's counters.

**Acceptance criteria:**
- [ ] All ten TARGET_EXAMPLE tables are produced, every row validates against TARGET's schemas, and `verify` is clean
- [ ] Phenomena 1, 2 and 5 hold on the output tables
- [ ] Ramp's autopay pulls the March statement's balance from X0666, and Rippling's 03-26 entry balances and continues the seeded numbering

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/examples/test_saas_institutions.py`
- [ ] Gate passes

**Dependencies:** Tasks 37, 39, 40-45
**Files likely touched:** `tests/examples/test_saas_institutions.py`, `tests/fixtures/worlds/saas_month/`, `examples/saas_startup/manifest.yaml` (only if a declaration needs fixing)
**Estimated scope:** M

## Task 47: `examples/trucking` with no code change

**Description:** Complete `examples/trucking/manifest.yaml` by hand from its `PROMPT.md`:
- a small trucking company with a few shippers and drivers
- a bank, plus the fuel-card issuer and the factoring company declared in Task 1
- relationships with terms
- a seed

It runs on the same engine with no change under `worldgen/`. Anything that turns out to need an engine change is a bug in an earlier task. Fix it in its own commit, record it here, and ask the user first if it adds or changes a mechanism or tool.

**Acceptance criteria:**
- [ ] `validate` exits 0, and an `as_agreed` run over a month verifies clean
- [ ] The fuel-card and factoring tables render and validate against their schemas, and factoring advances and reserve releases appear
- [ ] This task's own commit touches nothing under `worldgen/` (SC8)

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/examples/test_trucking.py`
- [ ] Gate passes
- [ ] Manual: a live 15-day trucking run verifies clean and is skimmed with `runs show`

**Dependencies:** Tasks 24, 40-45
**Files likely touched:** `examples/trucking/manifest.yaml`, `tests/examples/test_trucking.py`
**Estimated scope:** M

## Checkpoint 5: Institutions (after Tasks 46-47)
- [ ] Gate passes
- [ ] Every institution in both examples renders from declarations alone, and the neutrality test passes
- [ ] Review the state of the system with the user before the milestone

---

## Phase 6: First milestone

## Task 48: `examples/saas_startup` manifest and offline baseline

**Description:** Complete `examples/saas_startup/manifest.yaml` by hand over the D1 window (D2):
- **Tree:** `n_root` holds Alex's life. Under it are `n_alex` and `n_company`. Under `n_company` are the departments (engineering, sales, ops and self-serve), each with its actors. One staff node per institution sits outside the tree, and the market node acts for the catalog.
- **Cast:** the five people with Ramp cards and Mercury access as in TARGET_EXAMPLE 3.3; Contoso and the other enterprise customers; the existing self-serve subscribers as actors; and vendors with descriptor variants and `fields`.
- **Institutions, accounts and access:** the four declarations from Task 1, Mercury's three accounts, and the Stripe, Ramp and Rippling accounts.
- **Relationships:** with the terms from TARGET_EXAMPLE section 4. Cards on file and authorized debits are pulls under mandates.
- **Catalog:** the merchants people buy from, with descriptor variants and price ranges.
- **Seed:** TARGET_EXAMPLE section 2.1:
  - the Stripe payout in transit
  - Ramp's unpaid December statement
  - December 30-31 swipes not yet settled
  - counsel's open Net-30 invoice
  - relationship histories and mandates
  - Rippling's and Stripe's counters
- **Stories and noise:** those TARGET_EXAMPLE asks for that fall in the window, such as the Treasury transfers on 01-05 and 01-08.
- **Day-0 briefs** for every node.
- **Review dates:** `next_review` on two narrators inside the window, since the first default review falls after it.

**Acceptance criteria:**
- [ ] `validate` exits 0, and an `as_agreed` run followed by `verify` (including tree rules and isolation) is clean
- [ ] A test confirms every institution, entity and relationship from TARGET_EXAMPLE sections 3 and 4 is present by id, along with every seed item from section 2.1
- [ ] The seeded December swipes render in `ramp_card_transactions` with December `swipe_date`s and January `transaction_date`s

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/examples`
- [ ] Gate passes

**Dependencies:** Tasks 0 (D1, D2), 31, 35, 36, 46
**Files likely touched:** `examples/saas_startup/manifest.yaml`, `tests/examples/test_saas_manifest.py`
**Estimated scope:** M

## Task 49: Live 15-day milestone run

**Description:** Run `saas_startup` live over the D1 window through `RecordingLlm`, once with `idle_turns: always` and once with `when_items` (D3). Commit the recorded fixtures; they are synthetic, with no real PII. Add replay tests that query the output tables for the phenomena in the window (2 and 5). Write a review note in `tasks/milestone-15d.md` covering:
- both `runs show` summaries, with wall-clock time per day
- how actors handled the seed: the in-transit payout, the autopay, the open invoice, rent on a holiday, payroll on a Sunday
- sample deviations
- the reviews in the window: the dates narrators chose, their triggers, any escalations, and report turns per review
- anything that looked unrealistic

**Acceptance criteria:**
- [ ] The live runs verify clean (conservation, event links, obligations, tree rules, isolation), with 0 unanswered items or each one explained in the note
- [ ] Replay tests for phenomena 2 and 5 pass offline
- [ ] The review note is written

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/examples/test_phenomena_15d.py`
- [ ] Gate passes
- [ ] Manual: the user reads the note and browses the tables

**Dependencies:** Tasks 24, 25, 48
**Files likely touched:** `tests/fixtures/llm/saas_15d/`, `tests/examples/test_phenomena_15d.py`, `tasks/milestone-15d.md`
**Estimated scope:** S

## Checkpoint 6: Milestone (after Tasks 48-49)
- [ ] Gate passes
- [ ] The user reviews the live 15-day run and decides on prompt, tool or template changes, including how often narrators review and escalate
- [ ] Settle the `idle_turns` default from the measurements, and write it into SPEC.md

---

## Phase 7: Authoring

## Task 50: Day-0 tree run and manifest writer

**Description:** `tree/day_zero.py` runs the tree to day 0:
1. The root narrator gets the main prompt and the day-0 section of the narrator template. That section asks for a plain first generation: only what the prompt asks for.
2. The root uses the tree tools to build its part of the world:
   - from Tasks 27-30: spawn children; create entities, accounts, access grants, relationships, catalog entries and stories; brief each child; and set its first review with `schedule_review`
   - added in this task, for day 0 only (D5n): `write_seed`, and `declare_institution` under policy `institutions_at_reviews` (build and test both options)
3. Each new narrator then takes its own day-0 turn, top-down and level by level, with narrators on the same level in parallel. Actors, staff and the market take no day-0 turns.

`manifest/writer.py` serializes the resulting state to `manifest.yaml`, including institutions, catalog, seed, `nodes[].brief` and `nodes[].next_review`. The authoring log goes to `<world_dir>/authoring/<id>/log.jsonl` (D5h).

**Acceptance criteria:**
- [ ] With `FakeLlm` fixtures, a TARGET_EXAMPLE-like prompt yields a manifest that loads, and the written manifest round-trips, including its institutions, seed and each review date a narrator set
- [ ] A prompt with no one-offs produces no stories and no noise, and `write_seed` called at a review is rejected, as is `declare_institution` under the default `institutions_at_reviews: false`
- [ ] Levels run in order, and narrators on the same level are in flight at the same time

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tree/test_day_zero.py tests/manifest`
- [ ] Gate passes

**Dependencies:** Tasks 0 (D5h, D5n), 30, 37
**Files likely touched:** `worldgen/tree/day_zero.py`, `worldgen/manifest/writer.py`, `worldgen/tools/tree/{declare_institution,write_seed}.py`, `worldgen/agents/templates/narrator.md`
**Estimated scope:** M

## Task 51: Validate-and-repair loop

**Description:** After the day-0 tree run, `validate` runs on the draft. Each error goes to the narrator that wrote the offending item, found through `written_by` or through the authoring log's tool calls. That narrator gets a follow-up turn listing only its errors. This repeats for up to `authoring_repair_rounds` (config). A draft still invalid after that ends with a report and a nonzero exit.

**Acceptance criteria:**
- [ ] A fixture whose first draft has a dangling reference and a table column that doesn't fit its schema is repaired within the configured number of rounds
- [ ] Each error goes to the narrator that wrote the item, and no error goes to any other node
- [ ] A draft still invalid after the last round ends with a clear report

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tree/test_repair.py`
- [ ] Gate passes

**Dependencies:** Task 50
**Files likely touched:** `worldgen/tree/repair.py`, `worldgen/tree/day_zero.py`
**Estimated scope:** S

## Task 52: `worldgen author` and the 20-prompt fixture suite

**Description:** `worldgen author --prompt ... --out <manifest>` runs Tasks 50-51 and writes the manifest. Tests replay 20 fixture prompts with recorded responses. The prompts span several industries (SaaS, trucking, e-commerce, a restaurant group, a clinic, a credit union's member business, and others), and each declares its own institutions. As a live check, TARGET_EXAMPLE.md is used as the main prompt, and the result is compared by hand against `examples/saas_startup`.

**Acceptance criteria:**
- [ ] At least 18 of the 20 fixture prompts produce manifests that pass `validate` (SC7, first part)
- [ ] An authored manifest runs with the `as_agreed` policy and verifies clean
- [ ] A live authoring run from TARGET_EXAMPLE.md is reviewed with the user

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tree tests/test_cli.py`
- [ ] Gate passes
- [ ] Manual: author, then simulate, then `runs show`

**Dependencies:** Task 51
**Files likely touched:** `worldgen/cli.py`, `tests/fixtures/authoring/`, `tests/tree/test_author_suite.py`
**Estimated scope:** S

## Checkpoint 7 (after Tasks 50-52)
- [ ] Gate passes; prompt, manifest and run work end to end

---

## Phase 8: Revisions, quirks, run history

## Task 53: Prompt history and revision links

**Description:** `<world_dir>/prompt_history.json` (D5f) holds an ordered list of revisions for every prompt owner (node, relationship, story, noise). Each revision has:
- an id (a content hash)
- its text
- its author (a user or an agent)
- the run, day and turn it came from, if any

The manifest holds the head text.

Users edit prompts directly in the manifest (D5i). When `simulate` finds manifest text that differs from the head, it appends a revision authored by `user`. Two commands work on the history:
- `worldgen prompts history <manifest> <owner>` lists an owner's revisions.
- `worldgen prompts revert <manifest> <owner> <revision_id>` appends a new revision with the old text and writes it to the manifest.

`prompts.json` in each run snapshot is written from this history.

**Acceptance criteria:**
- [ ] A prompt edited in the manifest becomes a `user` revision at the next `simulate`, and that run's `prompts.json` carries its id
- [ ] Revert restores the old text as a new revision, writing both the manifest and the history in one atomic step
- [ ] Turns link to the revision ids they ran under, so a deviation can be traced to a user edit, a narrator's brief or an agent's quirk

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/engine/test_revisions.py tests/test_cli.py`
- [ ] Gate passes

**Dependencies:** Tasks 11, 17b
**Files likely touched:** `worldgen/engine/revisions.py`, `worldgen/runs/prompts_snapshot.py`, `worldgen/cli.py`
**Estimated scope:** S

## Task 54: `add_quirk`

**Description:** The actor tool `add_quirk` appends text to the actor's own prompt as a new revision, authored by the agent, with the run, day and turn. The revision applies from the actor's next turn. It is:
- written to the run's `prompt_revisions.json`
- logged as `quirk_added`
- appended to the live manifest and history in one atomic write, so later runs start from the revised prompt

**Acceptance criteria:**
- [ ] A quirk added on day d is in that actor's brief from d+1, and not in the rest of d's turn
- [ ] The quirk appears in the live manifest, in the history, in `prompt_revisions.json` and as a `quirk_added` entry
- [ ] The next run's `prompts.json` includes it, and the earlier run's directory is unchanged

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/tools/self tests/engine/test_revisions.py`
- [ ] Gate passes

**Dependencies:** Task 53
**Files likely touched:** `worldgen/tools/self/add_quirk.py`, `worldgen/engine/revisions.py`, `worldgen/runs/entries/quirk_added.py`
**Estimated scope:** S

## Checkpoint 8a: Revisions (after Tasks 53-54)
- [ ] Gate passes
- [ ] A user edit and a quirk both appear as revisions in the next run's `prompts.json`, and the earlier run's directory is unchanged

## Task 55: `runs tail` with filters, and cancel

**Description:**
- `runs tail <run_dir>` prints a live run's log as it is written, newest at the bottom, with the simulated day on each line. On a finished run it replays the log from the files.
- Filters: `--kind`, `--node`, `--entity`, `--institution` and `--deviations-only` (D5g).
- `runs cancel <run_dir>`, SIGINT or SIGTERM cancels in-flight turns, marks the run `cancelled` and closes the log cleanly.

**Acceptance criteria:**
- [ ] `tail` prints each entry within a second of its append, and on a finished run its output equals the filtered file content
- [ ] Each filter keeps exactly the matching entries on a fixture run, and `--deviations-only` keeps only deviations
- [ ] `runs cancel` mid-run leaves `status: cancelled` and a readable log

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/runs`
- [ ] Gate passes
- [ ] Manual: `runs tail --node n_morgan` on a live tracer run, then `runs cancel`

**Dependencies:** Tasks 22, 25
**Files likely touched:** `worldgen/runs/{run_store,log_filter,cancel}.py`, `worldgen/cli.py`
**Estimated scope:** M

## Task 56: Rerun from a run

**Description:** `simulate --from-run <run_dir>` starts a sibling run from that run's `manifest.yaml` and `prompts.json`, and records `parent_run`. `runs list` shows each run's parent.

**Acceptance criteria:**
- [ ] A `--from-run` child's `manifest.yaml` and `prompts.json` are byte-identical to its parent's
- [ ] Two runs from the same prompts give two separate snapshot directories (SC11)
- [ ] A past run reopens and replays from its own directory alone (tested by copying it elsewhere)

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/runs`
- [ ] Gate passes

**Dependencies:** Task 55
**Files likely touched:** `worldgen/runs/{simulation,run_store}.py`, `worldgen/cli.py`
**Estimated scope:** S

## Task 57: Noise traceability

**Description:** `runs show <run_dir> --noise <id>` lists the rows a noise prompt touched. A row counts if it came from an event made in a turn whose brief included that noise revision. The list is computed from the run's files alone.

**Acceptance criteria:**
- [ ] On a fixture run with one scoped noise prompt, the listed rows are exactly those reached through turns that included it
- [ ] Noise outside every brief's scope lists no rows (SC6)

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/runs/test_noise_trace.py`
- [ ] Gate passes

**Dependencies:** Tasks 25, 36
**Files likely touched:** `worldgen/runs/noise_trace.py`, `worldgen/cli.py`
**Estimated scope:** S

## Checkpoint 8: Run history (after Tasks 55-57)
- [ ] Gate passes
- [ ] A live tracer run is followed with `runs tail`, cancelled, rerun with `--from-run`, and one noise prompt traced with `runs show --noise`

---

## Phase 9: Completion

## Task 58: Docs pass: declaring an institution

**Description:** Bring `docs/declaring-an-institution.md` in line with the language as built. It ends with a walk-through that declares a small new institution from scratch (a prepaid expense card with a statement and autopay) and adds it to a fixture world. A test loads every declaration snippet in the doc and runs the walk-through world.

**Acceptance criteria:**
- [ ] Every declaration snippet in the doc loads (test)
- [ ] The walk-through institution renders validated rows in a fixture world with no change under `worldgen/` (SC8)
- [ ] The manifest reference test from Task 3 still passes, covering every field

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/docs`
- [ ] Gate passes

**Dependencies:** Tasks 46, 47
**Files likely touched:** `docs/declaring-an-institution.md`, `tests/docs/test_declaring_an_institution.py`
**Estimated scope:** S

## Task 59: 18-month run and the full phenomena suite

**Description:** Extend `examples/saas_startup` to TARGET_EXAMPLE's full range by moving `end` to 2022-06-30. Run it live with recording, and add replay tests for all five phenomena.

**Acceptance criteria:**
- [ ] Replay tests for phenomena 1-5 query the output tables and pass (SC2)
- [ ] `verify` is clean (SC3-5, SC12-14)
- [ ] The `runs show` timings and a review note go in `tasks/milestone-18m.md`

**Verification:**
- [ ] Tests pass: `uv run pytest -q tests/examples`
- [ ] Gate passes
- [ ] Manual: the user reviews the run with `runs show` and `runs tail`

**Dependencies:** Tasks 49, 54, 56
**Files likely touched:** `examples/saas_startup/manifest.yaml`, `tests/fixtures/llm/saas_18m/`, `tests/examples/test_phenomena_18m.py`, `tasks/milestone-18m.md`
**Estimated scope:** M

## Checkpoint: Complete
- [ ] Every SPEC success criterion is met (map in `tasks/plan.md`)
- [ ] The gate passes, with 100% coverage on `validators/`, `institutions/mechanisms/`, `engine/clearinghouse.py` and `agents/loop.py`
- [ ] Ready for review
