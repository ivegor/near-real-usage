# Thesis: NEAR's collapse was reward apps and sponsored transactions. Outside them, self-paid activity grew, and a few dozen accounts run it

*Snapshot as of 2026-11-11. Every number below equals the committed `docs/summary.json` (a test checks the key ones);
the live dashboard is rebuilt daily, so its NearBlocks and DefiLlama figures will move away from this text.
Account counts come from full scans of the NEAR BigQuery public dataset (`sql/account_age.sql`, `sql/top_accounts.sql`:
every transaction, not a sample); prices, fees and Intents volume from NearBlocks and DefiLlama. For accounts,
"YoY" = October 2026 vs October 2025, the last complete month, with the mean of August–October against the same three
months a year earlier in brackets, because single months are noisy.*

## One-paragraph summary

In October 2025, 43.6 million accounts acted on NEAR. In October 2026, 1.38 million did (−97%), and 560 thousand of
those are old accounts of one reward app sending a single transaction each in a one-off sweep. Counted account by
account, **97% of the accounts that disappeared belonged to reward and wallet apps**; KaiChing alone was 40.4 million.
That part of the collapse says nothing about demand for NEAR. The rest is not comfortable either: **outside those apps
the account base fell by two thirds** (1.81M → 0.62M; −57% on three-month means), and accounts that come back month
after month fell 73%. What did grow is narrower than "users": **transactions that senders pay for themselves, outside
the reward apps, are up 28%** (+35% on three-month means), while transactions sponsored through relayers fell 75%.
Transactions to the exchange, NEAR Intents, token contracts and bridges are up 37%, and Intents volume in October was
$129M a day against $56M a year earlier. All of it is run by very few accounts: **thirty accounts send half of all
transactions**, and reward apps still send 43%. Value reaches the token only in part: buybacks funded by Intents
revenue cover 18% of the new NEAR issued. The long-term case is therefore a narrow one: a small amount of
self-paid, financial activity operated by a few dozen accounts, not a growing user base. Usage does not lead price.

## Two corrections to our own drafts

**First draft: "returning accounts grew 37%".** It used the only proxy the daily aggregates allow,
`active accounts − new accounts`. The full-chain count says the opposite: core accounts active two months running fell
73%. One day shows why the proxy fails (2025-10-01, 4,632,736 transactions, the same number in BigQuery and NearBlocks):

* **"Active accounts" are transaction signers.** 74% of that day's transactions (3,448,826) were relayed: 17 relayer
  accounts signed them on behalf of 2,694,016 users. NearBlocks reported 288,151 active accounts. The users behind
  relayers are not in that number.
* **"New accounts" are not a subset of them.** 238,403 accounts were created that day in transactions signed by 12
  creator accounts (NearBlocks reported 267,015 new accounts). The proxy subtracts them from a count of signers. We did
  not check how many of those accounts ever transact.

**Second draft: "the remaining accounts are busier" and "named accounts grew on every measure".** A review of that
draft showed both rested on a single month and on a mean:

* Transactions per core account rose from 10.7 to 23.9 a month, but inside each account type almost nothing changed:
  implicit accounts 5.4 → 6.6, named accounts 142.5 → 150.9. With last year's mix of account types the figure would
  be 11.7. Low-activity accounts left; nobody became twice as active.
* Named `.near` accounts are +13% October to October but +2% on three-month means; over the last twelve months the
  series ran between 33,204 and 102,911. Named accounts with more than one transaction fell from 50,038 to 36,203
  (−28%). Only their transactions grew robustly: +20%, and +42% on three-month means.

We kept the proxy on the dashboard, labelled as misleading, because every aggregate-based analysis of NEAR inherits it.

## Claims and what the data says

