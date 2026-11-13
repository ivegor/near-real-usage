# NEAR Real Usage

**Track:** Investment Thesis (`thesis`), NEAR HACKATHON, November 2026.

**Problem.** NEAR's headline activity (daily transactions, active accounts) is easy to inflate with reward apps and
one-off accounts, so it is a weak basis for a long-term investment case. This project counts who actually acts on
NEAR, account by account over the whole chain, and tests with re-runnable code whether usage leads the NEAR price.

**Key findings (snapshot 2026-11-11; accounts: October 2026 vs October 2025, three-month means in brackets):**

* Accounts acting on NEAR fell **97%** (43.6M → 1.38M a month). **The whole fall is accounts whose fees an app was
  paying**: 43.05M a year ago, 0.55M now. One app, KaiChing, had 40.4M of them and stopped in spring 2026.
* Among accounts that pay their own fees, the regular ones (10 to 999 transactions a month) fell from
  **27,078 to 17,105** (−37%; −50%), while 475 heavy accounts (1,000 or more a month) send 91% of the
  self-paid transactions. Our first draft claimed returning accounts grew 37%; the full-chain count refuted it.
* **Self-paid transactions outside reward apps are up 28%** October to October, but flat over the year as a whole
  (−5% on eleven-month means): they jumped in September and October 2026. Transactions sponsored through relayers
  fell 75%. Transactions to the exchange, Intents, token contracts and bridges are up **37%**.
* **30 accounts send half of all transactions.** Reward and wallet apps still send 43% (Sweat alone 26%), or
  45% counting a one-off sweep by old KaiChing accounts.
* NEAR Intents volume: **$56M → $129M a day**, October to October. Usage does **not** lead price: 6 of 85 weekly
  lead-lag tests fall outside the noise band where about 4 are expected by chance.
