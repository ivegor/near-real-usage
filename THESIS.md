# Thesis: NEAR's collapse was accounts that apps were paying for. What pays its own way averaged below the year before until autumn 2026, then jumped, and a few hundred heavy accounts carry it

*Snapshot as of 2026-11-11. The numbers below are those of the committed `docs/summary.json` (a test checks the key
ones; a few supporting details, such as which accounts are an app's service accounts, are read from the committed
data files); the live dashboard is rebuilt daily, so its NearBlocks and DefiLlama figures will move away from this text.
Account counts come from full scans of the NEAR BigQuery public dataset (`sql/account_age.sql`,
`sql/payer_frequency.sql`, `sql/payers.sql`, `sql/top_accounts.sql`: every transaction, not a sample); prices, fees
and Intents volume from NearBlocks and DefiLlama. For accounts,
"YoY" = October 2026 vs October 2025, the last complete month, with the mean of August–October against the same three
months a year earlier in brackets, because single months are noisy.
This file is the argument. [`APPENDIX.md`](APPENDIX.md) holds the detail behind each section, under the same
headings, the side analyses and the history of our own drafts; the same test checks the numbers in both.*

## The long-term case, in short

After the largest reward app left, what remains on NEAR is the reward apps that stayed, which still send 43% of
transactions (in October, close to their lowest month), and a small amount of self-paid, financial activity carried by a few hundred heavy accounts. That
activity grew in autumn 2026 in two steps with different dates: NEAR Intents volume and the buybacks it funds stepped
up on 19 August and have held, while the load on the chain itself (its fees and gas) ran high for the four weeks of the price rally,
from 16 September to 15 October, and have come back down. What held is the volume and the buybacks in USD; the
buybacks in NEAR have held by the median day and not by the mean (see "Does it reach the token?"). The NEAR its revenue brings in equals 15% to 18% of the new NEAR
issued, depending on the window. That is a narrow case. Nine dated predictions say what would widen it or close it
(see "What would change our mind").

## Claims and what the data says

October 2025 → October 2026, three-month means in brackets. Each row in full, with every qualification, is in the
appendix.

| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | The collapse in activity is the exit of reward apps | **Supported for the size of the fall; what NEAR's own users did is open** | Accounts whose fees an app paid: 43,049,960 → 552,826 (100.6% of the net fall as counted, 99.2% with the one-off deletion taken out). That is more than the whole net loss of accounts (43,642,992 → 1,379,518), because self-paying accounts rose, 593,032 → 826,692, and the rise is itself a one-off: 560,092 old KaiChing accounts paid for one transaction each in October. KaiChing: 40.39M accounts a year ago, gone since spring. That says where the fall came from, not that NEAR's own users stayed: the independent accounts that returned fell 40,759 → 31,452, and how many regular self-paying accounts really left is not known (claim 3) |
| 2 | A stable core of returning users remains (first draft) | **Refuted** | Accounts outside the reward namespaces 1,814,743 → 621,166 (−66%; −57%), and that group is mostly other apps' sponsored accounts (96% of the returning ones a year ago) |
| 3 | The number of accounts that pay for themselves holds up | **Not established** | Outside the reward namespaces, regular self-paying accounts 27,078 → 17,105 (−37%; −50%), low of 7,201 in August 2026. But up to 15,162 of last year's were players of Meteor's reward game paying their own fees, whose calls a relayer submits now, so how many really left is not known (see "Who pays, and how often") |
| 4 | The remaining accounts are used more intensively (second draft) | **Mostly a change of mix** | 10.7 → 23.9 transactions per core account is mostly a change of mix: 11.7 at last year's mix of account types, so +9% is left (implicit accounts 5.4 → 6.6, named 142.5 → 150.9). The same accounts were not followed from one October to the next |
| 5 | Named `.near` accounts are a growing core (second draft) | **Not supported** | Accounts +13% (+2%); with more than one transaction −28% (−15%). Their transactions did grow: 8.96M → 10.77M (+20%; +42%) |
| 6 | Self-paid activity outside reward apps is growing | **On average below the year before for nine months, up in autumn 2026** | Core transactions paid by the sender 9.75M → 12.49M (+28%; +35%); on longer windows +24% (six months), +6% (nine) and −5% (eleven). In the nine months before the step (December to August) they averaged 7.61M against 9.16M a year earlier (−17%; −21% without the February burst), and all of that fall is implicit and other accounts: named `.near` accounts sent 4% more than a year earlier, implicit accounts 49% less (those under a year old 77% less) and other accounts 53% less. The jump came in the weeks of a price rally, and November started lower (see "Evidence against") |
| 7 | Financial use of the chain is growing | **Up in October 2026, and already above the year before in August, before the price doubled** | Transactions to the exchange, Intents, token contracts and bridges 6.72M → 9.18M a month (+37%); Ref/Rhea exchange +96%, token contracts +47%, bridges and chain signatures +43%. Without the transactions of one account whose sampled calls all failed, +29% |
| 8 | Cross-chain demand through NEAR is growing | **Up since 19 August 2026; level with November 2025** | NEAR Intents volume $55.6M → $128.6M a day (+131%, October to October, DefiLlama), but October 2025 was the middle of a ramp-up: November 2025 already averaged $122.0M (October 2026 is +5% on it). In the nine months in between volume averaged $74.5M; against that level October 2026 is +73% |
| 9 | NEAR's transactions come from many independent accounts | **Refuted** | 30 accounts send 50% of transactions; the top 10 send 37% (17% a year earlier); 486 accounts with 1,000+ transactions send 70%. Seven of the ten largest are relays or service accounts (Intents, Sweat, the bridges), so this counts who submits transactions; the people behind a relay are not visible on the chain |
| 10 | Intents revenue offsets the dilution of NEAR holders | **Not yet** | Buybacks (DefiLlama's name for the NEAR arriving at the revenue wallets) at $20.7M a year against $115M a year of net new NEAR: equal to 18% of the net new supply over the last 90 days, so at most that share of the dilution is offset,, 15% to 18% over other windows, and 13% in the median 90-day window since the buybacks began; 5.6 times the captured revenue needed |
| 11 | Usage changes lead price changes | **Not supported** | 6 of 85 lag tests outside the noise band, about 4 expected by chance; none stands after Holm's correction for testing 85 lags together |

Claims 2, 4 and 5 are what is left of three readings in our own drafts that did not survive closer measurement as
written; the appendix says what each was and what replaced it.

## Who pays, and how often

The cleanest way to split NEAR's accounts is by three questions a product owner would ask, and none of the lines
between the groups is a number we chose (`sql/payer_frequency.sql`, every transaction from August 2025 to October 2026):

* **Who pays the fee?** If a relayer submitted and paid for every transaction of the account in the month, an app is
  paying for that user: *sponsored*. If the account paid for at least one itself: *self-paying*.
* **Whose account is it?** KaiChing and HOT create accounts for their users inside their own namespaces
  (`.kaiching`, `.tg`). Everything else is outside them.
* **How often does it act?** Transactions in the month, by powers of ten. Under 10: *occasional*. 10 to 999: *regular*.
  1,000 or more is over 30 a day, every day: *heavy*. We read it as likely automated or institutional; the line is
  measured, that reading is not (see "Limits").

| Segment | October 2025 | October 2026 | Change (three-month means) |
|---|---|---|---|
| Sponsored accounts, all apps | 43,049,960 | 552,826 | −99%; −99% |
| Sponsored accounts outside the two reward namespaces (Sweat, Meteor and other apps) | 1,680,016 | 484,257 | −71%; −59% |
| HOT users who pay their own fees | 458,286 | 129,677 | −72%; −68% |
| of them regular (10 to 999 transactions a month) | 333,728 | 60,879 | −82%; −77% |
| Independent self-paying, occasional | 107,295 | 119,340 | +11%; −37% |
| Independent self-paying, **regular** | 27,078 | 17,105 | −37%; −50% |
| Independent self-paying, **heavy** | 370 | 475 | +28%; +0% |

Four things follow; the appendix has each in full.

* **The fall outside the reward namespaces was other apps' accounts.** A year ago 93% of the accounts outside the two
  reward namespaces were still someone's sponsored accounts. Named by the relayer that paid for them
  (`sql/payers.sql`), they were the accounts of two apps: Sweat's sponsored accounts went 1,246,366 → 410,890 and
  those of the game Ember 387,762 → 0.
* **Sponsored accounts measure what apps spent, not what users would pay.** That part of the collapse measures what
  apps were willing to spend on their users' fees, not whether those users would pay their own way. It is not nothing
  for the token: the relayers paid those fees in NEAR, and the day KaiChing stopped took about two thirds of the
  network's fees with it (see "Evidence against").
* **The fall of the regular class cannot be read as users leaving.** The regular self-paying accounts outside the
  reward namespaces are the closest thing the chain has to a count of its own users, and the group held another
  app's users. In October 2025, 15,162 accounts called the reward game of the Meteor wallet
  (`aa-harvest-moon.near`) themselves and paid the fees; by October 2026 Meteor's relayer submits those calls. Players
  who act through that relayer and pay for anything of their own can sit in either year's class as well (up to 4,313
  now and 9,110 a year ago). How many players were in each year's class the tables do not say, and the change
  without them lies anywhere from −53% or lower to +44% or more. As counted the change is −37%. The direction is not
  established without another query.
