# Implementation Plan: Financial World Generator (`worldgen`)

Source of truth: `SPEC.md`. Target output: `TARGET_EXAMPLE.md`. Tasks and their status live in `tasks/todo.md`.

## Overview

Build `worldgen` as `SPEC.md` describes it. A world is a tree of agents that starts from a seeded past:

- **Narrators** each tell one part of the story. At their reviews, on dates each narrator sets for itself, they read reports from their subtree, write their children's next briefs, and grow or prune their part of the tree. A child's escalation brings its parent's review forward to the next day.
- **Actors** sit at the leaves and take one tool-use turn per simulated day. They move money only through the universal act tools (`pay`, `collect`, `authorize`/`revoke`, `bill`, `answer_obligation`, `dispute`, `record_activity`, `annotate`), which are validated on the spot.
- **Staff** nodes decide situations for an institution (`hold`, `release`, `reverse`, `adjust`, `flag`). The **market** node acts for every catalog party.

Institutions are data. Each one is declared in the manifest with a calendar, payment methods and their settlement rules, a configured set of generic mechanisms (settlement, split, hold, sweep, statement, interest, numbering, descriptors), and tables with JSON Schemas and column sources. Act tools emit events and a clearinghouse settles them. Mechanisms run at day close, and each institution writes rows from events on its own accounts. Every run is a self-contained snapshot with a log you can follow live (`runs tail`). Reviewers edit prompts in the manifest and rerun.

Build order, riskiest first:

1. **The declaration language, on paper.** Declare Mercury, Ramp, Stripe, Rippling, a fuel-card issuer and a factoring company, and map every table column to a generic source, before any mechanism exists. If the language can't express them, SPEC changes before any code is written.
2. **Offline tracer bullet.** A fake LLM drives a tiny seeded world through the real agent loop. The world has an ops manager, a customer, a landlord and a declared bank.
3. **The same tracer on Claude.** The first big unknown is whether actors use their tools sensibly.
4. **The narrator tree inside the run:** reviews, escalation and a growing tree. This is the second big unknown.
5. **Actor life:** messages, mandates, bills, memory and noise. Then the market and staff.
6. **Mechanisms,** one per task in parallel lanes. Then the four SaaS institutions in full, and `examples/trucking` on the same engine with no code change.
7. **First milestone:** a live 15-day run of the TARGET_EXAMPLE world from a hand-written manifest.
8. **The rest:** authoring (running the tree to day 0), then prompt revisions, quirks and run history, then the 18-month run.

## Decisions (confirmed in Task 0)

On 2026-10-31 the user accepted every answer below as proposed, and added D7 the same day. D3-D7 are written into SPEC.md as current design. D1 and D2 shape Phases 6-7 and stay here. D5d, D5f, D5g, D5h and D5m are implementation choices, so they live here and in the tasks that build them.

