# Notes for coding agents

NEAR Real Usage is a reproducible research pipeline for the NEAR HACKATHON (November 2026), track Investment Thesis.
Start with `README.md` (what it is, how to run it) and `THESIS.md` (the argument and its limits).
`AGENTS.md` and `CLAUDE.md` are the same text under the two names coding agents look for; a test compares them, so
edit both.

## Build and test

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
python -m pytest -q                  # 111 tests, no network
python -m thesis build --offline     # rebuilds docs/ from the committed data, no network
python -m thesis build               # same, after refreshing data/raw/ from the public APIs
```

`docs/` (charts, `index.html`, `summary.json`) is build output and is committed; an offline build in a clean clone
reproduces the numbers exactly; the PNG files are byte-identical only with the library versions pinned in
`requirements.txt`.

## Rules that are easy to break

* **BigQuery costs quota.** `sql/account_age.sql` scans 482.64 GB; the free tier is 1 TB a month. Read the dry-run
  estimate before running anything, and never query the `accounts` table of the NEAR dataset (1.03 TB per query).
  The build does not need BigQuery: results are committed in `data/bq/`.
* **The account census ends on 2026-11-11** (`QUERY_END` in `thesis/population.py`). If the query is re-run, update
  that constant together with `data/bq/account_age.csv`: a month counts only if the scan reached its last day.
  Predictions B1 to B4 are scored by the build from `data/bq/` once the files there hold January 2027, all of it:
  run the frequency and top-accounts queries after the month has ended, because a result that is short of
  NearBlocks' daily counts by a day or more is left unscored.
* **A later run of a query adds months and keeps the earlier ones.** `sql/account_age.sql` and
  `sql/payer_frequency.sql` are run again with only their last date moved (`bq-age` and `bq-freq` refuse a result
  that drops months); the rows of a later `sql/top_accounts.sql` run are added to `data/bq/top_accounts_result.csv`,
  next to the October rows THESIS.md quotes. Tests of the October figures read the tables through
  `tests/snapshot.py`, which cuts them at the snapshot's months, and `tests/test_rerun.py` runs the whole build on
  tables extended this way. The days of the unfinished month are used only as rates per day of transactions, and
  for every namespace (`partial_month.txs_per_day` in the summary), not only where the month suits the argument.
* **A correction is applied to both periods.** The players of Meteor's game were first taken out of last year's
  regular accounts only; a player who still pays for one transaction is inside this year's count too, because a
  frequency class counts relayed transactions. A bound on one side of a comparison is not a range.
* **THESIS.md is a snapshot.** `tests/test_thesis_numbers.py` checks its key numbers, and the README's, against the
  frozen copy of the summary in `data/snapshot/` (`python -m thesis snapshot` refreshes it after an offline build).
  Change them together, and do not type numbers by hand: take them from `summary.json`.
* **A group defined by exclusion is not "own users".** "Outside the reward namespaces" and "independent" both turned
  out to hold other apps' users (Sweat and Ember; Meteor's game). Before reading such a group as a trend, list its
  largest contracts in both periods from `data/bq/top_accounts_result.csv`.
* **Public FastNEAR endpoints are rate-limited without a key.** `thesis/census.py` paces its requests on purpose;
  do not make it faster. Its committed results (`data/raw/census_*`) are the independent check quoted in THESIS.md;
  the build compares them with BigQuery in `cross_check` of `docs/summary.json`.
  `thesis/wallets.py` (balances of the revenue wallets, `data/raw/revenue_wallets.json`) and the `outcomes` command
  use the same paced client.
* **`predictions.csv` is frozen.** Its SHA-256 is quoted in `PREDICTIONS.md` and a test compares them. Do not edit
  it after the fact; add new predictions as a new file.
* **The app groups in `thesis/clients.py` are part of prediction B4.** `REWARD_APPS` and `FINANCE_APPS` stay as they
  were on 2026-11-13, when the prediction was frozen. Publish a different grouping next to them (as `ember` is), not
  instead of them.
* Everything in the repository is in English.
