# NEAR Real Usage

**Track:** Investment Thesis (`thesis`), NEAR HACKATHON, November 2026.

**Problem.** NEAR's headline activity (daily transactions, active accounts) is easy to inflate with reward apps and
one-off accounts, so it is a weak basis for a long-term investment case. This project counts who actually acts on
NEAR, account by account over the whole chain, and tests with re-runnable code whether usage leads the NEAR price.

**The long-term case, in short.** After the largest reward app left, what remains on NEAR is the reward apps that
stayed, which still send 43% of transactions (in October, close to their lowest month), and a small amount of
self-paid, financial activity carried by a few hundred heavy accounts. That activity grew in autumn 2026 in two steps: NEAR Intents volume and the buybacks it funds
stepped up on 19 August and have held, while the load on the chain (its fees and gas) ran high only for the four weeks of the price
rally, from 16 September to 15 October. What held is the volume and the buybacks in USD; the buybacks in NEAR have
held by the median day and not by the mean. The revenue it earns covers 15% to 18% of the new NEAR issued, depending on the
window. That is a narrow case; nine dated predictions say what would widen it or close it.

**Key findings (snapshot 2026-11-11; accounts: October 2026 vs October 2025, three-month means in brackets):**

* Accounts acting on NEAR fell **97%** (43.6M → 1.38M a month). **The whole fall is accounts whose fees an app was
  paying**: 43.05M a year ago, 0.55M now (99.2% of the fall with a one-off deletion of old accounts taken out). One app, KaiChing, had 40.4M of them and stopped in spring 2026; its
  relayer sent 2,000,000 transactions a day, to within a thousandth in 8 of its 17 months from December 2024 to April
  2026 (every series of the census leaves out its first month, November 2024, which has no month before it): a job
  with a quota.
* Among accounts that pay their own fees and are not in a reward app's namespace, **475 heavy accounts (1,000 or more
  transactions a month) send 91% of the self-paid transactions**. The regular ones (10 to 999 a month) number 17,105
  against 27,078 a year earlier, but up to 15,162 of last year's were players of one wallet's reward game who called
  it themselves and paid the fees, the game's calls are relayed now, and players acting through its relayer can be in
  the count of either year, so how many really left is not established. Our first draft claimed
  returning accounts grew 37%; the full-chain count refuted it.
* **Self-paid transactions outside reward apps are up 28%** October to October, but only since autumn: in the nine
  months before (December to August) they averaged 17% below the year before (below it in 7 of the 9 months), all of
  it in implicit and other accounts (named `.near` accounts +4%), and the year as a whole is flat (−5% on eleven-month
  means, the same on twelve). They jumped in the second half of September and the first half of October 2026, when the NEAR price went
  from $1.92 to $4.89 in one month, and in the first 11 days of November they run 12% below October's daily rate and
  5% below November 2025's (14% and 7% below without a one-off of dormant accounts on 10 November). Without
  the reward-side calls in both Octobers and one account whose calls fail, the October change is +26%. Transactions
  sponsored through relayers fell 75%. Transactions to the exchange, Intents, token contracts and bridges are up
  **37%** (+29% without that account); what is neither that group nor the reward apps is level (+3%). The keyless
  sample shows the group above the year before already in the second half of August 2026, before the price doubled (207
  thousand transactions a day against 61 thousand); what rose inside the rally is the exchange and the token
  contracts, and the exchange's part was back down by the second half of October.
* **30 accounts send half of all transactions.** Seven of the ten largest are relays or service accounts (Intents,
  Sweat, the bridges), so this counts who submits transactions, not how many people stand behind them. Reward and
  wallet apps still send 43% (Sweat alone 26%), or 45% counting the one-off deletion of old KaiChing accounts, in a
  month close to their low (by namespace 34% in October against 45% to 56% a month from April to August), and
  November started with more: in its first 11 days HOT's namespace sent 196 thousand transactions a day against
  100 thousand in October. HOT's lowest month was September, at a change of relayer; the return began in October.
* NEAR Intents volume: **$56M → $129M a day**, October to October, but that base was the middle of a ramp-up: the
  volume is level with November 2025 ($122M) and +73% on the nine months in between ($74.5M). It stepped up on 19
  August, as the price began to move and a month before it doubled, and has held since. Usage does **not** lead price: 6 of 85 weekly
  lead-lag tests fall outside the noise band where about 4 are expected by chance, and none stands after Holm's
  correction for testing them together.
