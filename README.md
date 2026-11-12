# NEAR Real Usage

**Track:** Investment Thesis (`thesis`), NEAR HACKATHON, November 2026.

**Problem.** NEAR's headline activity (daily transactions, active accounts) is easy to inflate with reward apps and
one-off accounts, so it is a weak basis for a long-term investment case. This project counts who actually acts on
NEAR, account by account over the whole chain, and tests with re-runnable code whether usage leads the NEAR price.

**Key findings (snapshot 2026-11-11; accounts: October 2026 vs October 2025, three-month means in brackets):**

* Accounts acting on NEAR fell **97%** (43.6M → 1.38M a month). **97% of the accounts that left belonged to reward and
  wallet apps**; one of them, KaiChing, had 40.4M accounts and stopped in spring 2026.
* Outside those apps the account base **also fell 66%** (−57%) and accounts active two months running fell **73%**.
  Our first draft claimed they grew 37%; the full-chain count refuted it.
* What grew is narrower than "users": **transactions senders pay for themselves, outside reward apps, are up 28%**
  (+35%), while transactions sponsored through relayers fell 75%. Transactions to the exchange, Intents, token
  contracts and bridges are up **37%**.
* **30 accounts send half of all transactions.** Reward and wallet apps still send 43% (Sweat alone 26%).
* NEAR Intents volume: **$56M → $129M a day**, October to October. Usage does **not** lead price: 6 of 85 weekly
  lead-lag tests fall outside the noise band where about 4 are expected by chance.
* Two claims of our own second draft ("remaining accounts are busier", "named accounts grew") did not survive a
  robustness check and are listed as refuted in THESIS.md.

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
| `python -m thesis build` | `data/raw/*.json` (exact API responses), `data/daily.csv`, `docs/*.png`, `docs/index.html`, `docs/summary.json`; summary printed to stdout. If an API is down, the build says so and uses the committed copy |
| `python -m thesis build --offline` | Same outputs rebuilt from the committed `data/raw/` files, no network |
| `python -m pytest -q` | 27 tests: parsing, metric formulas, a planted 3-week lead recovered by the lead-lag test, the account census on a hand-made table, block parsing with relayed transactions, the numbers quoted in THESIS.md against `docs/summary.json`, full offline build |
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
| Self-paid vs sponsored | a transaction is sponsored when a relayer signs it for the user (meta transaction), self-paid otherwise | Separates activity someone pays for from activity an app subsidises |
| YoY change | accounts: last complete month vs the same month a year earlier, and the same on three-month means; Intents: calendar month vs the same month a year earlier; prices and fees: last 90-day mean vs the 90 days a year earlier | One month can be an outlier; a 90-day window drifts as its base moves |
| Lead-lag vs price | `corr(Δlog metric_t, Δlog price_{t+k})`, weekly, k = −8…+8; fees are taken in NEAR | Does usage move before price? ±2/√n noise band shown. Fees in USD contain the price, so their correlation with it is mechanical |

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
thesis/census.py     keyless cross-check: random blocks + account ages over public RPC (results in data/raw/census_*)
sql/account_age.sql  the account census query (run once, result in data/bq/account_age.csv)
sql/top_accounts.sql the largest accounts and contracts (result in data/bq/top_accounts_result.csv)
sql/top_accounts.sql the largest accounts, contracts and relayers (result in data/bq/top_accounts_result.csv)
sql/one_day_actions.sql  one day by action kind
data/bq/             committed BigQuery results
tests/               unit + offline end-to-end tests
THESIS.md            claim, evidence, contrary evidence, what would change our mind
```

## Hackathon disclosures

* **Built during the hackathon window.** The repository was created in November 2026; all commits fall inside the
  window (no pre-hackathon baseline).
* **AI assistance.** Code and documentation were written with the help of an AI assistant (Claude) and reviewed and run
  by the author.
* **Libraries:** pandas, numpy, matplotlib, requests. No templates.
* **Data:** all data is public and fetched by the code in this repository or by the SQL in `sql/`. The BigQuery
  results in `data/bq/` were produced by running those queries in the BigQuery console (sandbox, no billing).
* **Other chains / projects:** none.

## License

MIT, see [LICENSE](LICENSE).
