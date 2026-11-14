# Predictions

Written on 2026-11-13, before any of the check dates. Each line is what THESIS.md expects if it is right; a miss
counts against it. The machine-readable list is [`predictions.csv`](predictions.csv).

## How the thresholds were chosen

No threshold is a number tuned to the outcome. Five are reference levels taken from the data (rules 1 and 2), four
are natural lines (rule 3), and each prediction answers a question someone running or funding the product would ask.

1. **New level or spike?** In September 2026 three things stepped up together: Intents volume, the buybacks it funds,
   and self-paid transactions outside reward apps (month by month; by half-months the step has two dates, see the
   first note below). The NEAR price rose in the same month, from $1.92 to $4.89, so
   the step may be the rally itself. A year earlier Intents volume had a one-month spike (November 2025)
   and fell straight back. So the test is the same for all three: does the metric stay **above the highest month of
   its range before the step** (December 2025 to August 2026 for Intents volume and self-paid transactions; March to
   August 2026 for the buybacks, which began on 23 February)? Above it, the step is a new level; back inside the old
   range, it was a spike. (A1, A2, A3, B2)
2. **Has the decline stopped?** Accounts that pay their own fees and act regularly slid for a year to a low in
   August 2026 and rebounded in September. The reference is **that low**: staying above it means the low was not
   broken; touching it again means the rebound was a spike. (B1)
3. **Which side of a natural line?** Where a product line exists, it is the threshold: buybacks offsetting **half** of
   dilution on the way to break-even (A4), **no** usable timing signal for the price (A5), **dozens rather than
   hundreds** of accounts sending half of the transactions (B3), and the point where reward apps and financial use are
   **equal** (B4).

The build recomputes the reference levels of rules 1 and 2 from the data and publishes them in `docs/summary.json`
under `predictions.baselines`; `tests/test_predictions.py` fails if a threshold in the file differs from the levels
in the frozen copy of that summary (`data/snapshot/thesis_summary.json`).

## The predictions

SHA-256 of `predictions.csv`: `7ff48f00d7131ae4cf1e5b11ff817242844e6b8dd3a0681d98e1fcbaac65d15a`
(a test fails if the file no longer matches; the commit that holds this version of the file is tagged
`predictions-2026-11-13`).

