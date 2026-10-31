# Declaring an institution

An institution is declared in the manifest, not coded. The declaration picks which payment methods the institution handles and how they settle, configures the generic mechanisms it runs, and says how each of its tables is built from what happens on its accounts. The engine has no code for any particular bank, card issuer or processor.

This document defines the language and checks it against two industries:
- the four institutions of `examples/saas_startup` (Mercury, Ramp, Stripe, Rippling), which the language was written for
- the three of `examples/trucking` (Prairie Hollow Bank, the RoadFleet fuel card and Ironbridge Freight Funding, a factoring company), which it was not

Each example's declarations are in its `manifest.yaml`, and its table schemas in its `schemas/`. Section 8 records what each industry made the language add: P1-P8 for SaaS, accepted, and T1-T6 for trucking, proposed for the user to decide. A trucking addition is marked "(T*n*, proposed)" where it appears.

## 1. How an institution sees money

- **Movement.** What one act tool, staff tool or mechanism moves between two accounts. A movement with a payment method is two linked events: an *initiation* (source account to the method's clearing account) and a *settlement* (clearing account to destination) on the settle day the settlement rules pick. A mechanism's movements inside one institution (interest, a fee, a split leg) have no method and settle at once. A movement a mechanism makes is initiated by the institution that runs it.
- **Posting.** One side of a movement on an account the institution holds. A transfer between two of its own accounts has two postings. A posting is known from initiation; its settle day is scheduled then and final when it settles.
- **Direction.** `in` when money arrives on the account, `out` when it leaves.
- **Counterparty.** The party on the other side: the holder of the other account. If that holder is also this account's holder, it is the other account's institution, so a payout from a company's Stripe balance to its own Mercury account shows Stripe on the Mercury side. For a mechanism's own movements (interest, a fee) it is the institution itself.
- **Record.** A zero-amount record event on an account the institution holds: `bill`, `record_activity`, `authorize`, `revoke`, `annotate`, and an obligation coming due (P3).
- **Own account.** Every institution has an implicit account of its own. Fees go into it, and interest and advances (T5, proposed) come out of it. It may go negative, and it has no rows of its own: rows come only from the accounts the institution holds for others.

Rows are built only from postings and records on the accounts the institution holds. That is the isolation rule, and nothing in the language can break it.

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
| `sweep` | when: `every` (`business_day`, `week` with a `day` such as `friday` (T3, proposed), or `month`), `after: statement` with `delay_days`, or `when: negative`; `direction` (`out` to the linked account, `in` from it, or `both`); `amount` (`available`, `statement.closing` or `shortfall`); `method`; optional `parts`; optional `setting` (P5) | Moves money between an account and its `linked` account on a schedule: payouts, autopay, a pull when a balance goes negative. The sweep links the postings it carries. `parts` splits one sweep into named movements, each with a memo and an amount; `rest` takes the remainder. A scheduled day that is not a business day runs on the next one. | `sweep.id`, `links`, `statement.sweep` |
| `statement` | `every: month` with an optional `close_day` (a day of the month), or `every: week` with a `close_day` weekday (T3, proposed); `per: account`; `by: settled` or `initiated` | Closes a statement each cycle with an opening and closing balance, and the postings in it in order, each with a running balance. A weekly statement's `statement.month` is the month its period ends in. | `statement.*`, `line.running_balance` |
| `advance` (T5, proposed) | `on` (a record filter), `percent`, `method` | When a matching record opens an obligation that is to be paid into the account, the institution pays `percent` of the obligation's amount from its own account to the account's `linked` account by `method`. It pays at that day's close, with action `advance`, linked to the record. When a payment that answers the obligation settles into the account, what is left after its carve legs first repays whatever of the advance is still outstanding, to the institution's own account; only the rest lands. Staff `hold` and `release` an advance like any movement. Staff `reverse` charges it back (recourse), for an `amount` up to what is outstanding, and what is reversed is no longer outstanding. | `advance.*` |
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

| Trigger | What changes | Tables in the examples |
|---|---|---|
| its movement settles | `event.settled` and `event.status` become final | `stripe_payouts` (status and arrival date) |
| staff hold or release it | `event.settled` moves | any posting rendered `when: initiated` |
| a sweep carries it | `sweep.id` is set | `stripe_charges`, `stripe_refunds` |
| its statement closes | `statement.id` is set | `ramp_card_transactions`, `roadfleet_transactions` |
| a statement's sweep runs | `statement.sweep.day` is set | `ramp_statements`, `roadfleet_statements` |
| it is annotated | `event.memo` changes | `ramp_card_transactions` |
| its obligation's status changes | `obligation.status` | `stripe_invoices`, `ironbridge_purchased_invoices` |
| its advance is held, released, settles, recovers or is charged back (T5, proposed) | `advance.*` | `ironbridge_purchased_invoices` |

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

A path that doesn't resolve gives null, and the row's schema check catches a required column left null. Under T6 (proposed), a detail that a table reads is also checked against its column's schema when the act tool is called.

**Paths:**

| Path | Value |
|---|---|
| `event.id`, `event.day`, `event.amount`, `event.method`, `event.memo`, `event.details.<key>`, `event.cause` | the movement's initiation event or the record event: `day` is the initiation day, and `amount` is unsigned |
| `event.settled`, `event.status` | the settle day (scheduled until final), and `pending`, `held` or `settled` |
| `posting.id`, `posting.amount`, `posting.direction` | the posting's stable id, and its amount signed by the table's `sign` |
| `posting.balance_after` | the account's balance just after this posting settled, signed like `posting.amount`. Postings settle in a fixed order within a day, the one statement lines use, so it equals the line's `line.running_balance`. Only in rows from postings rendered `when: settled` (T1, proposed). |
| `account.id`, `.name`, `.kind`, `.linked.name` | the account the row is on |
| `other_account.name` | the account on the other side |
| `instrument.name`, `instrument.issued_to.name`, `instrument.issued_to.fields.<key>` | the card used, by its own name (T2, proposed), and the party it was issued to (P1) |
| `payer`, `payee`, `counterparty`, `actor`, each with `.name`, `.descriptor`, `.category`, `.fields.<key>` | parties. `actor` is the entity of the node that made the call (the institution, for a mechanism). `category` is a catalog party's category. |
| `obligation.id`, `.amount`, `.status` | the obligation a movement answers or a record opens. The id is its record's id. The status is `open`, `paid`, `short_paid`, `skipped`, `cancelled` or `disputed`. |
| `returns.id` | the id of the returned movement's posting on the same account |
| `split.<leg>`, `split.net` | a leg's amount, and the amount less carve legs |
| `advance.amount`, `.day`, `.status`, `.charged_back` | on a record's row, the advance made against its obligation: its amount, the day it was paid, its status (`pending`, `held`, `funded` or `charged_back`) and the total charged back (T5, proposed) |
| `advance.recovered` | on a payment's row, how much of an advance it repaid (T5, proposed) |
| `sweep.id` | the posting id of the sweep that carried this posting |
| `statement.id`, `.month`, `.period_start`, `.period_end`, `.opening`, `.closing`, `.sweep.day` | the posting's statement, or the row's statement |
| `line.running_balance` | the balance after a statement line |
| `line.id`, `line.account`, `line.debit`, `line.credit`, `group.day` | an entry's line and group |
| `counter.<name>` | the number the numbering mechanism gave this unit |

Ids are UUIDs derived from the unit (a posting, a record, a statement, an entry line), so a unit has the same id in every table and in every rerun of a render. A seeded movement's posting keeps its id.

## 5. Seeding mechanism state

The seed gives each mechanism the state it would have on `start`:

| Mechanism | Seeded state | `saas_startup` | `trucking` |
|---|---|---|---|
| settlement | movements in flight, with their initiation days and arrival days | the December 30 Stripe payout arriving 01-04; December 30-31 Ramp swipes | December 30-31 fuel purchases; checks written in late December, not yet cleared; a debtor's check in the mail to Ironbridge; the advance on December 29's invoices, arriving 01-02 |
| hold | held postings and when each hold ends | Stripe charges from December 30-31 | none |
| statement | the last closed statement per account: its id, period, closing balance, and whether its sweep has run | Ramp's December statement, unpaid; Mercury's December statements | RoadFleet's statement closed Sunday December 31, autopay due 01-03; Prairie Hollow's December statement |
| sweep | the next run, for `every` schedules | Stripe's next business-day payout | Ironbridge's next reserve release, Friday 01-05 |
| numbering | each counter's next number, per `per` key | Rippling's `journal` at 14; each subscriber's invoice counter | Prairie Hollow's `check` at 5214; Ironbridge's `invoice` at 3142 |
| advance (T5, proposed) | each advanced obligation still open: its advance, status, and what has been recovered or charged back | | about forty purchased invoices, unpaid, with their advances funded |

## 6. Coverage: every column

### `saas_startup`

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

### `trucking`

`prairie_hollow_transactions` (rows: postings, rendered when settled)

| Column | Source |
|---|---|
| `id` | `posting.id` |
| `account_name` | `account.name` |
| `posted_date` | `event.settled` |
| `description` | match: `check` out -> "CHECK {counter.check}"; `check` in -> "REMOTE DEPOSIT"; leg `wire_fee` -> "OUTGOING WIRE FEE"; `adjust` -> `event.memo`; `wire` out/in -> "WIRE OUT/IN {counterparty.name}"; `advance` -> "{counterparty.descriptor} DES:ADVANCE"; `sweep` in -> "{counterparty.descriptor} DES:RESERVE"; else `counterparty.descriptor`, where P2's outgoing names cover Ironbridge's charge-backs and RoadFleet's autopay |
| `check_number` | `counter.check` |
| `amount` | `posting.amount` (inflow positive) |
| `running_balance` | `posting.balance_after` (T1) |

`prairie_hollow_statements` (rows: statements)

| Column | Source |
|---|---|
| `id` | `statement.id` |
| `account_name` | `account.name` |
| `statement_month` | `statement.month` |
| `period_start`, `period_end` | `statement.period_start`, `statement.period_end` |
| `beginning_balance` | `statement.opening` |
| `deposits_and_credits` | sum of lines in |
| `checks_paid` | sum of `check` lines out, as a magnitude |
| `other_debits` | sum of lines out other than checks, `adjust` and split legs, as a magnitude |
| `service_charges` | sum of `adjust` and split lines out, as a magnitude |
| `ending_balance` | `statement.closing` |

`roadfleet_transactions` (rows: `card` postings, rendered when settled, outflow positive)

| Column | Source |
|---|---|
| `id` | `posting.id` |
| `transaction_date` | `event.day` |
| `post_date` | `event.settled` |
| `card` | `instrument.name`, such as "Unit 103" (T2) |
| `driver_id` | `actor.fields.driver_id` |
| `odometer` | `event.details.odometer` (T6) |
| `merchant_name` | `counterparty.descriptor` |
| `city`, `state` | `event.details.city`, `event.details.state` (T6) |
| `product` | `event.details.product` (T6) |
| `gallons`, `price_per_gallon` | `event.details.gallons`, `event.details.price_per_gallon` (T6) |
| `amount` | `posting.amount` |
| `statement_id` | `statement.id` |

`roadfleet_statements` (rows: weekly statements, outflow positive)

| Column | Source |
|---|---|
| `id` | `statement.id` |
| `period_start`, `period_end` | `statement.period_start`, `statement.period_end` |
| `previous_balance` | `statement.opening` |
| `purchases` | sum of `card` lines out |
| `credits` | sum of lines in other than the autopay, as a magnitude |
| `payments` | sum of `sweep` lines, as a magnitude |
| `new_balance` | `statement.closing` |
| `autopay_date` | `statement.sweep.day` |

`ironbridge_purchased_invoices` (rows: `bill` records)

| Column | Source |
|---|---|
| `id` | `event.id` |
| `invoice_number` | template "{payee.fields.invoice_prefix}{counter.invoice:05}" |
| `load_number` | `event.details.load_number` (T6) |
| `debtor_name` | `payer.name` |
| `invoice_date` | `event.day` |
| `invoice_amount` | `obligation.amount` |
| `advance_amount` | `advance.amount` (T5) |
| `purchase_date` | `advance.day` (T5) |
| `status` | map `obligation.status`: paid -> Closed, short_paid -> Short Paid, disputed -> Disputed, cancelled -> Cancelled; else map `advance.status` (T5): held -> Pending Verification, charged_back -> Charged Back; else Open |
| `chargeback_amount` | `advance.charged_back` (T5) |

`ironbridge_reserve_activity` (rows: postings, rendered when settled)

| Column | Source |
|---|---|
| `id` | `posting.id` |
| `date` | `event.settled` |
| `type` | match: `sweep` -> Reserve Release; `adjust` -> Adjustment; answers an obligation -> Collection; else Unapplied Cash |
| `debtor_name` | match: `sweep` or `adjust` -> null; else `counterparty.name` |
| `invoice_id` | `obligation.id` |
| `gross_amount` | match: `sweep` or `adjust` -> null; else `event.amount` (what the debtor paid) |
| `fee_amount` | `split.fee` |
| `advance_recovered` | `advance.recovered` (T5) |
| `amount` | `posting.amount` (the net change to the reserve) |
| `reserve_balance` | `posting.balance_after` (T1) |

Every column has a source, and none needs custom code. Eight columns read paths that only the trucking additions provide: two use T1, one T2 and five T5. The seven detail columns use paths that already exist, and T6 makes them safe to require.

## 7. Coverage: every money flow and behavior

### `saas_startup`

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

### `trucking`

| PROMPT.md | Produced by | Tables it reaches |
|---|---|---|
| **Bank: a running balance on every transaction** | rows from postings when settled; `posting.balance_after` (T1) | `prairie_hollow_transactions` |
| **Bank: checks clear days later, not in number order** | `check` settles in 3-10 business days; numbering `check` per account, given when the check is written | `check_number`, `posted_date` |
| **Bank: monthly statement** | statement, monthly, `by: settled` | `prairie_hollow_statements` |
| **Bank: $25 per outgoing wire** | split `wire_fee` (add, to the bank's own account) | "OUTGOING WIRE FEE" rows, `service_charges` |
| **Bank: monthly service fee** | staff `adjust`, as for Mercury | `service_charges` |
| **Fuel card: a card per truck** | one account with cards "Unit 101" to "Unit 106" issued to the company (P1); a driver's `pay` names its truck's card | `roadfleet_transactions.card` (T2) |
| **Fuel card: driver ID, odometer, location, product, gallons, price** | `actor.fields.driver_id`; the rest from the driver's `pay` details, checked at the call (T6) | `roadfleet_transactions` |
| **Fuel card: weekly statement closing Sunday** | statement, `every: week`, `close_day: sunday` (T3) | `roadfleet_statements`, `statement_id` |
| **Fuel card: autopay two business days later** | sweep `after: statement`, `delay_days: 2`, pulling `statement.closing` by `ach` | `autopay_date`, `payments`; a bank ACH debit |
| **Factoring: invoices remit to Ironbridge** | Maria's `bill` with `to_account: a_ib_reserve` (T4); its record lands at Ironbridge | `ironbridge_purchased_invoices` |
| **Factoring: 90% advanced the next business day** | advance, 90%, by `ach` at the close of the bill's day, settling in 1 business day (T5) | `advance_amount`, `purchase_date`; bank "DES:ADVANCE" |
| **Factoring: an advance held while the load is verified** | Ironbridge staff `hold`, then `release` | status Pending Verification; the bank row posts later |
| **Factoring: Ironbridge collects and keeps 3%** | the debtor's `answer_obligation` -> `pay` into `a_ib_reserve`; split `fee` (carve); the advance repaid first (T5) | reserve activity Collection rows |
| **Factoring: the rest released every Friday** | sweep `every: week`, `day: friday` (T3), `direction: out`, `amount: available`, by `ach` | Reserve Release rows; bank "DES:RESERVE" |
| **Factoring: recourse after 90 days** | Ironbridge staff `reverse` the advance (T5) | status Charged Back, `chargeback_amount`; a bank ACH debit |
| **Load delivered -> invoice** | the driver's `record_activity` (the load, with its details); Maria's `bill` | purchased invoices |
| **Customer -> Ironbridge, late or short** | the debtor's `answer_obligation`, paying late or short; staff `reverse` the part of the advance a short pay didn't repay (T5) | Short Paid; reserve activity; a bank ACH debit |
| **A few direct customers, by check** | `bill` with `to_account: a_checking`; the debtor's `pay` by `check` | "REMOTE DEPOSIT" rows |
| **Drivers -> fuel card** | the driver's `pay` by `card` to a truck stop or lumper service from the catalog; a cash advance is a `pay` to the truck stop with its product | `roadfleet_transactions` |
| **RoadFleet -> checking** | the autopay above | |
| **Company -> drivers** | Maria's `pay` by `ach` to each driver, less the week's cash advances she reads on the fuel-card statement | bank, one row per driver |
| **Company -> lender, insurer, toll pass** | `collect` under mandates on checking | bank ACH debits |
| **Company -> repair shop, tire shops** | Maria's `pay` by `check` | CHECK rows, `checks_paid` |
| **Company -> state** | push terms, quarterly, by `ach` | bank |
| **Owner draws; a personal bill** | Maria's `pay` by `ach` to her own bank, which is tracked but not rendered; a personal vendor paid from checking | bank |
| **Stories** | breakdown: tow and repair paid by check, and fewer loads billed; fuel spike: higher `price_per_gallon` in the details; Copperline: messages, short pays, partial charge-backs; Tri-County: two advances charged back; used tractor: a wire down payment with its fee, and a card "Unit 107" added with `open_account` (P1); new driver: a cash advance taken off the first pay; low cash: Maria holds the repair check and draws nothing | all six tables |

## 8. What the language added

### `saas_startup` (accepted 2026-10-31)

The SaaS institutions needed eight changes beyond SPEC. The user accepted each one, and SPEC takes them in at Checkpoint 0.

**P1. Cards under one account.** An account can carry `instruments: [{id, issued_to, name}]`, each a card issued to an entity. A card `pay` uses the card issued to the actor's entity, or a card the call names. A mandate names a card. Postings carry the card, and columns read `instrument.issued_to.*`. Narrators add a card with `open_account` on an existing account (the hire in 4.2). This is why Ramp has one statement and one autopay for the company, and still names the cardholder on every row, including charges a vendor collects from a card on file.

**P2. Descriptors by direction.** `descriptors` may be a map `{in: [...], out: [...]}`, seen from the account the row is on. A plain list applies both ways. Mercury shows Stripe as "Deposit - STRIPE" on a payout and "Stripe - Expense - STRIPE" on a pull.

**P3. Obligations make a record when they come due.** An obligation from terms emits a zero-amount record event (`action: obligation`) when it comes due. For recurring terms its details include `period_start` and `period_end`. A bill's own record event plays this part for bills. The events that answer it link it, and rows from it render again when its status changes. Stripe invoices come from these records.

**P4. Pull obligations are recorded on the payee's collecting account.** Terms' `to_account` is read for pull terms under every policy, as the account the obligation is collected into. A subscription's invoices therefore land at Stripe before any `collect`.

**P5. `change_setting`.** A mechanism can mark one config key as a `setting`, with its allowed values (here the sweep's `every`, named `payout_schedule`). A new act tool, `change_setting(account, setting, value)`, lets an actor with access to the account change it. It is validated like any act tool and emits a zero-amount record event. This is how Morgan moves Stripe payouts to weekly.

**P6. Events record their call.** Events carry `call`, the id of the tool call or mechanism run that emitted them. The `entries` row source groups by it, so each payroll run is one Rippling entry.

**P7. Double charges come from the card issuer's staff.** Ramp's staff post a duplicate of a merchant's charge, and its reversal a few days later, with `adjust`. TARGET 3.4 says so.

**P8. Refunds return to their source by default.** Policy `receiving_account`'s default, `first_supporting`, also sends a refund back to the account it came from. Without this, a merchant's refund to the company could land in its Stripe balance, which also supports `card`.

### `trucking` (proposed, for the user to decide)

Trucking needed six changes. None is in SPEC, and nothing builds them until the user accepts them at Checkpoint 0. Each entry says what breaks without it.

**T1. A running balance on posting rows.** Add the path `posting.balance_after` (section 4), valid only in rows from postings rendered when settled; `validate` rejects it anywhere else. A small bank's transaction export, and a factor's reserve report, show a running balance on every row, before any statement closes. *Without it:* those tables render from `statement_lines`, so the last, unclosed month of a run has no rows. *Tasks:* 8 and 20.

**T2. A card's own name.** Add the path `instrument.name`. P1 gives every card a `name`, but columns could only read whom it was issued to. Fleet cards belong to trucks, not people, so RoadFleet's rows name the unit, and the driver comes from `actor.fields.driver_id`. *Without it:* each truck becomes an entity to issue its card to, which puts equipment among the world's parties. *Task:* 20, with P1's other instrument paths.

**T3. Weekly cycles name their weekday.** `statement` takes `every: week` with a `close_day` weekday, and a weekly `sweep` takes a `day` (section 2). Task 42 already plans a weekly sweep "on a given weekday"; this names the key. RoadFleet closes on Sunday, and Ironbridge releases the reserve on Friday. *Without it:* there is no weekly statement, and a weekly sweep has no defined weekday. *Tasks:* 42 and 43.

**T4. A bill says where to pay it.** `bill`'s `to_account` is read under every policy, as P4 does for pull terms. Task 34 reads it only under `receiving_account: named`. The account a bill names is where its record lands and where payments that answer it go. An invoice's remit-to line is part of the invoice, not our preference. With no account named, policy `receiving_account` picks as before. Factored invoices remit to Ironbridge and unfactored ones to the bank. Under the default `first_supporting`, both would go to whichever of the two accounts is listed first. This also states which account a SaaS bill's record lands on, which `stripe_invoices` relies on. *Without it:* the trucking world has to run under `receiving_account: named`. *Task:* 34, and SPEC's `receiving_account` row.

**T5. The `advance` mechanism.** Add the mechanism and its `advance.*` paths (sections 2 and 4), and give staff `reverse` an optional `amount`, for a partial charge-back. No existing mechanism pays out against an obligation before it is paid and takes the money back from its payment. That is the core of factoring, and also of refund anticipation and of invoice or purchase-order financing.
- Ironbridge advances each invoice at the close of the day it is submitted.
- Its staff hold an advance while they verify the load.
- A collection repays the advance after the fee.
- Staff charge back what a short pay or an unpaid invoice didn't repay.

*Without it:* staff would pay each advance with `adjust` and work out 90% themselves, but `adjust` posts fees and corrections, not transfers to another bank. Or Maria would draw on a credit line at Ironbridge, which loses per-invoice advances, the purchased-invoices report and Friday releases. *Tasks:* a new Phase 5 task, "The advance mechanism", after Tasks 34, 39 and 40 and before Task 47. Task 39 gains the `reverse` amount, and Task 21 the seeded advances.

**T6. Details a table reads are checked at the call.** When an act tool's posting or record will render in a table that reads `event.details.<key>`, the call is checked against those columns' schemas. A value that breaks its schema, or a missing detail the schema requires, rejects the call in the turn with the reason. The actor's brief lists, for each account it can use, the details its institution records and their allowed values. The brief carries this because the tool list must stay the same across turns. RoadFleet's rows read six details a driver supplies, and a product written "Diesel" instead of "DIESEL" would otherwise pass the call and then fail the run when its row renders. A SaaS bill's service period has the same problem. *Without it:* these columns become free strings, and the exports lose their fixed product codes. *Tasks:* 8 (`validate` maps each detail to its column's schema), 16 (the check) and 17b (the brief).

### Known simplifications (no change proposed)

`saas_startup`:
- Rippling pulls payroll funds from Mercury after payday, at the day close, instead of a few days before. The result is still the right debits, a little late.
- Withholding and employer tax are flat rates (22% and 12.8%, where TARGET's $3,200 on $25,000 gives 12.8%).
- `mercury_transactions.transaction_date` is the initiation day, which for incoming money is the day the sender initiated it.
- `mercury_treasury_records` reports deposits and withdrawals as magnitudes.

`trucking`:
- Ironbridge's 3% fee is a split of what the debtor paid, not of the invoice's face, so a short-paid invoice carries a smaller fee.
- Invoice numbers come from Ironbridge's counter for the client's account, so factored invoices number consecutively. A real sequence would skip the unfactored invoices' numbers, but those invoices appear in no table, so the difference can't be seen.
- Gallons and price per gallon are checked for format, not for multiplying out to the amount. The driver does that arithmetic.
- Driver pay posts one bank row per driver. Many banks post a payroll ACH batch as one debit.
- Ironbridge's verification is its staff holding an advance that has already been sent. A real factor sends it after verifying.

### Considered, no change proposed

- The bank's monthly service fee is staff `adjust`, as for Mercury. A fixed periodic fee isn't worth a mechanism while staff post it.
- A cash advance is a card `pay` to the truck stop with product CASH ADVANCE. The cash the driver receives isn't tracked, like any cash spending. Payroll takes advances off because Maria reads the fuel-card statement.
- Recourse is a staff decision, not a timer. Ironbridge's staff read aged items and charge back after 90 days, so they can give a slow debtor more time, as real factors do.
- Fleet cards have no per-product fees, such as a cash advance fee. A split's `on` filter can't see a detail, and the prompt names no such fee.