* **The heavy accounts carry the transactions.** The growth in self-paid transactions belongs to the heavy accounts:
  they send 91% of it (85% a year ago). That share is not new with the rally: from March to September 2026 there were
  171 to 266 heavy accounts, and they sent 91% to 95% of the self-paid transactions every month. Occasional accounts
  swing with one-off events and are not read as a trend.

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
| NEAR Intents | 8.9% | 1.6% | −13% | 2.01M transactions, up to 97% of them signed by two accounts (`intents.near`, `escrow.ai.near`). The second one's sampled calls did not go through (all 26 in the keyless sample failed, over 90 days); without its 513,339 transactions the count is down 35% |
| Meteor wallet | 3.1% | 0.7% | −29% | Wallet with a reward game |
| KaiChing | 0.4% (2.8% by namespace) | 49.6% | −100% | Reward app, gone since spring. In October its old accounts were deleted: 560,106 transactions that are not calls to any of the 40 largest contracts, and 560,092 accounts sent exactly one. All 13 of them that fall in the keyless sample are `DeleteAccount` on the account itself, between 2 and 7 October. NearBlocks counted 579,300 deleted accounts in October, 561,960 of them from 2 to 8 October |
| Other contracts in the top 40 | 7.1% | 3.0% | −62% | The fall is the game Ember (2.80M → 0.16M transactions); the other contracts are 1.42M → 1.44M (+2%) |
| Everything else | 9.8% | 5.9% | −73% | Transactions to contracts outside the 40 largest. A year ago 6.74M of them were sent by KaiChing's own accounts and 0.56M now are the one-off above; the rest is 1.58M → 1.65M (+4%) |

Reward and wallet apps still send 43% of transactions through their own contracts and relayers (86% a year ago), or
45% counting the KaiChing one-off, and October is near the low of that share: by namespace the reward apps sent 34%
of October's transactions against 31% in September and 45% to 56% in each month from April to August. The financial
half is larger than a year ago but operated by very few accounts: NEAR Intents' volume more than doubled while the
accounts sending its transactions fell from 26,272 to 5,353, and every contract of the group that had more than a
thousand callers a year ago and is in both lists has fewer now, except the exchange's main contract. Outside the
reward side and the financial group the rest of the chain is level, 3.00M → 3.09M (+3%), though its named part is not
the same activity in the two months.