A hash in a repository proves nothing about dates: history can be rewritten. So the file also has a timestamp that
does not depend on this repository. [`predictions.csv.ots`](predictions.csv.ots) is an
[OpenTimestamps](https://opentimestamps.org) proof made on 2026-11-13 at 15:47 UTC: the digest above was sent to
public calendar servers, which commit it to a Bitcoin block. The proof has since been completed (`ots upgrade`): it
holds the attestation of Bitcoin block 975705. `ots verify predictions.csv.ots` (from
`pip install opentimestamps-client`) or the form on opentimestamps.org checks it against the file; a test checks
that the proof is for the file's current digest. The first prediction is scored four days after that timestamp.

| Id | Question | Prediction | Threshold | Where the threshold comes from | Check on | Scoring |
|---|---|---|---|---|---|---|
| A1 | Is the autumn 2026 level of cross-chain demand holding? | NEAR Intents volume over the 7 days ending 2026-11-17 stays above the top of its range before the September step | > $89.6M a day | highest monthly mean of Dec 2025 to Aug 2026 (August 2026) | 2026-11-17 | automatic |
| A2 | Was the September step in cross-chain demand a new level or a spike? | NEAR Intents volume in December 2026 stays above the top of its range before the September step; in December 2025 it fell back after a one-month spike | > $89.6M a day | highest monthly mean of Dec 2025 to Aug 2026 (August 2026) | 2026-12-31 | automatic |
| A3 | Does the money reaching the token hold its new level? | Buybacks funded by Intents revenue in December 2026 stay above their highest month before the September step | > $0.72M | highest monthly buyback of Mar to Aug 2026 (August 2026) | 2026-12-31 | automatic |
| A4 | Do buybacks offset the dilution of holders? | Over the 90 days ending 2027-02-11 buybacks still offset less than half of the net new NEAR supply | < 50% | half of net new supply; break-even is 1.0 | 2027-02-11 | automatic |
| A5 | Can usage be used as a timing signal for the price? | No usage metric shows two neighbouring positive leads outside the noise band: usage still does not lead price | <= 0 | none today | 2027-02-11 | automatic |
| B1 | Has the base of regular self-paying accounts found a floor? | In January 2027 accounts that pay their own fees and act 10 to 999 times a month stay above their August 2026 low: the rebound holds | > 7,201 | their lowest month before the September step (August 2026) | 2027-02-01 | bigquery |
| B2 | Is self-paid activity at a new level or was it a spike? | Self-paid transactions outside the reward apps average above the top of their range before the September step over November 2026 to January 2027 | > 10.38M a month | highest month of Dec 2025 to Aug 2026 (February 2026) | 2027-02-01 | bigquery |
| B3 | Does the chain still depend on a few dozen accounts? | In January 2027 fewer than a hundred accounts still send half of all transactions | < 100 | dozens rather than hundreds; 30 in October 2026 | 2027-02-01 | bigquery |
| B4 | Which is the larger half of the chain: reward apps or financial use? | In January 2027 reward and wallet apps still send more transactions than the exchange, Intents, token contracts and bridges together | > 0 | the point where the two are equal; 43% vs 41% in October 2026 | 2027-02-01 | bigquery |

Two notes on what the reference months turned out to hold.

The step has two dates (see "Evidence against" in THESIS.md). Read by half-months, Intents volume and the buybacks
stepped up on 19 August 2026, as the price began to move and a month before it doubled, and the fees and gas on the
chain only from 16 September to 15 October. August, the reference month of A1, A2 and A3, therefore holds 13 days of the step: 58% of its Intents
volume and 65% of its buybacks came after 19 August. That makes those thresholds higher, not lower: without August the
top of Intents volume's range would be lower. A3 has a further weakness. Its threshold is in USD, and the buybacks
are bought with revenue counted in USD, so it can be met by the price alone: at the pace in NEAR of the last 30 days
before the file was frozen (13,548 NEAR a day), December's buybacks exceed $0.72M at any mean price above $1.72,
and the price was $1.59 on the day of the step. A hold on A3 says little unless the buybacks in NEAR hold too;
`docs/summary.json` publishes both under `value_capture.windows`.

One reference level needs a note. B2's reference month, February 2026, turned out to hold a one-off burst: a third
of its self-paid transactions came from dormant accounts that sent one transaction each (see "Limits" in THESIS.md).
Without them the top of the range is 8.65M (June 2026). The file is frozen, so the threshold stays at 10.38M, which
is the harder of the two for the prediction to stay above; `docs/summary.json` publishes both levels under
`predictions.baselines`. Months before the range were higher, 11.27M in November 2025 and 12.07M in December 2024:
the range is the nine months before the step, the same for all the metrics of rule 1. The first 11 days of B2's
window were in the census when the file was frozen: self-paid transactions ran at 356 thousand a day, a rate of
10.68M a month, 3% above the threshold and 12% below October's rate. Those days hold a one-off of dormant accounts on
10 November that the filter used for February takes out, though it was not deletions (NearBlocks counted 74 that
day): with the same filter, 347 thousand a day and 10.41M a month, 0.3%
above the threshold. The margin is thin. The rate was worked out
after the file was frozen, so it played no part in the choice of the threshold.

A second note, on B1. The accounts it counts turned out to include players of a reward game who paid their own fees:
up to 15,162 of the 27,078 a year ago called the game themselves, and up to 9,110 acted through its relayer and paid
for something else (how many are in both groups the tables do not say); the game's calls go through the relayer now
(see "Who pays, and how often" in THESIS.md). That
changes how the year before is read, not the threshold. The frozen statement of B1 leaves one thing unsaid: it
counts accounts outside the reward apps' namespaces (`.kaiching`, `.tg`), as the 7,201 does. The move was over before the low: Meteor fully sponsored
14,667 accounts in August 2026 and 15,409 in October, against 7,748 and 8,677 a year earlier, and in the keyless
sample, which starts on 14 August 2026, all 41 calls to the game come through the relayer. The August low and the
January value are both counted after it. Both can still hold players who pay for a transaction of their own, because
a relayed call counts towards the frequency class: up to 4,313 such accounts in October 2026.
Its statement ends "the rebound holds", which says more than the threshold can: a January just above 7,201 would be
a hold, and a fall of 58% from October's 17,105. A hold on B1 is read as "the August low was not broken", no more.
B4 is scored on its range. The groups' contracts outside a month's 40 largest are not in its count, and each can
have received up to the smallest entry of that list (`clients.groups_outside_the_40` in the summary). Until
2026-11-14 the build scored B4 on the count as listed; from that day it scores the end of the range nearer the
threshold and leaves B4 open when the range lies on both sides of it. In October 2026 the range is +1.3 to +2.8
points, on one side.

A third note, on what the data already held when the file was frozen. It ran through 2026-11-11. A1's window is the
seven days to 17 November, so one of its seven days was known, and the first 11 days of November had averaged
$129.7M a day, 45% above A1's threshold. B4 is about January, but the same eleven days of the census pointed its
way: HOT's namespace was sending 196 thousand transactions a day against 100 thousand in October (see "Evidence
against" in THESIS.md), and October was one month after HOT's lowest: September, when a new relayer took over, with the return
beginning in October and a further step on 9 November. The "43%
vs 41%" B4 starts from is October too, a month in which the reward apps' share was close to its low (34% of
transactions by namespace, against 45% to 56% a month from April to August). Neither figure set a threshold: A1's is
the top of the range before the September step, B4's is the point where the two groups are equal.