| # | Decision | Answer | Blocks |
|---|---|---|---|
| D1 | **Milestone window** (15 days) | 2021-01-01..2021-01-15, TARGET's own start. The milestone manifest is then the 18-month manifest with an earlier `end`. The window opens mid-flight from the seed:<br>• the December 30 Stripe payout arrives on 01-04<br>• December 30-31 Ramp swipes settle in January (phenomenon 5)<br>• Ramp's December statement is paid by autopay<br>• rent falls due on a bank holiday (01-01)<br>• Alex parks seed money in Treasury on 01-05 and 01-08<br>• payroll falls on a Sunday (01-10)<br>• counsel's Net-30 invoice is due on 01-15<br>• Stripe pays out every business day (phenomenon 2)<br>The first default review is 02-01, so two narrators get `next_review` dates inside the window. The tracer (which spans 03-31) and the Task 46 fixture world cover the month-end mechanisms. | Task 48 |
| D2 | **Milestone manifest source** | Hand-write `examples/saas_startup`, including the TARGET 2.1 seed. The milestone then judges the run loop on its own. Authoring comes after it and is compared against the hand-written manifest. | Phases 6-7 order |
| D3 | **SPEC open questions** | **OQ1:** a brief lists obligations due today and overdue ones, and `my_obligations` also shows the next `obligation_horizon_days` (config, default 30). **OQ2:** every actor, staff node and the market take a daily turn. Config `idle_turns: always\|when_items` (default `always`) lets the milestone measure the cost of the other choice. | Tasks 17, 19 |
| D4 | **SPEC choices to confirm** | **(a)** Default model `claude-opus-5-5`. **(b)** The Account and Access model. **(c)** Staff nodes sit outside the tree unless their institution is at the center of the story. **(d)** `jsonschema` becomes a runtime dependency, because `tables.py` checks every row against its table's schema as it renders (SPEC: adding runtime dependencies needs approval). **(e)** Drop "unknown tools" from Success Criterion 1, since no manifest field names a tool. | Tasks 2, 3, 7, 20, 24 |
| D5 | **Gap-fills** (SPEC is silent on these) | **(a)** A payment to a party lands in that party's first account that supports the payment method. A party with no such account (a catalog merchant, an employee) gets an implicit tracked account. `world_boundary` is only for money from outside the world.<br>**(b)** An act tool emits an initiation event into one clearing account per payment method, and the clearinghouse later emits the linked settlement event. `event.settled` is the settlement event's day. The settlement rules come from the institution holding the initiating side's account (the payer's for `pay`, the payee's for `collect`), or else from the other side's. With neither, the payment settles the same day. A `dispute` goes to the staff of that same institution.<br>**(c)** Events carry `memo` and `details` (a string map from the act tool call: an invoice number, a service period, gallons). Entities carry `fields` (an email, a job title). Declared columns can read all three. The record tools (`bill`, `record_activity`, `authorize`, `revoke`, `annotate`) emit zero-amount events so rows can link to them. An `annotate` event links the event it changes, and that row re-renders.<br>**(d)** Available funds are the posted balance minus pending outflows, or the remaining limit on an account with a limit. An act tool reserves funds when it runs. Act tools don't await, so check-and-reserve is atomic under asyncio.<br>**(e)** `nodes[].brief` holds each node's day-0 brief. Authoring happens at the start of day 0, and day 0's turns follow it.<br>**(f)** The live prompt history is `<world_dir>/prompt_history.json`. A revision id is a content hash, so ids exist before that file does.<br>**(g)** A deviation is an `answer_obligation` whose decision isn't the agreed `pay` or `collect`, or that moves a different amount (when the terms fix one) or on a different day. It drives `runs tail --deviations-only` and the deviation counts.<br>**(h)** `worldgen author` writes its log to `<world_dir>/authoring/<id>/log.jsonl`, in the same format as a run log.<br>**(i)** Users edit prompts in the manifest, and `simulate` records each changed prompt as a `user` revision. `worldgen prompts history\|revert` lists and reverts revisions.<br>**(j)** `default_chapter` is `week`, `month` or `quarter`: the first day of the next calendar week (a Monday), month or quarter after the review day. For a narrator's first review, it counts from the start day.<br>**(k)** Suppose an escalation is made while a review that covers the parent is under way, and the parent hasn't yet read its children's reports. Then it is read in that review and moves no date. Otherwise the parent's next review moves to the next day if it was later. The `escalated` entry records which of the two applied.<br>**(l)** A report turn uses the node's usual system prompt and tools, so the prompt cache still holds. Its act tools and `send_message` are rejected with a reason, because acting happens in the day's own turn.<br>**(m)** The engine ships two calendars: `us_federal` (Federal Reserve holidays, computed in code) and `every_day`.<br>**(n)** `write_seed` and `declare_institution` work only on day 0. The other tree tools work on day 0 and at reviews.<br>**(o)** A payment to a catalog party outside its price range goes through, and the tool result says it was unusual.<br>**(p)** A tree tool call with a list is applied all or nothing, and a rejection names every failing item. | Tasks 1, 3, 9, 10, 15, 16, 18, 26, 28, 29, 37, 50, 53 |
| D6 | **Overview and subagents** | The overview is the CLI. `run_started` lists every seed node (role, parent, `stands_for`), so `runs tail` opens with the starting tree. `runs show` prints the tree with its spawns and retirements. A subagent is a node a narrator spawns with `spawn_child`: a new participant in the world, which can be a narrator, an actor, or a staff node inside the tree. Actors don't spawn. | Tasks 11, 25, 29 |
| D7 | **Preferences are policies** (user, 2026-10-31) | Every rule that is our preference, not a real-world fact or a manifest declaration, is a switchable policy (SPEC: Policies). Each one is a file in `worldgen/policies/` whose docstring starts "Our preference:", with a comment on every option. The world's `config.policies` picks the options, and the code that applies a policy names it in a comment. The defaults are the D3 and D5 answers. Every option in the SPEC table is built and tested by the task that builds the rule (see the policy-to-task map). | Task 3 onward |
| D8 | **What the declaration language added** (user, Task 1, 2026-10-31) | All eight accepted as proposed in `docs/declaring-an-institution.md` section 8:<br>• **P1** card instruments under one account (Tasks 3, 16, 29, 33)<br>• **P2** descriptors by direction (Tasks 3, 5, 20)<br>• **P3** obligations emit a record event when due (Tasks 14, 18)<br>• **P4** terms' `to_account` read for pull terms (Tasks 5, 33)<br>• **P5** new act tool `change_setting`, with a mechanism `setting` (Tasks 34, 42)<br>• **P6** events carry `call` (Tasks 10, 20)<br>• **P7** duplicate charges come from issuer staff `adjust` (TARGET 3.4 reworded; SPEC's market example follows at Checkpoint 0)<br>• **P8** `receiving_account`'s default also returns refunds to their source (Task 16)<br>SPEC and the named tasks take these in at Checkpoint 0. | Checkpoint 0 |