## Does it reach the token?

Partly, and not enough yet. Over the last 90 days NEAR Intents charged $18.9M in fees,
51 times the network's own transaction fees. NEAR captured $5.1M of that
(27%); the rest stays with solvers and the front ends that route the swaps. Since
2026-02-23, by DefiLlama's description of its series, the captured revenue is used to buy NEAR on the open market. At the last 90 days' pace that is
$20.7M a year. Over the same period the supply of NEAR grew at 32.3M NEAR a
year net of burned fees (2.48% over the last 365 days), worth $115M a year at the
period's mean price of $3.58. **The buybacks equal 18% of the net new supply.** That is a ratio of two
flows, not a measured offset of anyone's dilution: "buybacks" is DefiLlama's name for the series, and its adapter
counts the NEAR and wNEAR arriving at the revenue wallets and files all of it as bought for holders since that date.
The purchases on the market are not in the data, nor is it known that the NEAR stays out of circulation for good;
what the chain shows is that the NEAR arrives and, so far, stays. If all of it was bought and is held, it offsets at
most 18% of the dilution (below). Covering all of the dilution needs
5.6 times the captured revenue at this price, and the market capitalisation is 227 times the
annual buyback. The bought NEAR is not burned, so supply itself does not shrink.

The 18% is close to the best window there has been. Of the 173 windows of 90 days since the buybacks began, it is the
6th highest; the median window covers 12.7%, and windows of other lengths that end on the same day give 15% to 18%.
And the step in buybacks is mostly the price. In USD they went from $17,025 a day before 19 August to $59,297 a day
since (3.5 times); in NEAR, from 10,456 to 17,016 NEAR a day (1.6 times). Whether the buybacks in NEAR have held
since depends on the statistic: by the mean of the last two half-months they have not, by the median day they have.