## Scoring

"automatic" predictions are scored by `python -m thesis build` from the daily NearBlocks and DefiLlama series as soon
as the data reaches the check date and covers every day of the window the prediction names (until then: open); the
status is on the dashboard and in `docs/summary.json` under `predictions`.
"bigquery" predictions are scored by the same build from the committed query results in `data/bq/`, as soon as
those hold the month a prediction names: `sql/payer_frequency.sql` (B1), `sql/account_age.sql` (B2) and
`sql/top_accounts.sql` (B3, B4) have to be run again by hand with later dates (the free BigQuery tier allows it once
a month) and their results committed, with `QUERY_END` in `thesis/population.py` moved to the new end of the scan.
Until then they are shown as open. A month counts only if the result holds all of it. For the census that is the day
its scan stopped (`QUERY_END`). The other two queries name whole months, so their result is partial only if the
query was run before the month ended; the build sets the month's transaction count in the result against NearBlocks'
daily counts and leaves the prediction open while the result is short by a day or more (the line is the quietest
day of that month, not a chosen tolerance). B4 is scored with the
app groups as they were on 2026-11-13: a contract or relayer that an app starts to use after that date is not in
them and counts as "other". The list of the month's 40 largest is committed with the result, so what was left out
can be seen.
A later run adds months and keeps the earlier ones. For `sql/payer_frequency.sql` and `sql/account_age.sql` only the
last date is moved, so that the result holds every earlier month too and replaces the file (`bq-freq` and `bq-age`
refuse a result that would drop months). `sql/top_accounts.sql` names two months a year apart: both are changed, to
January 2027 and January 2026, and the rows of the result are added to `data/bq/top_accounts_result.csv` next to the
October rows that THESIS.md quotes. `tests/test_rerun.py` runs the whole build on tables extended this way, and the
tests of the October figures read the tables cut at October, so they keep passing.
NearBlocks switches off the API the daily series comes from (`/v1/charts`) on 2026-11-22, before most check dates.
From then the build reads the API that replaces it for the columns that mean the same there (transactions, fees, gas,
price, market capitalisation, total supply), which is all that A1 to A4 and the check of the BigQuery months against
daily transaction counts need. The new API has no count of signers or of new accounts, so two of the five usage
metrics behind A5 stop in November 2026; A5 is scored on the series as they then stand, and that is said here now,
before the date, and not after it.
A5 counts both signs. A "positive lead" in its statement is a positive lag: the usage metric moves first. Until
2026-11-14 the build counted a pair of neighbouring lags only when both correlations were above zero; two neighbours
that both move against the price are as much a timing signal, so from that day a pair of either sign counts, as long
as both are of the same sign. That makes the prediction harder to hold, not easier; `predictions.csv` is unchanged,
and on the data it was frozen with both counts are 0.
A5's window is the whole series, so "covers every day of the window" means for A5 that every week from 2026-11-12 (the
day after the data it was frozen with) to the check date has a value of the price and of each usage series that goes
on after `/v1` (transactions, fees, Intents volume). Until then it stays open; without that rule it could be scored
on the old weeks alone. This rule was added on 2026-11-14, before the check date.
GitHub switches a scheduled workflow off after 60 days without activity in a public repository. If that happens
before a check date, the prediction is scored when the workflow is switched on again or the build is run by hand.
