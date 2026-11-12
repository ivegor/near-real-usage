# NEAR Real Usage

**Track:** Investment Thesis (`thesis`), NEAR HACKATHON, November 2026.

**Problem.** NEAR's headline activity (daily transactions, active accounts) is easy to inflate with reward apps and
one-off accounts, so it is a weak basis for a long-term investment case. This project counts who actually acts on
NEAR, account by account over the whole chain, and tests with re-runnable code whether usage leads the NEAR price.

**Key findings (data through 2026-11-11; accounts: October 2026 vs October 2025):**

* Accounts acting on NEAR fell **97%** (43.6M → 1.38M a month). **97% of the accounts that left belonged to two reward
  and wallet apps**; one of them, KaiChing, had 40.4M accounts and stopped in April 2026.
* Outside those apps the account base **also fell 66%** (1.81M → 0.62M) and accounts active two months running fell
  **73%**. Our own first draft claimed they grew 37%; the full-chain count refuted it (see THESIS.md, "A correction").
* The remaining base is busier: transactions per core account **10.7 → 23.9** a month. Named `.near` accounts grew
  **+13%** to 71K and now send **48%** of all NEAR transactions (6% a year ago).
* **30 accounts send half of all transactions.** 43% of transactions still belong to reward and wallet apps (Sweat
  alone 26%); 41% to trading, Intents, token transfers and bridges, and that part grew **+37%** in a year.
* NEAR Intents volume **+223%** (~$135M/day). Usage does **not** lead price: 9 of 85 weekly lead-lag tests fall outside
  the noise band where about 4 are expected by chance, and the strongest is fees moving with price in the same week.

Full argument, evidence against, and kill criteria: [`THESIS.md`](THESIS.md).

**What it is.** A reproducible research pipeline: one command downloads public data, computes the metrics, renders the
charts and a static dashboard, and prints every number used in [`THESIS.md`](THESIS.md). The account census is one SQL
query on NEAR's public BigQuery dataset; its result is committed, so the build needs no Google account.

## Run it (2 minutes)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m thesis build          # downloads data, rebuilds everything
open docs/index.html            # or: python -m http.server -d docs 8000
```

| Do this | See this |
|---|---|
| `python -m thesis build` | `data/raw/*.json` (exact API responses), `data/daily.csv`, `docs/*.png`, `docs/index.html`, `docs/summary.json`; summary printed to stdout |
| `python -m thesis build --offline` | Same outputs rebuilt from the committed `data/raw/` files, no network |
| `python -m pytest -q` | 20 tests: parsing, metric formulas, a planted 3-week lead recovered by the lead-lag test, the account census on a hand-made table, block parsing with relayed transactions, full offline build |
| Paste [`sql/account_age.sql`](sql/account_age.sql) into the BigQuery console, save the result as CSV, then `python -m thesis bq-age result.csv` | `data/bq/account_age.csv` rebuilt from the chain: 25 months × family × age × returning. Scans 482.64 GB (free tier is 1 TB a month); check the dry-run estimate first |
| Paste [`sql/top_accounts.sql`](sql/top_accounts.sql) into the BigQuery console (13.53 GB), save the result as `data/bq/top_accounts_result.csv` | The 40 largest accounts and the 40 largest contracts or relayers for October 2026 and October 2025, plus concentration: 30 accounts send half of all transactions |
| Paste [`sql/one_day_actions.sql`](sql/one_day_actions.sql) into the BigQuery console (0.6 GB) | One day by action kind: 3,448,826 relayed transactions signed by 17 relayers for 2,694,016 users; 238,403 accounts created by 12 creators; total equal to NearBlocks' count for that day |

**Live dashboard:** rebuilt from scratch by GitHub Actions on every push and daily
([`.github/workflows/build.yml`](.github/workflows/build.yml): tests → `python -m thesis build` → GitHub Pages),
so the published charts are always the output of the code in this repository.

## Metrics

| Metric | Formula | Why it matters |
|---|---|---|
| Actor | signer of a transaction, or, for a relayed (meta) transaction, the account the relayer acted for | Counts users, not relayers. On 2025-10-01, 17 relayers signed for 2.69M users |
| Account family | namespace of the actor: `.kaiching`, `.tg` (HOT wallet), `.sweat`, implicit (64 hex), `.near`, other | Separates reward and wallet apps from the rest ("core") |
| Account age | first appearance of the account in any transaction since genesis, relative to the first day of the month | New, recent and old users are different things |
| Active two months running | the actor was also active in the previous calendar month | A direct count of returning accounts |
| `active − new` (NearBlocks) | daily active accounts minus new accounts | The only "returning" proxy the aggregates allow. Shown to be wrong in direction; kept on the dashboard, labelled |
| NEAR Intents volume | DefiLlama daily volume | Cross-chain demand routed through NEAR |
| YoY change | accounts: last complete month vs the same month a year earlier; prices, fees, volume: last 90-day mean vs the 90 days a year earlier | Removes daily noise and seasonality |
| Lead-lag vs price | `corr(Δlog metric_t, Δlog price_{t+k})`, weekly, k = −8…+8 | Does usage move before price? ±2/√n noise band shown |

## Data sources

* NEAR public BigQuery dataset `bigquery-public-data.crypto_near_mainnet_us`, tables `transactions` and
  `transaction_actions` (`sql/account_age.sql`, `sql/top_accounts.sql`, `sql/one_day_actions.sql`). Fresh to within minutes in November 2026.
  Results are committed in `data/bq/`. Do not query the `accounts` table: one query on it scans 1.03 TB.
* NearBlocks daily network charts: `https://api.nearblocks.io/v1/charts` (no key needed).
* DefiLlama NEAR Intents volume: `https://api.llama.fi/summary/dexs/near-intents`.

No numbers are typed by hand: every figure in the dashboard and `THESIS.md` comes from `docs/summary.json`.

## Repository layout

```
thesis/population.py account census from BigQuery: families, age, returning accounts (unit-tested)
thesis/clients.py    largest accounts, the apps behind them, concentration (unit-tested)
thesis/sources.py    fetch + cache raw API responses, parse into a daily table
thesis/metrics.py    pure metric functions (unit-tested)
thesis/charts.py     charts, each with a one-sentence, number-backed caption
thesis/dashboard.py  static docs/index.html (GitHub Pages ready)
thesis/census.py     optional keyless check: sample random blocks and look up account ages over public RPC
thesis/bq.py         optional BigQuery API runner for the older queries in sql/
sql/account_age.sql  the account census query (run once, result in data/bq/account_age.csv)
sql/top_accounts.sql the largest accounts and contracts (result in data/bq/top_accounts_result.csv)
sql/                 other BigQuery queries (one day by action kind, freshness, heavy signers, signer cohorts)
data/bq/             committed BigQuery results
tests/               unit + offline end-to-end tests
THESIS.md            claim, evidence, contrary evidence, what would change our mind
```

## Hackathon disclosures

* **Built during the hackathon window.** The repository was created in November 2026; all commits fall inside the
  window (no pre-hackathon baseline).
* **AI assistance.** Code and documentation were written with the help of an AI assistant (Claude) and reviewed and run
  by the author.
* **Libraries:** pandas, numpy, matplotlib, requests; optional google-cloud-bigquery. No templates.
* **Data:** all data is public and fetched by the code in this repository or by the SQL in `sql/`. The BigQuery
  results in `data/bq/` were produced by running those queries in the BigQuery console (sandbox, no billing).
* **Other chains / projects:** none.

## License

MIT, see [LICENSE](LICENSE).
