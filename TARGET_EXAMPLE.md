# Target World: AccountingBench-Style SaaS Startup

**Reference benchmark:** [AccountingBench (Penrose)](https://accounting.penrose.com/)

## 1. Purpose: this document is the prompt for the world generator

This file describes, in as much detail as possible, the kind of world the generator in `SPEC.md` should be able to create. It is written to be handed to the root narrator as the main prompt: from it the narrator tree produces a manifest (institutions, entities, accounts, relationships, catalog, seed, stories, noise, prompts, time range), which the simulator then runs into the `source_data` tables in section 5. It describes the world and the output, not an implementation. How the simulator works is in `SPEC.md`.

Amounts, names and dates in this document are examples. A generated world matches this one when it shows the same kinds of events and stories (section 6), not the same numbers. Details marked † come from the public [AccountingBench](https://accounting.penrose.com/) page and its transcripts, so a world built from this prompt stays close to the real company's data.

**What AccountingBench-style data is.** The raw exports a small company would have: bank statements, a corporate card, a payment processor, and payroll journal entries. The data is only useful if it has the friction real exports have, so the world must be built from the money's side, not the accounting side:

1. **Causal grounding.** Every row traces to something that happened in the world: a customer renewing, a vendor billing, a payroll run, a person on a trip. Nobody first invents balanced journal entries and then reverse-engineers clean rows.
2. **Isolated actors.** Each customer, vendor, person and institution knows only what it would know. Stripe does not know what is in Mercury. Mercury does not know which customer invoices make up a `Deposit - STRIPE`. Each institution's tables hold only what that institution would record.
3. **Time-lagged money.** Cash moves through ACH, wire, card and payout channels that take days to settle and skip weekends and holidays, so tables disagree on dates at every month end.
4. **Human arbitrariness.** Discretionary spending follows what real people did that week (a client trip, a team dinner, a personal charge by mistake), not uniform random numbers.
5. **No hardcoded friction.** Settlement lags, batching and cutoff differences must come out of how the channels work (section 6), not special-case rules.

## 2. The company and the time frame

- **Business:** a Y Combinator-backed† B2B SaaS startup with revenue in the millions of dollars a year†. Most of it comes from enterprise accounts on annual contracts; a long tail of self-serve subscribers adds a few thousand dollars a month through Stripe†.
- **Time range:** 2021-01-01 to 2022-06-30 (18 months), currency USD.
- **Opening position:** the company already exists on day one (section 2.1). Its seed money sits in Mercury: about `$2,500,000` in `Mercury Treasury` by early 2021†, with `Mercury Checking X0666` as the operating account everything else settles into.
- **Headcount:** 5 core staff at the start (section 3.3), growing with a few hires; paid twice a month. Gross salaries run about `$25,000` a month in early 2021, with about `$3,200` of employer payroll tax†.
- **Systems the company uses (the only sources of data):**
  - **Mercury** bank with three accounts: `Mercury Checking X0666` (operating), `Mercury Checking X3354` (shown as `Mercury Savings X3354` in some places†), and `Mercury Treasury` (interest-bearing).
  - **Stripe** to collect card payments from self-serve customers and enterprise customers who pay by card.
  - **Ramp** corporate cards for staff and subscriptions, with a monthly statement paid by autopay from Mercury X0666.
  - **Rippling** for payroll, exporting journal entries on the 10th and 26th of each month.

### 2.1 History before the start

Like every real business, this one has a past, and the world starts in the middle of it. Write this history into the seed and into each node's prompt:

- The company was founded in mid-2020, went through Y Combinator†, and raised a seed round of a few million dollars by equity wire into Mercury X0666. On `2020-12-31` it moved `$2,000,000` of it into Mercury Treasury†.
- Payroll has run on the 10th and 26th since late June 2020, so Rippling's journal numbers are already in the teens (`JE #18` falls on `2021-03-10`).
- Dozens of self-serve subscribers have been paying for months, with cards on file at Stripe. Each customer's invoice numbers continue their sequence (`#FF308C68-0007` in February 2021).
- Contoso prepaid its first annual contract (`2020-12-01` to `2021-11-30`) by wire in December 2020.
- Vendors already bill their stored Ramp cards and authorized Mercury debits, and the office lease and the corporate counsel relationship are running.
- On `2021-01-01` money is still moving: a Stripe payout sent on December 30 is in transit, Ramp's December statement awaits its autopay, card swipes from December 30-31 have not settled, and counsel's December Net-30 invoice is unpaid.
- The five people have held their roles, cards and habits for months.

## 3. The cast: entities to create

Create each as an entity with its own prompt. Give every entity an id, kind and a short prompt describing how it behaves; the behavior comes from the prompt, not from many fixed fields. Entities should be mostly shells.

### 3.1 Customers

- **Self-serve subscribers (dozens at a time, a few hundred over the period):** monthly plans at `$25`, `$37`, `$39`, `$80`, `$139` or `$270`†, paid by a card kept on file at Stripe, which charges it on the renewal day. Each has a signup date, a renewal day, and a small chance of churn, refund or dispute. Most renewals are paid the day they are invoiced; some are paid a day or more later after a failed attempt, and a few amounts match no plan price because of a discount or proration (a `$30.00` payment†). Each subscriber is its own actor with a short prompt: create them many at a time, starting with the base that already exists (section 2.1) and adding signups through the period.
- **Enterprise buyers (a dozen or so, most of the revenue):** annual prepaid contracts paid by wire or ACH straight into Mercury, not Stripe. The anchor example is `Contoso`: `$85,363.20` per year†, contract `2020-12-01` to `2021-11-30`, paid up front (section 2.1), with an expansion after the CEO's New York trip in March 2021 and a renewal in December 2021. Enterprise buyers approve slowly and may pay late or short-pay.
- **Refunds and disputes:** a small share of charges are refunded or disputed days or weeks after payment, as full or partial refunds through Stripe.

### 3.2 Vendors

- **Cloud and compute:** `VERCEL INC - Monthly Pro Plan` (`$20.00`/month†), `AMAZON WEB SERVICES` (billed monthly for the compute the team actually used), `RUNPOD.IO` (GPU bursts bought when Sam runs experiments).
- **Marketing and ads:** `Facebook Ads` (billed `$400.00`† each time accumulated ad spend reaches that threshold), `LinkedIn` (campaigns around `$281.46`†), `GOOGLE ADS`.
- **SaaS tools:** `FIGMA`, `NOTION LABS`, `SLACK TECHNOLOGIES`, `LINEAR`, `GITHUB`, `GWORKSPACE`, mostly billed to a Ramp card monthly or annually.
- **Facilities, legal and operations:** a commercial landlord (`$7,000.00` rent per month by ACH or wire from Mercury), corporate counsel (quarterly retainer or Net-30 invoices), and `Amazon` (`AMZN MKTP US`) for equipment and supplies (a `$397.53` order†).
- Vendors bill one of three ways: a stored Ramp card, an authorized ACH debit from Mercury, or an invoice paid up to 30 days later. Usage-billed vendors bill from what the team used, so their bills follow its activity.

### 3.3 People

Five core people, each with a role, a Ramp card (some with Mercury access) and habits. Their prompts carry the personality.

| Person | Role and access | Typical business activity | Typical personal or commingled activity |
| :--- | :--- | :--- | :--- |
| **Alex Rivera** | Co-founder and CEO (Ramp card, Mercury wire/ACH) | Investor pitches in SF/NYC, board dinners, executive SaaS tools, conference flights | Uses the company Ramp card for Equinox, Peloton, weekend family hotels and groceries (`WHOLE FOODS`); wires personal estimated taxes or a car lease from Mercury |
| **Sam Chen** | Co-founder and CTO (Ramp card, cloud admin) | Scales AWS/Vercel, buys test GPUs (`RUNPOD.IO`), replaces laptops for new hires | Late-night DoorDash during outages; sometimes buys home-automation gear on Amazon with the company card and notes "Personal - will reimburse" |
| **Jordan Taylor** | VP of Sales (Ramp card) | Takes enterprise prospects to steakhouses, books last-minute flights and Ubers, buys client renewal gifts | Extends a 3-day sales trip in Miami over the weekend and charges personal beach-club dining to Ramp without a receipt |
| **Casey Patel** | Senior Engineer (virtual Ramp card) | Renews GitHub/Linear seats, buys monitor cables, orders team lunch at sprint planning | Clean card use; sometimes forgets receipts or writes terse memos ("cables") |
| **Morgan Lee** | Ops and Office Manager (Ramp card, vendor billing) | Pays office rent, orders Costco snacks, books Friday happy hours, handles annual insurance prepayments | Accidentally uses a Ramp card stored in a personal Uber Eats profile on a Sunday and adds a memo flagging the mistake |

Memos on Ramp swipes range from clear ("Client dinner with Acme VP"), to terse, to blank, to personal admissions ("Accidentally used company card for personal Uber Eats, please deduct"). Many are written days after the swipe, and some never.

### 3.4 Institutions

These are entities too. Declare each with the payment methods it handles, its mechanics and its tables in section 5. Each writes only its own tables, from events on its own accounts, and has a staff node that decides situations: holding a payout for review, returning a wire, posting a duplicate and reversing it.

- **Stripe:** invoices, card charges, refunds and payouts. Fee is `2.9% + $0.30` per charge. Charges become available about two days after they are made and are swept into a payout each business day, so `Deposit - STRIPE` lands in Mercury almost every business day, usually for `$35` to `$500` in early 2021†. If refunds exceed charges, Stripe pulls the difference by ACH from Mercury.
- **Ramp:** card transactions and monthly statements. Charges settle 1-3 days after the swipe. Statements close at a month-end cutoff and are paid by autopay from Mercury X0666.
- **Rippling:** payroll journal entries on the 10th and 26th, numbered in sequence (for example `JE #18` on `2021-03-10` and `JE #19` on `2021-03-26`), with matching ACH debits from Mercury for net pay and taxes. Each line's `account` is the company's own account name as set up in Rippling (`61100 - Salaries`, `61200 - Employer Payroll Tax`, `11100 - Mercury Checking X0666`).
- **Mercury:** settled bank lines for its three accounts, monthly statements, month-end interest (for example `Interest Accrual` of `$0.82` on checking†; Treasury earns a few hundred dollars a month, such as `$444.98` for January 2021†) and service fees. It sees only cash that has settled.
- **Merchants:** the catalog merchants people buy from (airlines, restaurants, Amazon, Apple) act through the market: they refund returns, and now and then charge a card twice and reverse it a few days later.

## 4. Relationships and money flows

The relationships are the map of the world. Create these edges, with a prompt and terms where they apply:

| Relationship | Money flow and timing |
| :--- | :--- |
| Self-serve customer -> company | Stripe charges the card on file on the renewal day; Stripe fee deducted; charges swept into a payout batch; payout lands in Mercury X0666 1-2 business days after it is initiated as `Deposit - STRIPE` |
| Enterprise customer -> company | Annual prepay by wire or ACH directly into Mercury, once per contract, for 10-12 months of service |
| Refunding customer -> Stripe | Refund days or weeks after the charge; net against the next payout, or an ACH pull (`Stripe - Expense - STRIPE`, for example `-$35.39` or `-$282.70`) when refunds exceed charges |
| Company -> vendor (card) | The vendor charges a Ramp card kept on file on its schedule; settles 1-3 days later; included in the monthly Ramp statement |
| Company -> vendor (ACH or invoice) | The vendor pulls an authorized ACH debit from Mercury, or sends a Net-30 invoice the company pays when due |
| Company -> landlord | `$7,000.00` rent each month by ACH or wire |
| Employee -> company | Salary on the 10th and 26th through Rippling; ACH debits for net pay and taxes |
| Person -> Ramp card | Business and personal swipes with memos of varying quality |
| Executive -> Mercury | Occasional off-cycle wires or ACH, business or personal |
| Ramp -> Mercury | Monthly autopay pull after the statement closes |
| Company -> Mercury Treasury | Internal transfers between the three accounts; monthly interest |

Channels differ in speed: card charges settle in 1-3 days, ACH in 1-3 business days, wires usually same or next business day, and nothing posts on weekends or federal bank holidays unless the channel allows it.

### 4.1 Example story: CEO trip to New York, March 2021

Stories are the cause of discretionary spending. This one shows the shape; the generator should write similar ones for other people and months. Narrative:

> CEO Alex Rivera flew to New York (March 11-14) to close the Contoso enterprise expansion. Hosted Contoso executives at Mastro's Steakhouse on March 12. Stayed two extra personal nights at the hotel with a spouse (March 13-14), bought personal AirPods Max at the Fifth Ave Apple Store on Saturday March 13 with the company Ramp card, and on March 15 initiated an ACH payment from Mercury Checking X0666 to cover a personal vehicle lease.

Money movements it causes:

- Ramp, on Alex's card:
  - `2021-03-11` `DELTA AIR LINES` `$642.20`, memo "NYC flight for Contoso meeting"
  - `2021-03-12` `MASTRO'S STEAKHOUSE NYC` `$784.50`, memo "Dinner w/ Contoso VP Eng & CFO"
  - `2021-03-13` `APPLE STORE #R001 NYC` `$598.81`, memo blank (Saturday, consumer retail)
  - `2021-03-14` `THE STANDARD HIGH LINE` `$1,800.00`, memo "4 nights NYC - 2 nights Contoso biz, 2 nights personal weekend"
- Mercury X0666: `2021-03-16` `ACH Debit - PORSCHE FINANCIAL` `($1,150.00)`

**One-offs:** this prompt asks for one-offs like this trip, personal charges, late or short payments and disputes (section 6.1), so the first generation includes them, spread across people and months. Beyond what this prompt asks for, the generator adds nothing on its own; reviewers add more through the per-entity prompts.

### 4.2 More stories

These follow the same shape: a reason, then the money it moves. Use them, and write others like them for other people and months.

- **Parking the seed money (January 2021)†.** After the `$2,000,000` moved into Mercury Treasury on 2020-12-31 (section 2.1), Alex moves `$1,000,000` more on `2021-01-05` and `$785,000` on `2021-01-08`. Money: internal transfers from X0666 to Treasury, and Treasury interest every month from then on.
- **Refunds outrun charges (February 2021)†.** A handful of subscribers get refunds in a quiet week, Stripe's balance goes negative, and Stripe pulls the difference from Mercury: `Stripe - Expense - STRIPE` of `-$282.70` on `2021-02-05`, and `-$35.39` on `2021-02-23`, the same day a `$489.54` payout lands. Money: Stripe refunds and ACH pulls from X0666 between ordinary payouts.
- **A hire (spring 2021).** A new engineer joins. Sam buys a laptop at the Apple Store and monitors and cables on Amazon with the company card, Ramp issues the hire a card, GitHub, Linear and Slack bill for more seats from their next cycle, and the hire's first payroll is prorated. Money: a few large equipment swipes, higher SaaS charges, a bigger payroll run.
- **Training experiment and ad push (summer 2021).** Sam runs a week of GPU experiments, topping up RunPod several times, and the next AWS bill jumps. Marketing runs a campaign the same month: Facebook bills `$400.00` every few days instead of every few weeks, LinkedIn charges for a campaign, and both slow down afterward. Money: bursts of RunPod swipes, a larger AWS charge, clustered threshold bills.
- **Stripe payouts go weekly.** Partway through the period, Morgan switches Stripe from daily to weekly payouts to make the bank easier to follow (the benchmark's own text mentions weekly Stripe payouts†). Money: fewer, larger `Deposit - STRIPE` lines, and more money in transit at each month end.
- **Annual renewals (one month each year).** Morgan pays the year's business insurance premium and renews a few annual SaaS plans in the same month. Money: several large one-time charges, each covering a year.
- **Contoso renewal (November-December 2021).** Jordan negotiates the renewal. Counsel reviews the order form in November and invoices in December on Net-30, paid in January. Contoso's procurement wires the renewal two weeks late and short over a disputed seat count, then sends a corrective wire. Money: a legal invoice that crosses year end, and a late, short enterprise wire followed by a corrective one.
- **Personal charge paid back.** Sam buys home-automation gear on Amazon with the company card, writes "Personal - will reimburse" in the memo, and two weeks later sends an ACH from a personal bank account to X0666. Money: a personal Ramp swipe and a matching `ACH Credit` in Mercury.
- **Running down checking (2022)†.** As the company burns cash, Mercury Checking X0666 runs down (the real account is near `$103,634.63` by late 2022†), and Alex moves money back from Treasury ahead of payroll and rent; once the transfer lands a day after a payroll debit. Money: Treasury-to-checking transfers sized to upcoming bills, and a near-overdraft.

---

## 5. JSON `source_data` Schema Specification

Each financial institution writes strictly to its own tables ([AccountingBench](https://accounting.penrose.com/)). Output is JSON only: one file per table, `<institution>/<table>.json`, holding an array of row objects that validates against the schemas below (JSON Schema 2020-12). Conventions:

- **Money** is a string with exactly two decimal places (`"-642.20"`), never a JSON number, so it parses to `Decimal` without float error.
- **Dates** are ISO `YYYY-MM-DD`; **months** are `YYYY-MM`; **ids** are UUIDs.
- **Nullable columns** are written as `null`; columns not listed in `required` may also be omitted.
- **Foreign keys** cannot be expressed in JSON Schema, so they are marked with the custom keyword `x-references: "<table>.<column>"`.

**`common.schema.json`** (shared definitions)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "common.schema.json",
  "$defs": {
    "uuid": {"type": "string", "format": "uuid"},
    "date": {"type": "string", "format": "date"},
    "month": {"type": "string", "pattern": "^\\d{4}-(0[1-9]|1[0-2])$", "description": "e.g. 2021-03"},
    "money": {
      "type": "string",
      "pattern": "^-?\\d+\\.\\d{2}$",
      "description": "Decimal amount as a string with exactly 2 places; never a JSON number"
    }
  }
}
```

**`mercury.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "mercury.schema.json",
  "description": "Written only by Mercury, from events on its own accounts. One <table>.json file per entry in properties.",
  "type": "object",
  "properties": {
    "mercury_transactions": {
      "title": "mercury_transactions",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"$ref": "common.schema.json#/$defs/uuid"},
          "account_name": {"type": "string", "enum": ["Mercury Checking X0666", "Mercury Checking X3354", "Mercury Treasury"]},
          "transaction_date": {"$ref": "common.schema.json#/$defs/date"},
          "posted_date": {"$ref": "common.schema.json#/$defs/date"},
          "description": {"type": "string"},
          "amount": {
            "$ref": "common.schema.json#/$defs/money",
            "description": "Positive for deposits, negative for withdrawals"
          },
          "transaction_type": {
            "type": "string",
            "enum": ["ACH Credit", "ACH Debit", "Wire", "Internal Transfer", "Interest", "Fee"]
          },
          "counterparty_name": {"oneOf": [{"type": "string"}, {"type": "null"}]}
        },
        "required": ["id", "account_name", "transaction_date", "posted_date", "description", "amount", "transaction_type"],
        "additionalProperties": false
      }
    },
    "mercury_statement_line_items": {
      "title": "mercury_statement_line_items",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"$ref": "common.schema.json#/$defs/uuid"},
          "statement_month": {"$ref": "common.schema.json#/$defs/month"},
          "account_name": {"type": "string"},
          "date": {"$ref": "common.schema.json#/$defs/date"},
          "description": {"type": "string"},
          "amount": {"$ref": "common.schema.json#/$defs/money"},
          "running_balance": {"$ref": "common.schema.json#/$defs/money"}
        },
        "required": ["id", "statement_month", "account_name", "date", "description", "amount", "running_balance"],
        "additionalProperties": false
      }
    },
    "mercury_treasury_records": {
      "title": "mercury_treasury_records",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"$ref": "common.schema.json#/$defs/uuid"},
          "statement_month": {"$ref": "common.schema.json#/$defs/month"},
          "beginning_balance": {"$ref": "common.schema.json#/$defs/money"},
          "deposits": {"$ref": "common.schema.json#/$defs/money"},
          "withdrawals": {"$ref": "common.schema.json#/$defs/money"},
          "interest_earned": {"$ref": "common.schema.json#/$defs/money"},
          "ending_balance": {"$ref": "common.schema.json#/$defs/money"}
        },
        "required": [
          "id",
          "statement_month",
          "beginning_balance",
          "deposits",
          "withdrawals",
          "interest_earned",
          "ending_balance"
        ],
        "additionalProperties": false
      }
    }
  }
}
```

**`ramp.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "ramp.schema.json",
  "description": "Written only by Ramp, from events on its own accounts. One <table>.json file per entry in properties.",
  "type": "object",
  "properties": {
    "ramp_card_transactions": {
      "title": "ramp_card_transactions",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"$ref": "common.schema.json#/$defs/uuid"},
          "cardholder_name": {"type": "string"},
          "cardholder_role": {"type": "string"},
          "swipe_date": {"$ref": "common.schema.json#/$defs/date"},
          "transaction_date": {"$ref": "common.schema.json#/$defs/date", "description": "Settlement date on Ramp"},
          "merchant_name": {"type": "string"},
          "amount": {
            "$ref": "common.schema.json#/$defs/money",
            "description": "Positive for spend, negative for merchant refunds"
          },
          "ramp_category": {"oneOf": [{"type": "string"}, {"type": "null"}], "description": "Noisy platform category hint"},
          "memo": {
            "oneOf": [{"type": "string"}, {"type": "null"}],
            "description": "Human-entered memo (may be null, helpful, or personal admission)"
          },
          "statement_id": {
            "oneOf": [{"$ref": "common.schema.json#/$defs/uuid"}, {"type": "null"}],
            "x-references": "ramp_statements.id"
          }
        },
        "required": [
          "id",
          "cardholder_name",
          "cardholder_role",
          "swipe_date",
          "transaction_date",
          "merchant_name",
          "amount"
        ],
        "additionalProperties": false
      }
    },
    "ramp_statements": {
      "title": "ramp_statements",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"$ref": "common.schema.json#/$defs/uuid"},
          "statement_month": {"$ref": "common.schema.json#/$defs/month"},
          "period_start": {"$ref": "common.schema.json#/$defs/date"},
          "period_end": {"$ref": "common.schema.json#/$defs/date"},
          "opening_balance": {"$ref": "common.schema.json#/$defs/money"},
          "new_charges": {"$ref": "common.schema.json#/$defs/money"},
          "payments_and_credits": {"$ref": "common.schema.json#/$defs/money"},
          "ending_balance": {"$ref": "common.schema.json#/$defs/money"},
          "autopay_date": {"oneOf": [{"$ref": "common.schema.json#/$defs/date"}, {"type": "null"}]}
        },
        "required": [
          "id",
          "statement_month",
          "period_start",
          "period_end",
          "opening_balance",
          "new_charges",
          "payments_and_credits",
          "ending_balance"
        ],
        "additionalProperties": false
      }
    }
  }
}
```

**`stripe.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "stripe.schema.json",
  "description": "Written only by Stripe, from events on its own accounts. One <table>.json file per entry in properties.",
  "type": "object",
  "properties": {
    "stripe_invoices": {
      "title": "stripe_invoices",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"$ref": "common.schema.json#/$defs/uuid"},
          "invoice_number": {"type": "string"},
          "customer_email": {"type": "string"},
          "customer_name": {"oneOf": [{"type": "string"}, {"type": "null"}]},
          "invoice_date": {"$ref": "common.schema.json#/$defs/date"},
          "service_period_start": {"$ref": "common.schema.json#/$defs/date"},
          "service_period_end": {"$ref": "common.schema.json#/$defs/date"},
          "amount_due": {"$ref": "common.schema.json#/$defs/money"},
          "status": {"type": "string", "enum": ["paid", "open", "void"]}
        },
        "required": [
          "id",
          "invoice_number",
          "customer_email",
          "invoice_date",
          "service_period_start",
          "service_period_end",
          "amount_due",
          "status"
        ],
        "additionalProperties": false
      }
    },
    "stripe_charges": {
      "title": "stripe_charges",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"$ref": "common.schema.json#/$defs/uuid"},
          "invoice_id": {
            "oneOf": [{"$ref": "common.schema.json#/$defs/uuid"}, {"type": "null"}],
            "x-references": "stripe_invoices.id"
          },
          "customer_email": {"type": "string"},
          "charge_date": {"$ref": "common.schema.json#/$defs/date"},
          "amount": {"$ref": "common.schema.json#/$defs/money"},
          "fee_amount": {"$ref": "common.schema.json#/$defs/money"},
          "net_amount": {"$ref": "common.schema.json#/$defs/money"},
          "payout_id": {
            "oneOf": [{"$ref": "common.schema.json#/$defs/uuid"}, {"type": "null"}],
            "x-references": "stripe_payouts.id",
            "description": "Set once swept into a payout batch"
          }
        },
        "required": ["id", "customer_email", "charge_date", "amount", "fee_amount", "net_amount"],
        "additionalProperties": false
      }
    },
    "stripe_refunds": {
      "title": "stripe_refunds",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"$ref": "common.schema.json#/$defs/uuid"},
          "charge_id": {
            "oneOf": [{"$ref": "common.schema.json#/$defs/uuid"}, {"type": "null"}],
            "x-references": "stripe_charges.id"
          },
          "refund_date": {"$ref": "common.schema.json#/$defs/date"},
          "amount": {"$ref": "common.schema.json#/$defs/money"},
          "reason": {"oneOf": [{"type": "string"}, {"type": "null"}]},
          "payout_id": {
            "oneOf": [{"$ref": "common.schema.json#/$defs/uuid"}, {"type": "null"}],
            "x-references": "stripe_payouts.id"
          }
        },
        "required": ["id", "refund_date", "amount"],
        "additionalProperties": false
      }
    },
    "stripe_payouts": {
      "title": "stripe_payouts",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"$ref": "common.schema.json#/$defs/uuid"},
          "payout_date": {"$ref": "common.schema.json#/$defs/date", "description": "Date initiated by Stripe"},
          "arrival_date": {"$ref": "common.schema.json#/$defs/date", "description": "Date settled in Mercury Checking X0666"},
          "gross_charges": {"$ref": "common.schema.json#/$defs/money"},
          "fees_deducted": {"$ref": "common.schema.json#/$defs/money"},
          "refunds_deducted": {"$ref": "common.schema.json#/$defs/money"},
          "net_payout_amount": {
            "$ref": "common.schema.json#/$defs/money",
            "description": "Positive for deposit, negative for expense pull"
          },
          "status": {"type": "string", "enum": ["paid", "in_transit"]}
        },
        "required": [
          "id",
          "payout_date",
          "arrival_date",
          "gross_charges",
          "fees_deducted",
          "refunds_deducted",
          "net_payout_amount",
          "status"
        ],
        "additionalProperties": false
      }
    }
  }
}
```

**`rippling.schema.json`**

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "rippling.schema.json",
  "description": "Written only by Rippling, from events on its own accounts. One <table>.json file per entry in properties.",
  "type": "object",
  "properties": {
    "rippling_journal_entries": {
      "title": "rippling_journal_entries",
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "id": {"$ref": "common.schema.json#/$defs/uuid"},
          "entry_date": {"$ref": "common.schema.json#/$defs/date"},
          "type": {"const": "Payroll Journal Entry"},
          "num": {"type": "integer", "description": "Journal number, e.g. 18, 19"},
          "description": {"type": "string"},
          "account": {"type": "string", "description": "The company's account name as set up in Rippling, e.g. 61100 - Salaries"},
          "debit": {"oneOf": [{"$ref": "common.schema.json#/$defs/money"}, {"type": "null"}]},
          "credit": {"oneOf": [{"$ref": "common.schema.json#/$defs/money"}, {"type": "null"}]}
        },
        "required": ["id", "entry_date", "type", "num", "description", "account"],
        "additionalProperties": false
      }
    }
  }
}
```

