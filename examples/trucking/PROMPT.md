# Ozark Ridge Freight: a small trucking company

This is the main prompt for a world from another industry, run on the same engine as `examples/saas_startup` with no code change. Amounts, names and dates are examples; a generated world matches when it shows the same kinds of events.

## The company and the time frame

- **Business:** Ozark Ridge Freight LLC, a dry-van carrier in Springfield, Missouri, with 6 tractors and 8 trailers. It hauls general freight across the Midwest and South, about 70% for freight brokers and 30% for direct shippers. Revenue is about $1.6 million a year; margins are thin, and cash is always tight because customers pay 30-45 days after delivery while fuel and drivers are paid every week.
- **Time range:** 2024-01-01 to 2024-12-31, currency USD.
- **History before the start:** founded in 2019 by Maria Delgado, who drove for ten years first. It has factored its broker invoices with Ironbridge Freight Funding since 2021, so on day one about forty invoices are already purchased and unpaid, with advances outstanding and a reserve balance building. Four tractors are financed and two are paid off. The fuel card statement for the last week of December awaits its autopay, drivers' fuel purchases from December 30-31 haven't posted, and a few checks written in the last week of December haven't cleared.

## Institutions (the only sources of data)

- **Prairie Hollow Bank:** the operating account (`Business Checking ••7731`). ACH, wires and paper checks. Shows each posted transaction with a running balance, and a monthly statement; checks clear a few days to two weeks after they are written, not always in number order. A small monthly service fee, and $25 for each outgoing wire.
- **RoadFleet fuel card:** one fleet account with a card per truck (`Unit 101` to `Unit 106`). Drivers enter their driver ID and odometer at the pump. Each transaction records the truck stop, city and state, product (diesel, DEF, a cash advance, a lumper payment), gallons and price per gallon. Statements close weekly on Sunday and are paid by autopay from checking two business days later.
- **Ironbridge Freight Funding:** buys broker and shipper invoices. Ozark Ridge's invoices tell customers to remit to Ironbridge. Ironbridge advances 90% of each invoice by ACH the next business day after verifying the load (sometimes it holds an advance while it verifies), collects from the customer, keeps a 3% fee, and releases the rest from the reserve every Friday. If a customer hasn't paid after 90 days, Ironbridge charges the advance back (recourse). Its reports list each purchased invoice and every movement through the client reserve.

## The cast

- **Maria Delgado:** owner and dispatcher. Books loads with brokers, submits invoices to Ironbridge each evening, pays the bills, and watches cash closely; draws money to her personal account when there is some to spare, and occasionally pays a personal bill from the business account.
- **Drivers (6 company drivers):** each assigned to a truck, paid weekly by direct deposit at 58-62 cents per mile, less any fuel-card cash advance from that week. Each has habits: one always buys DEF at the same Love's, one takes cash advances often, one forgets to enter the odometer, one swaps trucks when his is in the shop.
- **Customers:** freight brokers (Bluestem Logistics pays in 30 days; Copperline Brokerage in 40, and short-pays when it disputes detention) and direct shippers (Granite Hollow Foods pays by check; Tri-County Paper is slow and once doesn't pay at all). Loads pay $1,400 to $3,800 each, plus accessorials such as detention and lumper fees.
- **Vendors:** truck stops (Pilot, Love's, TA, Petro), a lender for the financed tractors (monthly ACH debits), an insurer (monthly premium), a repair shop paid by check, tire shops, a toll pass, and the state for quarterly fuel tax.

## Money flows

| Flow | How it moves |
|---|---|
| Load delivered -> invoice | the driver records the delivery; Maria bills the customer, remit-to Ironbridge; Ironbridge advances 90% to checking |
| Customer -> Ironbridge | pays the invoice in 30-45 days by ACH or check, sometimes late or short; Ironbridge recovers its advance and fee and releases the rest on Friday |
| Unpaid after 90 days, or short-paid | Ironbridge charges back from checking whatever of the advance it hasn't recovered |
| A few direct customers | invoices not factored, paid straight to checking by check |
| Drivers -> fuel card | diesel and DEF at truck stops, cash advances, lumper payments |
| RoadFleet -> checking | weekly autopay after the Sunday statement |
| Company -> drivers | weekly direct deposit settlements |
| Company -> lender, insurer | monthly ACH debits |
| Company -> repair shop | paper checks |
| Company -> state | quarterly fuel tax by ACH |
| Owner draws | ACH transfers to Maria's personal account at another bank |

## Stories and one-offs

A truck breaks down in Arkansas and is towed and repaired over four days (a big repair check, a driver on another truck, lost loads); fuel prices spike in spring; Copperline disputes detention and short-pays three invoices; Tri-County Paper goes silent and Ironbridge charges back two advances in the fall; Maria buys a used tractor in summer with a down payment by wire; a driver quits and a new one starts with a cash advance in his first week; cash runs so low in one week that Maria delays the repair shop and draws nothing for a month.
