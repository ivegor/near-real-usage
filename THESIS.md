# Thesis: NEAR's collapse was accounts that apps were paying for. What pays its own way ran below the year before until autumn 2026, then jumped, and a few hundred heavy accounts carry it

*Snapshot as of 2026-11-11. The numbers below are those of the committed `docs/summary.json` (a test checks the key
ones; a few supporting details, such as which accounts are an app's service accounts, are read from the committed
data files); the live dashboard is rebuilt daily, so its NearBlocks and DefiLlama figures will move away from this text.
Account counts come from full scans of the NEAR BigQuery public dataset (`sql/account_age.sql`,
`sql/payer_frequency.sql`, `sql/payers.sql`, `sql/top_accounts.sql`: every transaction, not a sample); prices, fees
and Intents volume from NearBlocks and DefiLlama. For accounts,
"YoY" = October 2026 vs October 2025, the last complete month, with the mean of August–October against the same three
months a year earlier in brackets, because single months are noisy.*

## One-paragraph summary

In October 2025, 43.6 million accounts acted on NEAR. In October 2026, 1.38 million did (−97%), and 560 thousand of
those are old accounts of one reward app being deleted, one transaction each. Counted account by
account, **the whole fall is accounts whose fees an app was paying**: 43.05 million of them a year ago, 0.55
million now. KaiChing alone was 40.4 million.
That part of the collapse says nothing about demand for NEAR. Outside the namespaces of the reward apps (KaiChing,
the HOT wallet, Sweat's service accounts) the account count also fell by two thirds, but **93% of those accounts
belonged to other apps, which paid their fees through a relayer**, and they are what fell. The accounts that say something about
demand pay their own fees and sit outside those namespaces. Among them **475 heavy accounts (1,000 or more
transactions a month) send 91% of the self-paid transactions**. The regular ones (10 to 999 a month) number 17,105
against 27,078 a year earlier (−37%; −50% on three-month means), but that fall is not a clean count of users
leaving: up to 15,162 of last year's accounts were players of one wallet's reward game, who paid their own fees then;
the game's calls go through a relayer now (see "Who pays, and how often"). What did grow is
narrower than "users": **transactions that senders pay for themselves, outside the reward apps, are up 28%**
October to October. That figure depends on the window: +35% on three-month means, +24% on six, +6% on nine and −5% on
eleven (+2% and −8% without a one-off burst in February 2026, see "Limits"). Read plainly, self-paid activity ran
below the year before for nine months (−17% from December to August) and jumped in September and October 2026, the months of a price rally (NEAR went from
$1.92 to $4.89 during September), while transactions sponsored through relayers fell 75%.
Transactions to the exchange, NEAR Intents, token contracts and bridges are up 37% October to October, a comparison
with no month before the rally in it. Intents volume in October was $129M a day against $56M a year earlier, but
that base was the middle of a ramp-up: against November 2025 ($122M) October is +5%, and against the nine months
in between ($74.5M a day) it is +73%. Most of it is submitted by very few accounts: **thirty accounts send half of
all transactions**, and reward apps still send 43% (45% counting the one-off deletion of old KaiChing accounts). Value
reaches the token only in part: buybacks funded by Intents revenue cover 18% of the new NEAR issued, by the
aggregator's series and by the balances of the revenue wallets read from the chain. The long-term
case is therefore a narrow one: a small amount of self-paid, financial activity submitted by a few dozen accounts.
On the chain itself we cannot show a growing base of users who pay their own way; how many people stand behind the
relays of Intents and the bridges cannot be read from it. Usage does not lead price.

## Three corrections to our own drafts

**First draft: "returning accounts grew 37%".** It used the only proxy the daily aggregates allow,
`active accounts − new accounts`. The full-chain count says the opposite: core accounts active two months running fell
73%. One day shows why the proxy fails (2025-10-01, 4,632,736 transactions, the same number in BigQuery and NearBlocks):

* **"Active accounts" are transaction signers.** 74% of that day's transactions (3,448,826) were relayed: 17 relayer
  accounts signed them on behalf of 2,694,016 users. NearBlocks reported 288,151 active accounts. The users behind
  relayers are not in that number.
* **"New accounts" are not a subset of them.** 238,399 accounts were created that day by 238,403 transactions whose first
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
pay for themselves are a different and much smaller population (see "Who pays, and how often"). Even there one
class, the regular accounts, turned out to hold the players of a reward game: a group defined by what it is not
keeps letting other apps' users in.

We kept the proxy on the dashboard, labelled as misleading, because every aggregate-based analysis of NEAR inherits it.

## Claims and what the data says

| # | Claim | Result | Evidence (October 2025 → October 2026; three-month means in brackets) |
|---|---|---|---|
| 1 | The collapse in activity is the exit of reward apps, not of NEAR's own users | **Supported** | Accounts whose fees an app paid: 43,049,960 → 552,826. That is more than the whole net loss of accounts (43,642,992 → 1,379,518), because self-paying accounts rose, 593,032 → 826,692, and the rise is itself a one-off: 560,092 old KaiChing accounts paid for one transaction each in October. Without them self-paying accounts fell: HOT users who pay their own fees 458,286 → 129,677, independent ones flat in October (134,743 → 136,920; −39% on three-month means). Counted by namespace alone, reward and wallet apps are 97.2% of the accounts lost and 96.2% of the transactions lost. KaiChing: 40.39M accounts a year ago, gone since spring except for the deletion of its old accounts in October |
| 2 | A stable core of returning users remains (first draft) | **Refuted** | Accounts outside the reward namespaces 1,814,743 → 621,166 (−66%; −57%); of them active the month before 924,642 → 248,954 (−73%; −69%); still falling: 959,812 (Jul) → 621,166 (Oct). That group is mostly other apps' sponsored accounts (96% of the returning ones a year ago), and its fall since July is Sweat's (808,128 → 410,890 sponsored accounts). The independent accounts that returned are 31,452 against 40,759 (−23%; −52%) |
| 3 | The number of accounts that pay for themselves holds up | **Not established** | Outside the reward namespaces, regular self-paying accounts 27,078 → 17,105 (−37%; −50%), low of 7,201 in August 2026. But a year ago up to 15,162 of them were players of Meteor's reward game paying their own fees; its relayer submits the game's calls now, and it fully sponsors 12,499 accounts outside the app namespaces against 7,589 a year ago. Up to 12,499 of the players can therefore have moved to the relayer rather than left, more than the whole fall of 9,973, so how many regular accounts really left is not known: the change lies between the counted −37% and +44% with all of the players taken out. Heavy accounts 370 → 475 (+28%; +0%), and they send 91% of self-paid transactions. Inside HOT's namespace the regular self-paying accounts are more numerous and fell faster: 333,728 → 60,879 (−82%; −77%) |
| 4 | The remaining accounts are used more intensively (second draft) | **Refuted** | 10.7 → 23.9 transactions per core account is a change of mix: 11.7 at last year's mix of account types |
| 5 | Named `.near` accounts are a growing core (second draft) | **Not supported** | Accounts +13% (+2%); with more than one transaction −28% (−15%). Their transactions did grow: 8.96M → 10.77M (+20%; +42%) |
| 6 | Self-paid activity outside reward apps is growing | **Below the year before for nine months, up in autumn 2026** | Core transactions paid by the sender 9.75M → 12.49M (+28%; +35%); on longer windows +24% (six months), +6% (nine) and −5% (eleven). In the nine months before the step (December to August) they averaged 7.61M against 9.16M a year earlier (−17%; −21% without the February burst), below the year before in 7 of the 9 months; sponsored through relayers 9.61M → 2.39M (−75%; −66%). The jump came in the months of a price rally and the series is volatile: see "Evidence against". Last year's figure also holds the reward game of claim 3, whose 532,727 direct calls were self-paid: without them the October change is at most +35% |
| 7 | Financial use of the chain is growing | **Up in October 2026; not measured before the rally** | Transactions to the exchange, Intents, token contracts and bridges 6.72M → 9.18M a month (+37%); Ref/Rhea exchange +96%, token contracts +47%, bridges and chain signatures +43%. On the keyless sample, which compares two 90-day windows and not two months, the same group is +108% (95% interval +36% to +229%). Both comparisons sit inside the autumn rally, and the committed tables hold no month before it for these contracts. The figure also depends on the grouping and on what a month's 40 largest contracts show (see "Limits") |
| 8 | Cross-chain demand through NEAR is growing | **Up since September 2026; level with November 2025** | NEAR Intents volume $55.6M → $128.6M a day (+131%, October to October, DefiLlama); +84% on the previous 90 days. But October 2025 was the middle of a ramp-up: November 2025 already averaged $122.0M (October 2026 is +5% on it), and the first 11 days of November 2026 average $129.7M against $125.4M a year earlier (+3%). In the nine months in between volume averaged $74.5M; against that level October 2026 is +73% |
| 9 | NEAR's transactions come from many independent accounts | **Refuted** | 30 accounts send 50% of transactions; the top 10 send 37% (17% a year earlier); 486 accounts with 1,000+ transactions send 70%. A relayed transaction is counted for the account the relayer acted for, not for the relayer. Counted by signer the year looks different: one relayer, KaiChing's, signed 44% of all transactions in October 2025, and the largest one now, Sweat's, signs 25%. Both counts describe the same event, an app with tens of millions of accounts leaving. Seven of the ten largest are relays or service accounts (Intents, Sweat, the bridges), so this counts who submits transactions; the people behind a relay are not visible on the chain |
| 10 | Intents revenue offsets the dilution of NEAR holders | **Not yet** | Buybacks at $20.7M a year against $115M a year of net new NEAR: 18% of dilution covered; 5.6 times the captured revenue needed. Read from the chain, the three revenue wallets grew by 18.3% of the new supply of the same 90 days, and by 15.4% over the last 30 |
| 11 | Usage changes lead price changes | **Not supported** | 6 of 85 lag tests outside the noise band, about 4 expected by chance; none stands after Holm's correction for testing 85 lags together |

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
| Sponsored accounts, all apps | 43,049,960 | 552,826 | −99%; −99% |
| Sponsored accounts outside the two reward namespaces (Sweat, Meteor and other apps) | 1,680,016 | 484,257 | −71%; −59% |
| HOT users who pay their own fees | 458,286 | 129,677 | −72%; −68% |
| of them regular (10 to 999 transactions a month) | 333,728 | 60,879 | −82%; −77% |
| Independent self-paying, occasional | 107,295 | 119,340 | +11%; −37% |
| Independent self-paying, **regular** | 27,078 | 17,105 | −37%; −50% |
| Independent self-paying, **heavy** | 370 | 475 | +28%; +0% |

Three things follow. A year ago 93% of the accounts outside the two reward namespaces were still someone's
sponsored accounts; what looked like the chain's own base falling by two thirds was mostly other apps' accounts going.
Named by the relayer that paid for them (`sql/payers.sql`), they were the accounts of two apps: Sweat's sponsored
accounts went 1,246,366 → 410,890 and those of the game Ember 387,762 → 0. Together that is
the whole fall (70% and 32% of it; the other groups, taken together, grew slightly).
The regular self-paying accounts outside the reward namespaces are the closest thing the chain has to a count of its
own users. Their number went from 27,078 to 17,105, after a year-long slide to 7,201 in August 2026 and a rebound in
September. Almost half of that slide came in one month, from 22,367 in January 2026 to 13,041 in February, and the
committed tables do not say why. That cannot be read as 9,973 users leaving, for the same reason as before: the group is defined by what it
is not, and it held another app's users. In October 2025, 15,162 accounts called the reward game of the Meteor
wallet (`aa-harvest-moon.near`) themselves, 35 times each on average, and paid the fees, so they counted as
self-paying. By October 2026 Meteor's relayer submits those calls. The contract is no longer among the 40
most-called (fewer than 26,690 direct transactions against 532,727), all 41 calls to it in the keyless sample of
autumn 2026 came through the relayer where 3 of 4 were direct a year earlier, and the accounts Meteor fully sponsors
went 8,677 → 15,409 (7,589 → 12,499 outside the app namespaces). Who pays for the game's calls changed. Whether the players stayed the tables do not say:
Meteor's transactions as a whole are down 29% (984,323 → 698,531), and 19,722 accounts act through its relayer
against 17,787 a year earlier. Nor do they say how many
of the 15,162 were in the regular class, only that it is at most all of them (56% of last year's 27,078). So the
change in regular accounts lies between the counted −37% and +44% with every player taken out, and its direction is
not established without another query. HOT's own regular self-paying users were twelve times as many a year ago and
fell faster; they are counted with their app because it creates their accounts for them. And
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
| NEAR Intents | 8.9% | 1.6% | −13% | 2.01M transactions, up to 97% of them signed by two accounts (`intents.near`, `escrow.ai.near`). The second one's calls do not go through (all 26 in the keyless sample failed) |
| Meteor wallet | 3.1% | 0.7% | −29% | Wallet with a reward game |
| KaiChing | 0.4% (2.8% by namespace) | 49.6% | −100% | Reward app, gone since spring. In October its old accounts were deleted: 560,106 transactions that are not calls to any of the 40 largest contracts, and 560,092 accounts sent exactly one. All 13 of them that fall in the keyless sample are `DeleteAccount` on the account itself, between 2 and 7 October |
| Other contracts in the top 40 | 7.1% | 3.0% | −62% | The fall is the game Ember (2.80M → 0.16M transactions); the other contracts are 1.42M → 1.44M (+2%) |
| Everything else | 9.8% | 5.9% | −73% | Transactions to contracts outside the 40 largest. A year ago 6.74M of them were sent by KaiChing's own accounts and 0.56M now are the one-off above; the rest is 1.58M → 1.65M (+4%) |

Three readings follow. First, the "infrastructure" picture is only half true: reward and wallet apps still send 43% of
transactions through their own contracts and relayers (86% a year ago), or 45% counting the KaiChing one-off (91% a
year ago counted the same way). Second,
the financial half is real and larger than a year ago, but it is operated by very few accounts. NEAR Intents is
the extreme case: its volume more than doubled while the number of transactions it received fell 13% and the accounts
sending them fell from 26,272 to 5,353. Intents users sign off-chain and a relayer submits, so its customers cannot
be counted from the chain at all. Third, the two bottom rows are not the rest of the chain shrinking. With Ember and
the transactions of KaiChing's own accounts put on the reward side, every transaction falls into one of three parts:
the reward side 131.26M → 10.36M (−92%), the financial group 6.72M → 9.18M (+37%), and everything else 3.00M → 3.09M
(+3%). Measured in transactions, what is outside the reward side did not shrink. That last part is defined by
exclusion, and its named part is not the same activity in the two months: of the contracts in it that are among the
40 largest, only `near` is in both. A year ago the largest were `nearprotolcol.near`, `neargives.near` and
`pyth-oracle.near`; now they are `cooldogsclub.near`, with 503,492 transactions from 36 accounts, and
`aggregate-oracle.near`. The total did not shrink; that is all the figure says.

## Does it reach the token?

Partly, and not enough yet. Over the last 90 days NEAR Intents charged $18.9M in fees,
51 times the network's own transaction fees. NEAR captured $5.1M of that
(27%); the rest stays with solvers and the front ends that route the swaps. Since
2026-02-23 the captured revenue is used to buy NEAR on the open market. At the last 90 days' pace that is
$20.7M a year. Over the same period the supply of NEAR grew at 32.3M NEAR a
year net of burned fees (2.48% over the last 365 days), worth $115M a year at the
period's mean price of $3.58. **Buybacks cover 18% of dilution.** Covering all of it needs
5.6 times the captured revenue at this price, and the market capitalisation is 227 times the
annual buyback. The bought NEAR is not burned, so supply itself does not shrink. (Who keeps the rest of the
fees and what happens to the bought NEAR is DefiLlama's description of its own series, saved with the data under
`methodology` in `data/raw/defillama_intents_fees.json`.) *(chart: value_capture)*

**The same money, read from the chain.** DefiLlama's revenue series counts the NEAR arriving at three wallets that
its adapter names: the buyback wallet, the front-end fund and the 1Click fund. We asked an archival RPC node, with no
key, what the three hold at the start and at the end of the same 90 days (`python -m thesis wallets`). Together they
held 1,456,744 NEAR more at the end. That is 0.98 of the revenue DefiLlama reports for those days, so the wallets
are keeping what arrives, and it is 18.3% of the 7.95M NEAR of net new supply: the 18% again, this time in NEAR and
with no price in it. The balances add three things the series does not show. The figure moves with the window: over
the last 30 days it is 15.4%. Of the 4.25M NEAR the three wallets hold, 53% is in the buyback wallet; almost all of
the rest, 2.00M NEAR, sits in the front-end fund. And the wallets cannot be read one by one: the 1Click fund was
emptied during the window (−502,528 NEAR) while the buyback wallet grew by 1,511,073, so the buyback wallet alone
gives 19.0% over the 90 days and 10.9% over the last 30. Whether the NEAR was bought on the market or arrived as
NEAR, the balances do not say.

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
  stopped between March and April 2026. Its relayer worked to a quota: 2,000,000 transactions a day, to within a
  thousandth, in 8 of its 17 months in the census (62,000,031 in October 2025, which has 31 days; 60,000,042 in
  November, which has 30). The step that analyses of the daily aggregates see and cannot name is this app stopping:
  NearBlocks' daily transactions went from 3,758,663 on 2026-04-01 to 1,063,375 on 2026-04-02 (−72%, the largest
  one-day fall in percent in the months of the census) while its active accounts, which count signers, barely moved (139,048 →
  137,183). KaiChing sent 70.55M transactions in March 2026, 2.28M a day, and 1.37M in the whole of April.
  HOT wallet accounts (`.tg`) fell 86% over the year. *(chart: population)*
* **Self-paid transactions rose in autumn 2026.** Outside the reward apps, transactions paid by the sender rose from 9.75M
  to 12.49M a month; September and October 2026 are two of the three highest months in the 23-month series (the
  third, December 2024, is one of the months where BigQuery counts fewer transactions than NearBlocks, see "Limits"). The whole
  fall in core transactions (−23%) is sponsored transactions disappearing. *(chart: population)*
* **Financial use is up October to October** while the reward side fell 92% and the rest of the chain stayed level
  (+3%): +37% in transactions to the exchange, Intents, token contracts and bridges, October to October, and +108%
  between the two 90-day windows of the keyless sample (95% interval +36% to +229%). *(chart: clients)*
* **Intents is a real flow, at a higher level since September.** $55.6M → $128.6M a day October to October, while the
  NEAR price roughly doubled over the same two months ($2.49 → $4.90). Since the step its monthly average has stayed
  above the $63.2M to $89.6M range of the nine months before, also in the first 11 days of November ($129.7M), when
  the price was 39% below its October peak. *(chart: intents)*

## Evidence against

* **No growth in regular self-paying accounts can be shown.** They number 17,105 against 27,078 a year earlier (−50%
  on three-month means), after sliding to 7,201 in August 2026. Part of that fall is one game moving its calls to
  a relayer (see "Who pays, and how often"), so its real size is unknown. The September rebound is two months old
  and came with a price rally. HOT users who pay their own fees fell 72%, the regular ones among them 82%.
* **The self-paid series is volatile.** Monthly values run from 5.8M to 13.1M with no smooth trend; December 2024 was
  12.07M, about where October 2026 is, and a third of February 2026 was a one-off burst (see "Limits"). Two strong
  months are not yet a trend.
* **The autumn step came with a price rally.** NEAR went from $1.92 to $4.89 during September 2026, peaked at $5.89
  on 12 October and was $3.58 on the snapshot date. In that one month Intents volume ($89.6M → $160.1M a day), the
  buybacks it funds ($0.72M → $1.84M a month), self-paid transactions outside the reward apps (7.84M → 13.10M) and
  regular self-paying accounts (7,201 → 18,379) all stepped up. The transactions are carried by heavy accounts, the
  largest of them exchange bots and relays, so one reading is that the step is trading around the rally and will
  leave with it. Predictions A2, A3 and B2 state the opposite, that the new level holds; a miss on them means this
  reading was the right one.
* **Very few accounts carry it.** The largest accounts in October 2026 are `intents.near` (1.44M transactions), three
  Sweat service accounts (1.0M to 1.4M each), two exchange bots (0.77M and 0.46M), a bridge relayer (0.66M) and
  `escrow.ai.near` (0.51M). Seven of the ten largest are relays or service accounts, so the count says who submits
  transactions, not how many people stand behind them; either way the chain depends on a handful of operators.
  And a large count is not always use. We asked a transaction index how the transactions to NEAR Intents in the
  sampled blocks ended (`python -m thesis outcomes`, 149 transactions in 99 blocks): all 26 sent by `escrow.ai.near`
  in the sample of autumn 2026 failed, against 2 failed of the 116 that `intents.near` signed itself and none of the
  7 from other accounts. About a quarter of the transactions NEAR Intents received in October is one account's call
  failing over and over.
* **Reward apps are still 43% to 45% of transactions.** KaiChing left, but Sweat, HOT and Meteor remain. Sweat's 11 service
  accounts in the `.sweat` namespace alone send 17.7% of all transactions while its user count fell 67%. The next exit
  would look the same.
* **Old accounts did not take over the core.** Accounts older than a year send 43% of core transactions, down from 52%
  (52% against 56% over three months).
* **Fees fell over the year.** Network fees of the last 90 days are down 52% in USD on the same 90 days a year
  earlier ($8,652 → $4,122 a day) and 68% in NEAR; on the 90 days just before them they are up (+138% in USD, +24%
  in NEAR). Intents volume is not revenue for the token: NEAR keeps 27% of Intents fees and the buybacks they fund cover
  18% of new supply (see "Does it reach the token?").
* **Usage does not lead price.** On weekly log-changes over ~6 years (n = 284–317 weeks depending on the metric and
  the lag, noise band ≈ ±0.11–0.12):
  Intents volume (n = 92–100 weeks, band ≈ ±0.20–0.21) and fees in NEAR show nothing outside the band at any lag from −8 to +8
  weeks; active accounts r = 0.14 at lag 0; transactions show four isolated bars of mixed sign. In total 6 of 85 lag
  tests fall outside the band where about 4 are expected by chance, and none of the 85 stands after Holm's correction
  for testing them together (the smallest p-value is 0.009; the first step of the correction asks for 0.0006). Fees in USD do correlate with price in the same
  week (r = 0.38), but only because USD fees are NEAR fees multiplied by the price. *(chart: lead_lag)*

## What would change our mind

These are written down as nine dated predictions in [`PREDICTIONS.md`](PREDICTIONS.md). Their thresholds are either
reference levels taken from the data (the top of a metric's range before the September 2026 step, or its low before
the rebound) or natural lines (parity, half of break-even, dozens rather than hundreds), not numbers tuned to the
outcome. The build scores all nine: five from the daily data as their dates
pass, four once the account queries have been run again for the month they name.

* **Regular self-paying accounts fall back to their low.** They bottomed at 7,201 in August 2026 and rebounded in
  September. A month at or below that low means the rebound was a spike and the base has not found a floor (B1
  checks January 2027).
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
  spike, not a new level, and the buybacks it funds fall with it (A1 checks the week to 17 November, A2 December).
* **A re-run shows a lead**: two neighbouring positive lags outside the band for any one metric (A5), and all the
  more so for several.

## Limits

* **"Outside the reward namespaces" is not "NEAR's own users".** The account-age census groups accounts by namespace,
  and a year ago 93% of the accounts outside `.kaiching`, `.tg` and `.sweat` were sponsored users of other apps
  (`.sweat` itself is 11 service accounts; Sweat's users are relayed implicit accounts). Read the age and returning
  figures of that group with this in mind; the payer and frequency split is the cleaner count.
* **Self-paying means the account paid for at least one transaction in the month.** It may also have sponsored ones.
  A sponsored account is not a lesser one; it is one an app is paying for, and it goes when the app does.
* **An account an app acts for is not shown to be a person.** For a relayed transaction we count the account the
  relayer acted for, and three things in the committed data say that such an account can be the app's own. KaiChing's
  relayer worked to a daily quota (see "Evidence for"). The game Ember sponsored the same accounts every month: of its
  387,762 in October 2025 all but 6 had also been active in September, and so had all but 9 of 387,784 the month
  before. And in the keyless sample 19 of the 41 relayed calls to Meteor's game are reward claims, 17 of them in
  batches of up to 4 in one block for accounts whose names start with the same two letters: a job walking a sorted
  list. "Sponsored accounts" therefore counts accounts that apps act for; how many people are behind them the chain
  does not say.
* **"Independent" is defined by exclusion, and it let another app's users in.** It means: pays for at least one of
  its own transactions and is not in the `.kaiching` or `.tg` namespace. A reward game whose players pay their own
  fees from ordinary accounts sits inside it. One did, Meteor's Harvest Moon with 15,162 accounts in October 2025,
  and it has moved to a relayer since (see "Who pays, and how often"). We found it by reading the 40 most-called
  contracts of both months; a smaller game of the same kind would not show there. Read the regular class as an upper
  bound on the independent accounts that act regularly, not as a count of users.
* **Frequency classes are powers of ten of a monthly count.** "Heavy" (1,000 or more) is our reading of that line as
  automation; we did not inspect the accounts one by one beyond the forty largest.
* **Account age is first appearance in a transaction**, as signer or receiver, since genesis. An account created by a
  contract call and first used later looks younger than it is.
* **"Active two months running" is a calendar-month measure.** It says nothing about retention within a month.
* **February, March and April 2026** each contain a one-off burst of existing implicit accounts sending one transaction
  each (about 3.5, 6.0 and 1.1 million accounts against about 0.1 million in an ordinary month; in February most were
  older than two years). They inflate core account counts in those three months; comparisons use October and
  August–October to avoid them. The bursts of March and April were sponsored through
  relayers. February's was paid by the senders, so it also sits in the self-paid series: 3.37M of that month's 10.38M
  self-paid core transactions (32%) came from implicit accounts older than a year that had not been active in January.
  The same group sent 27,664 the month before and never more than 1.4% of a month otherwise. Without that group the
  nine-month change quoted above is +2% instead of +6% and the eleven-month one −8% instead of −5%; the one-, three-
  and six-month figures move by less than a point.
* **The payer and frequency table knows two namespaces**, `.kaiching` and `.tg`; the account census knows three. The
  `.sweat` service accounts that paid for at least one of their own transactions (13 in October 2025, 7 in October
  2026) therefore count among the table's independent accounts, at most 13 of its 370 heavy accounts a year ago and
  7 of the 475 now, and their self-paid transactions are why the table has 9.77M where the census has 9.75M.
* **Intents volume, prices and gross fees are aggregator data** (DefiLlama, NearBlocks) and were not checked against a
  second source; captured revenue was, against the balances of the wallets it arrives at (see "Does it reach the
  token?"). That check reads three balances at three block heights. It does not trace where the NEAR came from, and
  a payment out of the wallets would show only as a smaller growth. The track brief names the NEAR Intents Explorer API for swap volume; it needs a partner key, so the
  volume here is DefiLlama's series for the same protocol, which needs none. Every year-on-year figure for Intents
  volume shrinks as its base moves through the ramp-up of autumn 2025: the 90-day one (+223% on 2026-11-11) every
  day, the calendar-month one at each month's end (+131% for October, about +3% for November so far). The steadier
  yardstick is the level between the two autumns, $74.5M a day from December 2025 to August 2026.
* **Transaction counts were checked against a second source, and three early months do not match.** Month by month,
  BigQuery's count and NearBlocks' differ by at most 484 transactions (0.002%) in 22 of the 25 months of the census,
  and for 2025-10-01 they are equal. In the other three BigQuery is lower: by 0.3% in November 2024, 1.2% in
  December 2024 and 2.5% in March 2025. We do not know which source is right there. Those months enter this text only
  inside the nine- and eleven-month windows and as the December 2024 level of self-paid transactions; no October or
  three-month comparison touches them.
* **Net new supply is not dilution for every holder.** New NEAR is issued mostly as staking rewards, so a holder who
  stakes receives part of it. The 18% compares buybacks with all of the net new supply, which is the most a holder
  could be diluted by.
* **Lead-lag scans 17 lags × 5 metrics = 85 tests**; about 4 bars outside ±2/√n are expected by chance. The p-values
  behind Holm's correction use Fisher's z, a normal approximation, on weekly changes. One of the
  five metrics is the `active − new` proxy shown above to be unreliable; it is reported for completeness.
* **The app table is a manual grouping** of the 40 largest contracts and relayers, which cover 90% of October 2026
  transactions. A relayed transaction is assigned to its relayer, not to the contract it finally calls. A month counts
  only the contracts among its 40 largest, so a group's contract outside them is filed under "Everything else" for
  that month: 7 contracts of the financial group a year ago (no more than 45,655 transactions each) and 6 now
  (no more than 26,690 each). Allowing for them, the +37% lies between +30% and +39%, and the gap between the reward
  apps and the financial group that prediction B4 is scored on, 2.0 points of all transactions in October 2026, lies
  between 1.3 and 2.8. The share of Intents transactions signed by two accounts is an upper bound for a similar
  reason: the query gives each account's total and its most frequent destination, not its count per destination.
  The grouping itself moves the figures too: two contracts in last year's "Other" row were called by the exchange's
  own bots (`pyth-oracle.near` and `acc.toalice.near`, 305,146 transactions); filed with the exchange they make it
  +64% instead of +96%, the financial group +31% instead of +37% and everything else +15% instead of +3%.
  The game Ember
  is not in the reward-app group: it sponsored 387,762 accounts a year ago (2.0% of transactions, 0.7% now) and is filed
  under "Other contracts in the top 40". With it the reward apps' share is 43.3% (88.3% a year ago). The group is left
  as it was when prediction B4 was written, so that the prediction is scored on the definition it was made with.
* **The account census ends on 2026-11-11** and costs 482.64 GB of BigQuery scanning to re-run (the free tier is 1 TB
  a month). The dashboard keeps October 2026 as its last month until the query is run again.
