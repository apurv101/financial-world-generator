# Declaring an institution

An institution is declared in the manifest, not coded. The declaration picks which payment methods the institution handles and how they settle, configures the generic mechanisms it runs, and says how each of its tables is built from what happens on its accounts. The engine has no code for any particular bank, card issuer or processor.

This document defines the language, checks it against the four institutions of `examples/saas_startup` (Mercury, Ramp, Stripe, Rippling), and records what the language had to add for them (section 8). Their declarations are in `examples/saas_startup/manifest.yaml`, and their table schemas in `examples/saas_startup/schemas/`.

## 1. How an institution sees money

- **Movement.** What one act tool, staff tool or mechanism moves between two accounts. A movement with a payment method is two linked events: an *initiation* (source account to the method's clearing account) and a *settlement* (clearing account to destination) on the settle day the settlement rules pick. A mechanism's movements inside one institution (interest, a fee, a split leg) have no method and settle at once. A movement a mechanism makes is initiated by the institution that runs it.
- **Posting.** One side of a movement on an account the institution holds. A transfer between two of its own accounts has two postings. A posting is known from initiation; its settle day is scheduled then and final when it settles.
- **Direction.** `in` when money arrives on the account, `out` when it leaves.
- **Counterparty.** The party on the other side: the holder of the other account. If that holder is also this account's holder, it is the other account's institution, so a payout from a company's Stripe balance to its own Mercury account shows Stripe on the Mercury side. For a mechanism's own movements (interest, a fee) it is the institution itself.
- **Record.** A zero-amount record event on an account the institution holds: `bill`, `record_activity`, `authorize`, `revoke`, `annotate`, and an obligation coming due (P3).
- **Own account.** Every institution has an implicit account of its own. Fees go into it and interest comes out of it, and it may go negative.

Rows are built only from postings and records on the institution's own accounts. That is the isolation rule, and nothing in the language can break it.

## 2. Declaration fields

```yaml
institutions:
  - id: inst_x            # the institution's entity
    calendar: us_federal  # its business days
    methods: {...}        # payment methods and their settlement rules
    mechanisms: {...}     # the generic mechanisms it runs, each configured
    tables: {...}         # its output tables
```

### `calendar`

The business-day calendar its settlement, holds and sweeps count in: `us_federal` (Federal Reserve holidays) or `every_day`.

### `methods`

One entry per payment method the institution handles. Together, these entries configure the settlement mechanism.

| Key | Meaning | Default |
|---|---|---|
| `settle_days` | `[min, max]` days from initiation to settlement, picked with `Rng` | required |
| `count` | `business` or `calendar` days | `business` |
| `settles_on` | `business_day`, or `any_day` for a method that posts on weekends and holidays (cards) | `business_day` |

Which institution's rules a payment follows is policy `settlement_rules` (by default, the initiating side's).

### `mechanisms`

Each mechanism is one engine class. An institution lists the ones it runs, with their config. Every `on` filter uses the posting filter keys in section 3.

| Mechanism | Config | What it does | Columns can read |
|---|---|---|---|
| `split` | named legs, each with `on`, `percent`, `fixed`, `mode` and `to` (`own` or an entity id) | `carve`: at settlement the payee receives the amount less the leg, and the leg goes to `to` (a processor fee, tax withholding). `add`: the payer also pays the leg, as its own movement with the same method, linked to the parent (employer tax). A leg's events have action `split` and the leg's name. Legs never trigger splits. | `split.<leg>`, `split.net` |
| `hold` | `on`, `days`, `count` | Money arriving on a matching posting is not available until the hold ends (an availability delay). Staff `hold` and `release` add and free holds by hand. | |
| `sweep` | when: `every` (`business_day`, `week`, `month`), `after: statement` with `delay_days`, or `when: negative`; `direction` (`out` to the linked account, `in` from it, or `both`); `amount` (`available`, `statement.closing` or `shortfall`); `method`; optional `parts`; optional `setting` (P5) | Moves money between an account and its `linked` account on a schedule: payouts, autopay, a pull when a balance goes negative. The sweep links the postings it carries. `parts` splits one sweep into named movements, each with a memo and an amount; `rest` takes the remainder. | `sweep.id`, `links`, `statement.sweep` |
| `statement` | `every: month`, optional `close_day`, `per: account`, `by: settled` or `initiated` | Closes a statement each cycle with an opening and closing balance, and the postings in it in order, each with a running balance. | `statement.*`, `line.running_balance` |
| `interest` | `on`, `basis: daily_balance`, `day_count` (`actual_365` or `actual_360`), `post: month_end` | Accrues on each matching account at its `rate`, and posts a movement from the institution's own account with action `interest`. | |
| `numbering` | named counters, each with `for` (a posting or record filter, or `entries`) and `per` (`institution`, `payer` or `account`) | Gives each matching posting, record or entry the next number of its counter. | `counter.<name>` |
| `descriptors` | none | Renders how a party appears on a row: a random pick from its `descriptors`, with `{ref}` replaced by a random code. It is always on. | `<party>.descriptor` |