* Three readings from our own drafts ("returning accounts grew", "remaining accounts are busier", "the base outside
  reward apps fell by two thirds") did not survive closer measurement, and a fourth ("regular self-paying accounts
  fell by a third") turned out to be partly one game changing who pays; THESIS.md lists each with what replaced it.
* Value reaches the token only in part: buybacks funded by Intents revenue run at **$20.7M a year** and cover **18%**
  of the net new NEAR issued over the last 90 days, the sixth-best of 173 such windows since they began (15% to 18%
  over other windows; $11.2M a year at the pace of the whole programme). In NEAR their step was 1.6 times, in USD 3.5
  times: most of it is the price. That figure is DefiLlama's; read from the chain with no key, the three wallets the
  revenue arrives at grew by 1,456,744 NEAR over the same 90 days, 18.3% of the new supply (15.4% over the last 30).
  The step in revenue since 19 August is 1.9 times more volume and a 1.6 times higher take (2.62 → 4.27 basis points
  of volume), which two other entries trace to one new, incentivised channel; over the last 30 days volume is down 22%
  and captured revenue 20%. At the issuance the approved HSP-029 ends at (1.6% a year, not yet in force) the 18% would
  be 28%.

Full argument, evidence against, and kill criteria: [`THESIS.md`](THESIS.md). Nine dated predictions, their
thresholds reference levels taken from the data or natural lines such as parity, scored by the build (five from
the daily series, four once the BigQuery queries are run again for January 2027): [`PREDICTIONS.md`](PREDICTIONS.md).

**Demo video (73 s):** [`demo/near-real-usage.mp4`](demo/near-real-usage.mp4).

**What it is.** A reproducible research pipeline: one command downloads public data, computes the metrics, renders the
charts and a static dashboard, and writes every number used in [`THESIS.md`](THESIS.md) to `docs/summary.json`. The account census is one SQL
query on NEAR's public BigQuery dataset; its result is committed, so the build needs no Google account.

## Run it (2 minutes)

Everything runs in one Docker image: Python 3.12.12 (the version in `.python-version`) and the libraries pinned in
`uv.lock`, installed with [uv](https://docs.astral.sh/uv/). From a clean clone, one command builds the image, which
runs the tests and rebuilds every output from the committed data with no network, and serves the dashboard on
<http://localhost:8000>:

```bash
docker build -t near-real-usage . && docker run --rm -p 8000:8000 near-real-usage
```

`make serve` does the same. If port 8000 is taken, map another one (`-p 8080:8000`) and open
<http://localhost:8080>. The committed `docs/` were built in this image. An offline build in it reproduces every file
byte for byte; that was checked on arm64 and on x86-64 (the image built for `linux/amd64` and run under emulation, not
on a native x86-64 machine). Outside the image, with uv on macOS, `summary.json` and the page are the same bytes as well,
and only the PNG files differ in their bytes, not in what they show.

Every other command is a `make` target that runs in the same image, on this repository mounted at `/app`, so that
what it writes lands in the repository. Without Docker, `uv run python -m thesis ...` and `uv run pytest -q` run the
same commands: uv installs Python 3.12.12 and the locked libraries itself, with no virtual environment to set up.

| Do this | See this |
|---|---|
| `make serve` | The tests and `python -m thesis build --offline` run while the image is built; the container serves the rebuilt `docs/` on <http://localhost:8000> |
| `make build` (network) | `data/raw/*.json` (exact API responses), `data/daily.csv`, `docs/*.png`, `docs/index.html`, `docs/summary.json`; stdout gets a short digest: one sentence per chart and the status of the nine predictions. If an API is down, the build says so and uses the committed copy |
| `make offline` | Same outputs rebuilt from the committed `data/raw/` files, no network |
| `make test` | 134 tests: parsing, metric formulas, a planted 3-week lead recovered by the lead-lag test, the account census on a hand-made table, block parsing with relayed transactions, the scoring of all nine predictions, the numbers quoted in THESIS.md, PREDICTIONS.md and this README against the frozen copy of the summary, full offline build, the build on tables extended the way a later run of the queries extends them, and one Python version named the same in `.python-version`, the Dockerfile, `pyproject.toml` and this README |
| `make protocol` (network, one request, no key) | `data/raw/protocol_config.json`: the maximum issuance in force, read from the protocol's own configuration; the build sets the approved cut (HSP-029) against it |
| `make wallets` (network, about 2 minutes, no key) | `data/raw/revenue_wallets.json`: what NEAR's three revenue wallets hold at the start and the end of the 90-day window and 30 days before its end, read from an archival RPC node. The build sets their growth against the new supply and against DefiLlama's revenue series |
| `make outcomes` (network, about 5 minutes, no key) | `data/raw/census_outcomes.csv`: how the transactions to NEAR Intents in the sampled blocks ended, by sender |
| `make census` (network, about 1.5 hours, no key, resumable) | `data/raw/census_sample.csv`, `census_existence.csv` and `census_meta.json`: the keyless block sample behind the independent check; `make thesis ARGS="census --seed N"` draws another sample |
| `uv run python -m thesis video` (needs ffmpeg, which the image does not carry) | `demo/near-real-usage.mp4`, a 73-second slideshow rendered from the build outputs, so the numbers on screen are the ones in `docs/summary.json` |
| Paste [`sql/account_age.sql`](sql/account_age.sql) into the BigQuery console, save the result as CSV, then `make thesis ARGS="bq-age result.csv"` (the file inside the repository) | `data/bq/account_age.csv` rebuilt from the chain: 25 months × family × age × returning. Scans 482.64 GB (free tier is 1 TB a month); check the dry-run estimate first |
| Paste [`sql/payer_frequency.sql`](sql/payer_frequency.sql) into the BigQuery console (91.28 GB), save the result as CSV, then `make thesis ARGS="bq-freq result.csv"` | `data/bq/payer_frequency.csv` rebuilt from the chain: accounts by who pays the fee (an app's relayer or the account itself), by namespace and by transactions per month, August 2025 to October 2026 |
| Paste [`sql/payers.sql`](sql/payers.sql) into the BigQuery console (53.23 GB), save the result as `data/bq/payers_result.csv` | Sponsored accounts named by the app whose relayer paid for them (Sweat, Ember, HOT, KaiChing, Meteor), July to October of 2025 and 2026 |
| Paste [`sql/top_accounts.sql`](sql/top_accounts.sql) into the BigQuery console (13.53 GB), save the result as `data/bq/top_accounts_result.csv` | The 40 largest accounts and the 40 largest contracts or relayers for October 2026 and October 2025, plus concentration: 30 accounts send half of all transactions. A later run for two other months adds its rows to the file; the build compares the latest month with the one a year earlier |
| Paste [`sql/one_day_actions.sql`](sql/one_day_actions.sql) into the BigQuery console (0.6 GB) | One day by action kind: 3,448,826 relayed transactions signed by 17 relayers for 2,694,016 users; 238,399 accounts created by 12 creators; total equal to NearBlocks' count for that day |

**Live dashboard:** <https://ivegor.github.io/near-real-usage/>, rebuilt from scratch by GitHub Actions on every push
and daily ([`.github/workflows/build.yml`](.github/workflows/build.yml): the same Docker image, tests → `python -m thesis build` → GitHub
Pages), so the published charts are always the output of the code in this repository. A daily run that cannot
download a source does not publish (`--require-fresh`), so the page never falls back to older data.

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
| YoY change | accounts: last complete month vs the same month a year earlier, and the same on three-month means; Intents: calendar month vs the same month a year earlier, and vs its level between the two autumns; prices and fees: last 90-day mean vs the 90 days a year earlier | One month can be an outlier; a 90-day window drifts as its base moves, and for Intents so does the calendar month, because last year's base was a ramp-up |
| Lead-lag vs price | `corr(Δlog metric_t, Δlog price_{t+k})`, weekly, k = −8…+8; fees are taken in NEAR | Does usage move before price? ±2/√n noise band shown. Fees in USD contain the price, so their correlation with it is mechanical |

## Data sources

* NEAR public BigQuery dataset `bigquery-public-data.crypto_near_mainnet_us`, tables `transactions` and
  `transaction_actions` (the five queries in `sql/`). Fresh to within minutes in November 2026.
  Results are committed in `data/bq/`. Do not query the `accounts` table: one query on it scans 1.03 TB.
* NearBlocks daily network charts: `https://api.nearblocks.io/v1/charts` (no key needed). NearBlocks switches `/v1`
  off on 2026-11-22; from then the build continues from `https://api.nearblocks.io/v3/` (`block-stats`, `txn-stats`,
  `address-stats`, `price-stats`) for the columns that mean the same there, and the series of signers, new and
  deleted accounts end (see "Limits" in THESIS.md). The v3 replies saved in `data/raw/` also give NearBlocks' own
  daily count of relayed users, used as a second source for the census.
* DefiLlama NEAR Intents volume: `https://api.llama.fi/summary/dexs/near-intents`.
* DefiLlama NEAR Intents fees, captured revenue and buybacks: `https://api.llama.fi/summary/fees/near-intents`
  (`python -m thesis fetch-value` refreshes the saved copies).
* FastNEAR public endpoints, no key: the block archive and an archival RPC node for the block sample, the same RPC
  node for the balances of the revenue wallets, and the transaction index `https://tx.main.fastnear.com` for the
  outcomes of sampled transactions. All are rate-limited; the code paces its requests.

No headline number is typed by hand: the figures in the dashboard and the key figures of `THESIS.md` come from
`docs/summary.json` (tests check the ones THESIS.md and this README quote against the frozen copy in
`data/snapshot/`). A few
supporting details in the text (which of the largest accounts are an app's service accounts or trading bots, for
example) are read from the committed data files and are not in that JSON.

The track brief suggests the NEAR Intents Explorer API for swap volume. It needs a partner key, so this project uses
DefiLlama and NearBlocks instead: both are keyless, so anyone can re-run every step.

## Repository layout

```
thesis/population.py account census from BigQuery: families, age, returning accounts (unit-tested)
thesis/segments.py   accounts by who pays the fee and how often they act (unit-tested)
thesis/clients.py    largest accounts, the apps behind them, concentration (unit-tested)
thesis/value.py      Intents fees, captured revenue and buybacks against net new NEAR supply (unit-tested)
thesis/autumn.py     autumn 2026 by half-months: the day Intents volume stepped up and the weeks of the burst (unit-tested)
thesis/wallets.py    the same revenue read from the balances of the wallets it arrives at (unit-tested)
thesis/predictions.py scores predictions.csv against the data (unit-tested)
thesis/sources.py    fetch + cache raw API responses, parse into a daily table
thesis/metrics.py    pure metric functions (unit-tested)
thesis/charts.py     charts, each with a one-sentence, number-backed caption
thesis/dashboard.py  static docs/index.html (GitHub Pages ready)
thesis/census.py     keyless cross-check: random blocks + account ages over public RPC (results in data/raw/census_*)
thesis/video.py      demo video: slides rendered from docs/summary.json and the charts
sql/account_age.sql  the account census query (run once, result in data/bq/account_age.csv)
sql/payer_frequency.sql who pays and how often (result in data/bq/payer_frequency.csv)
sql/payers.sql       which app's relayer paid for the sponsored accounts (result in data/bq/payers_result.csv)
thesis/payers.py     reads it; also checks that three separate queries count the same chain (unit-tested)
sql/top_accounts.sql the largest accounts, contracts and relayers (result in data/bq/top_accounts_result.csv)
sql/one_day_actions.sql  one day by action kind
data/bq/             committed BigQuery results
data/raw/            exact API responses and the keyless block sample
data/snapshot/       the frozen summary THESIS.md is checked against
docs/                build output: charts, index.html (the dashboard), summary.json
tests/               unit + offline end-to-end tests
THESIS.md            claim, evidence, contrary evidence, what would change our mind
AGENTS.md, CLAUDE.md the same notes for coding agents under the two names their tools look for
PREDICTIONS.md       nine dated predictions; predictions.csv is the frozen, machine-readable list
predictions.csv.ots  OpenTimestamps proof that predictions.csv existed on 2026-11-13
.python-version      the one Python version the project is checked on; the Dockerfile names the same one
pyproject.toml       the dependencies, pinned exactly; uv.lock pins everything they pull in
Dockerfile           the one environment: uv installs uv.lock; building it runs the tests and the offline build
Makefile             every command in that image, on the repository mounted at /app
```

## Hackathon disclosures

* **Built during the hackathon window.** The repository was created in November 2026; all commits fall inside the
  window (no pre-hackathon baseline).
* **AI assistance.** Code and documentation were written with the help of an AI assistant (Claude) and reviewed and run
  by the author.
* **Libraries:** pandas, numpy, matplotlib, requests; pytest for the tests; uv installs them and Docker runs them
  (`pyproject.toml`, `uv.lock`, `Dockerfile`); ffmpeg renders the demo video. No templates.
* **Data:** all data is public and fetched by the code in this repository or by the SQL in `sql/`. The BigQuery
  results in `data/bq/` were produced by running those queries in the BigQuery console (sandbox, no billing).
* **Other chains / projects:** none.

## License

MIT, see [LICENSE](LICENSE).