* Three readings from our own drafts ("returning accounts grew", "remaining accounts are busier", "the base outside
  reward apps fell by two thirds") did not survive closer measurement; THESIS.md lists each with what replaced it.

* Value reaches the token only in part: buybacks funded by Intents revenue run at **$20.7M a year** and cover **18%**
  of the net new NEAR issued.

Full argument, evidence against, and kill criteria: [`THESIS.md`](THESIS.md). Nine dated predictions whose thresholds
are taken from the data, scored by the build: [`PREDICTIONS.md`](PREDICTIONS.md).

**Demo video (71 s):** [`demo/near-real-usage.mp4`](demo/near-real-usage.mp4).

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
| `python -m pytest -q` | 44 tests: parsing, metric formulas, a planted 3-week lead recovered by the lead-lag test, the account census on a hand-made table, block parsing with relayed transactions, the numbers quoted in THESIS.md against `docs/summary.json`, full offline build |
| `python -m thesis video` (needs ffmpeg) | `demo/near-real-usage.mp4`, a 71-second slideshow rendered from the build outputs, so the numbers on screen are the ones in `docs/summary.json` |
| Paste [`sql/account_age.sql`](sql/account_age.sql) into the BigQuery console, save the result as CSV, then `python -m thesis bq-age result.csv` | `data/bq/account_age.csv` rebuilt from the chain: 25 months × family × age × returning. Scans 482.64 GB (free tier is 1 TB a month); check the dry-run estimate first |
| Paste [`sql/payer_frequency.sql`](sql/payer_frequency.sql) into the BigQuery console (91.28 GB) | Accounts by who pays the fee (an app's relayer or the account itself), by namespace and by transactions per month, August 2025 to October 2026 |
| Paste [`sql/top_accounts.sql`](sql/top_accounts.sql) into the BigQuery console (13.53 GB), save the result as `data/bq/top_accounts_result.csv` | The 40 largest accounts and the 40 largest contracts or relayers for October 2026 and October 2025, plus concentration: 30 accounts send half of all transactions |
| Paste [`sql/one_day_actions.sql`](sql/one_day_actions.sql) into the BigQuery console (0.6 GB) | One day by action kind: 3,448,826 relayed transactions signed by 17 relayers for 2,694,016 users; 238,403 accounts created by 12 creators; total equal to NearBlocks' count for that day |

**Live dashboard:** rebuilt from scratch by GitHub Actions on every push and daily
([`.github/workflows/build.yml`](.github/workflows/build.yml): tests → `python -m thesis build` → GitHub Pages),
so the published charts are always the output of the code in this repository.

## Metrics

| Metric | Formula | Why it matters |
|---|---|---|
| Actor | signer of a transaction, or, for a relayed (meta) transaction, the account the relayer acted for | Counts users, not relayers. On 2025-10-01, 17 relayers signed for 2.69M users |
| Account family | namespace of the actor: `.kaiching`, `.tg` (HOT wallet), `.sweat`, implicit (64 hex), `.near`, other | Shows which app created the account. Not a count of "own users": 93% of accounts outside the reward namespaces were sponsored users of other apps |
| Account age | first appearance of the account in any transaction since genesis, relative to the first day of the month | New, recent and old users are different things |
| Active two months running | the actor was also active in the previous calendar month | A direct count of returning accounts |
| `active − new` (NearBlocks) | daily active accounts minus new accounts | The only "returning" proxy the aggregates allow. Shown to be wrong in direction; kept on the dashboard, labelled |
| NEAR Intents volume | DefiLlama daily volume | Cross-chain demand routed through NEAR |
| Who pays (account) | sponsored: a relayer submitted every transaction of the account in the month; self-paying: the account paid for at least one | Separates users an app is paying for from accounts that spend their own money. The line is the fee payer, not a threshold |
| How often (account) | transactions in the month by powers of ten: occasional under 10, regular 10 to 999, heavy 1,000 or more | 1,000 a month is over 30 a day, which nobody does by hand; the lines are powers of ten, not tuned |
| Self-paid vs sponsored (transaction) | a transaction is sponsored when a relayer signs it for the user (meta transaction), self-paid otherwise | Separates activity someone pays for from activity an app subsidises |
| YoY change | accounts: last complete month vs the same month a year earlier, and the same on three-month means; Intents: calendar month vs the same month a year earlier; prices and fees: last 90-day mean vs the 90 days a year earlier | One month can be an outlier; a 90-day window drifts as its base moves |
| Lead-lag vs price | `corr(Δlog metric_t, Δlog price_{t+k})`, weekly, k = −8…+8; fees are taken in NEAR | Does usage move before price? ±2/√n noise band shown. Fees in USD contain the price, so their correlation with it is mechanical |

## Data sources

* NEAR public BigQuery dataset `bigquery-public-data.crypto_near_mainnet_us`, tables `transactions` and
  `transaction_actions` (`sql/account_age.sql`, `sql/top_accounts.sql`, `sql/one_day_actions.sql`). Fresh to within minutes in November 2026.
  Results are committed in `data/bq/`. Do not query the `accounts` table: one query on it scans 1.03 TB.
* NearBlocks daily network charts: `https://api.nearblocks.io/v1/charts` (no key needed).
* DefiLlama NEAR Intents volume: `https://api.llama.fi/summary/dexs/near-intents`.
* DefiLlama NEAR Intents fees, captured revenue and buybacks: `https://api.llama.fi/summary/fees/near-intents`
  (`python -m thesis fetch-value` refreshes the saved copies).

No headline number is typed by hand: the figures in the dashboard and the key figures of `THESIS.md` come from
`docs/summary.json` (a test checks the ones THESIS.md quotes against the frozen copy in `data/snapshot/`). A few
supporting details in the text (the number of accounts trading on one exchange, the size of two one-off bursts,
the range of sample sizes in the lead-lag test) are read from the committed data files and are not in that JSON.

The track brief suggests the NEAR Intents Explorer API for swap volume. It needs a partner key, so this project uses
DefiLlama and NearBlocks instead: both are keyless, so anyone can re-run every step.

## Repository layout

```
thesis/population.py account census from BigQuery: families, age, returning accounts (unit-tested)
thesis/segments.py   accounts by who pays the fee and how often they act (unit-tested)
thesis/clients.py    largest accounts, the apps behind them, concentration (unit-tested)
thesis/value.py      Intents fees, captured revenue and buybacks against net new NEAR supply (unit-tested)
thesis/predictions.py scores predictions.csv against the data (unit-tested)
thesis/sources.py    fetch + cache raw API responses, parse into a daily table
thesis/metrics.py    pure metric functions (unit-tested)
thesis/charts.py     charts, each with a one-sentence, number-backed caption
thesis/dashboard.py  static docs/index.html (GitHub Pages ready)
thesis/census.py     keyless cross-check: random blocks + account ages over public RPC (results in data/raw/census_*)
sql/account_age.sql  the account census query (run once, result in data/bq/account_age.csv)
sql/payer_frequency.sql who pays and how often (result in data/bq/payer_frequency.csv)
sql/payers.sql       which app's relayer paid for the sponsored accounts (result in data/bq/payers_result.csv)
thesis/payers.py     reads it; also checks that three separate queries count the same chain (unit-tested)
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