## Architecture Decisions

- **Day order.** A run starts by loading the seed:
  - Seed events go into `events.jsonl` first.
  - Money still in transit is queued to settle on its dates.
  - Open obligations come due.
  - Mandates are in force.
  - Each mechanism gets its seeded state.

  Day 0 is `start`. Each day d then runs four steps in order:
  1. **Reviews due today** (never on day 0). A narrator's next review date comes from its manifest `next_review`, then from its own `schedule_review` calls, and otherwise from `default_chapter` (D5j). An escalation can bring the date forward (D5k). A narrator due on the same day as one of its ancestors is reviewed as part of the ancestor's review. Reviews of separate subtrees run in parallel. A review makes three passes over the reviewing narrator's subtree:
     1. Every actor, and every staff node inside the tree, takes a report turn (D5l).
     2. Narrators report up level by level, starting from the deepest.
     3. The reviewing narrator writes its children's briefs and sets its next review. Then briefs go down level by level.

     Narrators on the same level run in parallel.
  2. **Briefs.** Every actor, staff and market brief is built from state as of the last close plus today's items.
  3. **Turns.** All actor, staff and market turns run in parallel. Act tools validate and execute inside the turn.
  4. **Day close.** The clearinghouse settles what is due. Each institution runs its mechanisms in one fixed engine order (set in Task 20) and renders and writes its tables. Messages, recorded activity and timers go into tomorrow's items. `day_closed` is logged.

  Events from day d become visible to other nodes from d+1.
- **One `AgentLoop` for every role.** The roles are narrator, actor, staff and market. A role is a system template plus a tool set. Each turn is a fresh conversation. The system prompt and tools are byte-identical per role and sent first, so they are served from the prompt cache. Tools are classes with a strict pydantic input and a `run` method. Bad input returns an error result to the model instead of raising.
- **Isolation through `NodeView`.** Briefs and read tools see the world only through a `NodeView` scoped to one node. It holds:
  - the node's entity's accounts, plus accounts it has access to
  - its inbox, obligations, notes and history, including the seed's past
  - for narrators, their children's prompts and reports
  - for staff, their institution's accounts and flagged items
  - for the market, the payments made to catalog parties

  An isolation validator scans the requests in `log.jsonl` for other nodes' private text.