| # | Claim | Result | Evidence (October 2025 → October 2026; three-month means in brackets) |
|---|---|---|---|
| 1 | The collapse in activity is the exit of reward apps, not of NEAR's own users | **Mostly supported** | Reward and wallet apps account for 97.2% of the accounts lost and 96.2% of the transactions lost. KaiChing: 40.39M accounts a year ago, gone since spring except a one-off 560,093 single-transaction accounts in October |
| 2 | A stable core of returning users remains (first draft) | **Refuted** | Core accounts 1,814,743 → 621,166 (−66%; −57%); of them active the month before 924,642 → 248,954 (−73%; −69%); still falling: 959,812 (Jul) → 621,166 (Oct) |
| 3 | The remaining accounts are used more intensively (second draft) | **Refuted** | 10.7 → 23.9 transactions per core account is a change of mix: 11.7 at last year's mix of account types |
| 4 | Named `.near` accounts are a growing core (second draft) | **Not supported** | Accounts +13% (+2%); with more than one transaction −28% (−15%). Their transactions did grow: 8.96M → 10.77M (+20%; +42%) |
| 5 | Self-paid activity outside reward apps is growing | **Supported, with a caveat** | Core transactions paid by the sender 9.75M → 12.49M (+28%; +35%); sponsored through relayers 9.61M → 2.39M (−75%; −66%). The series is volatile: see "Evidence against" |
| 6 | Financial use of the chain is growing | **Supported** | Transactions to the exchange, Intents, token contracts and bridges 6.72M → 9.18M a month (+37%); Ref/Rhea exchange +96%, token contracts +47%, bridges and chain signatures +43% |
| 7 | Cross-chain demand through NEAR is growing | **Supported** | NEAR Intents volume $55.6M → $128.6M a day (+131%, October to October, DefiLlama); +84% on the previous 90 days |
| 8 | NEAR's activity is spread over many independent users | **Refuted** | 30 accounts send 50% of transactions; the top 10 send 37% (17% a year earlier); 486 accounts with 1,000+ transactions send 70% |
| 9 | Intents revenue offsets the dilution of NEAR holders | **Not yet** | Buybacks at $20.7M a year against $115M a year of net new NEAR: 18% of dilution covered; 5.6 times the captured revenue needed |
| 10 | Usage changes lead price changes | **Not supported** | 6 of 85 lag tests outside the noise band, about 4 expected by chance |

## Who is left: the customers

October 2026, every transaction assigned to the contract it calls or, if relayed, to its relayer
(`sql/top_accounts.sql`; the grouping into apps is the table in `thesis/clients.py`):

| Who | Share of transactions | A year earlier | Transactions, YoY | What it is |
|---|---|---|---|---|
| Sweat | 25.8% | 7.5% | −45% | Move-to-earn app. Five service accounts send most of it; its relayed users fell 1,263,047 → 413,927 |
| Ref Finance / Rhea | 13.4% | 1.1% | +96% | Exchange and lending. 2,586 accounts, the largest are trading bots with hundreds of thousands of swaps a month |
| HOT wallet | 13.3% | 28.5% | −93% | Telegram wallet, reward claims |
| Token contracts (wNEAR, USDC, USDT) | 9.3% | 1.0% | +47% | Transfers and deposits into the exchange and Intents |
| Bridges, Aurora, chain signatures | 9.0% | 1.0% | +43% | Omni bridge, BTC and Zcash connectors, the MPC signer |
| NEAR Intents | 8.9% | 1.6% | −13% | 2.01M transactions, 97% signed by two accounts (`intents.near`, `escrow.ai.near`) |
| Meteor wallet | 3.1% | 0.7% | −29% | Wallet with a reward game |
| KaiChing | 0.4% | 49.6% | −100% | Reward app, gone |
| Other contracts in the top 40 | 7.1% | 3.0% | −62% | |
| Everything else | 9.8% | 5.9% | −73% | The long tail: 1.38M accounts minus the few hundred above |

Two readings follow. First, the "infrastructure" picture is only half true: reward and wallet apps still send 43% of
transactions (86% a year ago). Second, the financial half is real and growing in absolute terms, but it is operated
by very few accounts. NEAR Intents is the extreme case: its volume more than doubled while the number of transactions
it received fell 13% and the accounts sending them fell from 26,272 to 5,353. Intents users sign off-chain and a
relayer submits, so its customers cannot be counted from the chain at all.

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

