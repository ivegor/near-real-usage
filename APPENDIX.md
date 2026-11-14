# Appendix: the detail behind THESIS.md

*Same snapshot as [`THESIS.md`](THESIS.md) (2026-11-11), same frozen summary, and the same test checks the numbers
quoted here. THESIS.md is the argument; this file holds what it shortens: every claim with all its qualifications,
the readings behind each section under the same headings, the side analyses (one game's players, the half-months of
the autumn, HOT's change of relayer, the one-off bursts, other groupings of the apps) and the history of our own drafts.*

## The long-term case, in full

*The paragraph THESIS.md opened with before its five lines; the sections it points to ("Limits", "What would change
our mind") are those of THESIS.md.*

After the largest reward app left, NEAR's transactions come from few hands. The reward and wallet apps that stayed
still account for 43% of October's transactions (close to their lowest month), counted by the contract or relayer each
transaction goes through, and the exchange, Intents, token contracts and bridges for 41%. Self-paid transactions
outside the reward namespaces are 55% of all transactions, and most come from a few hundred heavy accounts: 475 of
them send 91% of the self-paid transactions outside `.kaiching` and `.tg`. That activity rose in autumn 2026 in two
steps with different dates: NEAR Intents volume and the revenue it brings in stepped up on 19 August and have stayed
above their earlier range (the date is set by a rule, see "Limits"), while the load on the chain itself (its fees and
gas) ran high for the four weeks of the price rally, from 16 September to 15 October, and has come back down. What
stayed up is the volume and the revenue in USD; in NEAR the revenue has held by the median day and not by the mean
(see "Does it reach the token?"). The NEAR that revenue brings in equals 18% of the new NEAR issued over the last 90
days (17.9% to 18.7% by three measurements that are not the same), close to the best window since the buybacks
began; the median 90-day window gives 13%. That is a narrow case,
and it is not a valuation of NEAR. Nine dated predictions say what would widen it or close it (see "What would change
our mind").

## Our own drafts, and what replaced them

Three readings from our earlier drafts did not survive closer measurement; claims 2, 4 and 5 below are what is left
of them.

**First draft: "returning accounts grew 37%".** It used the only proxy the daily aggregates allow,
`active accounts − new accounts`. The full-chain count says the opposite: core accounts active two months running fell
73%. One day shows why the proxy fails (2025-10-01, 4,632,736 transactions, the same number in BigQuery and NearBlocks):

* **"Active accounts" are transaction signers.** 74% of that day's transactions (3,448,826) were relayed: 17 relayer
  accounts signed them on behalf of 2,694,016 users. NearBlocks reported 288,151 active accounts. The users behind
  relayers are not in that number. The API that replaces the one we read now publishes that other side, and for
  this day it agrees with the BigQuery count almost to the account: 2,694,011 accounts acted for by 17 relayers in
  3,448,822 relayed transactions.
* **"New accounts" are not a subset of them.** 238,399 accounts were created that day by 238,403 transactions whose first
  action is `CREATE_ACCOUNT`, all signed by 12 creator accounts (NearBlocks reported 267,015 new accounts). The proxy
  subtracts them from a count of signers. We did not check how many of those accounts ever transact.

**Second draft: "the remaining accounts are busier" and "named accounts grew on every measure".** A review of that
draft showed both rested on a single month and on a mean:

* Transactions per core account rose from 10.7 to 23.9 a month, but inside each account type the change was much
  smaller: implicit accounts 5.4 → 6.6, named accounts 142.5 → 150.9. With last year's mix of account types the figure
  would be 11.7, +9%. Most of the rise is low-activity accounts leaving. Whether the
  accounts present in both months became busier was not measured: the census counts accounts by month, not one by one.
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

## Claims and what the data says, in full

| # | Claim | Result | Evidence (October 2025 → October 2026; three-month means in brackets) |
|---|---|---|---|
| 1 | The collapse in activity is the exit of reward apps | **Supported for the size of the fall; what NEAR's own users did is open** | Accounts whose fees an app paid: 43,049,960 → 552,826 (100.6% of the net fall as counted, 99.2% with the one-off deletion taken out). That is more than the whole net loss of accounts (43,642,992 → 1,379,518), because self-paying accounts rose, 593,032 → 826,692, and the rise is itself a one-off: 560,092 old KaiChing accounts paid for one transaction each in October. Without them self-paying accounts fell: HOT users who pay their own fees 458,286 → 129,677, independent ones flat in October (134,743 → 136,920; −39% on three-month means). Counted by namespace alone, reward and wallet apps are 97.2% of the accounts lost and 96.2% of the transactions lost. KaiChing: 40.39M accounts a year ago, gone since spring except for the deletion of its old accounts in October. That says where the fall came from, not that NEAR's own users stayed: the independent accounts that returned fell 40,759 → 31,452 (claim 2), and how many regular self-paying accounts really left is not known (claim 3) |
| 2 | A stable core of returning users remains (first draft) | **Refuted** | Accounts outside the reward namespaces 1,814,743 → 621,166 (−66%; −57%); of them active the month before 924,642 → 248,954 (−73%; −69%); still falling: 959,812 (Jul) → 621,166 (Oct). That group is mostly other apps' sponsored accounts (96% of the returning ones a year ago), and its fall since July is Sweat's (808,128 → 410,890 sponsored accounts). The independent accounts that returned are 31,452 against 40,759 (−23%; −52%) |
| 3 | The number of accounts that pay for themselves holds up | **Not established** | Outside the reward namespaces, regular self-paying accounts 27,078 → 17,105 (−37%; −50%), low of 7,201 in August 2026. But a year ago up to 15,162 of them were players of Meteor's reward game paying their own fees; its relayer submits the game's calls now, and it fully sponsors 12,499 accounts outside the app namespaces against 7,589 a year ago. The 4,910 more accounts it fully sponsors are 49% of the fall of 9,973, so how many regular accounts really left is not known. Both years' counts can also hold players who act through that relayer and pay for a transaction of their own, because a relayed call counts towards the frequency class: up to 4,313 accounts now and 9,110 a year ago, when the relayer was already submitting calls to the game. Taking out only those, the players counted in both years, the change lies between −53% and −5% (−29% with the most out of both years). The direct callers are counted a year ago only: with them out of last year as well the high end is +44% or more (+510% if none of those 9,110 also called the game directly, which the tables do not say), and the low end is −53% or lower, because who calls the game directly now the tables do not say. As counted it is −37%. Heavy accounts 370 → 475 (+28%; +0%), and they send 91% of self-paid transactions. Inside HOT's namespace the regular self-paying accounts are more numerous and fell faster: 333,728 → 60,879 (−82%; −77%) |
| 4 | The remaining accounts are used more intensively (second draft) | **Mostly a change of mix** | 10.7 → 23.9 transactions per core account is mostly a change of mix: 11.7 at last year's mix of account types, so +9% is left (implicit accounts 5.4 → 6.6, named 142.5 → 150.9). The same accounts were not followed from one October to the next |
| 5 | Named `.near` accounts are a growing core (second draft) | **Not supported** | Accounts +13% (+2%); with more than one transaction −28% (−15%). Their transactions did grow: 8.96M → 10.77M (+20%; +42%) |
| 6 | Self-paid activity outside reward apps is growing | **On average below the year before for nine months, up in autumn 2026** | Core transactions paid by the sender 9.75M → 12.49M (+28%; +35%); on longer windows +24% (six months), +6% (nine) and −5% (eleven). In the nine months before the step (December to August) they averaged 7.61M against 9.16M a year earlier (−17%; −21% without the February burst), below the year before in 7 of the 9 months and above it in May (+29%) and June (+49%), which are set against the two lowest months of the base (6.36M in May 2025 and 5.81M in June 2025) and came with the price's previous rise, from $1.34 a day on average in April 2026 to $2.13 in June. By account family the whole fall of 14.01M transactions over those nine months is implicit accounts (−11.07M, −49%; −65% without the February burst) and other accounts (−5.03M, −53%); named `.near` accounts sent 2.09M more (+4%). By age, the fall of implicit accounts is accounts under a year old: they sent 17.18M self-paid transactions a year earlier and 3.91M now (−77%), while older implicit accounts that had been active the month before sent 4.69M → 3.75M (−20%) and older ones that had not sent 3.14M more (most of it the February burst). The fall among the young implicit accounts is not made up in the older classes, which fits fewer new implicit accounts paying their own fees rather than the same accounts growing older; the census counts age classes, not accounts, so it cannot follow them. An age class alone can mislead: named `.near` accounts under a year old sent 9.06M fewer and those one to two years old 17.78M more, which fits one cohort moving into the next class rather than new old users, read from the class totals in the same way. Sponsored through relayers 9.61M → 2.39M (−75%; −66%). The jump came in the weeks of a price rally and the series is volatile: see "Evidence against". The base moves from month to month: November 2025 was 11.27M, and October 2026 is +11% on it. The census also holds the first 11 days of November 2026: 356 thousand a day, against 403 thousand in October (−12%) and 376 thousand in November 2025 (−5%); with the dormant accounts of the one-off of 10 November taken out of every month compared, as from February, 347 thousand against 401 thousand (−14%) and 375 thousand in November 2025 (−7%). Both Octobers hold transactions that are not independent use. Last year's figure holds the reward game of claim 3, whose 532,727 direct calls were self-paid: without them the October change is at most +35%. This year's holds 310,912 direct calls to reward-side contracts (Sweat's relayer calling `fast-auth.near`, and Ember's contract) and the 513,339 transactions of `escrow.ai.near`, whose sampled calls all failed. With the reward-side calls out of both years the change is +32% if all their callers are outside the reward namespaces (+32% to +33% allowing for such contracts outside the 40 largest); a call from inside those namespaces is not in the series at all, the keyless sample has one, and how many there are the tables do not say, so the change lies between +24% and +37%. With that account out as well, +26% on the same assumption, and between +19% and +31% without it |
| 7 | Financial use of the chain is growing | **Supported only as more transactions to the group's contracts, October to October; users, successful operations and demand are not measured** | Transactions to the exchange, Intents, token contracts and bridges 6.72M → 9.18M a month (+37%); Ref/Rhea exchange +96%, token contracts +47%, bridges and chain signatures +43%. The count holds the 513,339 transactions of `escrow.ai.near`, whose sampled calls to Intents all failed: without them the group is +29%, and Intents itself −35% instead of −13%. On the keyless sample, which compares two 90-day windows and not two months, the same group is +108% (95% interval +36% to +229%), but the two windows do not stand on the same footing: the recent one runs at about October's level (306 thousand a day against 296 thousand by October's full count), while last year's window sits below October 2025 (147 against 217 thousand) because the group was still rising inside it, from 61 thousand a day in its days of August to 187 thousand in its days of November. The sample covers 14 to 31 August 2026, before the price doubled: 207 thousand a day (95% interval 169 to 247 thousand), above the 61 thousand (12 to 143 thousand) of the same days of 2025, a figure that rests on 4 sampled transactions, and close to October 2025's full count. That comparison is a side observation, not a second confirmation of the October count, and when the rise began it does not settle. From those days to the end of the window the exchange and the token contracts went from 56 to 174 thousand a day (+213%) and Intents and the bridges from 152 to 158 thousand (+4%): the rise inside the rally is in calls to the exchange and the token contracts. Which contracts were called is measured; what each call was for, and whether it succeeded, is not. The figure also depends on the grouping and on what a month's 40 largest contracts show (see "Limits") |
| 8 | Cross-chain demand through NEAR is growing | **Higher since late August 2026; level with November 2025** | NEAR Intents volume $55.6M → $128.6M a day (+131%, October to October, DefiLlama); +84% on the previous 90 days. But October 2025 was the middle of a ramp-up: November 2025 already averaged $122.0M (October 2026 is +5% on it), and the first 11 days of November 2026 average $129.7M against $125.4M a year earlier (+3%). In the nine months in between volume averaged $74.5M; against that level October 2026 is +73%. The step came on 19 August, as the price began to move and a month before it doubled: $81M on 18 August, $134M on the 19th, at a price of $1.59 that rose 27% to $2.01 by 24 August and first stood at twice the step day's price on 19 September; the weekly mean has stayed above the top of the range before ($89.6M) since 21 August, its lowest since being $98.4M |
| 9 | NEAR's transactions come from many independent accounts | **Refuted** | 30 accounts send 50% of transactions; the top 10 send 37% (17% a year earlier); 486 accounts with 1,000+ transactions send 70%. A relayed transaction is counted for the account the relayer acted for, not for the relayer. Counted by signer the year looks different: one relayer, KaiChing's, signed 44% of all transactions in October 2025, and the largest one now, Sweat's, signs 25%. Both counts describe the same event, an app with tens of millions of accounts leaving. Seven of the ten largest are relays or service accounts (Intents, Sweat, the bridges), so this counts who submits transactions; the people behind a relay are not visible on the chain |
| 10 | Intents revenue offsets the dilution of NEAR holders | **No: the revenue equals 18% of the net new supply, and an offset to holders is not measured** | Buybacks (DefiLlama's name for the NEAR arriving at the revenue wallets) at $20.7M a year against $115M a year of net new NEAR: equal to 18% of the net new supply over the last 90 days as a ratio of USD (17.9%), 18.7% counted in NEAR at each day's price, a ratio of flows, not a measured offset; 15% to 17% over other windows ending on the same day, and 13% in the median 90-day window since the buybacks began; 5.6 times the captured revenue needed. Read from the chain, the three revenue wallets grew by 18.3% of the new supply of the same 90 days, and by 15.4% over the last 30. Revenue since 19 August is 1.9 times more volume and a 1.6 times higher take (the volume from that day, the take from the second half of September), and both have been falling for a month (see "Does it reach the token?"). At the issuance the approved HSP-029 ends at, the 18% would be 28% and the 5.6 times 3.6 |
| 11 | Usage changes lead price changes | **This test found no convincing lead** | 5 of 85 lag tests outside the noise band, about 4 expected by chance; none stands after Holm's correction for testing 85 lags together. A linear screen at fixed lags, not proof that no relation exists |

## Who pays, and how often

The segment table and the definitions are in THESIS.md. What the table says, and what it cannot say, in full:

Three things follow. A year ago 93% of the accounts outside the two reward namespaces were still someone's
sponsored accounts; what looked like the chain's own base falling by two thirds was mostly other apps' accounts going.
Named by the relayer that paid for them (`sql/payers.sql`), they were the accounts of two apps: Sweat's sponsored
accounts went 1,246,366 → 410,890 and those of the game Ember 387,762 → 0. Together that is
the whole fall (70% and 32% of it; the other groups, taken together, grew slightly).
The regular self-paying accounts outside the reward namespaces are the closest thing the chain has to a count of its
own users. Their number went from 27,078 to 17,105, after a year-long slide to 7,201 in August 2026 and a rebound in
September. Almost half of that slide came in one month, from 22,367 in January 2026 to 13,041 in February, and the
committed tables do not say why. They do date when the payer changed. The class's self-paid transactions fell from
1.29M in October 2025 to 0.68M in December while its accounts went from 27,078 to 24,553, and the relayed
transactions inside the class doubled, from 215 thousand in November to 439 thousand in December: by January 71% of
the fall in self-paid transactions to the August low had happened, and 24% of the fall in accounts. February's fall
was not the class's own: in the same month self-paying accounts with 2 to 9 transactions fell 23% and sponsored
accounts with 10 to 99 transactions 27%. The year's fall of 9,973 cannot be read as 9,973 users leaving either, for the same reason as before: the group is defined by what it
is not, and it held another app's users. In October 2025, 15,162 accounts called the reward game of the Meteor
wallet (`aa-harvest-moon.near`) themselves, 35 times each on average, and paid the fees, so they counted as
self-paying. By October 2026 Meteor's relayer submits those calls. The contract is no longer among the 40
most-called (at most 26,690 direct transactions against 532,727), all 41 calls to it in the keyless sample of
autumn 2026 came through the relayer where 3 of 4 were direct a year earlier, and the accounts Meteor fully sponsors
went 8,677 → 15,409 (7,589 → 12,499 outside the app namespaces). Who pays for the game's calls changed. Whether the players stayed the tables do not say:
Meteor's transactions as a whole are down 29% (984,323 → 698,531), and 19,722 accounts act through its relayer
against 17,787 a year earlier. That compares the relayer's accounts only. A year ago the game also had players who
only called it directly: a direct caller paid for something itself, so at most 9,110 of the 15,162 can be among the
relayer's accounts, which leaves at least 6,052 and puts the game at 23,839 to 32,949 accounts in all. If nobody calls
it directly now, that is a fall of 17% to 40%. The accounts Meteor fully sponsors made 23 transactions each a year ago
and 35 now, about as many as the direct players made then (35.1). Nor do the tables say how many
of the 15,162 were in the regular class, only that it is at most all of them (56% of last year's 27,078). And the
direct callers are not the only players a count of self-paying accounts can hold. A frequency class counts every
transaction of an account, the relayed ones too, and one self-paid transaction makes an account self-paying. Of the
19,722 accounts that act through Meteor's relayer now, it pays everything for 15,409, so up to 4,313 still pay for
something themselves and can be inside this year's 17,105. The same rule applies to last year: the relayer was
already submitting calls to the game then (1 of the 4 calls to it in last year's keyless sample, a reward claim),
and of its 17,787 accounts it paid everything for 8,677, so up to 9,110 such accounts can be inside last year's
27,078 as well. How many of them also called the game directly the tables do not say, so last year's class can hold
up to 15,162 players if all of them did and up to 24,272 (90% of it) if none did. One rule for both years
applies only to the players counted in both, those who act through the relayer: without them the change in regular
accounts lies between −53% (none of last year's accounts were such players, all 4,313 are in this year's class) and
−5% (all 9,110 were in last year's class, none are in this year's), and is −29% with both taken out. The direct
callers are counted a year ago only, and they make the high end: +44% with 15,162 players taken out of last year,
+510% with 24,272, and between +7% and +356% with this year's 4,313 taken out as well. The low end is open below for
the same reason: who still calls the game directly the tables do not say (at most 26,690 transactions, too few for the
40 largest), so this year's class can hold more players than 4,313, although none of the 41 calls to the game in the
sample of autumn 2026 was direct. As counted the change is −37%. The direction is not established without another
query. HOT's own regular self-paying users were twelve times as many a year ago and
fell faster; they are counted with their app because it creates their accounts for them. And
the growth in self-paid transactions (9.77M → 12.49M, +28%; +35%; 9.75M in the census, see "Limits") belongs to the
heavy accounts: they send 91% of it (85% a year ago). That share is not new with the rally: from March to September
2026 there were 171 to 266 heavy accounts, and they sent 91% to 95% of the self-paid transactions every month; in
August 2026 they sent 7.48M, 10% fewer than in October 2025. Occasional accounts swing with one-off events (the series
runs from 49,954 to 3.5 million independent accounts in fifteen months) and are not read as a trend.
*(chart: segments)*

## Who is left: the customers

The table is in THESIS.md. Its three readings in full:

Three readings follow. First, the "infrastructure" picture is only half true: reward and wallet apps still send 43% of
transactions through their own contracts and relayers (86% a year ago), or 45% counting the KaiChing one-off (91% a
year ago counted the same way). October is near the low of that share, not a typical month: by namespace, the only
grouping the census has for every month, the reward apps sent 34% of October's transactions against 31% in September,
45% to 56% in each month from April to August and 42% in the first 11 days of November (37% over the last three
months, 43% over six). The 43% against the financial group's 41% that prediction B4 starts from is a month of the
rally. Second,
the financial group receives more transactions than a year ago, but very few accounts send them. NEAR Intents is
the extreme case: its volume more than doubled while the number of transactions it received fell 13% and the accounts
sending them fell from 26,272 to 5,353. It is not the only one. Every contract of the group that had more than a
thousand callers a year ago and is in both lists has fewer now, except the exchange's main contract (1,915 → 2,586):
`wrap.near` 39,990 → 31,996 (−20%) while its transactions rose 24%, USDC 15,782 → 7,778 (−51%) while they rose 271%,
USDT 25,468 → 6,743 (−74%) and `token.rhealab.near` 4,675 → 3,319 (−29%). Intents users sign off-chain and a relayer submits, so its customers cannot
be counted from the chain at all. Third, the two bottom rows are not the rest of the chain shrinking. With Ember and
the transactions of KaiChing's own accounts put on the reward side, every transaction falls into one of three parts:
the reward side 131.26M → 10.36M (−92%), the financial group 6.72M → 9.18M (+37%), and everything else 3.00M → 3.09M
(+3%). Measured in transactions, what is outside the reward side did not shrink. That last part is defined by
exclusion, and its named part is not the same activity in the two months: of the contracts in it that are among the
40 largest, only `near` is in both. A year ago the largest were `nearprotolcol.near`, `neargives.near` and
`pyth-oracle.near`; now they are `cooldogsclub.near`, with 503,492 transactions from 36 accounts, and
`aggregate-oracle.near`. The total did not shrink; that is all the figure says.

## Does it reach the token?

The [main thesis](THESIS.md#does-it-reach-the-token) explains the fee split and the comparison with issuance.
Here are the checks across windows, the revenue sources and the wallet balances. Throughout, "buybacks" names
DefiLlama's wallet-inflow series; market purchases and permanent removal from circulation are not measured here.

The 18% is close to the best window there has been. Every window here is measured as a ratio of USD, like the 18%;
counted in NEAR at each day's price the 90 days give 18.7% (see the main text). Of the 173 windows of 90 days since
the buybacks began, it is the 6th highest; the median window covers 12.7%, and the windows that end before the step of 19 August cover 10.7% to
13.8%. Windows of other lengths that end on the same day give 15% to 17% (7 days 16.2%, 30 days 15.2%, 60 days
17.4%, 180 days 15.5%, the whole programme 15.1%), and calendar months 15.3% (August), 21.7% (September), 16.4%
(October) and 14.0% (the first 11 days of November); March was 16.4% as well, April to July 7.4% to 12.8%, and
February holds only the programme's first 6 days. The same holds for the captured share of the
fees, which is a ratio of two flows (the fees accrue swap by swap, the captured revenue arrives at the wallets in
transfers of its own): 27% over these 90 days, 30% over the last 30, 22% over the whole programme and 16% over March to August, the
months before the step. The $20.7M a year is the pace of these 90 days; the pace of the whole programme is $11.2M.
And the step in buybacks is mostly the price. In USD they went from $17,025 a day before 19 August to $59,297 a day
since (3.5 times); in NEAR, from 10,456 to 17,016 NEAR a day (1.6 times), and over the last 30 days they ran at
13,548 NEAR a day, about the level of August (13,296). Whether the buybacks in NEAR have held depends on the statistic.
By the half-months of "Evidence against", their mean from 16 to 31 October (12,708 NEAR a day) and from 1 to 11
November (12,928) is below the top before the step (13,367), while their median day is above the top of the median
days (10,901) by 8% and 16%. That top of the means rests on one day, 5 June 2026, with 64,513 NEAR, 32% of its
half-month; March's mean (14,445 NEAR a day) rests on 27 March in the same way (204,044 NEAR, 46% of the month), and
its median day is 6,714. What those two days were the data do not say, so which statistic is right for the buybacks
is open. In USD the buybacks have held by both. (Who keeps the rest of the
fees and what happens to the bought NEAR is DefiLlama's description of its own series, saved with the data under
`methodology` in `data/raw/defillama_intents_fees.json`.) *(chart: value_capture)*

**Where the step in revenue came from.** Revenue is volume times what is kept from each dollar of it, and the two did
not step together. In the 90 days before 19 August NEAR Intents carried $73.7M a day and NEAR kept 2.62 basis points of it;
from the step to 2026-11-11 it carried $139.0M a day and NEAR kept 4.27. Volume grew 1.9 times and the take 1.6
times, which together is the 3.1 times in revenue. But only the volume stepped on 19 August. By calendar half-month
from the step the take was 2.96 (19 to 31 August), 2.97, 4.48, 5.99, 4.97 and 3.78 (1 to 11 November) basis points.
The first half-month above the highest full month before the step (3.10 in May) is the second half of September:
from the step to 15 September the take was 2.96 on $130.6M a day, and from 16 September 4.85 on $143.1M a day. An
earlier version of this paragraph dated both steps to 19 August. By month the take was 2.3 to 3.1 basis points from May to August,
3.8 in September and 5.5 in October. So the new revenue is not only more swaps, and our data does not say what raised
the take. Two other entries in this hackathon traced the NEAR arriving at the revenue wallets on the chain, and both
name one cause: a confidential pool inside NEAR Intents, opened in these months. One finds none of the wallets'
inflow passing through accounts funded by it in June and 70% in October, and describes the swaps behind it as made
during an airdrop ([Wilivms/near-revenue-audit](https://github.com/Wilivms/near-revenue-audit/blob/288ae4a94588d49c36ccdd3e4828b5021971c153/README.md#L121), README at commit `288ae4a`); the other
finds at least 72% of the last 30 days' revenue leaving that pool's treasury first, against none in June
([abhirgfu/dark-matter](https://github.com/abhirgfu/dark-matter/blob/984e491f5ff17484926030458ad8296654ec64ec/README.md#L31), README at commit `984e491`). We did not reproduce their traces; our monthly
take (2.6 basis points in August, 5.5 in October) is the same rise they report. If they are right, most of the
revenue behind the buybacks now comes through one channel that is three months old and rewarded for being used, which
makes the level since August less tested than its 85 days suggest. That level is not flat either: over the last 30
days volume is 22% below the 30 days before, gross fees 26%, and captured revenue 20% in USD and 25% in NEAR.

**An approved cut in issuance would narrow the gap, slowly.** The other side of the ratio is set to change. House of
Stake proposal [HSP-029](https://gov.near.org/t/hsp-029-establish-a-24-month-issuance-ramp-to-a-1-6-target-rate-of-near-token-emissions/42644)
lowers the maximum issuance from 2.5% to 1.6% a year on a 24-month ramp that starts one quarter after ratification;
its header read "Status: Succeeded" on 2026-11-14. It is not in force: the protocol's own configuration, read from
the chain that day (`python -m thesis protocol`), still gives a maximum of 2.5%. As arithmetic on that one parameter,
with revenue, price and burn held where they are, the 18% becomes 28% at the end of the ramp and the 5.6 times
becomes 3.6. That is still far from break-even, it takes two years to arrive, and it needs validators to adopt the
change. None of the nine predictions depends on it: A4 is checked on 2027-02-11, about when the ramp can first start.

**The same money, read from the chain.** DefiLlama's revenue series counts the NEAR arriving at three wallets that
its adapter names: the buyback wallet, the front-end fund and the 1Click fund. We asked an archival RPC node, with no
key, what the three hold at the start and at the end of the same 90 days (`python -m thesis wallets`). Together they
held 1,456,744 NEAR more at the end. That is 0.98 of the revenue DefiLlama reports for those days, and the 4.25M NEAR
they hold at the end is 0.97 of all the captured revenue the series has counted since 2025-09-22 (4.37M NEAR at each
day's price), so the wallets are keeping what arrives. The growth of the 90 days is 18.3% of the 7.95M NEAR of net
new supply: a third measurement of the same flow, with no price in it, close to the 17.9% in USD and the 18.7% in
NEAR but not the same as either. The balances add three things the series does not show. The figure moves with the window: over
the last 30 days it is 15.4%. Of the 4.25M NEAR the three wallets hold, 53% is in the buyback wallet; almost all of
the rest, 2.00M NEAR, sits in the front-end fund. And the wallets cannot be read one by one: the 1Click fund was
emptied during the window (−502,528 NEAR) while the buyback wallet grew by 1,511,073, so the buyback wallet alone
gives 19.0% over the 90 days and 10.9% over the last 30. The balances confirm that NEAR accumulates in these
wallets. They do not say where each inflow came from, whether the NEAR was bought on the market or arrived as NEAR,
or whether it is profit after the incentives paid to bring the volume and the costs of the service. DefiLlama's
adapter counts every NEAR and wNEAR inflow to these wallets and files it as holders' revenue from 2026-02-23, which is
why "buybacks" is its label and not a measurement here.

## Evidence for

* **The headline numbers measured an app, not a network.** KaiChing peaked at 48.9 million accounts a month (August
  2025) and averaged under 2 transactions per account a month; it was 93% of all active accounts in October 2025 and
  stopped between March and April 2026. Its relayer's monthly totals came to 2,000,000 transactions a day, to within a
  thousandth, in 8 of its 17 months in the census, December 2024 to April 2026 (62,000,031 in October 2025, which
  has 31 days; 60,000,042 in November, which has 30). A total that round, month after month, points to a job with a
  daily quota; the census is monthly and does not show the days one by one. The step that analyses of the daily aggregates see and cannot
  name is this app stopping, with one more thing ending on the same day:
  NearBlocks' daily transactions went from 3,758,663 on 2026-04-01 to 1,063,375 on 2026-04-02 (−72%, the largest
  one-day fall in percent in the months of the census) while its active accounts, which count signers, barely moved (139,048 →
  137,183). NearBlocks' newer series of the accounts relayers acted for shows what the signer count could not: 2,819,581
  on the first day and 331,452 on the second. Its count of new accounts stepped down on the same day, from 99,785 to 20,655 (135,314 a day on average in
  March, 21,990 in April), and in the census the KaiChing accounts seen for the first time went from 3.65M in March
  to 70,024 in April. KaiChing sent 70.55M transactions in March 2026, 2.28M a day, and 1.37M in the whole of April.
  That accounts for the level: the median day of March carried 3.33M transactions and the median day of May 0.78M, a
  fall of 2.54M a day, of which KaiChing's rate is 90%. The one day is larger than KaiChing. It lost 2.70M
  transactions, and KaiChing's accounts can be at most 51% of that (everything they sent in April), so at least
  1.32M was sent by other accounts that stopped on the same day. A column of the daily data narrows it.
  NearBlocks' `active_contracts` is not defined in its reply, but on 2025-10-01 it is 2,689,404 against 2,694,016
  users behind relayers in BigQuery, so it tracks them. It fell by 1,197,273 from 1 to 2 April, against 1,195,765
  transactions that KaiChing's relayer submitted in the whole of April. That match suggests the relayer's last day was
  1 April; the census is monthly and cannot show it. If it was, KaiChing sent at least those 1,195,765 on 1 April and
  at most the other 177,305 of its April transactions on 2 April, so it is at least 38% of the one-day fall, and at
  most 51% in any case. The census has one candidate for the rest, the burst of
  sponsored implicit accounts of March and April (see "Limits"; 1.1 million of them in April, one transaction
  each), and the daily series dates it: transactions ran above the median day of 1 March to 1 April on every day
  from 23 March to 1 April, 5.89M above the median of the days before in March alone, against 6.0 million accounts of the burst in
  March, while `active_contracts` stayed within the range of the days before (2.16M to 2.22M) until 1 April. Who paid
  for them the committed tables do not name.
  HOT wallet accounts (`.tg`) fell 86% over the year. *(chart: population)*
* **Self-paid transactions rose in autumn 2026.** Outside the reward apps, transactions paid by the sender rose from 9.75M
  to 12.49M a month; September and October 2026 are two of the three highest of the 23 months from December 2024 to
  October 2026 (the third, December 2024, is one of the months where BigQuery counts fewer transactions than
  NearBlocks, see "Limits"). The whole
  fall in core transactions (−23%) is sponsored transactions disappearing. *(chart: population)*
* **Transactions to the financial contracts are up October to October** while the reward side fell 92% and the rest
  of the chain stayed level (+3%), a count of calls, not of users, successful operations or demand: +37% in transactions to the exchange, Intents, token contracts and bridges, October to October, and +108%
  between the two 90-day windows of the keyless sample (95% interval +36% to +229%; last year's window was still
  rising inside itself, see claim 7). As a side observation, from 14 to 31 August 2026, before the price doubled, the
  sample puts the group above the same days of 2025, though last year's figure rests on 4 sampled transactions (see
  claim 7). *(chart: clients)*
* **Intents is a real flow, at a higher level since 19 August.** $55.6M → $128.6M a day October to October, while the
  NEAR price roughly doubled over the same two months ($2.49 → $4.90). The step came as the price began to move, on a day it
  was $1.59 (27% higher five days later, at $2.01), a month before it first stood at twice that, and since then every half-month has averaged above the range of the nine months before ($63.2M to
  $89.6M a day), also the first 11 days of November ($129.7M), when the price averaged 35% below its October peak
  (39% on 11 November) but 142% above its price on the day of the step ($3.85 against $1.59). After the step the price
  never fell below $1.73 (20 August), so the new level of volume has not yet been seen at the price of the old one.
  *(chart: intents)*

## Evidence against

* **No growth in regular self-paying accounts can be shown.** They number 17,105 against 27,078 a year earlier (−50%
  on three-month means), after sliding to 7,201 in August 2026. Part of that fall is one game moving its calls to
  a relayer (see "Who pays, and how often"), so its real size is unknown. The September rebound is two months old
  and came with a price rally. HOT users who pay their own fees fell 72%, the regular ones among them 82%.
* **The self-paid series is volatile.** Monthly values run from 5.8M to 13.1M with no smooth trend; December 2024 was
  12.07M, about where October 2026 is, and a third of February 2026 was a one-off burst (see "Limits"). The two strong
  months are four strong weeks: on the keyless sample, self-paid transactions outside the namespaces ran at 320
  thousand a day in the first half of September, 556 thousand in the second, 492 thousand in the first half of
  October and 325 thousand in the second (two halves of a month, weighted by their days, give the census's full count
  of September and October to within 1%). November has started lower: in its first 11 days the series ran at 356
  thousand a day, 12% below October's rate, 18% below September's and 5% below November 2025's. At that rate the month
  would total 10.68M, 3% above the 10.38M that prediction B2 needs on average from November to January. Those days hold
  a one-off: on 10 November NearBlocks counted 177,510 signers against 77,792 on the median day of the others, and the
  census has 104,477 dormant implicit accounts with one transaction in those 11 days against 48,435 in all of October.
  Taken out of every month compared by the filter applied to February, the series runs at 347 thousand a day, 14%
  below October's rate and 7% below November 2025's, and the month would total 10.41M, 0.3% above the threshold. The
  filter has February's shape, not its cause: February was deletions (3.40 million by NearBlocks), and on 10 November
  NearBlocks counted 74. The keyless sample has one block of that day in which eight implicit accounts older than a
  year each sent a plain transfer to the same implicit account (block 223897411, at 09:29 UTC; one of the 6 blocks
  sampled that day, and the only block of that kind in the whole sample). Eleven days are not a month, and the
  census is monthly, so they cannot be set against the same days a year earlier.
* **The autumn step is two events, and the second came and went with a price rally.** NEAR went from $1.92 to $4.89
  during September 2026, peaked at $5.89 on 12 October and was $3.58 on the snapshot date. Month by month, Intents
  volume ($89.6M → $160.1M a day), the buybacks it funds ($0.72M → $1.84M a month), self-paid transactions outside the
  reward apps (7.84M → 13.10M) and regular self-paying accounts (7,201 → 18,379) all stepped up in September. By
  half-months they did not step up together. Set against the half-months from 16 April (after KaiChing stopped) to
  15 August, Intents volume and the buybacks in USD are above the highest of them in every half-month from 16 August
  on: volume stepped up on 19 August, at a price of $1.59, and has held (13 of August's days, 58% of its volume and 65%
  of its buybacks, are after the step). On the day of the step the price fell 3%, to its lowest since 18 May; it rose
  from the next day (27% higher on 24 August than on the 19th) and first stood at twice the step day's level on 19
  September, so the step came with the start of the move and a month before the price doubled. The reference top of
  every series compared here but one is its first half of June 2026, the peak of the price's previous rise ($2.21 a
  day on average in it); the exception is the count of new contracts. The chain's fees in NEAR and the gas it burned
  are above that top in the two half-months from 16 September to 15 October and in no other: 1,268 and 1,750 NEAR of
  fees a day against 1,006. By the median day as well (1,212 and 1,146 NEAR against a top of 949), so the burst is
  not a few days of it. A conditional deletion scenario subtracts one transaction for each deleted account on the
  same day, symmetrically in every half-month. This is not a measured count of transactions without deletions:
  a transaction can produce several deletion receipts, and receipts can execute on another day. Under that assumption,
  the transaction rate is above its reference top only from 16 to 30 September:
  887 thousand a day against a top of 867 thousand, and 834 thousand in the first half of October, when the deletion of
  old KaiChing accounts lifted the count as reported to 872 thousand. In the second half of October the chain was back
  at a scenario rate of 596 thousand transactions and 823 NEAR of fees a day, when the price was still $4.76 on average.
  The saved aggregates do not establish the scenario's error; missing deletion counts leave its result unavailable.
  Native NEAR
  transfers, counted in NEAR, came and went with the load: 17.1M NEAR a day in the first half of August, then 25.4M,
  45.5M, 87.6M and 66.7M to 15 October, and 37.7M and 31.6M since, above their earlier top (53.0M) only from 16
  September to 15 October. On the keyless sample the exchange rose earlier, from 1 September: 50 thousand
  transactions a day (95% interval 22 to 86 thousand) from 14 to 31 August, 131 thousand in the first half of
  September, 193 thousand and 133 thousand in the next two half-months, 26 thousand (95% interval 11 to 42 thousand)
  in the second half of October and 18 thousand in November. One daily series rose in the rally and has not come back
  down: NearBlocks' count of new contracts, 4.5 to 10.9 a day by half-months in July and August 2026, 31 to 36 from 16
  September to 31 October and 48.5 in the first 11 days of November, the highest of the half-months since 16 April 2026. What those
  contracts are the data do not say. So part of one reading is confirmed already:
  the exchange's transactions of the rally, and the extra load on the chain, have left with it, while the flow through
  Intents has held. Self-paid transactions outside the namespaces are in between, below their peak and above August.
  Predictions A2, A3 and B2 state that the new level holds; a miss on them would mean that the new level did not
  outlast the rally, which fits the reading that the rally's extra transactions were trading, but would not show
  what caused the step.
* **Very few accounts carry it.** The ten largest accounts in October 2026 are `intents.near` (1.44M transactions),
  three Sweat service accounts (1.0M to 1.4M each), two exchange bots (0.77M and 0.46M), two bridge relayers
  (`omni-relayer.bridge.near`, 0.66M, and `bridge-mng.near`, 0.44M), `escrow.ai.near` (0.51M) and `wx-cruce.near`
  (0.47M, mostly to `wrap.near`). Seven of them are relays or service accounts (`intents.near`, the three of Sweat,
  the two bridge relayers and `escrow.ai.near`), so the count says who submits transactions, not how many people stand
  behind them; either way the chain depends on a handful of operators.
  And a large count is not always use. We asked a transaction index how the transactions to NEAR Intents in the
  sampled blocks ended (`python -m thesis outcomes`, 149 transactions in 99 blocks): all 26 sent by `escrow.ai.near`
  in the sample of autumn 2026 failed, against 2 failed of the 116 that `intents.near` signed itself and none of the
  7 from other accounts. That account sent 513,339 transactions in October, about a quarter of what NEAR Intents
  received if all of them went there: the query gives an account's most frequent destination, not its count by
  destination, and every transaction of it in the sample went to Intents. The sample spans 90 days, not October, and
  26 transactions show that failing was the rule for this account, not how many of its October transactions failed.
  So taking all of them out is the far end, not a measured count of failed calls: the financial group is then up 29%,
  not 37%, and self-paid transactions outside the reward namespaces 23%, not 28%.
* **Reward apps are still 43% to 45% of transactions,** and October was close to their lowest month (see "Who is left:
  the customers"). KaiChing left, but Sweat, HOT and Meteor remain. Sweat's 11 service
  accounts in the `.sweat` namespace alone send 17.7% of all transactions while its user count fell 67%. The next exit
  would look the same. And November started with more of it, not less. In its first 11 days HOT's namespace (`.tg`)
  sent 196 thousand transactions a day against 100 thousand in October (+96%), most of the rise through its relayer
  (107 thousand a day against 36 thousand). The chain as a whole did not move (723 thousand a day against 730
  thousand), so the namespaces of the reward apps went from 34% of all transactions in October (2.8 points of it
  KaiChing's namespace, mostly the one-off deletion of its accounts) to 42%. These are the same eleven days in which
  self-paid transactions outside the reward apps ran 12% below October's rate. HOT's rise is measured from one month
  after its lowest, though: its namespace sent 194 thousand transactions a day in July, 154 thousand in August, 90
  thousand in September and 100 thousand in October, and through relayers 70, 42, 9 and 36 thousand (107 thousand in
  November); September is the lowest of the 24 months of that series. The accounts HOT paid everything for went
  108,444, 95,299, 27,652 and 70,432 from July to October. Its old relayer, `0-relay.hot.tg`, paid everything for
  94,596 of them in August and is not in the list of the twelve largest relayers after it; the new one, `0here.tg`,
  paid everything for 433 accounts in August, 27,652 in September and 70,432 in October (the payers query's list of
  the largest relayers). So September was the bottom, at a change of relayer, and the return began in October. The
  196 thousand a day of November average two levels. NearBlocks' count of users behind relayers (its newer API, which
  defines it) went from 80,193 on 8 November to 146,991 on the 9th, the largest one-day rise of the month, and the
  chain's transactions averaged 649 thousand a day from 1 to 8 November and 919 thousand from 9 to 11; its older
  `active_contracts` moved the same day, from 78,892 to 145,602. Signers stepped up earlier, from 46,478 and 48,060 on
  1 and 2 November to between 72,343 and 79,184 on the other days but the 10th. The same count of relayed users fell
  from 100,931 on 20 August to 63,143 on the 21st, the largest one-day fall of August, and the old relayer's last
  call in the keyless sample is on 16 August; the new one's first relayed call there is on 30 September. Which app's
  users moved on those days the daily counts do not say, and the sample holds 42 transactions of 9 and 10 November.
* **Old accounts did not take over the core.** Accounts older than a year send 43% of core transactions, down from 52%
  (52% against 56% over three months). That fall is a change of mix, as in claim 4. Old accounts sent 69% of the
  sponsored core transactions a year ago and send 64% now, against 36% and 39% of the self-paid ones, and sponsored
  transactions shrank from 50% of the core to 16%. Inside the self-paid transactions old accounts gained (36% → 39%;
  40% → 50% over three months); at last year's mix of the two, October 2026 would give 51%.
* **Fees fell over the year.** Network fees of the last 90 days are down 52% in USD on the same 90 days a year
  earlier ($8,652 → $4,122 a day) and 68% in NEAR; on the 90 days just before them they are up (+138% in USD, +24%
  in NEAR). Most of the fall in NEAR is the step of 2 April, when KaiChing stopped: 1,967 NEAR of fees on 1 April,
  743 on 2 April, and 2,564 NEAR on the median day of March against 844 on the median day of May, 1,720 of the 2,285
  NEAR a day the 90-day figure lost: fees in NEAR fell by about two thirds in the step in which KaiChing stopped. The daily data have no fees by app, and KaiChing is at most half of that day's fall in transactions, so how much of the fees was KaiChing's is not measured. Intents volume is not revenue for the token: NEAR keeps 27% of Intents fees and the buybacks they fund cover
  18% of new supply (see "Does it reach the token?").
* **The revenue step leans on a higher take, and the last month is down.** Since the step in volume NEAR keeps 4.27 basis
  points of Intents volume against 2.62 before, and all of that rise came four weeks after the step (2.96 up to 15
  September, 4.85 from 16 September); two other entries trace most of that revenue to one new,
  incentivised channel (see "Does it reach the token?"). Over the last 30 days volume, gross fees and captured revenue
  are all a fifth to a quarter below the 30 days before.
* **No usage metric leads price in our tests.** On weekly log-changes over ~6 years, complete weeks only (n = 282–315 weeks depending on the metric and
  the lag, noise band ≈ ±0.11–0.12):
  Intents volume (n = 90–98 weeks, band ≈ ±0.20–0.21) and fees in NEAR show nothing outside the band at any lag from −8 to +8
  weeks; active accounts r = 0.15 at lag 0 and 0.12 at −5 weeks (price first); transactions show three isolated bars
  of mixed sign. In total 5 of 85 lag
  tests fall outside the band where about 4 are expected by chance, and none of the 85 stands after Holm's correction
  for testing them together (the smallest p-value is 0.006; the first step of the correction asks for 0.0006). Fees in USD do correlate with price in the same
  week (r = 0.38), mostly because USD fees are NEAR fees multiplied by the price: in NEAR, fees show nothing outside
  the band. What was tested is a linear
  correlation of weekly changes at fixed lags of up to eight weeks: it finds no lead that stands, and it does not rule
  out one that is non-linear or holds only in some periods. *(chart: lead_lag)*

The weekly price mean requires seven finite, positive daily quotes. Zero placeholders before trading began do not
count towards a complete week; zero activity on a day can still be a valid observation. This correction on
2026-11-14 removes one early price change from the scan, with no change to the 5-of-85 count or the Holm verdict.

## Limits

The relay-position correction described in THESIS.md is in the SQL, but the committed BigQuery tables remain the
original results. Their actor/payer classifications have not been remeasured. The quoted scan costs are those of
the original queries; a fresh dry-run estimate is required before executing the corrected queries.

The keyless sample has a separate historical limitation: the old collector inferred absence at 365 days from
absence at 30 days, although an account can be deleted and recreated. Its unchecked older dates cover 250 accounts /
252 transactions in the prior window and 109 accounts / 206 transactions in the recent window. The saved age shares
are retained, and their bootstrap intervals do not cover this classification uncertainty. The old block parser also
lacked `DelegateV2` support. The collector now checks both dates independently and the parser supports that archival
action; neither correction has been applied to the saved sample by a new download.

The limits that THESIS.md states in a line or two, in full.

* **An account an app acts for is not shown to be a person.** For a relayed transaction we count the account the
  relayer acted for, and three things in the committed data say that such an account can be the app's own. KaiChing's
  relayer's monthly totals point to a daily quota (see "Evidence for"). The game Ember's sponsored accounts look like a
  fixed set: of its 387,762 in October 2025 all but 6 had also been active in September, and of the 387,784 it sponsored in
  September all but 9 had been active in August. The query records only that an account was active the month before, not through
  which app or who paid, so that it was Ember's own set every month is a reading, not a measurement. And in the keyless sample 19 of the 41 relayed calls to Meteor's game are reward claims, 17 of them in
  batches of up to 4 in one block for accounts whose names start with the same two letters: a job walking a sorted
  list. "Sponsored accounts" therefore counts accounts that apps act for; how many people are behind them the chain
  does not say.
* **"Independent" is defined by exclusion, and it let another app's users in.** It means: pays for at least one of
  its own transactions and is not in the `.kaiching` or `.tg` namespace. A reward game whose players pay their own
  fees from ordinary accounts sits inside it. One did, Meteor's Harvest Moon, called directly by 15,162 accounts in
  October 2025, and its calls have moved to a relayer since (see "Who pays, and how often"). We found it by reading
  the 40 most-called contracts of both months; a smaller game of the same kind would not show there. Read the regular class as an upper
  bound on the independent accounts that act regularly, not as a count of users. The same holds for transactions: a
  direct call to a reward-side contract that sits outside the namespaces is paid by its sender, so it is inside
  "self-paid transactions outside the reward apps". As far as each month's 40 largest contracts show, that is 532,727
  calls a year ago (the game) and 310,912 now: 145,956 to `fast-auth.near`, whose main caller is Sweat's relayer, and
  164,956 to Ember's contract from 44 accounts. Each is the most that the 40 largest can put inside the series,
  because the tables do not give the namespace of every caller. A reward-side contract outside a month's 40 largest
  received at most as many calls as the smallest of them: up to 91,310 more a year ago (two such contracts) and 26,690
  now (one), so with the reward-side calls out of both years the change lies between +32% and +33% if every caller is
  outside the reward namespaces. Not every one is: the keyless sample has a `.tg` account calling the game directly a
  year ago, and a call from inside the namespaces is not in the series, so there is nothing to take out for it. How
  many there are the tables do not say. With that left open, the change lies between +24% (none of last year's calls
  in the series, all of this year's) and +37% (the other way round); with `escrow.ai.near` out as well, between +19%
  and +31%. The figure that takes every call out of both years is the one for callers outside the namespaces, not a
  bound.

* **The pace of November is eleven days.** The census scan stopped on 2026-11-11, so the unfinished month is used
  only as rates per day of transactions, set against the rates of whole months: for the self-paid transactions
  outside the reward apps, and for the namespaces of the reward apps, so that the month is not quoted only where it
  slows down. Accounts of a part of a month are not compared with a month at all, except to say that HOT's count
  already exceeds October's. The filter applied to February's burst (implicit accounts older than a year that were not
  active the month before) is applied to these days too, because they hold a one-off of the same shape (not of the same cause, see "Evidence
  against"), and it is
  applied to the months they are set against as well.

* **The census's series start in December 2024.** The table begins with November 2024, which has no month before it,
  so it cannot say which accounts returned; to keep every series of the census on the same months, they all leave it
  out, and the counts of months above (KaiChing's 17, the self-paid series' 23) start in December 2024. The check of
  transaction counts against NearBlocks (below) uses all 25 months. For transactions the first month is only a base:
  twelve months against the twelve before, which need it, give −4.8%, the same as eleven.
* **February, March and April 2026** each contain a one-off burst of existing implicit accounts sending one transaction
  each (about 3.5, 6.0 and 1.1 million accounts against about 0.1 million in an ordinary month; in February most were
  older than two years). The three monthly bursts are two events: February's, and a run of ten days from 23 March to
  1 April (see "Evidence for") that the monthly census splits in two. They inflate core account counts in those
  months; comparisons use October and August–October to avoid them. The run of March and April was sponsored through
  relayers. February's was paid by the senders, so it also sits in the self-paid series: 3.37M of that month's 10.38M
  self-paid core transactions (32%) came from implicit accounts older than a year that had not been active in January.
  The same group sent 27,664 the month before and never more than 1.4% of a month otherwise. Without that group the
  nine-month change quoted above is +2% instead of +6% and the eleven-month one −8% instead of −5%; the one-, three-
  and six-month figures move by less than a point. What that one transaction was, the census does not say. A second
  source agrees with the burst in size and in month: NearBlocks counted 3,401,092 deleted accounts in February,
  3,401,061 of them on the 16 days from 3 to 18 February, against 26 a day in January. Its count is of accounts
  deleted, the census's of accounts that sent one transaction, so the two are not the same measurement. Who deleted
  them neither names, but the daily signers narrow it: on the days of the burst they rose by 0.94 for each deleted
  account (correlation 0.9985 from 3 to 18 February; 0.97 and 0.9998 for the deletions of old KaiChing accounts from 2
  to 8 October), so the accounts signed their own deletions, not a relayer or a few service accounts: whoever held
  their keys. The run of March and April was not deletions: NearBlocks counted 636 and 3,656 deleted accounts in those
  months.
  The filter has the shape of February's burst and does not catch three others. Named accounts: 351,443, 270,590 and
  260,431 existing `.near` accounts not active the month before sent one transaction in March, April and May 2025,
  against 6,881 in the median month, almost all paid by themselves, while NearBlocks counted 391,240, 299,354 and
  359,850 deletions in those months (the hump in the first chart of the dashboard). Taken out as well, above the
  median month, they move the nine-month window from +2% to +3%, the eleven-month one from −8% to −7%, and the nine
  months before the step from −21% to −20%. December 2025: NearBlocks counted 382,253 deletions on five days from 17 to 22
  December, and the census cell that lost the most accounts in the month after is implicit accounts aged one to two
  years that had been active the month before: 397,029 in December, 338,456 of them with one transaction, and 65,418
  in January. In size and profile that matches the accounts the game Ember sponsored (387,762 in October 2025), but
  the tables carry no names; they were active the month before, so the filter does not take them out. They are
  inside the self-paid series: the payer table has 463,515 self-paying accounts outside the app namespaces with one
  transaction in December 2025, 393,404 above its median month (70,111), 5.8% of that month's self-paid transactions.
  Taken out, the nine months before the step are −17.5% instead of −17.0%. But the months they are set against held
  deletions too (NearBlocks counted 195,960 in December 2024 and 159,795 in January 2025, besides those of March to
  May 2025), and the payer table starts in August 2025, so the same rule cannot reach the base: −17.5% is one end, not
  a corrected figure. And in April
  a second group: 236,998 implicit accounts first seen in March sent one transaction, mostly relayed; they were active
  in March, so the burst rule, which counts accounts that were not, misses them.
* **The payer and frequency table knows two namespaces**, `.kaiching` and `.tg`; the account census knows three. The
  `.sweat` service accounts that paid for at least one of their own transactions (13 in October 2025, 7 in October
  2026) therefore count among the table's independent accounts, at most 13 of its 370 heavy accounts a year ago and
  7 of the 475 now, and their self-paid transactions are why the table has 9.77M where the census has 9.75M.
* **Intents volume, prices and gross fees are aggregator data** (DefiLlama, NearBlocks) and were not checked against a
  second source. DefiLlama's fee adapter reads gross fees from Dune tables published under NEAR's own account
  (`dune.near.dataset_near_intents_*`), so that series is the project's own report passed on. Captured revenue was checked, against the balances of the wallets it arrives at (see "Does it reach the
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
  inside the nine-, eleven- and twelve-month windows and as the December 2024 level of self-paid transactions; no October or
  three-month comparison touches them.

* **The app table is a manual grouping** of the 40 largest contracts and relayers, which cover 90% of October 2026
  transactions. A relayed transaction is assigned to its relayer, not to the contract it finally calls. A month counts
  only the contracts among its 40 largest, so a group's contract outside them is filed under "Everything else" for
  that month: 7 contracts of the financial group a year ago (no more than 45,655 transactions each) and 6 now
  (no more than 26,690 each). Allowing for them, the +37% lies between +30% and +39%, and the gap between the reward
  apps and the financial group that prediction B4 is scored on, 2.0 points of all transactions in October 2026, lies
  between 1.3 and 2.8. HOT's two bridge contracts (`v2_1.omni.hot.tg`, `bridge-refuel.hot.tg`, 84,269 transactions
  in October 2026) are filed with HOT, as the group was frozen; filed with the bridges they put that gap between 0.4
  and 1.9 points. On the keyless sample, 1 of the 576 transactions of autumn 2026 filed with the reward and wallet
  apps finally called a contract of the financial group, and 15 called HOT's bridges. The share of Intents transactions signed by two accounts is an upper bound for a similar
  reason: the query gives each account's total and its most frequent destination, not its count per destination.
  The grouping itself moves the figures too: two contracts in last year's "Other" row were called by the exchange's
  own bots (`pyth-oracle.near` and `acc.toalice.near`, 305,146 transactions); filed with the exchange they make it
  +64% instead of +96%, the financial group +31% instead of +37% and everything else +15% instead of +3%.
  With the failing calls of `escrow.ai.near` taken out as well, the financial group is +23%. This year's "Other" row
  holds a contract of the same kind, `aggregate-oracle.near` (157,054 transactions from 8 accounts; those of them that are among
  the 40 largest accounts or in the keyless sample are implicit; the method is `report_pyth_pro_prices`). Its owner is not in the tables; the one link to the exchange is a name: the keyless
  sample has a call of the same method to `agg-oracle.stg.ref-dev-team.near`, the exchange's staging contract. Filed
  with the exchange as well, all three make it +72%, the financial group +33%, everything else +9%, and the financial
  group without `escrow.ai.near` +26%.
  The game Ember
  is not in the reward-app group: it sponsored 387,762 accounts a year ago (2.0% of transactions, 0.7% now) and is filed
  under "Other contracts in the top 40". With it the reward apps' share is 43.3% (88.3% a year ago). The group is left
  as it was when prediction B4 was written, so that the prediction is scored on the definition it was made with.
* **The daily source changes on 2026-11-22.** NearBlocks switches off the API this text was built from (`/v1/charts`;
  its replies carry a `sunset` header with that date). The committed copy keeps every number here reproducible. The
  daily build then goes on from the API that replaces it, for the columns that mean the same there: transactions, fees,
  gas, price, market capitalisation and total supply (a test compares the two committed copies day by day). Counts of
  signers ("active accounts"), of new and of deleted accounts are not in the new API, so those series end with the
  old one and the dashboard says where; its own "active accounts" is another quantity, signers plus the accounts
  relayers acted for, and is not spliced onto the old series. Predictions A1 to A4 and the check of B1 to B4 against
  daily transaction counts use only columns that continue; A5 is then scored on account series that stop in November 2026.

## Limits, as THESIS.md states them in full

*Word for word the list that THESIS.md gives in a line or two each. "Above" and the sections it points to are those of
THESIS.md; the section before this one adds detail to several of its items.*

* **"Outside the reward namespaces" is not "NEAR's own users".** The account-age census groups accounts by namespace,
  and a year ago 93% of the accounts outside `.kaiching`, `.tg` and `.sweat` were sponsored users of other apps
  (`.sweat` itself is 11 service accounts; Sweat's users are relayed implicit accounts). Read the age and returning
  figures of that group with this in mind; the payer and frequency split is the cleaner count.
* **Self-paying means the account paid for at least one transaction in the month.** It may also have sponsored ones.
  A sponsored account is not a lesser one; it is one an app is paying for, and it goes when the app does. Self-paying
  is a technical category: the account signed a transaction and paid its fee. Who funded the account, whether rewards
  repaid the fees and who holds its keys is not checked, so it does not show that a user is willing to pay with money
  of their own.
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
* **Relay classification was corrected on 2026-11-14.** The saved BigQuery tables recognised a meta transaction
  only when Delegate was its first action. The queries now recognise Delegate in any position, as the block parser
  already did. The saved data have not been refreshed, so the effect on this snapshot is unmeasured; matching total
  transaction counts cannot detect misclassified actors or fee payers.
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
* **Lead-lag scans 17 lags × 5 metrics = 85 tests**; about 4 bars outside ±2/√n are expected by chance. A week counts
  only when all seven of its days are in the data: the snapshot ends on a Wednesday, and with its three days set
  against full weeks the count was 6, not 5. The p-values behind Holm's correction use Fisher's z, a normal
  approximation. Each of the seven daily prices must also be finite and positive; the source's zero placeholders
  before trading began are missing prices, while a genuine zero activity day remains an observation. The statistical
  band and p-values treat the weeks as independent, and they are not: weekly price changes correlate
  0.31 with the week before, the usage metrics' changes −0.10 to −0.27. Allowing for that by Bartlett's formula
  (autocorrelations up to eight weeks, on the matched observations of each metric and lag) narrows the band, because
  the signs are opposite: 7 of 85 tests fall outside it, and still none stands after Holm's correction (smallest
  p-value 0.003). Calendar gaps stay gaps when computing lags and autocorrelations. The formula uses autocorrelations
  estimated from the same data, so this is a check, not an exact band. One of the five metrics is
  the `active − new` proxy shown above to point the wrong way; it stays in the scan because A5 was frozen with it,
  and it is not read here as evidence about users.
* **The app table is a manual grouping** of the 40 largest contracts and relayers, which cover 90% of October 2026
  transactions. Allowing for the group's contracts outside a month's 40 largest, the +37% lies between +30% and +39%.
  Filing the contracts the exchange's own bots called with the exchange gives the financial group +31% to +33%. The
  reward-app group is left as it was when prediction B4 was written, so HOT's two bridge contracts stay in it; filed
  with the bridges, the gap B4 is scored on is +0.4 to +1.9 points of all transactions in October 2026 instead of +1.3
  to +2.8. The groups are assigned by contract and relayer, not by what a transaction was for (see "Who is left: the
  customers").
* **The step date is found after the fact.** The rule takes the last day on which the 7-day mean of Intents volume was
  at or below the top of its earlier range and dates the step to the largest one-day rise in the week before it, which
  gives 19 August. That the weekly mean has stayed above the line since is part of how the day is chosen. What the
  rule does not fix is the margin: the weekly mean has not gone below $98.4M since, 10% above the line of $89.6M. The
  date marks a change in level; it is not a test of a structural break and does not name its cause.
* **This is not a valuation.** The thesis measures usage and how much of its revenue reaches the token. It does not
  estimate what NEAR is worth or what holding it would return.
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