- **Conservation by construction.** Every event moves money between two accounts. Per-method clearing accounts hold money in flight (D5b), including the seed's. `verify` re-checks conservation on every run, and hypothesis tests cover act tools and mechanisms.
- **Obligations follow their direction.** A push obligation goes to the payer's handler, who answers with `pay`. A pull obligation goes to the payee's handler, who answers with `collect` under a mandate. Either way, the payment method comes from the terms and the handler names the account. The market handles the side of a catalog party.
- **Institutions are data.** `institutions/institution.py` runs one declaration. Each mechanism is one engine class that the declaration configures, and `tables.py` renders rows from declared column sources. No file in `worldgen/` names an institution, industry, payment method or relationship type. A test from Task 2 checks this against every such name in `examples/`.
- **Policies (D7).** A preference is never an inline constant or branch. `manifest/policies.py` holds the `Policies` model, with one field per policy, typed by that policy's enum (or a number) and defaulting to our preference. The task that builds a rule adds its policy file, its field and its docs entry, and tests every option. Code that applies a policy takes `Policies` through its constructor and comments the branch with the policy's name.
- **Updatable rows.** Rows are keyed by id, and rendering an id again replaces the row. This covers:
  - posting a movement on settlement
  - moving a payout from `in_transit` to `paid`
  - backfilling `payout_id` and `statement_id`
  - annotated memos

  Every render logs `row_rendered`.
- **Row schemas.** Every row is checked against its table's JSON Schema when it renders (D4d), and `verify` checks again.
- **Test LLMs.** `FakeLlm` either runs a script or replays recorded whole-turn fixtures. `tests/support/as_agreed.py` is a scripted policy that drives whole worlds offline:
  - It answers every obligation as agreed: push obligations with `pay`, pull obligations with `collect`, from the first account it can use with that payment method.
  - It writes stock reports and briefs.
  - Staff and the market do nothing else.

  No `Llm` implementation is added to `worldgen/` beyond `AnthropicLlm` and the fake.
- **Logging.** Each log entry kind is its own file under `worldgen/runs/entries/`, added by the task that first emits it. Everything a reviewer inspects (`runs list`, `show`, `tail`, the noise trace) is computed from run files alone.
- **Out of scope for this plan:** `booking/` (derived books), tax jurisdictions, reactive terms, answer keys, and worlds without a company at the center. Staff inside the tree is supported and tested on a fixture, because SPEC allows it.

## Task List (index; status is tracked in `tasks/todo.md`)

**Phase 0: Decisions and the declaration language**
- Task 0: Confirm D1-D6 and sync SPEC.md
- Task 1: The institution declaration language, on paper
- Task 1b: The language tested on trucking
- **Checkpoint 0:** the user approves the decisions and the language

**Phase 1: Foundation and tracer bullet (fake LLM)**
- Task 2: Project scaffold, CLI and the neutrality test
- Task 3: Manifest models: world, config, nodes, entities, accounts, access
- Task 4: Manifest models: tables and column sources
- Task 4b: Manifest models: institutions
- **Checkpoint 1a:** the declarations load
- Task 5: Manifest models: relationships, terms, catalog, stories, noise
- Task 6: Manifest models: seed and mandates
- Task 7: `worldgen validate`: references, tree, time range
- Task 8: `worldgen validate`: payment methods and table columns
- **Checkpoint 1b:** the manifest validates
- Task 9: Clock, calendars, Rng and money
- Task 10: Accounts, events and ledger
- Task 11: Run directory, `run.json` and `log.jsonl`
- Task 12: Llm interface and `FakeLlm`
- **Checkpoint 1c:** the engine types
- Task 13: Tool base class and `AgentLoop`
- Task 14: Compiler: obligations and story steps
- Task 15: Clearinghouse and the settlement mechanism
- **Checkpoint 1d:** a scripted turn, a schedule and settlement
- Task 16: Act tools, part 1: validation, reservation and `pay`
- Task 17: Node tree, `NodeView` and read tools
- Task 17b: Actor briefs and the actor role
- Task 18: Answering obligations
- **Checkpoint 1e:** an obligation answered and settled
- Task 19: Day loop
- Task 20: Institutions and tables: movement rows
- Task 21: Loading the seed
- **Checkpoint 1f:** the tracer runs day by day from its seed
- Task 22: `worldgen simulate`
- Task 23: `worldgen verify`
- **Checkpoint 1:** the tracer world simulates and verifies offline

**Phase 2: Live loop (highest risk)**
- Task 24: `AnthropicLlm`, recorder and live tracer smoke test
- Task 25: `worldgen runs list|show` with a loop-quality summary
- **Checkpoint 2:** a live tracer run reviewed with the user