* **The core shrank by two thirds, and has not stopped.** 1.81M → 0.62M accounts in a year, and 0.96M → 0.62M in the
  last four months alone. Implicit (unnamed) accounts fell 69% and their transactions 62%. Whatever NEAR's organic base
  is, it is smaller than a year ago.
* **The self-paid series is volatile.** Monthly values run from 5.8M to 13.1M with no smooth trend; December 2024 was
  12.07M, about where October 2026 is. Two strong months are not yet a trend.
* **Very few accounts carry it.** The largest accounts in October 2026 are `intents.near` (1.44M transactions), three
  Sweat service accounts (1.0M to 1.4M each), two exchange bots (0.77M and 0.46M), a bridge relayer (0.66M) and
  `escrow.ai.near` (0.51M). This is concentration risk, not adoption.
* **Reward apps are still 43% of transactions.** KaiChing left, but Sweat, HOT and Meteor remain. Sweat's 11 service
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

Eight of these are written down as dated predictions with thresholds in [`PREDICTIONS.md`](PREDICTIONS.md); the build
scores the ones that need only daily data as soon as it reaches their check date.

* **Core accounts stop falling.** Two consecutive quarters with core accounts flat or up would mean the base has found
  a floor. Today it has not.
* **Self-paid core transactions fall back below 10M a month** for a quarter: then September and October 2026 were a
  spike, and nothing outside the reward apps is growing.
* **A reward app re-inflates the headline.** Active accounts jumping by millions with under 2 transactions per account
  is KaiChing again, not growth. It may already be starting: in the first 11 days of November 2026 HOT (`.tg`)
  accounts number 297,843, more than in all of October (198,246).
* **Intents volume falls back towards 2025 levels while the price holds.** Then the price is not tracking this flow.
* **A re-run shows a consistent lead**: several adjacent positive lags outside the band for more than one metric.

## Limits

* **"Core" is not "human".** It is every account outside three namespaces (`.kaiching`, `.tg`, `.sweat`). It still
  contains bots, application accounts and other apps that use implicit accounts. `.sweat` itself is 11 service
  accounts, not a user namespace; Sweat's users are counted in the core as relayed implicit accounts.
* **Self-paid vs sponsored is measured in transactions, not accounts.** The census does not say how many accounts pay
  for themselves.
* **Account age is first appearance in a transaction**, as signer or receiver, since genesis. An account created by a
  contract call and first used later looks younger than it is.
* **"Active two months running" is a calendar-month measure.** It says nothing about retention within a month.
* **February and March 2026** each contain a one-off burst of existing implicit accounts sending one transaction each
  (about 3.5 and 6 million accounts; in February most were older than two years). They inflate core account counts in
  those two months; comparisons use October and August–October to avoid them.
* **Intents volume, prices and fees are aggregator data** (DefiLlama, NearBlocks). We verified NearBlocks' daily
  transaction count against BigQuery for one day (exact match) and nothing else. The 90-day year-on-year change in
  Intents volume (+223% on 2026-11-11) shrinks every day as its base moves through the ramp-up of autumn 2025, so
  this text quotes the calendar-month comparison.
* **Lead-lag scans 17 lags × 5 metrics = 85 tests**; about 4 bars outside ±2/√n are expected by chance. One of the
  five metrics is the `active − new` proxy shown above to be unreliable; it is reported for completeness.
* **The app table is a manual grouping** of the 40 largest contracts and relayers, which cover 90% of October 2026
  transactions. A relayed transaction is assigned to its relayer, not to the contract it finally calls.
* **The account census ends on 2026-11-11** and costs 482.64 GB of BigQuery scanning to re-run (the free tier is 1 TB
  a month). The dashboard keeps October 2026 as its last month until the query is run again.
