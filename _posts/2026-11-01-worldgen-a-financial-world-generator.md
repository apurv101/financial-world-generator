---
layout: post
title: "worldgen: a financial world generator"
date: 2026-11-01
---

`worldgen` creates realistic synthetic financial data. It simulates a business as a world of LLM agents (founders, employees, customers, vendors, banks) and records what they do the way real institutions would. The output is the raw exports a business would actually have: bank transactions, card transactions, payment processor charges and payouts, and payroll journal entries.

> **Status:** design phase. There is no code yet. This repo holds the spec, the build plan, and the language for declaring institutions, checked on paper against two industries. See [Where we are](#where-we-are).

## Why

Real financial data is private, and data generated from rules looks too clean. Real exports are messy because of how money moves and how people behave:

- A customer pays on March 30, but the payout arrives on April 1, so the March bank statement leaves it out.
- Forty card charges, fees and refunds show up in the bank as one line: `Deposit - STRIPE`.
- The CEO buys something personal on the company card and leaves the memo blank.
- A customer pays late, short-pays, then sends a corrective wire.
- The same merchant appears as `AMZN Mktp US*2K4L` one month and `Amazon.com` the next.

You can't get this mess by inventing tidy journal entries and working backwards. `worldgen` builds data from the money's side instead. People and businesses make decisions, money moves through channels with real delays, and each institution records only what it would see. Every row traces back to something that happened in the world.

## How it works

```
main prompt  ("a B2B SaaS startup, 18 months, 5 staff ...")
    |
narrator tree builds the world on day 0
    |
world manifest  (institutions, people, accounts, relationships, history, stories, prompts)
    |
day-by-day simulation: every agent takes a turn, using tools
    |
institutions record what happened on their accounts
    |
JSON tables per institution  +  an event log explaining every row
```

**A world is a tree of agents.**
- **Narrators** tell the story. The root narrator holds one person's life, for example the CEO's. Each narrator below it covers one part of that life: the company, the sales team, a household. Narrators brief their children, read their reports, and add or remove people as the story needs (a hire, a new customer, a dropped vendor). Siblings never see each other, so they decide independently.
- **Actors** sit at the leaves: the people, customers and vendors who move money.
- **Staff** act for an institution and make judgment calls: hold a payout for review, return a wire, reverse a duplicate charge.
- **The market** acts for all the shops, airlines and restaurants people buy from.

**Every world starts with a history.** On day one, money is already in transit, invoices are open, and cards are on file with vendors, because every real business has a past.

**Every simulated day, every agent takes a turn.** It looks at its own balances, inbox and bills, then decides what to do using tools: pay, collect, bill, dispute, send a message, make a note. Paying rent on time is a decision just like paying it late. Most days are ordinary, and some aren't.

**The engine checks every action on the spot.** It checks that the actor can use the account and the payment method, that a collection has the payer's permission, that the funds are there, and that money is conserved. A rejected payment goes back to the agent with the reason, so it can move money from savings and try again.

**Institutions are declared, not coded.** A bank, card issuer, processor or factoring company is written in the manifest. The declaration picks the payment methods the institution handles, sets up generic mechanisms (settlement delays, fees, holds, payouts, statements, interest, numbering, merchant descriptors), and says how each output table is built. A new institution or a new industry needs a manifest, not code. See [`docs/declaring-an-institution.md`](https://github.com/apoorvbuilds/financial-world-generator/blob/main/docs/declaring-an-institution.md).

**Edit any prompt and rerun.** Every person, relationship, story and one-off ("pays late once, then short-pays") is a prompt in the manifest. Change one, run again, and the data is regenerated.

## The harness

The project is a harness around a model we don't train. These are its parts and where each one lives in the design:

| Part | In `worldgen` |
|---|---|
| **Tools:** what an agent can do | A fixed set per role: narrators build and brief, actors move money and talk, staff decide for their institution. The same tools work in every industry. |
| **Context:** what an agent sees | Each turn's brief holds the agent's prompt, its narrator's plan, any one-offs that apply to it, and today's bills, messages and story steps. It never shows another agent's private state. |
| **Checks:** what keeps the output right | Every action is validated as it happens. After the run, `verify` checks invariants: money is conserved, every row traces to an event, institutions stay isolated, and the tree follows its rules. |
| **The loop:** how work is split into steps | Day by day: narrator reviews, then all turns in parallel, then settlement and institution mechanisms at day close. |
| **Records:** what makes runs inspectable and comparable | Every model request, response and tool call goes into the run's log, and every run is kept as a snapshot. |
| **Evals:** how we know it got better | Tests that query the output for the target phenomena, plus a suite of 20 world prompts, at least 18 of which must produce valid worlds. |

Runs are **non-deterministic by design**. Two runs of the same world can differ, and both must pass every check. Correctness comes from the invariants and the event log, not from reproducing the same rows.

## Design principles

- **The engine is domain-neutral.** Engine code never names an institution, industry, payment method or relationship type. A SaaS startup, a trucking company and a credit union differ only in their prompt and manifest.
- **The LLM decides, code records.** Agents decide what happens. They never write table rows: rows are built from events by the institution that holds the account.
- **Friction emerges, never hardcoded.** Lags, batching and cutoff mismatches come from how the channels work and what agents choose, not from special-case rules.
- **Institutions are good-enough approximations.** We model what shows up in an institution's exports, not its internal operations. Approximations are listed in the docs.
- **Preferences are switchable policies.** Wherever a world could reasonably work another way (which account a payment lands in, which institution hears a dispute), the choice is a named policy with a default, and each world can switch it.
- **Coverage, not exact numbers.** A generated world matches its target when it shows the same kinds of events and stories, not the same amounts or dates.

## Example worlds

| World | What it is | Institutions |
|---|---|---|
| [`examples/saas_startup`](https://github.com/apoorvbuilds/financial-world-generator/tree/main/examples/saas_startup) | A small B2B SaaS company, 2021-2022, modeled on the [AccountingBench](https://accounting.penrose.com/) company. [`TARGET_EXAMPLE.md`](https://github.com/apoorvbuilds/financial-world-generator/blob/main/TARGET_EXAMPLE.md) is its main prompt. | Mercury (bank), Ramp (cards), Stripe (processor), Rippling (payroll) |
| [`examples/trucking`](https://github.com/apoorvbuilds/financial-world-generator/tree/main/examples/trucking) | Ozark Ridge Freight, a six-truck carrier in Missouri, 2024. It shows that a new industry needs no code change. | Prairie Hollow Bank, RoadFleet fuel card, Ironbridge Freight Funding (factoring) |

Each example so far holds its institution declarations (`manifest.yaml`) and a JSON Schema for every output table (`schemas/`).

## What a run produces

```
worlds/<name>/runs/<run_id>/
  run.json                  status, timing, counts
  manifest.yaml             the world exactly as it was run
  prompts.json              every prompt in force at the start
  prompt_revisions.json     prompts agents changed during the run
  events.jsonl              every money movement and record, the source of truth
  log.jsonl                 every model call, tool call, review and rejection, in order
  <institution>/<table>.json   the output tables
```

A run is never edited after it finishes, and later edits to the world don't change it.

## Where we are

**Done**
- [`SPEC.md`](https://github.com/apoorvbuilds/financial-world-generator/blob/main/SPEC.md): the full design.
- [`TARGET_EXAMPLE.md`](https://github.com/apoorvbuilds/financial-world-generator/blob/main/TARGET_EXAMPLE.md): the SaaS world, written as the prompt the generator will receive.
- [`tasks/plan.md`](https://github.com/apoorvbuilds/financial-world-generator/blob/main/tasks/plan.md) and [`tasks/todo.md`](https://github.com/apoorvbuilds/financial-world-generator/blob/main/tasks/todo.md): the build plan, about 60 small tasks with checkpoints.
- [`docs/declaring-an-institution.md`](https://github.com/apoorvbuilds/financial-world-generator/blob/main/docs/declaring-an-institution.md): the institution declaration language, tested on paper against the SaaS institutions and the trucking ones. Every SaaS table column maps to a generic source. Trucking needed six small additions, which are proposed and waiting for approval.

**Next**
1. **Checkpoint 0:** approve the declaration language and decide on the additions trucking needed.
2. **Tracer bullet:** a tiny world (an ops manager, a customer, a landlord, a bank) runs through the real agent loop, first with a scripted fake model, then with Claude.
3. **Narrator tree:** reviews, briefs, escalation and a growing cast during the run.
4. **Actor life and institutions:** messages, bills, card-on-file payments, memory and one-offs, then the market, staff, and each generic mechanism. Then the trucking world runs on the same engine with no code change.
5. **First milestone:** a live 15-day run of the SaaS world (January 1-15, 2021) from a hand-written manifest, to see how well the agent loop works.
6. **Authoring:** turn a one-paragraph prompt into a whole world.
7. **Run history and the full 18-month run.**

## Planned commands

None of these exist yet. They are the interface the spec defines.

```
uv sync                                          # install
uv run worldgen author --prompt "..." --out worlds/demo/manifest.yaml   # build a world from a prompt
uv run worldgen validate worlds/demo/manifest.yaml                     # check a manifest
uv run worldgen simulate worlds/demo/manifest.yaml                     # run it
uv run worldgen runs list|show|tail|cancel worlds/demo                 # run history; tail follows a live run
uv run worldgen prompts history|revert worlds/demo                     # prompt revisions
uv run worldgen verify worlds/demo/runs/<run_id>                       # check the run's invariants
```

## Tech stack

Python 3.12, `pydantic` v2, `PyYAML`, `typer`, `jsonschema`, and the Anthropic Python SDK (default model `claude-opus-5-5`). Money is always `Decimal`. Tests use `pytest` and `hypothesis`, with fake model responses so they stay stable even though runs aren't deterministic.