---

## 6. How real-world friction should emerge

Because each entity acts on its own schedule through channels with real delays, discrepancies appear across tables without any special-case rules. A correct world shows all of the following:

| Phenomenon | Causal chain across independent entities |
| :--- | :--- |
| **1. In-transit month-end payouts** | Customers pay on March 29-31 -> Stripe batches a payout on March 30 (`payout_date = 2021-03-30`, `arrival_date = 2021-04-01`) -> the ACH is held until April 1 -> the Mercury March statement excludes it |
| **2. Many-to-one payout batching** | Dozens of customer charges, processing fees and refunds in `stripe_*` are swept into a single net transfer that appears in `mercury_statement_line_items` simply as `Deposit - STRIPE` |
| **3. Enterprise prepayments vs. service delivery** | Contoso renews its annual contract in December 2021 (`2021-12-01` to `2022-11-30`) and wires cash up front, one cash event in Mercury for 12 months of ongoing service; other enterprise buyers sign and prepay during the period the same way |
| **4. Executive and employee personal commingling** | A weekend trip produces swipes at `APPLE STORE` and `EQUINOX` on Ramp and a personal car lease wired from Mercury X0666, mixed in with normal weekday business travel |
| **5. Ramp swipe-to-settlement cutoff lag** | A card swipe on March 30 (`swipe_date = 2021-03-30`) settles on April 1 (`transaction_date = 2021-04-01`), so it lands on the next month's Ramp statement |

