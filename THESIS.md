# Thesis: NEAR did not lose its users in 2026, it lost one reward app. What is left is small, concentrated and busier

*Data through 2026-11-11. Account counts come from a full scan of the NEAR BigQuery public dataset
(`sql/account_age.sql` and `sql/top_accounts.sql`, every transaction, not a sample); prices, fees and Intents volume
from NearBlocks and DefiLlama.
"YoY" for accounts = October 2026 vs October 2025, the last complete month; for prices, fees and volume = mean of the
last 90 days vs the same 90 days a year earlier. Every number below is in `docs/summary.json`, rebuilt by
`python -m thesis build`.*

## One-paragraph summary

In October 2025, 43.6 million accounts acted on NEAR. In October 2026, 1.38 million did (−97%). Read from the daily
aggregates, that is a network that died. Counted account by account, **97% of the accounts that disappeared belonged to
two reward and wallet apps**, KaiChing and HOT, and KaiChing alone was 40.4 million of them. That part of the collapse
says nothing about demand for NEAR. The rest is not a comfortable story either: **outside those apps the account base
also fell by two thirds** (1.81M → 0.62M), and accounts that come back month after month fell 73%. One group grew:
**named `.near` accounts**, 71 thousand of them (+13%), which now send 48% of all transactions (6% a year ago), 20%
more than a year earlier. **Thirty accounts now send half of all transactions.** What they do splits almost evenly:
43% of transactions still belong to reward and wallet apps (Sweat alone is a quarter), 41% to trading, NEAR Intents,
token transfers and bridges, and that second group is the one that grew, +37% in a year. Add Intents volume, which
tripled to about $135M a day, and the long-term case becomes clear and narrow: NEAR today is a few dozen operators
and one cross-chain product, not a growing user base. Usage does not lead price.

## A correction we made to our own first draft

The first version of this thesis claimed that "returning accounts" *grew* 37% year on year. It used the only proxy the
daily aggregates allow, `active accounts − new accounts`. The full-chain count says the opposite: core accounts active
two months running fell 73%. The proxy fails for two reasons, both visible on a single day (2025-10-01, 4,632,736
transactions, the same number in BigQuery and in NearBlocks):

* **"Active accounts" are transaction signers.** 74% of that day's transactions (3,448,826) were relayed: 17 relayer
  accounts signed them on behalf of 2,694,016 users. NearBlocks reported 288,151 active accounts. The users behind
  relayers are not in that number.
* **"New accounts" mostly never transact.** 238,403 accounts were created that day by 12 creator accounts (NearBlocks
  reported 267,015 new accounts). Subtracting them from 288,151 signers subtracts accounts that were never part of it.

We kept the proxy on the dashboard, labelled as misleading, because every aggregate-based analysis of NEAR inherits it.

## Claims and what the data says

| # | Claim | Result | Evidence (October 2025 → October 2026 unless stated) |
|---|---|---|---|
| 1 | The collapse in activity is the exit of reward apps, not of NEAR's own users | **Mostly supported** | Reward and wallet apps (KaiChing, HOT, Sweat namespaces) account for 97.2% of the accounts lost and 96.2% of the transactions lost. KaiChing had 40.39M active accounts in October 2025; in October 2026 only 2 of its accounts were active two months running |
| 2 | A stable core of returning users remains (our first draft) | **Refuted** | Core accounts 1,814,743 → 621,166 (−66%); of them active the month before 924,642 → 248,954 (−73%); still falling: 959,812 (Jul) → 621,166 (Oct) |
| 3 | The remaining core is used more intensively | **Supported** | Core transactions fell only 23% (19.36M → 14.87M a month) while core accounts fell 66%: 10.7 → 23.9 transactions per account a month |
| 4 | Named `.near` accounts are a growing core | **Supported, and small** | 62,880 → 71,332 accounts (+13%), transactions 8.96M → 10.77M (+20%), share of all NEAR transactions 6.4% → 47.6% |
| 5 | Cross-chain demand through NEAR is growing | **Supported** | NEAR Intents volume $41.7M → $134.9M a day (+223%, 90-day means, DefiLlama) |
| 6 | Financial use of the chain is growing, not only Intents volume | **Supported** | Transactions to the exchange, Intents, token contracts and bridges 6.72M → 9.18M a month (+37%); Ref/Rhea exchange +96%, token contracts +47%, bridges and chain signatures +43% |
| 7 | NEAR's activity is spread over many independent users | **Refuted** | 30 accounts send 50% of transactions; the top 10 send 37% (17% a year earlier); 486 accounts with 1,000+ transactions send 70% |
| 8 | Usage changes lead price changes | **Not supported** | See "Evidence against" |

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