**Where the step in revenue came from.** Revenue is volume times what is kept from each dollar of it, and the step of
19 August is both: volume grew 1.9 times and the take 1.6 times, from 2.62 to 4.27 basis points. Our data does not say
what raised the take. Two other entries in this hackathon traced the NEAR arriving at the revenue wallets on the chain,
and both name one cause: a confidential pool inside NEAR Intents, opened in these months
([Wilivms/near-revenue-audit](https://github.com/Wilivms/near-revenue-audit),
[abhirgfu/dark-matter](https://github.com/abhirgfu/dark-matter)). We did not reproduce their traces. If they are
right, most of the revenue behind the buybacks now comes through one channel that is three months old and rewarded for
being used. And the level is not flat: over the last 30 days volume is 22% below the 30 days before, gross fees 26%,
and captured revenue 20% in USD and 25% in NEAR.

**An approved cut in issuance would narrow the gap, slowly.** House of Stake proposal
[HSP-029](https://gov.near.org/t/hsp-029-establish-a-24-month-issuance-ramp-to-a-1-6-target-rate-of-near-token-emissions/42644)
lowers the maximum issuance from 2.5% to 1.6% a year on a 24-month ramp; it is not in force, and the protocol's own
configuration still gives a maximum of 2.5%. As arithmetic on that one parameter, with revenue, price and burn held
where they are, the 18% becomes 28% at the end of the ramp and the 5.6 times becomes 3.6.

**The same money, read from the chain.** We asked an archival RPC node, with no key, what the three wallets DefiLlama's
adapter names hold at the start and at the end of the same 90 days (`python -m thesis wallets`). Together they held
1,456,744 NEAR more at the end. That is 0.98 of the revenue DefiLlama reports for those days, and 18.3% of the 7.95M
NEAR of net new supply: the 18% again, this time in NEAR and with no price in it. Over the last 30 days it is 15.4%.
Whether the NEAR was bought on the market or arrived as NEAR, the balances do not say. *(chart: value_capture)*

## An independent check: a keyless sample of the chain

Every account and transaction count above comes from one source, BigQuery. As a check we measured the chain a second way, with no key and no
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
  stopped between March and April 2026. Its relayer's monthly totals came to 2,000,000 transactions a day, to within a
  thousandth, in 8 of its 17 months in the census: a total that round, month after month, points to a job with a
  daily quota, though the census is monthly and does not show the days one by one. The step that analyses of the daily aggregates see and cannot name
  is this app stopping: NearBlocks' daily transactions went from 3,758,663 on 2026-04-01 to 1,063,375 on 2026-04-02.
  KaiChing can be at most 51% of that one-day fall (everything it sent in April); the census is monthly, so how much
  it was is not measured. If its relayer sent all of April's relayed transactions on 1 April, as a column of the daily
  data suggests, it is at least 38%. *(chart: population)*
* **Self-paid transactions rose in autumn 2026.** Outside the reward apps, transactions paid by the sender rose from 9.75M
  to 12.49M a month; September and October 2026 are two of the three highest of the 23 months from December 2024 to
  October 2026. The whole fall in core transactions (−23%) is sponsored transactions disappearing. Both Octobers also
  hold transactions that are not independent use (reward-side calls, and one account whose calls fail): without them
  the October change is +26% if every caller of the reward-side contracts is outside the reward namespaces, and between
  +19% and +31% as far as the tables can say (see "Limits"). *(chart: population)*
* **Financial use is up October to October** while the reward side fell 92% and the rest of the chain stayed level
  (+3%). In the second half of August 2026, before the price doubled, the group was already above the same days of
  2025 on the keyless sample: 207 thousand transactions a day against 61 thousand. *(chart: clients)*
* **Intents is a real flow, at a higher level since 19 August.** The step came as the price began to move, on a day it
  was $1.59, and since then every half-month has averaged above the range of the nine months before ($63.2M to
  $89.6M a day), also the first 11 days of November ($129.7M). After the step the price never fell below $1.73
  (20 August), so the new level of volume has not yet been seen at the price of the old one. *(chart: intents)*

## Evidence against

* **No growth in regular self-paying accounts can be shown.** They number 17,105 against 27,078 a year earlier (−50%
  on three-month means), after sliding to 7,201 in August 2026. Part of that fall is one game moving its calls to
  a relayer (see "Who pays, and how often"), so its real size is unknown. The September rebound is two months old
  and came with a price rally. HOT users who pay their own fees fell 72%, the regular ones among them 82%.
* **The self-paid series is volatile, and November started lower.** Monthly values run from 5.8M to 13.1M with no
  smooth trend; December 2024 was 12.07M, about where October 2026 is, and a third of February 2026 was a one-off
  burst (see "Limits"). The two strong months are four strong weeks: on the keyless sample, self-paid transactions
  outside the namespaces ran at 320 thousand a day in the first half of September, 556 thousand in the second, 492
  thousand in the first half of October and 325 thousand in the second. In the first 11 days of November it runs at
  356 thousand a day: 12% below October's rate and 5% below November 2025's. Those days hold a one-off of dormant
  accounts on 10 November; with the filter used for February applied to every month compared it runs at 347 thousand
  a day, 14% below October's rate and 7% below November 2025's.
* **The autumn step is two events, and the second came and went with a price rally.** NEAR went from $1.92 to $4.89
  during September 2026, peaked at $5.89 on 12 October and was $3.58 on the snapshot date. By half-months, Intents
  volume and the buybacks in USD stepped up on 19 August and have held, while the chain's fees in NEAR and the gas it
  burned were above their earlier top only in the two half-months from 16 September to 15 October, and on the keyless
  sample the exchange's transactions rose from 1 September and were back down by the second half of October. So the
  exchange's transactions of the rally, and the extra load on the chain, have left with it, while the flow through
  Intents has held. Predictions A2, A3 and B2 state that the new level holds; a miss on them would mean that the new level
  did not outlast the rally, which fits the trading reading but would not show what caused the step.
* **Very few accounts carry it, and a large count is not always use.** Seven of the ten largest accounts in October
  2026 are relays or service accounts (`intents.near`, three of Sweat, two bridge relayers and `escrow.ai.near`), so
  the count says who submits transactions, not how many people stand behind them; either way the chain depends on a
  handful of operators. All 26 transactions that `escrow.ai.near` sent to NEAR Intents in the keyless sample failed.
  That account sent 513,339 transactions in October, about a quarter of what NEAR Intents received if all of them went
  there. The sample spans 90 days, not October, so taking all of them out is the far end, not a measured count of
  failed calls: the financial group is then up 29%, not 37%, and self-paid transactions outside the reward namespaces
  23%, not 28%.
* **Reward apps are still 43% to 45% of transactions,** and October was close to their lowest month (see "Who is left:
  the customers"). KaiChing left, but Sweat, HOT and Meteor remain. Sweat's 11 service
  accounts in the `.sweat` namespace alone send 17.7% of all transactions while its user count fell 67%. The next exit
  would look the same. And November started with more of it, not less: in its first 11 days HOT's namespace (`.tg`)
  sent 196 thousand transactions a day against 100 thousand in October, while the chain as a whole did not move.
  HOT's rise is measured from one month after its lowest, though: September is the lowest of the 24 months of that
  series, at a change of relayer, and the return began in October.
* **Old accounts did not take over the core.** Accounts older than a year send 43% of core transactions, down from 52%
  (52% against 56% over three months). That fall is a change of mix, as in claim 4: sponsored transactions shrank from
  50% of the core to 16%, and inside the self-paid transactions old accounts gained (36% → 39%).
* **Fees fell over the year.** Network fees of the last 90 days are down 52% in USD on the same 90 days a year
  earlier ($8,652 → $4,122 a day) and 68% in NEAR; on the 90 days just before them they are up (+138% in USD, +24%
  in NEAR). Most of the fall in NEAR is the step of 2 April: the day KaiChing stopped took about two thirds of the
  network's fees with it.
* **The revenue step leans on a higher take, and the last month is down.** Since 19 August NEAR keeps 4.27 basis
  points of Intents volume against 2.62 before, and two other entries trace most of that revenue to one new,
  incentivised channel (see "Does it reach the token?"). Over the last 30 days volume, gross fees and captured revenue
  are all a fifth to a quarter below the 30 days before.
* **No usage metric leads price in our tests.** On weekly log-changes over ~6 years, 6 of 85 lag tests fall outside
  the noise band where about 4 are expected by chance, and none of the 85 stands after Holm's correction for testing
  them together (the smallest p-value is 0.009; the first step of the correction asks for 0.0006). Fees in USD do
  correlate with price in the same week (r = 0.38), mostly because USD fees are NEAR fees multiplied by the price:
  in NEAR, fees show nothing outside the band.
  What was tested is a linear correlation of weekly changes at fixed lags of up to eight weeks: it finds no lead that
  stands, and it does not rule out one that is non-linear or holds only in some periods. It is a screen, not a proof
  that no lead exists (see "Limits" on the dependence between weeks). *(chart: lead_lag)*

## What would change our mind

These are written down as nine dated predictions in [`PREDICTIONS.md`](PREDICTIONS.md). Their thresholds are either
reference levels taken from the data (the top of a metric's range before the September 2026 step, or its low before
the rebound) or natural lines (parity, half of break-even, dozens rather than hundreds), not numbers tuned to the
outcome. The build scores all nine: five from the daily data as their dates
pass, four once the account queries have been run again for the month they name. "The September step" is the
predictions' name for the month after their reference range; read by half-months it is two events (see "Evidence
against"), and the reference range of Intents volume and buybacks already holds the first of them: the last 13 days
of August, after 19 August, which makes their thresholds harder to stay above, not easier.

* **Regular self-paying accounts fall back to their low.** They bottomed at 7,201 in August 2026 and rebounded in
  September. A month at or below that low means the rebound was a spike and the base has not found a floor (B1
  checks January 2027).
* **Self-paid core transactions fall back into their old range.** From December 2025 to August 2026 their highest
  month was 10.38M (February 2026); earlier months were higher, up to 12.07M in December 2024. A quarter
  averaging below 10.38M means September and October did not set a level above that range. It would not mean that
  nothing outside the reward apps grows: a third of that February was a one-off burst (see "Limits"), without it the
  top of the range is 8.65M (June 2026), so a quarter can miss B2 and still be above
  the top of the range without that burst.
  The threshold we wrote down is the harder of the two to stay above. The first 11 days of that quarter are in the
  census already, at a rate of 10.68M a month, or 10.41M without the one-off of 10 November (B2 checks November to
  January).
* **A reward app re-inflates the headline.** Active accounts jumping by millions with under 2 transactions per account
  is KaiChing again, not growth. HOT's November is not that pattern, but it is a reward app growing again: in the
  first 11 days of November 2026 HOT (`.tg`) accounts number 297,843, more than in all of October (198,246), with 7.2
  transactions each and 96% of them older than a year, so old accounts are coming back rather than new ones being
  made, and its transactions run at almost twice October's daily rate (see "Evidence against").
* **Intents volume falls back into its old range.** From December 2025 to August 2026 no month averaged above $89.6M
  a day, and August, the highest at $89.6M, owes it to its last 13 days; November 2025 had spiked to $122M and fell straight back. A month below $89.6M means autumn 2026 was a second
  spike, not a new level, and the buybacks it funds fall with it (A1 checks the week to 17 November, A2 December).
* **A re-run shows a lead**: two neighbouring positive lags outside the band with correlations of one sign, with or
  against the price, for any one metric (A5), and all the
  more so for several.

## Limits

* **"Outside the reward namespaces" is not "NEAR's own users".** The account-age census groups accounts by namespace,
  and a year ago 93% of the accounts outside `.kaiching`, `.tg` and `.sweat` were sponsored users of other apps
  (`.sweat` itself is 11 service accounts; Sweat's users are relayed implicit accounts). Read the age and returning
  figures of that group with this in mind; the payer and frequency split is the cleaner count.
* **Self-paying means the account paid for at least one transaction in the month.** It may also have sponsored ones.
  A sponsored account is not a lesser one; it is one an app is paying for, and it goes when the app does.
* **An account an app acts for is not shown to be a person.** For a relayed transaction we count the account the
  relayer acted for, and the committed data shows such accounts acting like the app's own: KaiChing's relayer's monthly totals
  point to a daily quota, nearly all of the game Ember's sponsored accounts had also been active the month before, and Meteor's relayer claims rewards in
  batches for accounts whose names start with the same two letters. "Sponsored accounts" counts accounts that apps act for; how many people
  are behind them the chain does not say.
* **"Independent" is defined by exclusion, and it let another app's users in.** It means: pays for at least one of
  its own transactions and is not in the `.kaiching` or `.tg` namespace. Meteor's game sat inside it (see "Who pays,
  and how often"). We found it by reading the 40 most-called contracts of both months; a smaller game of the same kind
  would not show there. Read the regular class as an upper bound on the independent accounts that act regularly, not
  as a count of users. The same holds for transactions: direct calls to reward-side contracts outside the namespaces
  are inside "self-paid transactions outside the reward apps", and a call from inside the namespaces is not. How many
  of each the tables do not say, so with those calls out the October change lies between +24% and +37%.
* **A transaction is counted whether it succeeded or not.** None of the queries here reads how a transaction ended.
  That was checked on a sample for one contract only, NEAR Intents, where all sampled calls of one account failed
  (see "Evidence against"). How many transactions fail elsewhere on the chain is not measured.
* **The pace of November is eleven days.** The census scan stopped on 2026-11-11, so the unfinished month is used
  only as rates per day of transactions, set against the rates of whole months, for every series it is quoted for.
* **Frequency classes are powers of ten of a monthly count.** "Heavy" (1,000 or more) is our reading of that line as
  automation; we did not inspect the accounts one by one beyond the forty largest.
* **Account age is first appearance in a transaction**, as signer or receiver, since genesis. An account created by a
  contract call and first used later looks younger than it is.
* **"Active two months running" is a calendar-month measure.** It says nothing about retention within a month.
* **One-off bursts.** February, March and April 2026 each contain a one-off burst of existing implicit accounts
  sending one transaction each (about 3.5, 6.0 and 1.1 million accounts against about 0.1 million in an ordinary
  month). February's was paid by the senders, so it also sits in the self-paid series: 3.37M of that month's 10.38M
  self-paid core transactions (32%), and NearBlocks counted 3,401,092 deleted accounts that month. Without that group
  the nine-month change is +2% instead of +6% and the eleven-month one −8% instead of −5%. Deletions in other months
  (named accounts in spring 2025, December 2025) are smaller and are set out in the appendix with what they move.
* **The census's series start in December 2024**, because the first month of the table has no month before it.
  Transaction counts were checked against NearBlocks month by month: they differ by at most 484 transactions (0.002%)
  in 22 of the 25 months, and BigQuery is lower in three early months (by up to 2.5%), which no October or
  three-month comparison touches.
* **Intents volume, prices and gross fees are aggregator data** (DefiLlama, NearBlocks) and were not checked against a
  second source; captured revenue was, against the balances of the wallets it arrives at. Every year-on-year figure for
  Intents volume shrinks as its base moves through the ramp-up of autumn 2025; the steadier yardstick is the level
  between the two autumns, $74.5M a day from December 2025 to August 2026.
* **Net new supply is not dilution for every holder.** New NEAR is issued mostly as staking rewards, so a holder who
  stakes receives part of it. The 18% compares buybacks with all of the net new supply, which is the most a holder
  could be diluted by. It is a ratio of flows: what it does for holders depends on the NEAR being bought on the market
  and kept out of circulation, which the data do not show.
* **Lead-lag scans 17 lags × 5 metrics = 85 tests**; about 4 bars outside ±2/√n are expected by chance. The p-values
  behind Holm's correction use Fisher's z, a normal approximation, on weekly changes. Band and p-values treat the weeks
  as independent, and they are not: weekly price changes correlate 0.31 with the week before, the usage metrics' changes
  −0.09 to −0.27. Signs this opposite at the first lag narrow the true band rather than widen it (Bartlett's formula),
  but no correction for the dependence was computed, so band and p-values are approximate. One of the
  five metrics is the `active − new` proxy shown above to be unreliable; it is reported for completeness.
* **The app table is a manual grouping** of the 40 largest contracts and relayers, which cover 90% of October 2026
  transactions. Allowing for the group's contracts outside a month's 40 largest, the +37% lies between +30% and +39%.
  Filing the contracts the exchange's own bots called with the exchange gives the financial group +31% to +33%. The
  reward-app group is left as it was when prediction B4 was written.
* **The daily source changes on 2026-11-22.** NearBlocks switches off the API this text was built from. The committed
  copy keeps every number here reproducible, and the daily build goes on from the API that replaces it for the columns
  that mean the same there; counts of signers, of new and of deleted accounts end with the old one.
* **The traces of where the revenue comes from are not ours.** The confidential-pool share quoted in "Does it reach
  the token?" is the work of two other entries; we checked that they state it and that our take per dollar of volume
  rises as theirs does, not their on-chain traces.
* **The issuance scenario is one parameter.** It scales the measured net new supply by 1.6/2.5 and holds revenue,
  price and burned fees fixed; the cut is approved by governance and not yet adopted by validators.
* **The account census ends on 2026-11-11** and costs 482.64 GB of BigQuery scanning to re-run (the free tier is 1 TB
  a month). The dashboard keeps October 2026 as its last month until the query is run again.
