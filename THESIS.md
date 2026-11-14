# Thesis: NEAR's collapse was accounts that apps were paying for. What pays its own fees averaged below the year before until autumn 2026, then jumped, and a few hundred heavy accounts carry it

*Snapshot as of 2026-11-11. This file is the argument; [`APPENDIX.md`](APPENDIX.md) holds the detail behind
each section, under the same headings. Where the numbers come from and how they are checked is at the end of the
next section.*

## The long-term case, in short

1. **The collapse was accounts an app was paying for.** Accounts acting on NEAR fell 97% (43.6M → 1.38M a month);
   those whose fees an app paid went from 43.05M to 0.55M, which is the whole fall (claim 1).
2. **What is left is in few hands.** 30 accounts send half of all transactions; outside the reward apps' namespaces
   475 heavy accounts send 91% of the self-paid ones (claim 9 and "Who pays, and how often").
3. **Self-paid activity ran below the year before, on average, until autumn 2026.** It is up 28% October to October,
   after nine months averaging 17% below the year before, and the jump came in the weeks of a price rally (claim 6).
4. **Little of it reaches the token so far.** The NEAR that Intents revenue brings in equals 18% of the net new NEAR
   issued over the last 90 days; matching the issuance at this price needs 5.6 times the revenue (claim 10).
5. **Usage did not lead the price in this test.** 5 of 85 weekly lead-lag tests fall outside the noise band, where
   about 4 are expected by chance, and none stands after Holm's correction (claim 11).

