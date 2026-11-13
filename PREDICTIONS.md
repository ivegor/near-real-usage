# Predictions

Written on 2026-11-13, before any of the check dates. Each line is what THESIS.md expects if it is right; a miss
counts against it. The machine-readable list is [`predictions.csv`](predictions.csv).

## How the thresholds were chosen

No threshold is a number we picked. Each one is a reference level taken from the data by one of three rules, and
each prediction answers a question someone running or funding the product would ask.

1. **New level or spike?** In September 2026 three things stepped up together: Intents volume, the buybacks it funds,
   and self-paid transactions outside reward apps. A year earlier Intents volume had a one-month spike (November 2025)
   and fell straight back. So the test is the same for all three: does the metric stay **above the highest month of
   its range before the step** (December 2025 to August 2026)? Above it, the step is a new level; back inside the old
   range, it was a spike. (A1, A2, A3, B2)
2. **Has the decline stopped?** Accounts that pay their own fees and act regularly slid for a year to a low in
   August 2026 and rebounded in September. The reference is **that low**: staying above it means a floor has been
   found; touching it again means the rebound was a spike. (B1)
3. **Which side of a natural line?** Where a product line exists, it is the threshold: buybacks offsetting **half** of
   dilution on the way to break-even (A4), **no** usable timing signal for the price (A5), **dozens rather than
   hundreds** of accounts sending half of the transactions (B3), and the point where reward apps and financial use are
   **equal** (B4).

`tests/test_predictions.py` recomputes the reference levels of rules 1 and 2 from the committed data and fails if a
threshold in the file differs from them.

## The predictions

SHA-256 of `predictions.csv`: `7ff48f00d7131ae4cf1e5b11ff817242844e6b8dd3a0681d98e1fcbaac65d15a`
(a test fails if the file no longer matches; the commit that holds this version of the file is tagged
`predictions-2026-11-13`).

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

One reference level needs a note. B2's reference month, February 2026, turned out to hold a one-off burst: a third
of its self-paid transactions came from dormant accounts that sent one transaction each (see "Limits" in THESIS.md).
Without them the top of the range is 8.65M (June 2026). The file is frozen, so the threshold stays at 10.38M, which
is the harder of the two for the prediction to stay above; `docs/summary.json` publishes both levels under
`predictions.baselines`.

## Scoring

"automatic" predictions are scored by `python -m thesis build` from the daily NearBlocks and DefiLlama series as soon
as the data reaches the check date and covers every day of the window the prediction names (until then: open); the
status is on the dashboard and in `docs/summary.json` under `predictions`.
"bigquery" predictions need `sql/account_age.sql`, `sql/payer_frequency.sql` and `sql/top_accounts.sql` to be run for the named month (the free
BigQuery tier allows it once a month) and are shown as open until then.
