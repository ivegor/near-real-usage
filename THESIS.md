# Thesis: NEAR's collapse was users that apps were paying for. What pays its own way was flat for a year, jumped in autumn 2026, and a few hundred heavy accounts carry it

*Snapshot as of 2026-11-11. Every number below equals the committed `docs/summary.json` (a test checks the key ones);
the live dashboard is rebuilt daily, so its NearBlocks and DefiLlama figures will move away from this text.
Account counts come from full scans of the NEAR BigQuery public dataset (`sql/account_age.sql`,
`sql/payer_frequency.sql`, `sql/payers.sql`, `sql/top_accounts.sql`: every transaction, not a sample); prices, fees
and Intents volume from NearBlocks and DefiLlama. For accounts,
"YoY" = October 2026 vs October 2025, the last complete month, with the mean of August–October against the same three
months a year earlier in brackets, because single months are noisy.*

## One-paragraph summary

In October 2025, 43.6 million accounts acted on NEAR. In October 2026, 1.38 million did (−97%), and 560 thousand of
those are old accounts of one reward app sending a single transaction each in a one-off sweep. Counted account by
account, **the whole fall is accounts whose fees an app was paying**: 43.05 million of them a year ago, 0.55
million now. KaiChing alone was 40.4 million.
That part of the collapse says nothing about demand for NEAR. Outside the namespaces of the reward apps (KaiChing,
the HOT wallet, Sweat's service accounts) the account count also fell by two thirds, but **93% of those accounts
were users of other apps whose fees a relayer paid**, and they are what fell. The accounts that say something about
demand pay their own fees and sit outside those namespaces: of them, **the regular ones (10 to 999 transactions a
month) fell from 27,078 to 17,105** (−37%; −50% on three-month means), while
**475 heavy accounts (1,000 or more a month) send 91% of the self-paid transactions**. What did grow is
narrower than "users": **transactions that senders pay for themselves, outside the reward apps, are up 28%**
October to October. That figure depends on the window: +35% on three-month means, +24% on six, +6% on nine and −5% on
eleven (+2% and −8% without a one-off burst in February 2026, see "Limits"). Read plainly, self-paid activity was
flat for most of the year and jumped in September and October 2026, while transactions sponsored through relayers
fell 75%.
Transactions to the exchange, NEAR Intents, token contracts and bridges are up 37%, and Intents volume in October was
$129M a day against $56M a year earlier. All of it is submitted by very few accounts: **thirty accounts send half of
all transactions**, and reward apps still send 43% (45% counting a one-off sweep by old KaiChing accounts). Value
reaches the token only in part: buybacks funded by Intents revenue cover 18% of the new NEAR issued. The long-term
case is therefore a narrow one: a small amount of self-paid, financial activity submitted by a few dozen accounts.
On the chain itself no base of users who pay their own way is growing; how many people stand behind the relays of
Intents and the bridges cannot be read from it. Usage does not lead price.

## Three corrections to our own drafts

**First draft: "returning accounts grew 37%".** It used the only proxy the daily aggregates allow,
`active accounts − new accounts`. The full-chain count says the opposite: core accounts active two months running fell
73%. One day shows why the proxy fails (2025-10-01, 4,632,736 transactions, the same number in BigQuery and NearBlocks):

* **"Active accounts" are transaction signers.** 74% of that day's transactions (3,448,826) were relayed: 17 relayer
  accounts signed them on behalf of 2,694,016 users. NearBlocks reported 288,151 active accounts. The users behind
  relayers are not in that number.
* **"New accounts" are not a subset of them.** 238,403 accounts were created that day by transactions whose first
  action is `CREATE_ACCOUNT`, all signed by 12 creator accounts (NearBlocks reported 267,015 new accounts). The proxy
  subtracts them from a count of signers. We did not check how many of those accounts ever transact.

**Second draft: "the remaining accounts are busier" and "named accounts grew on every measure".** A review of that
draft showed both rested on a single month and on a mean:

* Transactions per core account rose from 10.7 to 23.9 a month, but inside each account type almost nothing changed:
  implicit accounts 5.4 → 6.6, named accounts 142.5 → 150.9. With last year's mix of account types the figure would
  be 11.7. Low-activity accounts left; nobody became twice as active.
* Named `.near` accounts are +13% October to October but +2% on three-month means; over the last twelve months the
  series ran between 33,204 and 102,911. Named accounts with more than one transaction fell from 50,038 to 36,203
  (−28%). Only their transactions grew robustly: +20%, and +42% on three-month means.

**Third draft: "outside reward apps the account base fell by two thirds".** True as a count, wrong as a reading. We
had defined "the rest of the chain" by exclusion, as every account outside three namespaces. Split by who pays the
fee, 93% of those 1.81M accounts turn out to be sponsored users of other apps, and they fell 71%. The accounts that
pay for themselves are a different and much smaller population, and only its frequency classes are stable enough to
read (see "Who pays, and how often").

We kept the proxy on the dashboard, labelled as misleading, because every aggregate-based analysis of NEAR inherits it.

## Claims and what the data says

| # | Claim | Result | Evidence (October 2025 → October 2026; three-month means in brackets) |
|---|---|---|---|
| 1 | The collapse in activity is the exit of reward apps, not of NEAR's own users | **Supported** | Accounts whose fees an app paid: 43,049,960 → 552,826. That is more than the whole net loss of accounts (43,642,992 → 1,379,518), because self-paying accounts rose, 593,032 → 826,692, and the rise is itself a one-off: 560,092 old KaiChing accounts paid for one transaction each in October. Without them self-paying accounts fell: HOT users who pay their own fees 458,286 → 129,677, independent ones flat (134,743 → 136,920). Counted by namespace alone, reward and wallet apps are 97.2% of the accounts lost and 96.2% of the transactions lost. KaiChing: 40.39M accounts a year ago, gone since spring except that October sweep |
| 2 | A stable core of returning users remains (first draft) | **Refuted** | Accounts outside the reward namespaces 1,814,743 → 621,166 (−66%; −57%); of them active the month before 924,642 → 248,954 (−73%; −69%); still falling: 959,812 (Jul) → 621,166 (Oct) |
| 3 | The number of accounts that pay for themselves holds up | **Only at the top** | Outside the reward namespaces, regular self-paying accounts 27,078 → 17,105 (−37%; −50%), low of 7,201 in August 2026; heavy accounts 370 → 475 (+28%; +0%), and they send 91% of self-paid transactions. Inside HOT's namespace the regular self-paying accounts are more numerous and fell faster: 333,728 → 60,879 (−82%; −77%) |
| 4 | The remaining accounts are used more intensively (second draft) | **Refuted** | 10.7 → 23.9 transactions per core account is a change of mix: 11.7 at last year's mix of account types |
| 5 | Named `.near` accounts are a growing core (second draft) | **Not supported** | Accounts +13% (+2%); with more than one transaction −28% (−15%). Their transactions did grow: 8.96M → 10.77M (+20%; +42%) |
| 6 | Self-paid activity outside reward apps is growing | **Flat for a year, up in autumn 2026** | Core transactions paid by the sender 9.75M → 12.49M (+28%; +35%); on longer windows +24% (six months), +6% (nine) and −5% (eleven); sponsored through relayers 9.61M → 2.39M (−75%; −66%). The series is volatile: see "Evidence against" |
| 7 | Financial use of the chain is growing | **Supported** | Transactions to the exchange, Intents, token contracts and bridges 6.72M → 9.18M a month (+37%); Ref/Rhea exchange +96%, token contracts +47%, bridges and chain signatures +43% |
| 8 | Cross-chain demand through NEAR is growing | **Supported** | NEAR Intents volume $55.6M → $128.6M a day (+131%, October to October, DefiLlama); +84% on the previous 90 days |
| 9 | NEAR's transactions come from many independent accounts | **Refuted** | 30 accounts send 50% of transactions; the top 10 send 37% (17% a year earlier); 486 accounts with 1,000+ transactions send 70%. Seven of the ten largest are relays or service accounts (Intents, Sweat, the bridges), so this counts who submits transactions; the people behind a relay are not visible on the chain |
| 10 | Intents revenue offsets the dilution of NEAR holders | **Not yet** | Buybacks at $20.7M a year against $115M a year of net new NEAR: 18% of dilution covered; 5.6 times the captured revenue needed |
| 11 | Usage changes lead price changes | **Not supported** | 6 of 85 lag tests outside the noise band, about 4 expected by chance |

## Who pays, and how often

The cleanest way to split NEAR's accounts is by three questions a product owner would ask, and none of the lines
between the groups is a number we chose (`sql/payer_frequency.sql`, every transaction from August 2025 to October 2026):

* **Who pays the fee?** If a relayer submitted and paid for every transaction of the account in the month, an app is
  paying for that user: *sponsored*. If the account paid for at least one itself: *self-paying*.
* **Whose account is it?** KaiChing and HOT create accounts for their users inside their own namespaces
  (`.kaiching`, `.tg`). Everything else is outside them.
* **How often does it act?** Transactions in the month, by powers of ten. Under 10: *occasional*. 10 to 999: *regular*.
  1,000 or more is over 30 a day, every day, which nobody does by hand: *heavy*, meaning automated or institutional.

| Segment | October 2025 | October 2026 | Change (three-month means) |
|---|---|---|---|
| Sponsored users, all apps | 43,049,960 | 552,826 | −99%; −99% |
| Sponsored users outside the two reward namespaces (Sweat, Meteor and other apps) | 1,680,016 | 484,257 | −71%; −59% |
| HOT users who pay their own fees | 458,286 | 129,677 | −72%; −68% |
| of them regular (10 to 999 transactions a month) | 333,728 | 60,879 | −82%; −77% |
| Independent self-paying, occasional | 107,295 | 119,340 | +11%; −37% |
| Independent self-paying, **regular** | 27,078 | 17,105 | −37%; −50% |
| Independent self-paying, **heavy** | 370 | 475 | +28%; +0% |

Three things follow. A year ago 93% of the accounts outside the two reward namespaces were still someone's
sponsored users; what looked like the chain's own base falling by two thirds was mostly other apps' users leaving.
Named by the relayer that paid for them (`sql/payers.sql`), they were the users of two apps: Sweat's sponsored
accounts went 1,246,366 → 410,890 and those of the game Ember 387,762 → 0. Together that is
the whole fall (70% and 32% of it; the other groups grew slightly).
The regular self-paying accounts outside the reward namespaces are the closest thing the chain has to a count of its
own users, and they fell from 27,078 to 17,105, after a year-long slide to 7,201 in August 2026 and a rebound in
September. HOT's own regular self-paying users were twelve times as many a year ago and fell faster; they are counted
with their app because it creates their accounts for them. And
the growth in self-paid transactions (9.77M → 12.49M, +28%; +35%; 9.75M in the census, see "Limits") belongs to the
heavy accounts: they send 91% of it (85% a year ago). Occasional accounts swing with one-off events (the series
runs from 49,954 to 3.5 million independent accounts in fifteen months) and are not read as a trend.
*(chart: segments)*

## Who is left: the customers

October 2026, every transaction assigned to the contract it calls or, if relayed, to its relayer
(`sql/top_accounts.sql`; the grouping into apps is the table in `thesis/clients.py`):

| Who | Share of transactions | A year earlier | Transactions, YoY | What it is |
|---|---|---|---|---|
| Sweat | 25.8% | 7.5% | −45% | Move-to-earn app. Five service accounts send most of it; its relayed users fell 1,263,047 → 413,927 |
| Ref Finance / Rhea | 13.4% | 1.1% | +96% | Exchange and lending. 96% of these transactions go to the main contract from 2,586 accounts, the largest of them trading bots with hundreds of thousands of swaps a month; 15,140 accounts used the concentrated-liquidity contract, for 44,392 transactions |
| HOT wallet | 13.3% | 28.5% | −93% | Telegram wallet, reward claims |
| Token contracts (wNEAR, USDC, USDT) | 9.3% | 1.0% | +47% | Transfers and deposits into the exchange and Intents |
| Bridges, Aurora, chain signatures | 9.0% | 1.0% | +43% | Omni bridge, BTC and Zcash connectors, the MPC signer |
| NEAR Intents | 8.9% | 1.6% | −13% | 2.01M transactions, 97% signed by two accounts (`intents.near`, `escrow.ai.near`) |
| Meteor wallet | 3.1% | 0.7% | −29% | Wallet with a reward game |
| KaiChing | 0.4% (2.8% by namespace) | 49.6% | −100% | Reward app, gone since spring. In October its old accounts sent 560,106 transactions, one each, to contracts outside the top 40 |
| Other contracts in the top 40 | 7.1% | 3.0% | −62% | |
| Everything else | 9.8% | 5.9% | −73% | Transactions to contracts outside the 40 largest, including the KaiChing one-off above |

Two readings follow. First, the "infrastructure" picture is only half true: reward and wallet apps still send 43% of
transactions through their own contracts and relayers (86% a year ago), or 45% counting the KaiChing one-off. Second,
the financial half is real and growing in absolute terms, but it is operated by very few accounts. NEAR Intents is
the extreme case: its volume more than doubled while the number of transactions it received fell 13% and the accounts
sending them fell from 26,272 to 5,353. Intents users sign off-chain and a relayer submits, so its customers cannot
be counted from the chain at all.

## Does it reach the token?

Partly, and not enough yet. Over the last 90 days NEAR Intents charged $18.9M in fees,
51 times the network's own transaction fees. NEAR captured $5.1M of that
(27%); the rest stays with solvers and the front ends that route the swaps. Since
2026-02-23 the captured revenue is used to buy NEAR on the open market. At the last 90 days' pace that is
$20.7M a year. Over the same period the supply of NEAR grew at 32.3M NEAR a
year net of burned fees (2.48% over the last 365 days), worth $115M a year at the
period's mean price of $3.58. **Buybacks cover 18% of dilution.** Covering all of it needs
5.6 times the captured revenue at this price, and the market capitalisation is 227 times the
annual buyback. The bought NEAR is held, not burned, so supply itself does not shrink. *(chart: value_capture)*

## An independent check: a keyless sample of the chain

Everything above comes from one source, BigQuery. As a check we measured the chain a second way, with no key and no
Google account (`python -m thesis census`): 449 random blocks from the FastNEAR block archive, 2,400 of their
transactions, and for each of the 1,553 accounts behind them a `view_account` call on an archival RPC node to
learn whether the account already existed 30 and 365 days before the window.

| | Sample, Aug 14 – Nov 11, 2025 | BigQuery, Sep–Oct 2025 | Sample, Aug 14 – Nov 11, 2026 | BigQuery, Sep–Oct 2026 |
|---|---|---|---|---|
| Transactions sent through a relayer | 78% | 75% | 35% | 34% |
| Transactions from accounts older than one year | 38% (95% interval 32–47%) | 46% | 69% (65–73%) | 64% |
| Transactions sent by the ten largest accounts | 14% | 17% (October) | 39% | 37% (October) |

The two agree on size and direction. They should not match exactly: the sample measures age at the start of a 90-day
window and asks whether the account existed, BigQuery measures it at the start of each month and asks when the account
first appeared in a transaction. The 2026 old-account share is the one cell where the BigQuery figure falls just
outside the sample's interval. The sample also reads what a relayed transaction finally calls, which the BigQuery
tables above do not: a year ago 55% of sampled transactions were a single call, `earn.kaiching :: claim`.
*(chart: signer_census)*

## Evidence for

* **The headline numbers measured an app, not a network.** KaiChing peaked at 48.9 million accounts a month (August
  2025) and averaged under 2 transactions per account a month; it was 93% of all active accounts in October 2025 and
  stopped between March and April 2026. HOT wallet accounts (`.tg`) fell 86% over the year. *(chart: population)*
* **What people pay for themselves grew.** Outside the reward apps, transactions paid by the sender rose from 9.75M
  to 12.49M a month; September and October 2026 are two of the three highest months in the 23-month series. The whole
  fall in core transactions (−23%) is sponsored transactions disappearing. *(chart: population)*
* **Financial use grew in absolute terms** while everything else shrank: +37% in transactions to the exchange,
  Intents, token contracts and bridges. *(chart: clients)*
* **Intents is a real, growing flow.** $55.6M → $128.6M a day October to October, while the NEAR price roughly doubled
  over the same two months ($2.49 → $4.90). *(chart: intents)*

## Evidence against

* **Regular self-paying accounts fell by a third to a half.** 27,078 → 17,105 October to October, −50% on
  three-month means, after sliding for a year to 7,201 in August 2026. The September rebound is two months old.
  HOT users who pay their own fees fell 72%, the regular ones among them 82%.
* **The self-paid series is volatile.** Monthly values run from 5.8M to 13.1M with no smooth trend; December 2024 was
  12.07M, about where October 2026 is, and a third of February 2026 was a one-off burst (see "Limits"). Two strong
  months are not yet a trend.
* **Very few accounts carry it.** The largest accounts in October 2026 are `intents.near` (1.44M transactions), three
  Sweat service accounts (1.0M to 1.4M each), two exchange bots (0.77M and 0.46M), a bridge relayer (0.66M) and
  `escrow.ai.near` (0.51M). Seven of the ten largest are relays or service accounts, so the count says who submits
  transactions, not how many people stand behind them; either way the chain depends on a handful of operators.
* **Reward apps are still 43% to 45% of transactions.** KaiChing left, but Sweat, HOT and Meteor remain. Sweat's 11 service
  accounts in the `.sweat` namespace alone send 17.7% of all transactions while its user count fell 67%. The next exit
  would look the same.
* **Old accounts did not take over the core.** Accounts older than a year send 43% of core transactions, down from 52%.
* **Fees fell.** Network fees are down 52% in USD over the last 90 days ($8,652 → $4,122 a day) and 68% in NEAR.
  Intents volume is not revenue for the token: NEAR keeps 27% of Intents fees and the buybacks they fund cover
  18% of new supply (see "Does it reach the token?").
* **Usage does not lead price.** On weekly log-changes over ~6 years (n = 292–317 weeks, noise band ≈ ±0.11–0.12):
  Intents volume (n = 100 weeks, band ±0.20) and fees in NEAR show nothing outside the band at any lag from −8 to +8
  weeks; active accounts r = 0.14 at lag 0; transactions show four isolated bars of mixed sign. In total 6 of 85 lag
  tests fall outside the band where about 4 are expected by chance. Fees in USD do correlate with price in the same
  week (r = 0.38), but only because USD fees are NEAR fees multiplied by the price. *(chart: lead_lag)*

## What would change our mind

These are written down as nine dated predictions in [`PREDICTIONS.md`](PREDICTIONS.md). Their thresholds are reference
levels taken from the data (the top of a metric's range before the September 2026 step, its latest value, or a natural
line such as break-even), not numbers we picked; the build scores the ones that need only daily data.

* **Regular self-paying accounts fall back to their low.** They bottomed at 7,201 in August 2026 and rebounded in
  September. A month at or below that low means the rebound was a spike and the base has not found a floor.
* **Self-paid core transactions fall back into their old range.** From December 2025 to August 2026 their highest
  month was 10.38M (February 2026); earlier months were higher, up to 12.07M in December 2024. A quarter
  averaging below 10.38M means September and October were a spike, and nothing outside the reward apps is growing.
  A third of that February was a one-off burst (see "Limits"): without it the top of the range is 8.65M (June 2026),
  so the threshold we wrote down is the harder of the two to stay above.
* **A reward app re-inflates the headline.** Active accounts jumping by millions with under 2 transactions per account
  is KaiChing again, not growth. It may already be starting: in the first 11 days of November 2026 HOT (`.tg`)
  accounts number 297,843, more than in all of October (198,246).
* **Intents volume falls back into its old range.** From December 2025 to August 2026 no month averaged above $89.6M
  a day; November 2025 had spiked to $122M and fell straight back. A month below $89.6M means autumn 2026 was a second
  spike, not a new level, and the buybacks it funds fall with it.
* **A re-run shows a consistent lead**: several adjacent positive lags outside the band for more than one metric.

## Limits

* **"Outside the reward namespaces" is not "NEAR's own users".** The account-age census groups accounts by namespace,
  and a year ago 93% of the accounts outside `.kaiching`, `.tg` and `.sweat` were sponsored users of other apps
  (`.sweat` itself is 11 service accounts; Sweat's users are relayed implicit accounts). Read the age and returning
  figures of that group with this in mind; the payer and frequency split is the cleaner count.
* **Self-paying means the account paid for at least one transaction in the month.** It may also have sponsored ones.
  A sponsored user is not a lesser user; it is a user an app is paying for, and it leaves when the app does.
* **Frequency classes are powers of ten of a monthly count.** "Heavy" (1,000 or more) is our reading of that line as
  automation; we did not inspect the accounts one by one beyond the forty largest.
* **Account age is first appearance in a transaction**, as signer or receiver, since genesis. An account created by a
  contract call and first used later looks younger than it is.
* **"Active two months running" is a calendar-month measure.** It says nothing about retention within a month.
* **February and March 2026** each contain a one-off burst of existing implicit accounts sending one transaction each
  (about 3.5 and 6 million accounts; in February most were older than two years). They inflate core account counts in
  those two months; comparisons use October and August–October to avoid them. March's burst was sponsored through
  relayers. February's was paid by the senders, so it also sits in the self-paid series: 3.37M of that month's 10.38M
  self-paid core transactions (32%) came from implicit accounts older than a year that had not been active in January.
  The same group sent 27,664 the month before and never more than 1.4% of a month otherwise. Without that group the
  nine-month change quoted above is +2% instead of +6% and the eleven-month one −8% instead of −5%; the one-, three-
  and six-month figures move by less than a point.
* **The payer and frequency table knows two namespaces**, `.kaiching` and `.tg`; the account census knows three. The
  `.sweat` service accounts that paid for at least one of their own transactions (13 in October 2025, 7 in October
  2026) therefore count among the table's independent accounts, at most 13 of its 370 heavy accounts a year ago and
  7 of the 475 now, and their self-paid transactions are why the table has 9.77M where the census has 9.75M.
* **Intents volume, prices and fees are aggregator data** (DefiLlama, NearBlocks). We verified NearBlocks' daily
  transaction count against BigQuery for one day (exact match) and nothing else. The 90-day year-on-year change in
  Intents volume (+223% on 2026-11-11) shrinks every day as its base moves through the ramp-up of autumn 2025, so
  this text quotes the calendar-month comparison.
* **Lead-lag scans 17 lags × 5 metrics = 85 tests**; about 4 bars outside ±2/√n are expected by chance. One of the
  five metrics is the `active − new` proxy shown above to be unreliable; it is reported for completeness.
* **The app table is a manual grouping** of the 40 largest contracts and relayers, which cover 90% of October 2026
  transactions. A relayed transaction is assigned to its relayer, not to the contract it finally calls. The game Ember
  is not in the reward-app group: it sponsored 387,762 users a year ago (2.0% of transactions, 0.7% now) and is filed
  under "Other contracts in the top 40". With it the reward apps' share is 43.3% (88.3% a year ago). The group is left
  as it was when prediction B4 was written, so that the prediction is scored on the definition it was made with.
* **The account census ends on 2026-11-11** and costs 482.64 GB of BigQuery scanning to re-run (the free tier is 1 TB
  a month). The dashboard keeps October 2026 as its last month until the query is run again.
