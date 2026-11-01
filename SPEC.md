# Spec: Financial World Generator

Status: DRAFT for review. Generalizes the single-scenario `TARGET_EXAMPLE.md`, the kind of output this system should produce. `TARGET_EXAMPLE.md` is written as a detailed world description that doubles as the main prompt handed to the root narrator. It is also expressed as `examples/saas_startup` (one instance of this system).

## Assumptions (correct me before planning starts)

1. Greenfield: no implementation exists in this repo yet.
2. Python 3.12. The core is **non-deterministic by design**: LLM agents decide every event an entity produces, inside the simulation loop, so noise and behavior are steered by the prompts in the manifest.
3. LLM inference is unlimited: there is no budget on calls, tokens or concurrency. The design uses more agents, more turns and richer tool use wherever that makes a world more realistic. Wall-clock time is the remaining limit.
4. For now the output is **JSON tables only**: each institution's tables, as the manifest declares them, written as JSON files as they are generated. In `examples/saas_startup` these are AccountingBench-style `source_data` tables (bank, card, processor, payroll).
5. The world manifest is the single contract between "authoring" and "simulation": a human or the narrator tree can write it, the simulator only reads it.
6. **The spec is domain-neutral.** The business, its institutions, their mechanics and tables, relationship terms and the catalog all come from the main prompt and live in the manifest. A SaaS startup, a trucking company and a credit union differ only in their prompt and manifest. The first world built is `examples/saas_startup`.

## Objective

Create near-real financial scenarios and situations: many varied, realistic synthetic financial worlds. A world is told top-down as a story and simulated bottom-up as money movement:

```
main prompt
    |
root narrator -> child narrators (recursively) -> actors          (authoring: the tree run to day 0)
    |
World Manifest (institutions, node tree, entities, accounts, relationships, catalog, seed, stories, noise, prompts, time range)
    |
compiler -> day loop: narrator reviews (reports up, briefs down) + one turn per actor per day
                |
     settlement + institution mechanisms
                |                      |
     event log + run log     each institution's declared tables
```

How a run works: the world is a tree of agents. The root narrator holds someone's life (in `examples/saas_startup`, the co-founder and CEO's), and each inner node narrates one part of it: the company, a department, a household. The leaves are actors: the people, customers and vendors who move money. Each narrator briefs its children, and siblings never see each other, so they decide independently. The world starts from a seed, the history already in place on its first day, because every real business has a past. Every simulated day each actor takes a turn, using tools to look at its own accounts and inbox, pay, collect, bill and send messages. All events go into one shared stream. Each institution the manifest declares takes the events on its accounts and writes them as rows in its own JSON tables; settlement delays, fees, payouts, statements and interest happen there, through generic mechanisms each institution configures. Edit any prompt in the manifest, rerun, and the data is recreated.

Users: (a) authors who want a new world by prompt, (b) reviewers who inspect and edit the manifest and rerun the simulation.

The narrator tree builds the world on day 0: institutions, nodes, entities, accounts, relationships, the catalog, the seed, stories and the time range. Every node, relationship, story and noise item carries a prompt. These prompts are where one-offs live (a late payment, a personal charge, a disputed invoice), and all of them are editable in the manifest; data is generated from them.

The world generated from the main prompt is plain: it holds what the prompt asks for and nothing more, on day 0 and through the whole run. At every review, narrators brief, spawn and write stories only within what the prompts above them ask for. A main prompt that asks for many kinds of events gets them; one that asks for few gets few. Reviewers then add and edit one-offs in the per-node prompts and regenerate.

Success looks like: a reviewer types a one-paragraph prompt, reviews a generated manifest, runs the simulator, and gets institution tables with realistic friction (settlement lags, batched payouts, messy descriptors, personal commingling) plus an event log that explains where every row came from.

## Tech Stack

