# NEAR Real Usage

**Track:** Investment Thesis (`thesis`), NEAR HACKATHON, November 2026.

**Problem.** NEAR's headline activity (daily transactions, active accounts) is easy to inflate with bots and one-off
accounts, so it is a weak basis for a long-term investment case. This project separates *repeat, paid-for* usage from
raw activity and tests, with re-runnable code, whether that usage leads the NEAR price.

**Key findings (data through 2026-11-11, last 90 days vs a year earlier):**

* Active accounts **−75%**, but returning accounts (active − new) **+37%** (+11% by medians), now at least 83% of
  actives. Caveat: `active − new` is a lower bound and was a loose one a year ago, so the size of this gain is
  uncertain (see THESIS.md, "Evidence against").
* Fees per active account **+120%** in USD (+43% in NEAR terms), transactions per active account **−30%**:
  less automation, more paid usage.
* NEAR Intents volume **+223%** (~$135M/day).
* Usage does **not** lead price: returning accounts and Intents volume show no weekly-change correlation outside the
  noise band at any lag; fees move with price in the same week (r = 0.38); transaction counts show only scattered
  bars of mixed sign (9 of 85 lag tests outside the band, about 4 expected by chance).

Full argument, evidence against, and kill criteria: [`THESIS.md`](THESIS.md).

**What it is.** A reproducible research pipeline: one command downloads public data, computes usage-quality metrics,
renders six charts and a static dashboard, and prints every number used in [`THESIS.md`](THESIS.md).

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
| `python -m pytest -q` | 8 tests: parsing, metric formulas, a planted 3-week lead recovered by the lead-lag test, data-consistency checks, full offline build |
| `python -m thesis build --bq` | Optional BigQuery cross-check (see below) |

**Live dashboard:** rebuilt from scratch by GitHub Actions on every push and daily
([`.github/workflows/build.yml`](.github/workflows/build.yml): tests → `python -m thesis build` → GitHub Pages),
so the published charts are always the output of the code in this repository.

## Metrics

| Metric | Formula | Why it matters |
|---|---|---|
| Returning accounts | `active_accounts − new_accounts` (a lower bound; the build counts the days where new > active) | Users who came back, not one-off or airdrop-farm accounts |
| Tx per active account | `txns / active_accounts` | Rising with flat users = automation, not adoption |
| Fees per active account | `fees_usd / active_accounts` (also in NEAR: divided by the daily price) | Usage that someone paid for; NEAR terms remove the token-price effect |
| NEAR Intents volume | DefiLlama daily volume | Cross-chain demand routed through NEAR |
| YoY change | last 90-day mean vs the 90 days a year earlier (medians and a quarter-on-quarter comparison are in `summary.json`) | Removes daily noise and seasonality |
| Lead-lag vs price | `corr(Δlog metric_t, Δlog price_{t+k})`, weekly, k = −8…+8 | Does usage move before price? ±2/√n noise band shown |

## Data sources

* NearBlocks daily network charts: `https://api.nearblocks.io/v1/charts` (no key needed).
* DefiLlama NEAR Intents volume: `https://api.llama.fi/summary/dexs/near-intents`.
* Optional: NEAR public BigQuery dataset `bigquery-public-data.crypto_near_mainnet_us` (`sql/*.sql`).
  NEAR Lake, its upstream source, was deprecated in March 2026, so `sql/freshness.sql` runs first and
  the dashboard states the latest date found. Every query has an 80 GB `maximum_bytes_billed` cap and a dry run first.
  To enable: `pip install google-cloud-bigquery && gcloud auth application-default login`.

No numbers are typed by hand: every figure in the dashboard and `THESIS.md` comes from `docs/summary.json`
(the March→April 2026 step quoted under "Limits" is monthly means of `data/daily.csv`).

## Repository layout

```
thesis/sources.py    fetch + cache raw API responses, parse into a daily table
thesis/metrics.py    pure metric functions (unit-tested)
thesis/charts.py     6 charts, each with a one-sentence, number-backed caption
thesis/dashboard.py  static docs/index.html (GitHub Pages ready)
thesis/bq.py         optional BigQuery cross-check
sql/                 BigQuery queries (freshness, heavy signers, signer cohorts)
tests/               unit + offline end-to-end tests
THESIS.md            claim, evidence, contrary evidence, what would change our mind
```

## Hackathon disclosures

* **Built during the hackathon window.** The repository was created in November 2026; all commits fall inside the
  window (no pre-hackathon baseline).
* **AI assistance.** Code and documentation were written with the help of an AI assistant (Claude) and reviewed and run
  by the author.
* **Libraries:** pandas, numpy, matplotlib, requests; optional google-cloud-bigquery. No templates.
* **Other chains / projects:** none.

## License

MIT, see [LICENSE](LICENSE).