**For a long-term holder.** That is a narrow case, and it is not a valuation of NEAR: what the data supports is one
product, NEAR Intents, and a few hundred heavy accounts. Holding NEAR for years on this evidence is a bet on two
changes that are not in the data yet. One is the revenue that reaches the token matching the new NEAR issued: at this
price that takes 5.6 times the captured revenue, or 3.6 times at the issuance the approved HSP-029 ends at. The other
is the base widening beyond those accounts and that product: outside the reward namespaces, regular accounts that pay
their own fees number 17,105 against 27,078 a year earlier as counted, and how many really left is not established
(claim 3). Nothing here says when, or whether, either happens. Nine dated predictions check the first steps, through
February 2027 (see "What would change our mind"). The same case as one paragraph, with the shares of the app groups
and the two steps of the autumn and their dates, is in the [appendix](APPENDIX.md#the-long-term-case-in-full).

*The numbers below are those of the committed `docs/summary.json` (a test checks the key
ones; a few supporting details, such as which accounts are an app's service accounts, are read from the committed
data files); the live dashboard is rebuilt daily, so its NearBlocks and DefiLlama figures will move away from this text.
Account counts come from full scans of the NEAR BigQuery public dataset (`sql/account_age.sql`,
`sql/payer_frequency.sql`, `sql/payers.sql`, `sql/top_accounts.sql`: every transaction, not a sample); prices, fees
and Intents volume from NearBlocks and DefiLlama. For accounts,
"YoY" = October 2026 vs October 2025, the last complete month, with the mean of August–October against the same three
months a year earlier in brackets, because single months are noisy.
The appendix also holds the side analyses and the history of our own drafts; the same test checks the numbers in
both files.*

## Claims and what the data says

October 2025 → October 2026, three-month means in brackets. Claims 2, 4 and 5 were readings in our own drafts that
did not survive closer measurement; they, and every row below in full, are in the
[appendix](APPENDIX.md#claims-and-what-the-data-says-in-full).

| # | Claim | Result | Evidence |
|---|---|---|---|
| 1 | The collapse in activity is the exit of reward apps | **Supported for the size of the fall; what NEAR's own users did is open** | Accounts whose fees an app paid: 43,049,960 → 552,826 (100.6% of the net fall as counted, 99.2% with the one-off deletion taken out). That is more than the whole net loss of accounts (43,642,992 → 1,379,518), because self-paying accounts rose on a one-off (in the appendix). KaiChing: 40.39M accounts a year ago, gone since spring. That says where the fall came from, not that NEAR's own users stayed: the independent accounts that returned fell 40,759 → 31,452, and how many regular self-paying accounts really left is not known (claim 3) |
| 3 | The number of accounts that pay for themselves holds up | **Not established** | Outside the reward namespaces, regular self-paying accounts 27,078 → 17,105 (−37%; −50%), low of 7,201 in August 2026. But up to 15,162 of last year's were players of Meteor's reward game paying their own fees, whose calls a relayer submits now, so how many really left is not known (see "Who pays, and how often") |
| 6 | Self-paid activity outside reward apps is growing | **On average below the year before for nine months, up in autumn 2026** | Core transactions paid by the sender 9.75M → 12.49M (+28%; +35%); on longer windows +24% (six months), +6% (nine) and −5% (eleven). In the nine months before the step (December to August) they averaged 7.61M against 9.16M a year earlier (−17%; −21% without the February burst), and all of that fall is implicit and other accounts: named `.near` accounts sent 4% more than a year earlier, implicit accounts 49% less (those under a year old 77% less) and other accounts 53% less. Self-paying is a technical category: it does not show that the money was the users' own. The jump came in the weeks of a price rally, and November started lower (see "Evidence against") |
| 7 | Financial use of the chain is growing | **Supported only as more transactions to the group's contracts, October to October; users, successful operations and demand are not measured** | Transactions to the exchange, Intents, token contracts and bridges 6.72M → 9.18M a month (+37%); Ref/Rhea exchange +96%, token contracts +47%, bridges and chain signatures +43%. The count holds the 513,339 transactions of one account whose sampled calls to Intents all failed: without them the group is +29%. This counts transactions to the group's contracts, not who sent them, whether they succeeded or why they were sent (see "Who is left: the customers") |
| 8 | Cross-chain demand through NEAR is growing | **Higher since late August 2026; level with November 2025** | NEAR Intents volume $55.6M → $128.6M a day (+131%, October to October, DefiLlama), but October 2025 was the middle of a ramp-up: November 2025 already averaged $122.0M (October 2026 is +5% on it). In the nine months in between volume averaged $74.5M; against that level October 2026 is +73% |
| 9 | NEAR's transactions come from many independent accounts | **Refuted** | 30 accounts send 50% of transactions; the top 10 send 37% (17% a year earlier); 486 accounts with 1,000+ transactions send 70%. Seven of the ten largest are relays or service accounts (Intents, Sweat, the bridges), so this counts who submits transactions; the people behind a relay are not visible on the chain |
| 10 | Intents revenue offsets the dilution of NEAR holders | **No: the revenue equals 18% of the net new supply, and an offset to holders is not measured** | Buybacks (DefiLlama's name for the NEAR arriving at the revenue wallets) at $20.7M a year against $115M a year of net new NEAR: equal to 18% of the net new supply over the last 90 days as a ratio of USD (17.9%); counted in NEAR at each day's price it is 18.7%, and the revenue wallets' balances grew by 18.3% of the new NEAR. The median 90-day window since the buybacks began gives 12.7%. Matching the issuance at this price needs 5.6 times the captured revenue. Whether the NEAR was bought on the market and stays out of circulation the data do not show |
| 11 | Usage changes lead price changes | **This test found no convincing lead** | 5 of 85 lag tests outside the noise band, about 4 expected by chance; none stands after Holm's correction for testing 85 lags together, nor with the band adjusted for the dependence between weeks. A linear screen at fixed lags, not proof that no relation exists |

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
  for the token: the relayers paid those fees in NEAR, and the network's fees fell by about two thirds in the step in
  which KaiChing stopped (see "Evidence against"; how much of it was KaiChing's is not measured).
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
(`sql/top_accounts.sql`; the grouping into apps is the table in `thesis/clients.py`).

This files a transaction by the account it passes through, not by what it was for: a wallet's relayer can carry a
swap, and a call to an exchange can be paid for by rewards, so the reward and financial groups below are not a
measure of motive. How much that matters can be read on the keyless sample, which sees what a relayed transaction
finally calls: of the 576 sampled transactions of autumn 2026 that the table would file with the reward and wallet
apps, 1 ended in a contract of the financial group and 15 in HOT's own bridge contracts, which the table files with
HOT (0.4% of October's transactions). Most of the rest are calls to the apps' own reward and token contracts.

| Who | Share of transactions | A year earlier | Transactions, YoY | What it is |
|---|---|---|---|---|
| Sweat | 25.8% | 7.5% | −45% | Move-to-earn app. Five service accounts send most of it; its relayed users fell 1,263,047 → 413,927 |
| Ref Finance / Rhea | 13.4% | 1.1% | +96% | Exchange and lending. 96% of these transactions go to the main contract from 2,586 accounts, the largest of them trading bots with hundreds of thousands of swaps a month; 15,140 accounts used the concentrated-liquidity contract, for 44,392 transactions |
| HOT wallet | 13.3% | 28.5% | −93% | Telegram wallet: reward claims (`game.hot.tg`), its relayer and its own bridge contracts |
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
group receives more transactions than a year ago, but very few accounts send them: NEAR Intents' volume more than doubled while the
accounts sending its transactions fell from 26,272 to 5,353, and every contract of the group that had more than a
thousand callers a year ago and is in both lists has fewer now, except the exchange's main contract. Outside the
reward side and the financial group the rest of the chain is level, 3.00M → 3.09M (+3%), though its named part is not
the same activity in the two months.

## Does it reach the token?

Partly, and not enough yet. Over the last 90 days NEAR Intents charged $18.9M in fees,
51 times the network's own transaction fees. NEAR captured $5.1M of that
(27%, a ratio of two flows over the period: the fees accrue swap by swap, the captured revenue arrives at the
wallets in transfers of its own); the rest stays with solvers and the front ends that route the swaps. Since
2026-02-23, by DefiLlama's description of its series, the captured revenue is used to buy NEAR on the open market. At the last 90 days' pace that is
$20.7M a year. Over the same period the supply of NEAR grew at 32.3M NEAR a
year net of burned fees (2.48% over the last 365 days), worth $115M a year at the
period's mean price of $3.58. **The buybacks equal 18% of the net new supply.** That figure is a ratio of USD,
17.9%: buybacks in USD over the new NEAR valued at the period's mean price. Counted in NEAR, each day's buyback at
that day's price over the new NEAR, it is 18.7%, and the balances of the wallets the revenue arrives at grew by 18.3%
of the new NEAR (below). They are three measurements, not one: they part whenever the price moves inside the window
and the NEAR does not arrive evenly, so prediction A4 is scored on the first two and holds only if both do. Each is
a ratio of two flows, not a measured offset of anyone's dilution: "buybacks" is DefiLlama's name for the series, and its adapter
counts the NEAR and wNEAR arriving at the revenue wallets and files all of it as bought for holders since that date.
The purchases on the market are not in the data, nor is it known that the NEAR stays out of circulation for good;
what the chain shows is that the NEAR arrives and, so far, stays. If all of it was bought and is held, it offsets at
most 18% of the dilution (below). Covering all of the dilution needs
5.6 times the captured revenue at this price, and the market capitalisation is 227 times the
annual buyback. The bought NEAR is not burned, so supply itself does not shrink.

The 18% is close to the best window there has been: the median 90-day window since the buybacks began covers 12.7%,
and windows of other lengths that end on the same day give 15% to 17% (each window in the appendix).
And the step in buybacks is mostly the price. In USD they went from $17,025 a day before 19 August to $59,297 a day
since (3.5 times); in NEAR, from 10,456 to 17,016 NEAR a day (1.6 times). Whether the buybacks in NEAR have held
since depends on the statistic: by the mean of the last two half-months they have not, by the median day they have.

**Where the step in revenue came from.** Revenue is volume times what is kept from each dollar of it, and the two did
not step together. Volume stepped on 19 August. The take stayed near its earlier level for four more weeks, 2.96 basis
points from the step to 15 September against 2.62 in the 90 days before, and rose in the second half of September: 4.85
from 16 September to 2026-11-11, with 3.78 in the first 11 days of November. Over the whole period since the step that
is 1.9 times the volume and 1.6 times the take. An earlier version of this paragraph dated both to 19 August; the take
by half-month, now computed by the build, shows that only the volume moved that day. Our data does not say
what raised the take. Two other entries in this hackathon traced the NEAR arriving at the revenue wallets on the chain,
and both name one cause: a confidential pool inside NEAR Intents, opened in these months
([Wilivms/near-revenue-audit](https://github.com/Wilivms/near-revenue-audit/blob/288ae4a94588d49c36ccdd3e4828b5021971c153/README.md#L121),
[abhirgfu/dark-matter](https://github.com/abhirgfu/dark-matter/blob/984e491f5ff17484926030458ad8296654ec64ec/README.md#L31); both linked at the commit we read). We did not reproduce their traces. If they are
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
NEAR of net new supply: a third measurement of the same flow, with no price in it, close to the other two but not
the same as either. Over the last 30 days it is 15.4%. The balances confirm that NEAR accumulates in these wallets.
They do not say where each inflow came from, whether the NEAR was bought on the market or arrived as NEAR, or
whether it is profit after the incentives paid to bring the volume and the costs of the service.
*(chart: value_capture)*

## An independent check: a keyless sample of the chain

Every account and transaction count above comes from one source, BigQuery. As a check we measured the chain a second way, with no key and no
Google account (`python -m thesis census`): 449 random blocks from the FastNEAR block archive, 2,400 of their
transactions, and archival `view_account` calls for each of the 1,553 accounts behind them. The saved run checked existence
30 days before the window and checked 365 days only when the nearer check found the account.

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
The age shares retain that original classification. Absence at 30 days does not establish absence at 365 days: an
account may be deleted and recreated. The older check was inferred for 250 accounts / 252 transactions in the prior
window and 109 accounts / 206 transactions in the recent window; these are unchecked observations, not measured
errors, and the intervals do not cover that uncertainty. The parser also lacked historical `DelegateV2` support.
Both code paths were corrected on 2026-11-14, but the saved sample has not been refreshed or revalidated.
*(chart: signer_census)*

## Evidence for

* **The headline numbers measured an app, not a network.** KaiChing peaked at 48.9 million accounts a month (August
  2025) and averaged under 2 transactions per account a month; it was 93% of all active accounts in October 2025 and
  stopped between March and April 2026. Its relayer's monthly totals came to 2,000,000 transactions a day, to within a
  thousandth, in 8 of its 17 months in the census: a total that round, month after month, points to a job with a
  daily quota, though the census is monthly and does not show the days one by one. The step that analyses of the
  daily aggregates see and cannot name is this app stopping together with something else that ended the same day,
  most likely a burst of sponsored implicit accounts (the census's one candidate, see the appendix): NearBlocks' daily
  transactions went from 3,758,663 on 2026-04-01 to 1,063,375 on 2026-04-02. KaiChing is 90% of the fall in the
  level, from the median day of March to that of May, but at most 51% of that one-day fall (everything it sent in
  April), and at least 38% if its relayer's last day was 1 April, as a column of the daily data suggests; the census
  is monthly, so which it was is not measured. *(chart: population)*
* **Self-paid transactions rose in autumn 2026.** Outside the reward apps, transactions paid by the sender rose from 9.75M
  to 12.49M a month; September and October 2026 are two of the three highest of the 23 months from December 2024 to
  October 2026. The whole fall in core transactions (−23%) is sponsored transactions disappearing. Both Octobers also
  hold transactions that are not independent use (reward-side calls, and one account whose calls fail): without them
  the October change is +26% if every caller of the reward-side contracts is outside the reward namespaces, and between
  +19% and +31% as far as the tables can say (see "Limits"). *(chart: population)*
* **Transactions to the financial contracts are up October to October** while the reward side fell 92% and the rest
  of the chain stayed level (+3%). That is a count of calls to the exchange, Intents, token contracts and bridges; it
  does not show more users, more successful operations or more demand. A side observation, not a second
  confirmation: on the keyless sample, from 14 to 31 August 2026, before the price doubled, the group ran at 207
  thousand transactions a day against 61 thousand on the same days of 2025 (95% intervals 169 to 247 and 12 to 143
  thousand). Last year's figure rests on 4 sampled transactions, and from September to mid-November 2025 the group
  already ran at 177 thousand a day (109 to 283 thousand), so when the rise began the sample does not settle.
  *(chart: clients)*
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
  did not outlast the rally, which fits the reading that the rally's extra transactions were trading (a reading:
  which contracts were called is measured, what the calls were for is not), but would not show what caused the step.
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
  (52% against 56% over three months). That fall is a change of mix, as in [appendix claim 4](APPENDIX.md#claims-and-what-the-data-says-in-full): sponsored transactions shrank from
  50% of the core to 16%, and inside the self-paid transactions old accounts gained (36% → 39%).
* **Fees fell over the year.** Network fees of the last 90 days are down 52% in USD on the same 90 days a year
  earlier ($8,652 → $4,122 a day) and 68% in NEAR; on the 90 days just before them they are up (+138% in USD, +24%
  in NEAR). Most of the fall in NEAR is the step of 2 April: fees in NEAR fell by about two
  thirds between the median days of March and May. The daily data have no fees by app, and KaiChing is at most half
  of that day's fall in transactions, so how much of the fees was KaiChing's is not measured.
* **The revenue step leans on a higher take, and the last month is down.** Since the step in volume NEAR keeps 4.27 basis
  points of Intents volume against 2.62 before, and all of that rise came four weeks after the step (2.96 up to 15
  September, 4.85 from 16 September); two other entries trace most of that revenue to one new,
  incentivised channel (see "Does it reach the token?"). Over the last 30 days volume, gross fees and captured revenue
  are all a fifth to a quarter below the 30 days before.
* **No usage metric leads price in our tests.** On weekly log-changes over ~6 years (complete weeks only), 5 of 85
  lag tests fall outside the noise band where about 4 are expected by chance, and none of the 85 stands after Holm's
  correction for testing them together (the smallest p-value is 0.006; the first step of the correction asks for
  0.0006). Allowing for the dependence between weeks does not change that (see "Limits"). Fees in USD do
  correlate with price in the same week (r = 0.38), mostly because USD fees are NEAR fees multiplied by the price:
  in NEAR, fees show nothing outside the band.
  What was tested is a linear correlation of weekly changes at fixed lags of up to eight weeks. The result is that
  this test found no convincing lead; it does not rule out one that is non-linear or holds only in some periods.
  *(chart: lead_lag)*

## What would change our mind

These are written down as nine dated predictions in [`PREDICTIONS.md`](PREDICTIONS.md). Their thresholds are either
reference levels taken from the data (the top of a metric's range before the September 2026 step, or its low before
the rebound) or natural lines (parity, half of break-even, dozens rather than hundreds), not numbers tuned to the
outcome. The build scores all nine: five from the daily data as their dates
pass, four once the account queries have been run again for the month they name. "The September step" is the
predictions' name for the month after their reference range; read by half-months it is two events (see "Evidence
against"), and the reference range of Intents volume and buybacks already holds the first of them: the last 13 days
of August, after 19 August, which makes their thresholds harder to stay above, not easier.

A prediction that holds checks the condition it states and nothing wider. Several are control lines rather than
tests of the economic case: B1 holds if the August low is not broken, even after a fall of more than half from
October; A3's line is in USD and can be met by the price alone; A5 is a screen re-run on the whole history, not a
test of timing on new data. So the number of predictions that hold is not a count of confirmations of this thesis;
PREDICTIONS.md says, prediction by prediction, what a hold shows and what it does not.

* **Regular self-paying accounts fall back to their low.** They bottomed at 7,201 in August 2026 and rebounded in
  September. A month at or below that low means the rebound was a spike and the base has not found a floor (B1
  checks January 2027). A hold means only that the low was not broken: a January far below October, just above
  7,201, holds too and would not show that the rebound held.
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
* **A re-run shows a lead** (A5): for any one metric, two neighbouring positive lags outside the noise band with
  correlations of one sign, with or against the price. A5 is a screen, not the test above: it has no correction for
  testing many lags, and with no lead at all it would fail in 3.5% of runs if the lags were independent. Dependence can raise or lower that rate; 3.5% is an independent-null
  illustration, not a lower bound. A failure would call for the Holm-corrected test and a test on weeks after the snapshot; it would
  not by itself make usage a timing signal for the price.

## Limits

Each limit is named here in a line or two. The full text of every one, with its numbers, is in the
[appendix](APPENDIX.md#limits-as-thesismd-states-them-in-full); the relay correction is given in full because the
account tables depend on it.

* **Relay classification was corrected on 2026-11-14.** The saved BigQuery tables recognised a meta transaction
  only when Delegate was its first action. The queries now recognise Delegate in any position, as the block parser
  already did. The saved data have not been refreshed, so the effect on this snapshot is unmeasured; matching total
  transaction counts cannot detect misclassified actors or fee payers.
* **"Outside the reward namespaces" is not "NEAR's own users".** A year ago 93% of the accounts outside `.kaiching`,
  `.tg` and `.sweat` were sponsored users of other apps; the payer and frequency split is the cleaner count.
* **Self-paying means the account paid for at least one transaction in the month.** It is a technical category: who
  funded the account and whether rewards repaid the fees is not checked.
* **An account an app acts for is not shown to be a person.** "Sponsored accounts" counts accounts that apps act for;
  how many people are behind them the chain does not say.
* **"Independent" is defined by exclusion, and it let another app's users in.** Read the regular class as an upper
  bound on the independent accounts that act regularly, not as a count of users; with the calls to reward-side
  contracts out, the October change in self-paid transactions lies between +24% and +37%.
* **A transaction is counted whether it succeeded or not.** How transactions ended was checked on a sample for one
  contract only, NEAR Intents.
* **The pace of November is eleven days.** The unfinished month is used only as rates per day of transactions.
* **Frequency classes are powers of ten of a monthly count.** "Heavy" (1,000 or more) read as automation is our
  reading; the accounts were not inspected one by one beyond the forty largest.
* **Account age is first appearance in a transaction.** An account created by a contract call and first used later
  looks younger than it is.
* **"Active two months running" is a calendar-month measure.** It says nothing about retention within a month.
* **One-off bursts.** February, March and April 2026 each contain a one-off burst of existing implicit accounts
  sending one transaction each. February's sits in the self-paid series (3.37M of that month's 10.38M); without it
  the nine-month change is +2% instead of +6%.
* **The census's series start in December 2024.** Transaction counts differ from NearBlocks' by at most 0.002% in 22
  of the 25 months; BigQuery is lower in three early months, which no October or three-month comparison touches.
* **Intents volume, prices and gross fees are aggregator data**, not checked against a second source; captured
  revenue was, against the balances of the wallets it arrives at. The steadier yardstick for volume is its level
  between the two autumns, $74.5M a day.
* **Net new supply is not dilution for every holder.** The 18% is a ratio of flows: what it does for holders depends
  on the NEAR being bought on the market and kept out of circulation, which the data do not show.
* **Lead-lag scans 17 lags × 5 metrics = 85 tests**, and its band treats the weeks as independent, which they are
  not. Allowing for that, 7 of 85 tests fall outside the band and still none stands after Holm's correction.
* **The app table is a manual grouping** of the 40 largest contracts and relayers. Allowing for the group's contracts
  outside a month's 40 largest, the +37% lies between +30% and +39%.
* **The step date is found after the fact.** A rule dates the step to 19 August. The date marks a change in level; it
  is not a test of a structural break and does not name its cause.
* **This is not a valuation.** The thesis measures usage and how much of its revenue reaches the token. It does not
  estimate what NEAR is worth or what holding it would return.
* **The daily source changes on 2026-11-22.** NearBlocks switches off the API this text was built from. The committed
  copy keeps every number here reproducible; counts of signers, of new and of deleted accounts end with the old API.
* **The traces of where the revenue comes from are not ours.** The confidential-pool share quoted in "Does it reach
  the token?" is the work of two other entries.
* **The issuance scenario is one parameter.** The cut is approved by governance and not yet adopted by validators.
* **The account census ends on 2026-11-11** and costs 482.64 GB of BigQuery scanning to re-run.