Further messiness the generator should allow: inconsistent vendor descriptors across months (from each merchant's descriptor variants); late-posted rows from staff holding a payout or returning a wire; duplicates from a merchant charging twice and reversing it a few days later; blank or misleading memos, some added days after the swipe; and customers who pay late, short-pay or send a corrective wire.

### 6.1 Coverage: kinds of events and stories

Beyond the five phenomena, the world should show events of these kinds over its 18 months. Coverage only needs to be close: not every kind has to appear in every run, and amounts, dates and who is involved are up to the generator.

- **Self-serve customers:** signups through the period, monthly renewals, renewals paid a day or more late after a failed attempt, amounts off plan prices (discounts, prorations), plan changes, churn, full and partial refunds, disputes, and Stripe pulling from Mercury when refunds exceed charges.
- **Enterprise customers:** annual prepays by wire or ACH, slow approvals, a late payment, a short payment followed by a corrective wire, a mid-term expansion, a renewal.
- **Vendors:** fixed SaaS plans billed to stored Ramp cards, monthly and annual; usage bills that follow what the team used; ads billed each time spend reaches a threshold; rent by ACH or wire; Net-30 legal invoices, some for work done the month before; equipment for hires (laptops, monitors); annual prepayments such as insurance; a vendor raising its price.
- **People:** payroll on the 10th and 26th; a hire and its first payroll; business travel and client entertainment; personal charges on company cards, some admitted in memos and some left blank; personal payments from company accounts; a personal charge paid back; memos written days after the swipe.
- **Merchants:** a returned item refunded to a card; a double charge reversed a few days later.
- **Institutions:** payouts in transit at month end; a change in payout schedule; a Stripe pull and a payout on the same day; a payout held for review; a returned wire; Ramp statements and autopay; monthly interest and fees; large transfers into Treasury and smaller ones back to checking; account labels that differ between places (X3354 as checking or savings).
- **Stories:** the chains in sections 4.1 and 4.2, and others like them for different people and months.

---

## 7. What the generator should produce from this prompt

1. **World:** name, the time range in section 2, and currency.
2. **Institutions:** the four in section 3.4, each declared with its payment methods, mechanics and the tables in section 5, and each with a staff node.
3. **Entities and nodes:** the cast in section 3, each with a prompt carrying its personality and its history, and each node with its first brief for January 2021. Self-serve subscribers are individual actors, created many at a time; enterprise customers, key vendors and the five people are individual too.
4. **Catalog:** the merchants people buy from, each with descriptor variants (`descriptors`), acted for by the market.
5. **Relationships:** the edges in section 4, with terms where they are fixed (Contoso's amount and dates, rent, plan prices, payroll dates) and prompts where they are loose (when a customer pays, how an executive behaves). Cards on file and authorized debits are pulls the payee collects.
6. **Seed:** the history in section 2.1.
7. **Stories and noise:** the stories in sections 4.1 and 4.2, and enough others to cover section 6.1, spread across people and months.