- Python 3.12, `pydantic` v2 (manifest + event models), `PyYAML`, `typer` (CLI), `jsonschema` (checks every rendered row against its table's JSON Schema)
- LLM calls go through the `Llm` interface, whose implementation is `AnthropicLlm` (`worldgen/llm/anthropic_llm.py`) on the Anthropic Python SDK (`anthropic`, async client). The model and effort level are set in world config (default model `claude-opus-5-5`). Credentials come from the environment (`ANTHROPIC_API_KEY` or an `ant auth login` profile)
- JSON tables as the only output format, written as rows are generated
- `pytest`, `hypothesis` (property tests), `ruff`, `mypy --strict`
- Money is `decimal.Decimal` everywhere; never `float`. Dates are `datetime.date`; engine time is integer day index from `start_date`, negative for the seed's past.

## Commands

```
Install:   uv sync
Test:      uv run pytest -q --cov=worldgen --cov-fail-under=90
Lint:      uv run ruff check . && uv run ruff format --check .
Types:     uv run mypy --strict worldgen
Author:    uv run worldgen author --prompt "B2B SaaS, 18 months, 5 staff" --out worlds/demo/manifest.yaml   # runs the narrator tree to day 0
Validate:  uv run worldgen validate worlds/demo/manifest.yaml
Simulate:  uv run worldgen simulate worlds/demo/manifest.yaml     # new run in worlds/demo/runs/<run_id>/: <institution>/<table>.json + log.jsonl
Runs:      uv run worldgen runs list|show|tail|cancel worlds/demo   # run history; `tail` follows a live run's log
Prompts:   uv run worldgen prompts history|revert worlds/demo   # the world's prompt revisions; `revert` restores an earlier one
Verify:    uv run worldgen verify worlds/demo/runs/<run_id>        # ledger invariants, tree rules, every row traces to an event
```

## Project Structure

Convention: one file per role, tool, template, mechanism, booking rule and validator.

```
worldgen/
  manifest/        -> pydantic models: World, Policies, Institution, Node, Entity, Account, Access, Mandate, Relationship, Terms, CatalogEntry, Seed, Story, Noise, TimeRange
  policies/        -> one file per policy: a rule that is our preference, its options (each commented) and its default
  tree/
    nodes.py       -> the node tree: parent, children, role, and the entity each node stands for
    spawn.py       -> adds and retires nodes, on day 0 and during a run
    briefs.py      -> builds a node's brief for a turn: prompt, chapter brief, noise in scope, today's items
    reviews.py     -> a narrator's review: reports up its subtree, then briefs down, one level at a time; review dates and escalations
  agents/
    loop.py        -> AgentLoop: one turn of one node, a tool-use loop the engine owns
    roles/         -> narrator.py, actor.py, staff.py, market.py: the tool set for each role
    templates/     -> system prompt templates (one per role)
  tools/           -> one file per tool, grouped as read/, act/, talk/, tree/, self/, staff/
  compiler/        -> manifest -> obligation schedule (resolves refs, expands relationship terms into dated obligations)
  engine/
    clock.py       -> day tick; business-day calendars and holidays, per institution
    rng.py         -> Rng: the injected source of randomness for mechanisms
    day.py         -> one simulated day: the reviews due that day, parallel turns, day close
    seed.py        -> loads the seed: money in transit, open obligations, mandates, institution state
    obligations.py -> open obligations per handler; asks again, then logs, any left unanswered
    inbox.py       -> messages and recorded activity between nodes, delivered the next day
    revisions.py   -> prompt revision history
    clearinghouse.py -> money in flight per payment method, settled by its institution's settlement rules
  institutions/
    institution.py -> runs one declared institution: its mechanisms on its accounts
    mechanisms/    -> one file per generic mechanism: settlement, split, hold, sweep, statement, interest, numbering, descriptors
    tables.py      -> builds a declared table's rows from events and checks them against the table's JSON Schema
  events/          -> event schema + event log writer
  booking/         -> one file per booking rule (derived books, post-v1 policy variants)
  validators/      -> one file per invariant (conservation, isolation, schema, tree, seed)
  llm/             -> base.py (Llm interface), anthropic_llm.py (AnthropicLlm), fake.py (test double)
  sinks/           -> json_files.py, run_log.py (append-only log.jsonl writer)
  runs/            -> run_id.py, run_meta.py, run_store.py (list/open/tail), one file per log entry kind
  cli.py
examples/saas_startup/   -> TARGET_EXAMPLE expressed as a manifest, with its institution declarations and table schemas
examples/trucking/       -> a small world from another industry, run with no code change (Success Criterion 8)
tests/                    -> mirrors worldgen/ layout
docs/                     -> manifest reference, declaring an institution
```

## Core Concepts

| Concept | Definition |
|---|---|
| **Node** | An agent in the world, with its own prompt, state and memory. Each node has one role. **Narrators** (the root and every inner node of the tree) tell one part of the story: they brief their children, read their reports, and add or retire children. They never move money. **Actors** (the leaves) are people, customers and vendors, and move money only through act tools. **Staff** nodes act for an institution and decide situations on top of its mechanisms. An institution the story only touches has one staff node outside the tree; an institution at the center of the story (a credit union, a bank) has its staff inside the tree, as leaves under narrators. The **market** node sits outside the tree and acts for every catalog party. A node may stand for an entity (Alex's leaf stands for `p_ceo`) or for a part of the story (the sales department). |
| **Entity** | A party in the world: a business, a person, an institution, or anything else the prompt names (a customer, a vendor, a shipper, a member). `kind` is a label from the prompt, except `institution`, which the engine reads. An entity holds accounts and is a party to relationships. Entities are shells (id, kind, name, `descriptors`, and free-form `fields` such as an email or a job title, which table columns can read); behavior comes from the prompts of the nodes that act for them. |
| **Institution** | An entity that holds accounts for others and records what happens on them in its own tables (a bank, a card issuer, a payment processor, a payroll provider, a fuel-card company). The manifest declares each one: the payment methods it handles, its business-day calendar, the mechanisms it runs and its tables. The engine provides a fixed set of generic mechanisms: settlement (delays per payment method, cutoffs, weekends and holidays), splits (fees, withholding), holds (availability delays, reserves), sweeps (moving a balance between linked accounts on a schedule: payouts, autopay, pulls when a balance goes negative), statements (a cycle with totals), interest, numbering and descriptors. Each declared table has a JSON Schema and, for every column, its source: an event field, the account, a party, the statement, a counter or a descriptor. Judgment on top of the mechanisms belongs to the institution's staff. A payment follows the settlement rules of the institution that holds the initiating side's account (the payer's for `pay`, the payee's for `collect`), or else the other side's (policy `settlement_rules`); a payment with no institution on either side settles the same day. A `dispute` goes to the staff of that same institution (policy `dispute_venue`). |
| **Account** | Money an entity holds, at an institution or not. Its `kind` is a label from the prompt (checking, card, share account, fuel card). What the engine reads is the payment methods it supports, its limit, its rate and its linked accounts. Accounts at an institution produce rows in that institution's tables. All other accounts (a customer's own bank, the CEO's personal bank) are tracked for balances and conservation but not rendered. A payment to a party lands in that party's first account that supports the payment method (policy `receiving_account`); a party with no such account (a catalog party, a person whose own bank is not in the world) gets an implicit tracked account. Only money from outside the world enters and leaves through the `world_boundary` account. |
| **Access** | A grant that lets an actor use another entity's account with named payment methods: the ops manager may pay rent by wire from the company's checking account; the CEO may pay by card with a company card. An actor uses its own entity's accounts, and other entities' accounts only through access. |
| **Mandate** | A standing permission a payer gives a payee to `collect` from one of its accounts: a card on file, a direct-debit authorization, an autopay enrollment. Actors give and end mandates with `authorize` and `revoke`; mandates in force at `start` are part of the seed. A collection without a mandate is rejected. |
| **Relationship** | An edge between entities (customer-of, employed-by, leases-from, ...). Carries a `prompt` (e.g. "annual prepay, disputes invoices"), optional terms and a handler for each party: the node that bills, pays or collects under it. Terms are generic: a schedule (dates or a recurrence), an amount (fixed or left to the prompt), the payer and payee, a payment method, and a direction: `push` (the payer pays) or `pull` (the payee collects under a mandate). This is where recurring obligations such as subscriptions, rent, payroll and loan payments live. The compiler turns terms into dated obligations, and the handler of each one decides what actually happens, so amounts and timing can be non-deterministic. A catalog party's handler is the market node. A relationship is written by the lowest narrator whose subtree holds a node for every party that is neither an institution nor a catalog party. The set of relationships is the map of the world, and the main structure the code owns. |
| **Obligation** | A dated item under a relationship's terms (rent due on the 1st, a renewal on the 14th, payroll on the 10th) or under a bill. A push obligation goes to the payer's handler, a pull obligation to the payee's handler. It appears in the handler's brief on its due day, and the handler's answer produces the events (see Simulation Model). |
| **Seed** | The world's state at `start`, because every financial world has a past: opening balances, money still in transit (seed events dated before `start`), open bills and disputes (obligations open on day one), each relationship's history (since when, cycles already billed, paid up to when), mandates in force, and each institution's state (unpaid statements, pending balances, counters). Each node's backstory is part of its prompt. Narrators write the seed on day 0, and reviewers edit it in the manifest like everything else. |
| **Catalog** | Parties that exist in the world but have no node of their own: shops, airlines, restaurants, ad platforms. Each entry is an entity with a category, a price range and `descriptors`. Narrators write the catalog on day 0 and add to it during a run; actors browse it with `catalog`. The market node acts for every catalog party. |
| **Chapter** | One narrator's planning period, from one of its reviews to the next. At a review, reports come up from the narrator's subtree and new briefs go down it. Each narrator sets the date of its own next review, so chapters vary in length between narrators and over time: the root may plan quarterly while the sales narrator checks in weekly during a big deal. A child's escalation brings its parent's review forward. |
| **Brief** | What a narrator tells a child for a chapter: plans, intent and context for its part of the story ("you fly to New York March 11-14 to close the Contoso expansion"). A node's prompt is who it is; its brief is what is going on. |
| **Message** | Text one node sends another: a bill notice, a dunning email, a dispute, "can we split this payment". Delivered to the recipient's inbox the next day. An actor can message the handlers on the other side of the relationships it handles, the market about a payment it made to a catalog party, and anyone who has messaged it. |
| **Story** | A time-ordered causal chain of steps (e.g. "CEO NYC trip closes Contoso expansion"), written by a narrator or a reviewer. Each step names an actor in the writer's subtree, a day and an intent, optionally with a counterparty and amount, and appears in that actor's brief on its day. The actor decides the events. |
| **Noise / one-off** | A free-text prompt attached to a node, relationship, story or single step, and added to the brief of every agent in its scope (a node's scope is its subtree). Agents act on it when deciding events: blank or terse memos, duplicate charges, refunds, late or short payments, personal commingling. Institution-side messiness comes from mechanisms and staff (a held payout, a returned wire, a duplicate posted and reversed): each party's statement name is rendered from its `descriptors` (variants written by the narrator that creates the party), and posting lags come from settlement. |
| **Act tool** | A tool that moves money or changes a record. Act tools are universal (see Tools by role): every world uses the same ones with its own payment methods and names, so in `examples/saas_startup` a card swipe is `pay` by card from a Ramp card account and a subscription renewal is `collect` under a card on file. The engine validates each call and executes it as one action that emits zero or more events. |
| **Policy** | A rule we chose where a world could reasonably work another way: our preference, not a fact about the real world and not something the manifest declares (which account a payment lands in, which institution hears a dispute, whether a node with nothing to do takes a turn). Every policy is a named option in code with a default, switchable per world in `config.policies` (see Policies). |
| **Event** | Immutable record: `id, day, action, source_account, dest_account, amount, method, cause, memo, details, turn, links`. `action` is the act tool, staff tool or mechanism that produced it; `cause` is a short plain-text summary of why it happened (e.g. "Contoso annual prepay due under r_contoso"); `memo` is the memo or receipt note the actor wrote; `details` is a map of strings from the tool call (an invoice number, a service period, a quantity), which table columns can read; `turn` is the agent turn that produced it; `links` are related events (the payment a refund returns, the charges a payout carries). Money in flight sits in one clearing account per payment method: a payment's act tool emits an initiation event into it, and the clearinghouse later emits the linked settlement event, whose day is the payment's settled date. The record tools (`bill`, `record_activity`, `authorize`, `revoke`, `annotate`) emit zero-amount events so rows can link to them; an `annotate` event links the event it changes, and that event's row renders again. Seed events have days before `start`. Every rendered row traces back to events. |

## Simulation Model

Decisions are made while the clock runs, not planned up front.

- **Day 0 (authoring):** the root narrator reads the main prompt and spawns its children, which spawn theirs, down to the actors. With tree tools, narrators declare institutions; create entities, accounts, access grants, relationships and catalog entries; write the seed and stories; write each child's first brief; and set their own first review. Tree tools that create things take a list, so one call can create fifty subscribers; a list call is applied all or nothing, and a rejection names every failing item (policy `list_calls`). `write_seed` works only on day 0, and so does `declare_institution` (policy `institutions_at_reviews`); the other tree tools also work at reviews. The result is saved as the manifest, with each node's first brief in `nodes[].brief`, and a reviewer can edit it before the run. Authoring happens at the start of day 0: a run starts from the manifest, day 0's turns run on those briefs, and reviews start after day 0.
- **The seed:** day one starts from the seed. Money in transit settles on its dates, open obligations appear in briefs, mandates are in force, institutions continue their counters and unpaid statements, and each node's history tools return its past. Tables start at `start`. Seed events are recorded so rows can link to them, and opening balances already include them. A row for a seeded movement keeps its id, so a refund in the first week can point at a charge from before `start`, as in a real export that starts on a date.
- **A growing tree:** during a run, narrators add and retire nodes as the story needs (a hire, a new customer, a dropped vendor), with the entities, accounts, access and catalog entries that come with them. A node a narrator adds with `spawn_child` is a new participant in the world: a narrator, an actor, or a staff node inside the tree. Actors never spawn. Each change is logged with the narrator that made it.
- **Reviews:** a review runs at the start of its day, before that day's turns, and covers the reviewing narrator's subtree. Each actor and staff node in the subtree takes a report turn and reports what happened since its last report with `report_up`. A report turn uses the node's usual system prompt and tools, but its act tools and `send_message` are rejected with a reason, because acting happens in the day's own turn (policy `report_turn_tools`). The narrators below the reviewing narrator then read their children's reports and report to their own parent, one level at a time from the deepest. The reviewing narrator reads its children's reports, writes each child's next brief, adds or retires children, and sets its next review with `schedule_review` (a date and a reason, such as "in two weeks" or "the day after Contoso's procurement decision"). Briefs then go down the subtree one level at a time: each narrator below writes its children's next briefs, adds or retires children, and sets its own next review. A narrator that sets no date reviews on the date policy `default_chapter` gives (`week`, `month` or `quarter`, default `month`): the first day of the next calendar week (a Monday), month or quarter, counted from the review day, or from the start day before a narrator's first review. When a narrator and one of its descendants are due on the same day, the descendant's review is part of its ancestor's. Narrators at the same level of a review work in parallel. A narrator sees its own prompt and brief, its children's prompts and reports, and its own past chapters.
- **Escalation:** any actor or narrator with a parent can call `escalate` with a reason (cash runs out in 9 days, a customer is leaving). The reason reaches its parent as an urgent report. If a review that covers the parent is under way and the parent has not yet read its children's reports, the escalation is read in that review and moves no date (policy `escalation_in_review`); otherwise the parent's next review moves to the next day if it was later. The `escalated` log entry records which of the two applied. In that review the parent handles it or escalates to its own parent.
- **Turns:** every simulated day, every actor, every staff node and the market node take one turn, all in parallel. A turn starts from the node's brief: its prompt (current revision), its chapter brief, noise in scope, and today's items (obligations due today and overdue ones, story steps, new messages, activity recorded by the other side, timers firing, balance changes). The node then calls tools until it is done. "Nothing today" is a normal turn, and most days are ordinary. A node takes its turn even when its brief holds no items, so people can act on a whim (policy `idle_turns`).
- **Agent loop:** each turn is a tool-use loop owned by the engine (`agents/loop.py`). The engine sends the role's system prompt, the node's tools and its brief, executes every tool call in each response (results for parallel calls go back together), and continues until the model replies without calling a tool or the turn reaches `max_tool_calls_per_turn` (world config). Each turn is a fresh conversation: what a node remembers between turns lives in its notes and history, reached through tools. Each role's system prompt and tool list are byte-identical across turns and come before the brief, so they are served from the prompt cache.
- **Tools by role:**

  | Role | Read | Act | Other |
  |---|---|---|---|
  | Narrator | `children_reports`, `my_chapters` | none | `spawn_child`, `retire_child`, `brief_child`, `schedule_review`, `declare_institution`, `create_entity`, `open_account`, `grant_access`, `write_relationship`, `write_catalog`, `write_seed`, `write_story`, `report_up`, `escalate` |
  | Actor | `my_balances`, `my_statement`, `my_inbox`, `my_obligations`, `search_my_history`, `catalog` | `pay`, `collect`, `authorize`, `revoke`, `bill`, `answer_obligation`, `dispute`, `record_activity`, `annotate` | `send_message`, `set_timer`, `note_to_self`, `add_quirk`, `report_up`, `escalate` |
  | Staff | its institution's accounts and flagged items | `hold`, `release`, `reverse`, `adjust`, `flag` | `send_message`; inside the tree also `report_up`, `escalate` |
  | Market | `catalog`, payments to catalog parties, `my_inbox`, `my_obligations` | `pay`, `collect`, `answer_obligation` | `send_message` |

  The act tools:
  - `pay`: push money from an account the actor can use, by a payment method that account supports, to one or more parties. It may point to an obligation, or to an earlier payment it returns (a refund).
  - `collect`: pull money from a payer's account under a mandate.
  - `authorize` / `revoke`: give or end a mandate on one of the actor's accounts.
  - `bill`: ask a party for payment, which opens an obligation for the payer's handler.
  - `answer_obligation`: answer obligations in the brief (see Obligations).
  - `dispute`: contest a past payment with the institution that moved it; its staff decide.
  - `record_activity`: record something delivered or used under a relationship, with no money (compute hours, loads hauled, ad spend).
  - `annotate`: add or change the memo or receipt on one of the actor's own past transactions.

  Staff tools: `hold` and `release` delay and free a movement or a balance; `reverse` returns a movement (a returned wire, a chargeback); `adjust` posts a fee, a correction, or a duplicate and its reversal; `flag` marks an item for review.
- **LLM decides every event:** the LLM decides every event an entity produces; paying rent on time is a decision just like paying it late. Most answers are "as agreed", so a world stays mostly ordinary, but recurring flows drift the way real ones do (rent paid on the 3rd one month, a vendor raising its price, payroll changing after a hire).
- **Act tools are checked on the spot:** the engine validates every act tool call (the tool is in the role's set, the actor has access to the account and the payment method, a collection has a mandate, funds are available (policy `available_funds`), money is conserved) and executes or rejects it inside the turn. The result goes straight back to the model, so a rejected payment can be followed by a transfer from savings and a retry. Tool schemas are strict, and every act tool takes a `cause`. The LLM never writes rows. The catalog's price ranges keep invented activity plausible: a payment to a catalog party outside its range still goes through, and the tool result tells the actor it was unusual (policy `catalog_price_range`). Events produced on a day become visible to other nodes from the next day.
- **Obligations:** a handler answers every obligation in its brief with `answer_obligation` (pay, collect, pay late, short-pay, skip, dispute, cancel, change) and a `cause`; one call can answer many. A paying answer runs `pay`, and a collecting answer runs `collect`. If a turn ends with an obligation unanswered, the engine continues the turn once with a message listing just the missing items, then logs `obligation_unanswered` and renders nothing for it (policy `unanswered_obligation`). An obligation paid late comes back to the handler's brief on the new date. A brief lists obligations due today and overdue ones (policy `obligations_in_brief`), and `my_obligations` also lists the obligations coming due within the next 30 days (policy `obligation_horizon_days`), so a handler can plan for them (a vendor that bills monthly, a large annual renewal).
- **Messages:** `send_message` is how nodes negotiate, dispute and chase each other. `bill` sends the bill to the payer's handler as a message and opens an obligation for it. `record_activity` reaches the other party's handler the same way, so a vendor can bill from what was used.
- **Institutions are declared, mechanisms are coded:** the LLM decides what entities do; code decides how institutions record it. The engine runs the generic mechanisms, and each institution's declaration in the manifest picks and configures them and declares its tables, so a new institution or a new industry needs a manifest, not code. Staff decide situations on top of the mechanisms (hold a payout for review, return a wire, post a duplicate and reverse it), validated like any other action.
- **Reacting to its own finances:** institutions report balances to the actors with access to an account (`my_balances`, `my_statement`). Low cash lets an actor move money between accounts it can use, delay or cut spending, chase receivables, or raise cash. A payment attempted without funds surfaces as a rejected payment or fee. Customers react the same way (pay late, short-pay, cancel). These feedback loops are intended, and each decision is logged with its `cause`.
- **Parallelism:** nodes cannot see each other's state, so all turns on a simulated day run in parallel, as do reviews of separate subtrees and the narrators at one level of a review. The day closes when every turn has finished: settlement runs, mechanisms run, institutions write rows, and the day's messages, recorded activity and the timers due tomorrow go into tomorrow's briefs.
- **Quirks and prompt revisions:** an actor may add a quirk with `add_quirk`. It is appended to the actor's prompt as a new revision, applies from its next turn, and can be edited like any other prompt. Each revision records its text, its author (a user or an agent), and the run, day and turn it came from, and can be reverted. Later runs start from the revised prompt, so worlds can grow more eccentric over repeated runs. A prompt a user edits in the manifest becomes a `user` revision the next time `simulate` runs; `worldgen prompts history` lists a world's revisions and `worldgen prompts revert` restores an earlier one.
- **Logging:** runs are not reproducible, so every model request and response, and every tool call with its input and result, is recorded in the run's `log.jsonl` together with the prompt revisions and brief in force. The log is shown live and kept for every run (see Run history).

### Policies

A rule in this spec that names a policy describes that policy's default. Every policy is one file in `worldgen/policies/` that says it is our preference and lists its options, each with a comment, so every preference can be found in one place and switched. A world picks options in `config.policies`; any it doesn't name take their defaults. Rules stated without a policy are the engine's structure (the event model, clearing accounts, parallel turns whose events are visible the next day, the seed as the state at `start`) or invariants (conservation, isolation, act-tool validation).

| Policy | Default (our preference) | Other options |
|---|---|---|
| `receiving_account` | `first_supporting`: a payment lands in the payee's first account that supports the payment method | `named`: it lands where the call, the bill or the terms say, and a refund goes back to the account it came from; a payment that names no account when several fit is rejected with the choices (closest to the real world) |
| `settlement_rules` | `initiator`: the rules of the institution that holds the initiating side's account (the payer's for `pay`, the payee's for `collect`), or else the other side's | `payer`, `payee`: that side's institution, or else the other side's |
| `dispute_venue` | `initiator`: the staff of the institution whose settlement rules applied | `payer`: the payer's institution, or else the payee's (closest to the real world) |
| `available_funds` | `posted_minus_pending`: the posted balance minus pending outflows, or the remaining limit | `posted`: the posted balance or the remaining limit, ignoring pending outflows |
| `catalog_price_range` | `allow_and_note`: a payment outside a catalog party's price range goes through, and the tool result says it was unusual | `reject` |
| `idle_turns` | `always`: every node takes a turn every day | `when_items`: a node with no items that day skips its turn |
| `obligations_in_brief` | `due_and_overdue` | `with_upcoming`: the brief also lists what comes due within `obligation_horizon_days` |
| `obligation_horizon_days` | `30`: how many days ahead `my_obligations` looks | any whole number of days; `0` shows nothing ahead |
| `unanswered_obligation` | `ask_once`: the engine continues the turn once with the missing items, then logs `obligation_unanswered` | `log_only`: it logs at once |
| `default_chapter` | `month` | `week`, `quarter` |
| `escalation_in_review` | `read_in_review`: an escalation made during a review that hasn't yet read its reports is read there | `next_day`: every escalation moves the parent's review to the next day |
| `report_turn_tools` | `report_only`: act tools and `send_message` are rejected in a report turn | `all`: a report turn can act and send messages |
| `list_calls` | `all_or_nothing`: one failing item rejects the whole call | `per_item`: the valid items apply, and the failing ones are named |
| `child_roles` | `inside_parts`: a narrator makes narrators only for groups inside its part, such as departments or a household; every outside party with a deal of its own is an actor | `any_group`: any group whose several people will each act is a narrator, inside the narrator's part or outside it, so the tree goes as deep as the people who act |
| `institutions_at_reviews` | `false`: `declare_institution` works only on day 0 | `true`: narrators can also declare institutions at reviews |

### Run history (log)

Every run is kept, never overwritten, and is a self-contained snapshot of that simulated world. Each run gets its own directory `<world_dir>/runs/<run_id>/` (`run_id` is a sortable timestamp plus short suffix) holding everything that went in and everything that came out:

```
worlds/demo/runs/20261028T142201Z-a3f/
  run.json          -> metadata: start/end time, status (running|done|failed|cancelled), counts, manifest sha256, parent_run (if rerun from another run)
  manifest.yaml     -> exact copy of the manifest as run (institutions, node tree, entities, accounts, relationships, catalog, seed, stories, noise, time range)
  prompts.json      -> every prompt in force at start, keyed by owner (node, relationship, story, noise), each with its revision id, text and author
  prompt_revisions.json -> revisions added during the run (agent quirks), with the day and turn that produced them
  log.jsonl         -> append-only, one JSON object per line, in the order things happened (includes every model request, response and tool call)
  events.jsonl      -> events for this run, starting with the seed's
  <institution>/<table>.json   -> one folder per declared institution
```

- **Snapshot rule:** a run directory is never edited after it finishes and never refers to files outside itself (no pointers to the live manifest or current prompts). Editing the world afterward changes nothing in past runs. Opening a run shows the prompts, manifest, tree, decisions and tables exactly as they were.
- **Rerun:** rerunning with the same initial prompts creates a new sibling run directory with its own manifest copy, prompts, log and tables. Because the core is non-deterministic, the two snapshots may differ. Rerunning from an old run ("restore and run") loads that run's `manifest.yaml` and `prompts.json` as the starting point, and records it as `parent_run`.
- **Log entries:** `{seq, ts, day, kind, ...}` where `kind` is one of:
  - run: `run_started` (the starting tree: every node with its role, parent and `stands_for`), `seed_loaded` (counts of seed events, open obligations and mandates), `day_closed`, `run_finished`
  - tree: `review_started` (narrator, trigger: scheduled, default or escalated, escalating node), `review_scheduled` (narrator, date, reason), `escalated` (node, parent, reason, whether a review under way read it or the parent's review moved), `report_written` (node, parent), `brief_written` (narrator, child, chapter), `node_spawned` / `node_retired` (narrator, node)
  - turns: `turn_started` / `turn_finished` (node), `llm_call` (node, turn, request, response, prompt revision ids), `tool_call` (node, turn, tool, input, result), `action_rejected` (node, turn, tool, reason), `message_sent` (from, to, message id), `obligation_unanswered` (obligation id, handler), `quirk_added`
  - money: `event`, `row_rendered` (institution, table, row id, linked event ids)

  The log is the run's narrative; the event log (`events.jsonl`) remains the source of truth for money, and `log.jsonl` references it by event id rather than duplicating amounts.
- **Written as it happens:** the engine appends each entry and flushes it as soon as it occurs (including on crash, so a failed run keeps a partial log and `status: failed`).
- **Followed live:** `worldgen runs tail` prints the active run's log as it is written, starting with the tree in `run_started`, newest at the bottom, with the simulated day on each line. It filters by kind, node, entity and institution, and deviations only.
- **History:** `worldgen runs list` shows every past run (time, status, prompt revisions, row and deviation counts), and `runs show` opens one from its files and prints its tree with every spawn and retirement. Deleting a run removes its directory.
- **Retention:** runs are kept until a user deletes them, and there is no prune command; `log.jsonl` is plain text and may grow large, which is accepted.

## Manifest Shape (excerpt)

```yaml
world: {name: demo, start: 2021-01-01, end: 2022-06-30, currency: USD}   # rng_seed: optional, best-effort
config: {model: claude-opus-5-5, effort: high, max_tool_calls_per_turn: 40, policies: {default_chapter: month, idle_turns: always}}   # a policy not named takes its default
institutions:
  - id: inst_ramp                     # the institution's entity
    calendar: us_federal              # business days and holidays
    methods: {card: {settle_days: [1, 3], weekends: true}}
    mechanisms:
      statement: {every: month, by: settled}
      sweep: {after: statement, delay_days: 3, from: linked, method: ach}   # autopay from the linked bank account
    tables:
      ramp_card_transactions:
        schema: schemas/ramp_card_transactions.json
        columns: {cardholder_name: actor.name, swipe_date: event.day, transaction_date: event.settled, merchant_name: payee.descriptor, amount: event.amount, memo: event.memo, statement_id: statement.id}
  # Mercury, Stripe and Rippling are declared the same way
nodes:
  - {id: n_root, role: narrator, next_review: 2021-04-01, prompt: "Alex Rivera's life: co-founder and CEO of a B2B SaaS startup founded in mid-2020, married, lives in San Francisco"}   # holds the main prompt
  - {id: n_alex, role: actor, parent: n_root, stands_for: p_ceo, prompt: "pitches investors, travels for big deals, uses the company card for personal things"}
  - {id: n_company, role: narrator, parent: n_root, stands_for: co_self, prompt: "the startup: 5 staff, YC-backed, seed money raised in 2020, self-serve and enterprise customers"}   # no next_review: default_chapter gives 2021-02-01
  - {id: n_sales, role: narrator, parent: n_company, next_review: 2021-01-15, prompt: "enterprise deals and the self-serve tail"}
  - {id: n_jordan, role: actor, parent: n_sales, stands_for: p_jordan, prompt: "VP of Sales; entertains prospects, extends trips over weekends", brief: "Contoso wants to meet in New York in March; book it once their procurement confirms"}   # brief: the first chapter's brief, written on day 0
  - {id: n_contoso, role: actor, parent: n_sales, stands_for: cust_contoso, prompt: "enterprise buyer since December 2020, slow approvals, pays by wire"}
  - {id: n_mercury, role: staff, stands_for: inst_mercury, prompt: "small-business bank; reviews unusually large outgoing wires"}   # no parent: outside the tree
  - {id: n_market, role: market, prompt: "merchants act like real ones: most returns refunded within a week, a rare double charge reversed a few days later"}
entities:
  - {id: co_self, kind: company}
  - {id: p_ceo, kind: person, name: Alex Rivera}
  - {id: p_jordan, kind: person, name: Jordan Taylor, fields: {title: VP of Sales, email: jordan@example.com}}
  - {id: cust_contoso, kind: customer, name: Contoso}
  - {id: inst_mercury, kind: institution, name: Mercury}
  - {id: inst_ramp, kind: institution, name: Ramp}
catalog:
  - {id: v_amazon, category: retail, price: ["5.00", "900.00"], descriptors: ["AMZN Mktp US*{ref}", "Amazon.com*{ref}", "AMZN MKTP US"]}   # {ref} becomes a random reference code
  - {id: v_figma, category: software, price: ["15.00", "75.00"], descriptors: ["FIGMA", "FIGMA INC"]}
accounts:
  - {id: a_x0666, holder: co_self, at: inst_mercury, kind: checking, name: "Mercury Checking X0666", methods: [ach, wire, book], opening: "1162480.15"}
  - {id: a_ramp_alex, holder: co_self, at: inst_ramp, kind: card, name: "Ramp card - Alex Rivera", methods: [card], limit: "25000.00", linked: a_x0666}
  - {id: a_contoso_bank, holder: cust_contoso, kind: checking, methods: [ach, wire], opening: "2000000.00"}   # no `at`: tracked, not rendered
access:
  - {node: n_alex, account: a_x0666, methods: [wire, ach]}
  - {node: n_alex, account: a_ramp_alex, methods: [card]}
relationships:
  - id: r_contoso
    parties: [cust_contoso, co_self]
    kind: customer_of
    written_by: n_sales
    handlers: {co_self: n_jordan}   # cust_contoso's handler defaults to n_contoso, the node that stands for it
    prompt: "annual prepay, expands mid-term after the NYC trip"
    terms: {payer: cust_contoso, payee: co_self, direction: push, method: wire, amount: "85363.20", schedule: {every: year, from: 2020-12-01}}   # optional; compiled into dated obligations
  - id: r_figma
    parties: [co_self, v_figma]
    kind: subscribes_to
    written_by: n_company
    handlers: {co_self: n_casey}    # v_figma is a catalog party, so its handler is n_market
    terms: {payer: co_self, payee: v_figma, direction: pull, method: card, amount: "45.00", schedule: {every: month, day: 14}}
seed:
  in_transit:
    - {id: e_seed_payout, day: 2020-12-30, action: sweep, source: a_stripe_balance, dest: a_x0666, method: ach, amount: "1243.18", arrives: 2021-01-04, cause: "Stripe payout of Dec 28-29 charges"}
  open_obligations:
    - {relationship: r_counsel, due: 2021-01-15, amount: "4500.00", cause: "December Net-30 invoice"}
  history:
    - {relationship: r_contoso, since: 2020-12-01, paid_through: 2021-11-30}
    - {relationship: r_figma, since: 2020-07-14, cycles_billed: 6}
  mandates:
    - {payer_account: a_ramp_casey, payee: v_figma}
  institutions:
    inst_rippling: {counters: {journal: 14}}
    inst_ramp: {unpaid_statement: "8412.55"}
stories:
  - id: s_nyc_trip
    written_by: n_root
    steps:
      - {day: 2021-03-11, actor: n_alex, intent: "fly to New York for the Contoso meeting", counterparty: DELTA AIR LINES, amount: "642.20"}
noise:
  - {scope: {story: s_nyc_trip}, prompt: "leaves memos blank on the personal weekend charges"}
  - {scope: {node: n_contoso}, prompt: "pays late and short-pays once, then sends a corrective wire"}
```

## Code Style

```python
# worldgen/institutions/mechanisms/descriptors.py
import string

from worldgen.engine.rng import Rng
from worldgen.manifest.entity import Entity


class Descriptors:
    """Render how a party's name appears on one statement row."""

    ref_chars = string.ascii_uppercase + string.digits

    def render(self, party: Entity, rng: Rng) -> str:
        pattern = rng.choice(party.descriptors or [party.name])
        ref = "".join(rng.choice(self.ref_chars) for _ in range(9))
        return pattern.replace("{ref}", ref)
```

```python
# worldgen/policies/receiving_account.py
from enum import StrEnum


class ReceivingAccount(StrEnum):
    """Our preference: which of a payee's accounts a payment lands in."""

    # Default. The payee's first account that supports the payment method.
    FIRST_SUPPORTING = "first_supporting"
    # Closest to the real world. Where the call, bill or terms say; a refund returns to its source.
    NAMED = "named"
```

Conventions: `snake_case` files named for the single thing they hold; one public class per file; docstring is one line; every rule that is our preference is a policy in `worldgen/policies/`, whose docstring starts with "Our preference:" and whose options each have a comment, and code that applies it reads the world's `config.policies` and names the policy in a comment at that spot; randomness through the injected `Rng`, and LLM calls through an injected `Llm` client, never imported directly, so tests can substitute fakes; every tool is a class with a strict JSON input schema and a `run` method that returns what the model sees; no module-level state.

## Testing Strategy

- **Unit** (`tests/<mirror path>`): every tool, mechanism, table builder and validator. LLM and `Rng` faked so tests stay stable even though the core is not deterministic.
- **Property** (`hypothesis`): conservation (sum of events per account from `start` = rendered balance change), isolation (an institution's tables are built only from events on its own accounts; a brief or read-tool result never holds another node's state beyond messages sent to it and, for a narrator, its children's prompts and reports), settlement (no row posted before `initiated + min_delay` of its payment method, none on non-business days unless the method allows).
- **Invariants over goldens**: no checksum goldens. `examples/saas_startup` is run and checked for the TARGET_EXAMPLE phenomena and the validators, not for exact rows. `examples/trucking` runs on the same engine and is checked by the validators.
- **LLM calls** (day 0 and run time): mocked with recorded fixtures, each holding a whole turn (every request and response of its tool loop). Tests assert manifests validate, refs resolve and invariants hold, never exact prose. One opt-in live smoke test behind `WORLDGEN_LIVE=1`.
- **Policies**: every option of every policy is tested. A test fails if a policy's docstring doesn't start with "Our preference:", or if a policy is missing from `Policies` or from the manifest reference.
- **Coverage**: >= 90% lines on `worldgen/`, 100% on `validators/`, `engine/clearinghouse.py`, `institutions/mechanisms/` and `agents/loop.py`.

## Boundaries

- **Always:** use `Decimal` for money; route randomness through `Rng` and LLM calls through `Llm`; log every model call and tool call to the run log; validate every act tool call against the role's tools, the actor's access, mandates and available funds; run tests + ruff + mypy before commit; add a validator when adding an invariant; make every rule that is our preference a policy, with its default and its options; keep one-thing-per-file layout; update `docs/` when the manifest schema changes.
- **Ask first:** adding runtime dependencies; changing the manifest schema in a breaking way (bump `schema_version`); adding or changing a generic mechanism, act tool or staff tool; changing a policy's default; changing an example world's table schemas; choosing an accounting policy for derived books; any network call beyond the model API; adding another `Llm` implementation or model provider.
- **Never:** let an LLM write rendered rows without a matching event (money must still be conserved); build one institution's tables from another's; give a node a brief or tool that shows another node's state; use `float` for amounts; name an institution, industry, payment method or relationship type in engine code (they live in the manifest); hardcode special-case friction (it must emerge from declared mechanisms and agents' choices); decide a preference anywhere but through its policy; commit API keys or generated worlds containing real PII.

## Success Criteria

1. `worldgen validate` rejects manifests with dangling refs (nodes, entities, institutions, accounts, access, mandates, handlers, catalog parties), a node tree with a cycle or more than one root, story steps or review dates outside the time range, unknown mechanisms, payment methods, policies or policy options, a declared table whose column sources don't fit its schema, or a seed whose past movements are dated on or after `start` or arrive before it, each with a pointing error message.
2. `examples/saas_startup` reproduces every phenomenon in TARGET_EXAMPLE section 6 (in-transit month-end Stripe payout, many-to-one payout batching, enterprise prepay vs delivery, exec commingling, Ramp swipe-to-settle cutoff lag), asserted by tests that query the output tables.
3. Variation without breakage: two runs of the same manifest may differ, but every run passes conservation and event-link checks (criteria 4 and 5).
4. Conservation: for every account, opening balance + sum of its events from `start` = closing balance, and for every rendered account the rendered rows give the same closing balance; the sum of all events from `start` across the world is 0, counting the `world_boundary` account. Opening balances already include the seed's events.
5. Event links: 100% of rendered rows link to at least one event; `worldgen verify` reports 0 orphans.
6. Noise is traceable: every turn records the noise prompts in its brief (by revision id), so the rows any noise prompt touched can be listed from the run's files. Noise is checked by the invariants.
7. `worldgen author` turns a one-paragraph prompt into a day-0 tree, with its institutions, catalog and seed, whose manifest passes `validate` on >= 90% of 20 fixture prompts (mocked-LLM replay) spanning several industries. Editing any prompt in the manifest and running `simulate` regenerates the JSON tables.
8. A new institution or a new industry needs only a manifest, with no code change: demonstrated by `examples/trucking`, a small trucking company with a fuel-card issuer and a factoring company, run on the same engine as `examples/saas_startup`.
9. Rows are written to the tables as they are produced, from the first simulated day. Transient model API errors are retried with backoff and never fail a run on their own. No turn makes more than `max_tool_calls_per_turn` tool calls. A run can be cancelled from the CLI, which ends it with `status: cancelled` and a readable log.
10. Every act tool call is validated: a call outside the role's tools, without access to the account and payment method, a collection without a mandate, or beyond available funds is rejected, its reason is returned to the agent in the same turn and logged as `action_rejected`, and nothing is rendered for it.
11. Run history: every run creates `runs/<run_id>/` with `run.json` and an append-only `log.jsonl`; rerunning never overwrites an earlier run. Every `row_rendered` entry matches a row in that run's tables and every `event` entry matches an event, and vice versa (tested). `runs tail` shows entries as they are appended, a killed run leaves a readable partial log with `status: failed`, and a past run can be reopened and replayed from its files alone. Each run directory contains its own `manifest.yaml` and `prompts.json`; editing the live manifest or prompts afterward leaves earlier run directories byte-identical (tested), and two runs started from the same initial prompts produce two separate snapshot directories.
12. Every obligation is answered: each obligation due within a run has either an `answer_obligation` tool call or an `obligation_unanswered` entry, and no event pays or collects an obligation without such a call (tested).
13. Isolation: no brief or tool result shows a node another node's state, except messages sent to it, for a narrator its children's prompts and reports, and for the market node the payments made to catalog parties (tested on every brief and tool result of an `examples/saas_startup` run).
14. Tree rules: every node except the root has exactly one parent; every node added during a run has a `node_spawned` entry naming the narrator that added it; every relationship and story was written by a narrator whose subtree holds the nodes it names; every review has a `review_started` entry naming its trigger, and every escalation is followed by a review of its parent no later than the next day (checked by `worldgen verify`).