**Phase 3: Narrator tree (second-highest risk)**
- Task 26: Reviews, part 1: review dates and reports up
- Task 27: Reviews, part 2: briefs down and `schedule_review`
- Task 28: Escalation
- **Checkpoint 3a:** reviews run offline
- Task 29: Growing the tree
- Task 30: Relationships, stories and catalog entries written during a run
- Task 31: Tree-rule and isolation validators
- **Checkpoint 3:** the user reads a live tracer run's reviews

**Phase 4: Actor life, the market and staff**
- Task 32: Messages and inbox
- Task 33: Mandates and `collect`
- Task 34: Record tools: `bill`, `record_activity` and `annotate`
- **Checkpoint 4a:** talking and billing
- Task 35: Timers, notes, history and statements
- Task 36: Noise in briefs
- Task 37: The catalog and the market node
- **Checkpoint 4b:** memory, noise and the market
- Task 38: Staff nodes: `flag`, `hold` and `release`
- Task 39: Disputes, `reverse` and `adjust`
- **Checkpoint 4:** staff

**Phase 5: Mechanisms and institutions (two parallel lanes)**
- Task 40: The split mechanism
- Task 41: The hold mechanism
- Task 42: The sweep mechanism
- **Checkpoint 5a:** the payouts lane
- Task 43: The statement mechanism
- Task 44: The interest mechanism
- Task 45: The numbering mechanism
- **Checkpoint 5b:** the statements lane
- Task 46: The four SaaS institutions in full
- Task 47: `examples/trucking` with no code change
- **Checkpoint 5:** every institution in both examples renders from declarations

**Phase 6: First milestone (15 days)**
- Task 48: `examples/saas_startup` manifest and offline baseline
- Task 49: Live 15-day milestone run
- **Checkpoint 6:** milestone review with the user

**Phase 7: Authoring (the tree run to day 0)**
- Task 50: Day-0 tree run and manifest writer
- Task 51: Validate-and-repair loop
- Task 52: `worldgen author` and the 20-prompt fixture suite
- **Checkpoint 7**

**Phase 8: Revisions, quirks, run history**
- Task 53: Prompt history and revision links
- Task 54: `add_quirk`
- **Checkpoint 8a:** revisions
- Task 55: `runs tail` with filters, and cancel
- Task 56: Rerun from a run
- Task 57: Noise traceability
- **Checkpoint 8:** run history

**Phase 9: Completion**
- Task 58: Docs pass: declaring an institution
- Task 59: 18-month run and the full phenomena suite
- **Checkpoint: Complete**

## SPEC success criteria to task map

| SC | Tasks |
|---|---|
| 1 validate errors | 4, 4b, 7, 8, 21 |
| 2 phenomena | 42, 43 (row level); 46 (1, 2, 5 on a fixture world); 49 (2, 5 in the window); 59 (all five) |
| 3-5 variation, conservation, event links | 10, 15, 21, 23, 46, 49, 59 |
| 6 noise traceable | 36, 57 |
| 7 author; edit and rerun | 50-52, 53 |
| 8 new institution or industry by manifest only | 1, 1b, 2, 47, 58 |
| 9 rows as produced, retries, tool-call cap, cancel | 20, 13, 24, 55 |
| 10 act tools validated | 16, 33 |
| 11 run history | 11, 22, 23, 55, 56 |
| 12 obligations answered | 18, 23 |
| 13 isolation | 17, 17b, 31, 32, 37, 49 |
| 14 tree rules | 26-31 |

## Policy to task map

| Policy | Built in | Notes |
|---|---|---|
| `default_chapter` | 3 (field), 9 (dates) | |
| `settlement_rules` | 15 | `payee` and the `collect` side are tested again in 33 |
| `available_funds` | 16 | |
| `receiving_account` | 16 | `named` takes a `to_account` in `pay` and refunds return to their source. Terms gain `to_account` in 5, used in 18; bills gain it in 34 |
| `obligation_horizon_days` | 17 | |
| `obligations_in_brief` | 17b | |
| `unanswered_obligation` | 18 | |
| `idle_turns` | 19 | measured both ways in 49 |
| `report_turn_tools` | 26 | `send_message` part in 32 |
| `escalation_in_review` | 28 | |
| `list_calls` | 29 | |
| `catalog_price_range` | 37 | |
| `dispute_venue` | 39 | |
| `institutions_at_reviews` | 50 | |

