# Predictions

Written on 2026-11-13, before any of the check dates. Each line is what THESIS.md expects if it is right; a miss
counts against it. The machine-readable list is [`predictions.csv`](predictions.csv).

SHA-256 of `predictions.csv`: `5fea0635893e0d78d1689e7b42b0f04ea1884c0dd8bb21bead5e281a33a3416b`
(a test fails if the file no longer matches; the commit that introduced it is tagged `predictions-2026-11-13`).

| Id | Check on | Prediction | Scoring |
|---|---|---|---|
| A1 | 2026-11-17 | NEAR Intents volume averages at least $100M a day over the 7 days ending 2026-11-17 | automatic |
| A2 | 2026-11-30 | Buybacks funded by Intents revenue reach at least $1.2M in November 2026 | automatic |
| A3 | 2027-02-11 | Buybacks still cover less than 30% of net new NEAR supply over the 90 days ending 2027-02-11 | automatic |
| A4 | 2027-02-11 | No more than 8 of the 85 weekly lead-lag tests fall outside the noise band: usage still does not lead price | automatic |
| B1 | 2027-02-01 | Accounts outside the reward apps in January 2027 are below the October 2026 count of 621166 | bigquery |
| B2 | 2027-02-01 | Self-paid transactions outside the reward apps average at least 10M a month over November 2026 to January 2027 | bigquery |
| B3 | 2027-02-01 | In January 2027 at most 50 accounts still send half of all transactions | bigquery |
| B4 | 2027-02-01 | In January 2027 reward and wallet apps still send at least 35% of all transactions | bigquery |

**Scoring.** "automatic" predictions are scored by `python -m thesis build` from the daily NearBlocks and DefiLlama
series as soon as the data reaches the check date; the status is shown on the dashboard and in `docs/summary.json`
under `predictions`. "bigquery" predictions need `sql/account_age.sql` and `sql/top_accounts.sql` to be run for the
named month (the free BigQuery tier allows it once a month) and are shown as open until then.

**How they follow from the thesis.** A1 and A2: cross-chain demand and the buybacks it funds keep their level. A3: value
capture stays far from covering dilution. A4: usage does not lead price. B1: the account base outside reward apps has
not found a floor. B2: self-paid activity is the part that holds. B3: the chain stays concentrated. B4: reward apps
are still a large part of what the chain does.