### `tables`

Each table has a `schema` (a JSON Schema file for `<table>.json`, an array of rows; each row is checked as it renders), optionally a `sign`, its `rows`, and its `columns`, which give exactly one source for every property in the schema.

## 3. Rows

| `rows.from` | One row per | Renders | Notes |
|---|---|---|---|
| `postings` | posting on the institution's accounts | `when: initiated` or `when: settled` | Its source unit is the posting, with its movement's events. |
| `statement_lines` | posting on a closed statement | when the statement closes | |
| `statements` | closed statement | when it closes | |
| `records` | record on the institution's accounts | when the record is made | An obligation's record renders again when its status changes. |
| `entries` | line of a grouped entry | when the group is made | `group: call` groups the events one call emitted, with the split legs they triggered (P6). `lines` declares each line's `account`, `debit` and `credit` sources. |

**Filters.** `rows.where`, and every mechanism's `on`, take these keys. A key may hold one value or a list (any of them). `{not: x}` excludes.

| Key | Matches on |
|---|---|
| `action` | the act tool, staff tool or mechanism that produced the event (`pay`, `collect`, `sweep`, `split`, `interest`, `adjust`, `reverse`, `obligation`, `bill`, ...) |
| `method` | the payment method |
| `direction` | `in` or `out` |
| `account`, `account_kind` | the account's id, or its `kind` label |
| `returns` | `present` for a refund or reversal of an earlier movement, `absent` otherwise |
| `obligation` | `present` when the movement answers an obligation |
| `leg` | the split leg's name |
| `rate` | `present` for an account with an interest rate |

**Sign.** `sign: inflow_positive` (the default) makes money arriving on the account positive. `sign: outflow_positive` flips it, for card issuers (spend is positive), payouts and refunds. The sign applies to every money value the table reads from postings, statements and sums.

**Updates.** Rows are keyed by id, and rendering an id again replaces the row. A row renders again when:

| Trigger | What changes | Tables in `saas_startup` |
|---|---|---|
| its movement settles | `event.settled` and `event.status` become final | `stripe_payouts` (status and arrival date) |
| staff hold or release it | `event.settled` moves | any posting rendered `when: initiated` |
| a sweep carries it | `sweep.id` is set | `stripe_charges`, `stripe_refunds` |
| its statement closes | `statement.id` is set | `ramp_card_transactions` |
| a statement's sweep runs | `statement.sweep.day` is set | `ramp_statements` |
| it is annotated | `event.memo` changes | `ramp_card_transactions` |
| its obligation's status changes | `obligation.status` | `stripe_invoices` |

Every render logs `row_rendered` with the events the row links to.

## 4. Column sources

A source is one of these:

| Form | Example | Meaning |
|---|---|---|
| path | `event.memo` | a value from the row's source unit (below) |
| `null` | `null` | null |
| `const` | `{const: Payroll Journal Entry}` | a fixed value |
| `template` | `{template: "#{payer.fields.invoice_prefix}-{counter.invoice:04}"}` | paths in braces, with an optional zero-padded width |
| `map` | `{map: obligation.status, values: {cancelled: void}, else: {const: open}}` | look a value up; the values are literals, and `else` is a source |
| `match` | `{match: [{when: {action: interest}, value: {const: Interest}}], else: counterparty.name}` | the first `when` (a filter) that matches gives the `value` source |
| `sum` | `{sum: links, where: {action: collect}, of: event.amount, magnitude: true}` | sums over `links`, `statement.lines`, `group` or (in a sweep's `parts`) `carried`. `of` defaults to the signed `posting.amount`, and `magnitude` drops the sign. |

A path that doesn't resolve gives null, and the row's schema check catches a required column left null.

**Paths:**

| Path | Value |
|---|---|
| `event.id`, `event.day`, `event.amount`, `event.method`, `event.memo`, `event.details.<key>`, `event.cause` | the movement's initiation event or the record event: `day` is the initiation day, and `amount` is unsigned |
| `event.settled`, `event.status` | the settle day (scheduled until final), and `pending`, `held` or `settled` |
| `posting.id`, `posting.amount`, `posting.direction` | the posting's stable id, and its amount signed by the table's `sign` |
| `account.id`, `.name`, `.kind`, `.linked.name` | the account the row is on |
| `other_account.name` | the account on the other side |
| `instrument.issued_to.name`, `instrument.issued_to.fields.<key>` | the card used, and the person it was issued to (P1) |
| `payer`, `payee`, `counterparty`, `actor`, each with `.name`, `.descriptor`, `.category`, `.fields.<key>` | parties. `actor` is the entity of the node that made the call (the institution, for a mechanism). `category` is a catalog party's category. |
| `obligation.id`, `.amount`, `.status` | the obligation a movement answers or a record opens. The id is its record's id. The status is `open`, `paid`, `short_paid`, `skipped`, `cancelled` or `disputed`. |
| `returns.id` | the id of the returned movement's posting on the same account |
| `split.<leg>`, `split.net` | a leg's amount, and the amount less carve legs |
| `sweep.id` | the posting id of the sweep that carried this posting |
| `statement.id`, `.month`, `.period_start`, `.period_end`, `.opening`, `.closing`, `.sweep.day` | the posting's statement, or the row's statement |
| `line.running_balance` | the balance after a statement line |
| `line.id`, `line.account`, `line.debit`, `line.credit`, `group.day` | an entry's line and group |
| `counter.<name>` | the number the numbering mechanism gave this unit |

Ids are UUIDs derived from the unit (a posting, a record, a statement, an entry line), so a unit has the same id in every table and in every rerun of a render. A seeded movement's posting keeps its id.

## 5. Seeding mechanism state

The seed gives each mechanism the state it would have on `start`:

| Mechanism | Seeded state | `saas_startup` |
|---|---|---|
| settlement | movements in flight, with their initiation days and arrival days | the December 30 Stripe payout arriving 01-04; December 30-31 Ramp swipes |
| hold | held postings and when each hold ends | Stripe charges from December 30-31 |
| statement | the last closed statement per account: its id, period, closing balance, and whether its sweep has run | Ramp's December statement, unpaid; Mercury's December statements |
| sweep | the next run, for `every` schedules | Stripe's next business-day payout |
| numbering | each counter's next number, per `per` key | Rippling's `journal` at 14; each subscriber's invoice counter |

## 6. Coverage: every SaaS column

`mercury_transactions` (rows: postings, rendered when settled)

| Column | Source |
|---|---|
| `id` | `posting.id` |
| `account_name` | `account.name` |
| `transaction_date` | `event.day` |
| `posted_date` | `event.settled` |
| `description` | match: interest -> "Interest Accrual"; `book` out/in -> "Transfer to/from {other_account.name}"; `adjust` -> `event.memo`; else `counterparty.descriptor` |
| `amount` | `posting.amount` (inflow positive) |
| `transaction_type` | match: interest -> Interest; `adjust` -> Fee; `book` -> Internal Transfer; `wire` -> Wire; `ach` in -> ACH Credit; `ach` out -> ACH Debit |
| `counterparty_name` | match: interest, `adjust` or `book` -> null; else `counterparty.name` |

`mercury_statement_line_items` (rows: statement lines)

| Column | Source |
|---|---|
| `id` | `posting.id` |
| `statement_month` | `statement.month` |
| `account_name` | map: `a_x3354` -> "Mercury Savings X3354"; else `account.name` |
| `date` | `event.settled` |
| `description` | as in `mercury_transactions` (a YAML anchor) |
| `amount` | `posting.amount` |
| `running_balance` | `line.running_balance` |

`mercury_treasury_records` (rows: statements of accounts of kind `treasury`)

| Column | Source |
|---|---|
| `id` | `statement.id` |
| `statement_month` | `statement.month` |
| `beginning_balance` | `statement.opening` |
| `deposits` | sum of lines in, excluding interest, as a magnitude |
| `withdrawals` | sum of lines out, as a magnitude |
| `interest_earned` | sum of interest lines |
| `ending_balance` | `statement.closing` |

`ramp_card_transactions` (rows: `card` postings, rendered when settled, outflow positive)

| Column | Source |
|---|---|
| `id` | `posting.id` |
| `cardholder_name` | `instrument.issued_to.name` (P1) |
| `cardholder_role` | `instrument.issued_to.fields.title` (P1) |
| `swipe_date` | `event.day` |
| `transaction_date` | `event.settled` |
| `merchant_name` | `counterparty.descriptor` |
| `amount` | `posting.amount` |
| `ramp_category` | `counterparty.category` |
| `memo` | `event.memo` |
| `statement_id` | `statement.id` |

`ramp_statements` (rows: statements, outflow positive)

| Column | Source |
|---|---|
| `id` | `statement.id` |
| `statement_month` | `statement.month` |
| `period_start`, `period_end` | `statement.period_start`, `statement.period_end` |
| `opening_balance` | `statement.opening` |
| `new_charges` | sum of `card` lines out |
| `payments_and_credits` | sum of lines in, as a magnitude |
| `ending_balance` | `statement.closing` |
| `autopay_date` | `statement.sweep.day` |

`stripe_invoices` (rows: `obligation` and `bill` records)

| Column | Source |
|---|---|
| `id` | `event.id` |
| `invoice_number` | template "#{payer.fields.invoice_prefix}-{counter.invoice:04}" |
| `customer_email` | `payer.fields.email` |
| `customer_name` | `payer.name` |
| `invoice_date` | `event.day` |
| `service_period_start`, `service_period_end` | `event.details.period_start`, `event.details.period_end` (P3) |
| `amount_due` | `obligation.amount` |
| `status` | map `obligation.status`: paid -> paid; cancelled or skipped -> void; else open |

`stripe_charges` (rows: `collect` postings by `card`, rendered when initiated)

| Column | Source |
|---|---|
| `id` | `posting.id` |
| `invoice_id` | `obligation.id` |
| `customer_email` | `payer.fields.email` |
| `charge_date` | `event.day` |
| `amount` | `event.amount` (the gross) |
| `fee_amount` | `split.fee` |
| `net_amount` | `posting.amount` (what reached the balance) |
| `payout_id` | `sweep.id` |

`stripe_refunds` (rows: `card` postings out that return a charge, outflow positive)

| Column | Source |
|---|---|
| `id` | `posting.id` |
| `charge_id` | `returns.id` |
| `refund_date` | `event.day` |
| `amount` | `posting.amount` |
| `reason` | match: `reverse` (a lost dispute) -> "dispute"; else `event.memo` |
| `payout_id` | `sweep.id` |

`stripe_payouts` (rows: `sweep` postings, rendered when initiated, outflow positive)

| Column | Source |
|---|---|
| `id` | `posting.id` |
| `payout_date` | `event.day` |
| `arrival_date` | `event.settled` |
| `gross_charges` | sum of carried `collect` postings, of `event.amount` |
| `fees_deducted` | sum of carried `collect` postings, of `split.fee` |
| `refunds_deducted` | sum of carried postings that return a charge, as a magnitude |
| `net_payout_amount` | `posting.amount` (a pull from the bank is negative) |
| `status` | map `event.status`: settled -> paid; else in_transit |

`rippling_journal_entries` (rows: entry lines, one entry per payroll call, P6)

| Column | Source |
|---|---|
| `id` | `line.id` |
| `entry_date` | `group.day` |
| `type` | const "Payroll Journal Entry" |
| `num` | `counter.journal` |
| `description` | template "Payroll {group.day}" |
| `account` | `line.account`: "61100 - Salaries", "61200 - Employer Payroll Tax", "11100 - {account.linked.name}" |
| `debit` | `line.debit`: gross pay (sum of `pay` amounts), then employer tax (sum of `employer_tax` legs), then null |
| `credit` | `line.credit`: null, null, then everything the group paid out. It equals the two debits, so every entry balances. |

No column is left without a source, and none needs custom code.

## 7. Coverage: every money flow and behavior

| TARGET | Produced by | Tables it reaches |
|---|---|---|
| **3.4 Stripe fee** 2.9% + $0.30 | split `fee` (carve, to Stripe's own account) | `stripe_charges.fee_amount`, `stripe_payouts.fees_deducted` |
| **3.4 Stripe availability** about two days | hold, 2 business days | when charges join a payout |
| **3.4 Stripe daily payouts** | sweep, `every: business_day`, `direction: both`, by `ach` (1-2 business days) | `stripe_payouts`, Mercury "Deposit - STRIPE" |
| **3.4 Stripe pulls** when refunds exceed charges | the same sweep pulling the shortfall from the linked account | negative `stripe_payouts` row, Mercury "Stripe - Expense - STRIPE" (P2) |
| **3.4 Ramp settlement and cutoff** | `card` settles in 1-3 days on any day; statement `by: settled` closes at month end | `swipe_date` vs `transaction_date`; phenomenon 5 |
| **3.4 Ramp autopay** | sweep `after: statement`, `delay_days: 3`, pulling `statement.closing` by `ach` | `ramp_statements.autopay_date`, Mercury ACH Debit |
| **3.4 Rippling numbered, balanced entries** | handler's `answer_obligation` paying everyone from the payroll account; split `withholding` (carve) and `employer_tax` (add); numbering `journal` per entry | `rippling_journal_entries` |
| **3.4 Rippling's Mercury debits** for net pay and taxes | sweep `when: negative` with `parts` Net Pay and Taxes | two Mercury ACH Debits per run |
| **3.4 Mercury statements** | statement per account, monthly, `by: settled` | `mercury_statement_line_items`, `mercury_treasury_records` |
| **3.4 Mercury interest** | interest on accounts with a `rate`, posted at month end | `Interest` rows, `interest_earned` |
| **3.4 Mercury service fees** | staff `adjust` | `Fee` rows |
| **3.4 Merchants refund returns** | the market's `pay` with `returns`, to the card account (P8) | negative `ramp_card_transactions` row |
| **3.4 A duplicate charge, reversed** | Ramp staff `adjust` the duplicate, then its reversal (P7) | `ramp_card_transactions` |
| **4 Self-serve customer -> company** | an obligation from pull terms (record: P3); the company handler's `collect` under the card on file into the Stripe account (P4); split, hold, sweep | `stripe_invoices`, `stripe_charges`, `stripe_payouts`, Mercury |
| **4 Enterprise customer -> company** | the customer handler's `answer_obligation` -> `pay` by `wire` or `ach` | Mercury ACH Credit or Wire |
| **4 Refunding customer -> Stripe** | the company handler's `pay` by `card` with `returns`, from the Stripe account; the sweep nets or pulls | `stripe_refunds`, `refunds_deducted`, pulls |
| **4 Company -> vendor (card)** | the market's `collect` under a mandate on a Ramp card | `ramp_card_transactions`, `ramp_statements` |
| **4 Company -> vendor (ACH or invoice)** | the vendor handler's `collect` under a mandate on X0666, or its `bill` then the company handler's `pay` | Mercury ACH Debit |
| **4 Company -> landlord** | `answer_obligation` -> `pay` by `ach` or `wire` | Mercury |
| **4 Employee -> company (salary)** | as for Rippling above | Rippling, Mercury |
| **4 Person -> Ramp card** | the actor's `pay` by `card` with its card (P1); `annotate` for late memos | `ramp_card_transactions` |
| **4 Executive -> Mercury** | the actor's `pay` by `wire` or `ach` from X0666 under access | Mercury |
| **4 Ramp -> Mercury** | Ramp autopay above | |
| **4 Company -> Treasury** | `pay` by `book` between own accounts; interest | Mercury, `mercury_treasury_records` |
| **4.1 NYC trip** | four card `pay`s with memos, one blank; one `ach` `pay` from X0666 | Ramp, Mercury |
| **4.2 Parking seed money; running down checking** | `book` transfers sized by the actor | Mercury |
| **4.2 Refunds outrun charges** | refunds, then the sweep pulls; a payout settling the same day | Stripe, Mercury |
| **4.2 A hire** | narrator spawns the hire with a card (P1) and an employment relationship; equipment `pay`s; a prorated first payroll answer | Ramp, Rippling |
| **4.2 GPU experiment and ad push** | card `pay`s at RunPod; `record_activity` of compute and ad spend; usage `collect`s by the market | Ramp |
| **4.2 Payouts go weekly** | Morgan changes the payout `setting` from `business_day` to `week` (P5) | fewer, larger `stripe_payouts` |
| **4.2 Annual renewals** | `pay`s and `collect`s with yearly terms | Ramp, Mercury |
| **4.2 Contoso renewal** | counsel's `bill`; Contoso's `answer_obligation` paying late and short, then a corrective `pay` | Mercury |
| **4.2 Personal charge paid back** | a personal card `pay` with its memo; later Sam's `pay` by `ach` from a personal bank to the company | Ramp, Mercury ACH Credit |
| **6 phenomena 1-5** | 1: sweep on 03-30 by `ach` (1-2 business days) settles 04-01, after Mercury's March statement. 2: one sweep carries many charges, fees and refunds. 3: a yearly push obligation. 4: actor choices. 5: card settle days and a statement `by: settled`. | |
| **6 held payout, returned wire** | Stripe staff `hold`/`release` on the sweep; Mercury staff `reverse` | `arrival_date` moves; a Wire credit |

## 8. What the language added (accepted 2026-10-31)

The SaaS institutions needed eight changes beyond SPEC. The user accepted each one, and SPEC takes them in at Checkpoint 0.

**P1. Cards under one account.** An account can carry `instruments: [{id, issued_to, name}]`, each a card issued to an entity. A card `pay` uses the card issued to the actor's entity, or a card the call names. A mandate names a card. Postings carry the card, and columns read `instrument.issued_to.*`. Narrators add a card with `open_account` on an existing account (the hire in 4.2). This is why Ramp has one statement and one autopay for the company, and still names the cardholder on every row, including charges a vendor collects from a card on file.

**P2. Descriptors by direction.** `descriptors` may be a map `{in: [...], out: [...]}`, seen from the account the row is on. A plain list applies both ways. Mercury shows Stripe as "Deposit - STRIPE" on a payout and "Stripe - Expense - STRIPE" on a pull.

**P3. Obligations make a record when they come due.** An obligation from terms emits a zero-amount record event (`action: obligation`) when it comes due. For recurring terms its details include `period_start` and `period_end`. A bill's own record event plays this part for bills. The events that answer it link it, and rows from it render again when its status changes. Stripe invoices come from these records.

**P4. Pull obligations are recorded on the payee's collecting account.** Terms' `to_account` is read for pull terms under every policy, as the account the obligation is collected into. A subscription's invoices therefore land at Stripe before any `collect`.

**P5. `change_setting`.** A mechanism can mark one config key as a `setting`, with its allowed values (here the sweep's `every`, named `payout_schedule`). A new act tool, `change_setting(account, setting, value)`, lets an actor with access to the account change it. It is validated like any act tool and emits a zero-amount record event. This is how Morgan moves Stripe payouts to weekly.

**P6. Events record their call.** Events carry `call`, the id of the tool call or mechanism run that emitted them. The `entries` row source groups by it, so each payroll run is one Rippling entry.

**P7. Double charges come from the card issuer's staff.** Ramp's staff post a duplicate of a merchant's charge, and its reversal a few days later, with `adjust`. TARGET 3.4 says so.

**P8. Refunds return to their source by default.** Policy `receiving_account`'s default, `first_supporting`, also sends a refund back to the account it came from. Without this, a merchant's refund to the company could land in its Stripe balance, which also supports `card`.

### Known simplifications (no change proposed)

- Rippling pulls payroll funds from Mercury after payday, at the day close, instead of a few days before. The result is still the right debits, a little late.
- Withholding and employer tax are flat rates (22% and 12.8%, where TARGET's $3,200 on $25,000 gives 12.8%).
- `mercury_transactions.transaction_date` is the initiation day, which for incoming money is the day the sender initiated it.
- `mercury_treasury_records` reports deposits and withdrawals as magnitudes.