## Parallelization

- **Must be sequential:** the core, Tasks 2-23. Within it, Tasks 9 and 12 depend only on the scaffold and Task 11 only on Task 3, so they can run alongside the rest of the manifest models (Tasks 4-8).
- **After Checkpoint 2:** the narrator lane (26-31) and the actor-life lane (32-36) both add sections to `tree/briefs.py`. They can run in parallel if the brief is composed from ordered section functions and each lane adds its own.
- **After Checkpoint 4, two mechanism lanes:**
  - payouts: split, hold, sweep (40-42), closed by Checkpoint 5a
  - statements: statement, interest, numbering (43-45), closed by Checkpoint 5b. Numbering depends on nothing else in the lane, so it can start at once.

  Each mechanism is its own file with its own config model, and Task 20 fixes the day-close order up front, so the lanes don't conflict. Tasks 46 and 47 join the lanes and can run in parallel with each other.
- **Authoring (50-52)** needs the tree tools (26-30), the catalog (37) and `validate`, so it can run alongside Phases 5-6.
- **Run history (53-57)** needs only Tasks 11, 17b, 22, 25 and 36, so it can run alongside Phases 5-7.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| The generic declaration language can't express a real institution's tables or behavior (Rippling's balanced journal lines, Stripe's per-customer invoice numbers, factoring advances and reserves) | High | Tasks 1 and 1b map every column and behavior on paper first, for two industries. Gaps go to the user as mechanism changes before Phase 5 builds on them. Task 47 runs trucking with no code change. |
| Institution- or industry-specific code creeps into the engine | Medium | From Task 2, the neutrality test fails on any example's institution, payment method or relationship name in `worldgen/` |
| A seed that doesn't add up: opening balances, in-transit money and institution state disagree | Medium | The seed validator (Task 21). Conservation is counted from `start`, with in-transit money opening in clearing accounts. |
| Actors misuse tools, invent implausible activity, or all behave alike | High | Strict tool schemas; rejection reasons returned within the turn; catalog price ranges; a live tracer before any scale-out; `runs show` metrics; the milestone review |
| Narrator briefs are too vague or too directive, reports bloat, or the tree sprawls | High | Live reviews at Checkpoint 3, before institutions; `runs show` counts spawns and report and brief lengths; another review at the milestone |
| Narrators review every day or almost never, or actors escalate everything | High | `schedule_review` rejects dates that aren't after today or that fall past the world end. `runs show` reports reviews by trigger, chapter lengths and escalations. The narrator template is tuned at Checkpoint 3 and the milestone. |
| Wall-clock time: hundreds of actors × a daily turn × 546 days, plus a report turn for every actor in a reviewed subtree | High (18-month run) | Parallel turns; prompt-cached prefixes; per-day wall-clock time and report turns per review measured at the milestone; the `idle_turns` switch (D3) |
| Money leaks through clearing, splits, sweeps or reversals | High | Double-entry events; hypothesis conservation tests per mechanism; `verify` on every run |
| Concurrent turns overdraw a shared account | Medium | Synchronous check-and-reserve (D5d); a test with concurrent turns on one account |
| A brief or tool result leaks another node's state | Medium | `NodeView` as the only path to state; a log-scanning isolation validator, run on the milestone |
| Recorded fixtures stop replaying after prompt or tool changes | Medium | Fixtures keyed by turn and call index; tests assert invariants, not prose; re-record whenever a template or tool schema changes |
| A quirk written to the live manifest collides with a user editing it | Low | One atomic write per quirk. `simulate` turns any manifest change into a `user` revision, so nothing is lost silently. |
| `log.jsonl` grows large (every request and response) | Low | SPEC accepts this; `runs tail` filters keep it readable |

## Open Questions

- Any change to the mechanism set, the act tools or the column vocabulary that Tasks 1 and 1b propose. These are decided at Checkpoint 0.