Two readings follow. First, the "B2B" picture is only half true: reward and wallet apps still send 43% of
transactions (86% a year ago). Second, the financial half is real and growing in absolute terms, but it is operated
by very few accounts. NEAR Intents is the extreme case: its volume tripled while the number of transactions it
received fell 13% and the accounts sending them fell from 26,272 to 5,353. Intents users sign off-chain and a relayer
submits, so its customers cannot be counted from the chain at all.

## Evidence for

* **The headline numbers measured an app, not a network.** KaiChing peaked at 48.9 million accounts a month (August
  2025) and averaged under 2 transactions per account a month; it was 93% of all active accounts in October 2025. It
  stopped between March and April 2026. HOT wallet accounts (`.tg`) fell 86% over the year. *(chart: population)*
* **Activity per remaining account doubled.** Outside the reward apps, transactions per account went from 10.7 to 23.9
  a month. Named `.near` accounts send about 150 transactions a month each. *(chart: population)*
* **The named-account core grew on every measure.** Accounts +13%, transactions +20%, accounts active two months
  running +12% (42,316 → 47,531), accounts older than a year +18% (36,014 → 42,512). *(chart: population)*
* **Intents is a real, growing flow.** Daily volume tripled year on year while the NEAR price rose 39%. *(chart: intents)*

## Evidence against

* **The core shrank by two thirds, and has not stopped.** 1.81M → 0.62M accounts in a year, and 0.96M → 0.62M in the
  last four months alone. Implicit (unnamed) accounts fell 69% and their transactions 62%. Whatever NEAR's organic base
  is, it is smaller than a year ago.
* **The growing cohort is tiny and heavy.** 71 thousand named accounts at 150 transactions a month each is the profile
  of bots, market makers, solvers and application back ends, not of retail users. The largest named accounts in
  October 2026 are `intents.near` (1.44M transactions), two exchange bots (0.77M and 0.46M), a bridge relayer (0.66M)
  and `escrow.ai.near` (0.51M). This is concentration risk, not adoption.
* **Reward apps are still 43% of transactions.** KaiChing left, but Sweat, HOT and Meteor remain, and Sweat is now the
  single largest source of transactions on NEAR while its own user count fell 67%. The next exit would look the same.
* **Old accounts did not take over the core.** Accounts older than a year send 43% of core transactions, down from 52%.
  The base is not "a loyal old guard"; it turns over.
* **Total fees fell.** Network fees are down 52% YoY ($8,652 → $4,122 a day). Intents volume is not the same thing as
  revenue for the token; we did not measure value capture.
* **Usage does not lead price.** On weekly log-changes over ~6 years (n = 292–317 weeks, noise band ≈ ±0.11–0.12):
  Intents volume (n = 100 weeks, band ±0.20) shows nothing outside the band at any lag from −8 to +8 weeks; fees move
  with price in the same week (r = 0.38, and 0.18 at ±1 week, a symmetric pattern that weekly averaging produces);
  active accounts r = 0.14 at lag 0; transactions show four isolated bars of mixed sign. In total 9 of 85 lag tests
  fall outside the band where about 4 are expected by chance. *(chart: lead_lag)*

## What would change our mind

* **Core accounts stop falling.** Two consecutive quarters with core accounts flat or up would mean the base has found
  a floor. Today it has not.
* **The named-account core stops growing.** If `.near` accounts or their transactions fall below their October 2025
  level, the one positive trend is gone.
* **A new reward app re-inflates the headline.** Active accounts jumping by millions with under 2 transactions per
  account is KaiChing again, not growth; this thesis would ignore it, and so should a reader.
* **Intents volume falls back towards 2025 levels while the price holds.** Then the price is not tracking this flow.
* **A re-run shows a consistent lead**: several adjacent positive lags outside the band for more than one metric.

## Limits

* **"Core" is not "human".** It is every account outside three namespaces (`.kaiching`, `.tg`, `.sweat`). It still
  contains bots, application accounts and other apps that use implicit accounts.
* **Account age is first appearance in a transaction**, as signer or receiver, since genesis. An account created by a
  contract call and first used later looks younger than it is.
* **"Active two months running" is a calendar-month measure.** It says nothing about retention within a month.
* **February and March 2026** each contain a one-off burst of single-use implicit accounts (about 3.5 and 6 million). They
  inflate core account counts in those two months; the year-on-year comparison uses October to avoid them.
* **Intents volume, prices and fees are aggregator data** (DefiLlama, NearBlocks). We verified NearBlocks' daily
  transaction count against BigQuery for one day (exact match) and nothing else.
* **Lead-lag scans 17 lags × 5 metrics = 85 tests**; about 4 bars outside ±2/√n are expected by chance. One of the
  five metrics is the `active − new` proxy shown above to be unreliable; it is reported for completeness.
* **The app table is a manual grouping** of the 40 largest contracts and relayers, which cover 90% of October 2026
  transactions. A relayed transaction is assigned to its relayer, not to the contract it finally calls.
* **Re-running the account census costs 482.64 GB** of BigQuery scanning. It fits the free 1 TB a month, once.
