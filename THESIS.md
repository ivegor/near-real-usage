# Thesis: NEAR's usage got smaller and better. The case rests on paying repeat users and Intents, not on activity momentum

*Data through 2026-11-11 (NearBlocks daily charts, DefiLlama NEAR Intents). "YoY" = mean of the last 90 days vs the
same 90 days a year earlier. Every number below is reproduced by `python -m thesis build` and stored in
`docs/summary.json`; if a re-run on newer data changes a number, the dashboard is the source of truth.*

## One-paragraph summary

Headline NEAR activity collapsed over the past year: active accounts −75%, daily transactions −84%, new accounts −96%.
Read naively, that is a dying network. It is not what the composition shows. The accounts that left were one-off and
farm accounts; the core of **returning** accounts (active − new) *grew* 37% by this measure (+11% by medians; the
measure is a lower bound, see "Evidence against"), and they now make up at least 83% of daily actives. Each active
account pays **2.2× more in fees** in USD (1.4× in NEAR terms) while sending **30% fewer transactions**: less
automation, more paid usage. NEAR Intents volume **tripled** to about $135M a day. What the data does **not** support is the popular idea
that usage *leads* price: weekly changes in usage do not predict weekly changes in NEAR price. The investment case is
therefore a slow, fundamentals one (a smaller, stickier, paying user base plus cross-chain flow through Intents), not a
"buy when activity spikes" signal.

## Claims and what the data says

| # | Claim | Result | Evidence (90-day mean, YoY) |
|---|---|---|---|
| 1 | Repeat usage holds up independently of headline activity | **Supported, size uncertain** | Returning accounts 44,236 → 60,746/day (+37%; +11% by medians) while active accounts fell 290,216 → 71,693 (−75%). `active − new` is a lower bound, and a loose one a year ago |
| 2 | Activity is becoming less automated and more paid-for | **Supported** | Tx per active account 16.0 → 11.2 (−30%); fees per active account $0.030 → $0.066 (+120% in USD, +43% in NEAR terms, +53% by USD medians) |
| 3 | Cross-chain demand through NEAR is growing | **Supported** | NEAR Intents volume $41.7M → $134.9M/day (+223%) |
| 4 | Usage changes lead price changes | **Not supported** | See "Evidence against" |

## Evidence for

* **The user base shrank to its core, and the core grew.** New accounts fell from 248,771 to 10,946 a day (−96%), so
  almost all of the drop in actives is the disappearance of accounts that appeared once. Returning accounts rose 37%
  (+11% by medians) and their share of actives went from at least 15% to at least 83%.
  *(charts: accounts, usage_vs_price)*
* **Less bot-like, more paid usage per account.** Transactions per active account fell 30% while fees per active
  account rose 120% in USD and 43% in NEAR terms (the NEAR price itself is up 39%, so part of the USD rise is the
  token price). Rising fees with falling transaction counts per user is the opposite of the automated-spam
  pattern. *(charts: tx_per_active, fees_per_active)*
* **Intents is a real, growing flow.** Daily Intents volume tripled year on year. Per active account it went from
  about $155 to about $2,097 a day. *(chart: intents)*

## Evidence against

* **Total fees fell.** Network fees are down 52% YoY ($8,652 → $4,122/day). Per-user quality is up, but the absolute
  fee base is small, so this is not (yet) a cash-flow story.
* **Usage does not lead price.** On weekly log-changes over ~6 years (n = 292–317 weeks, noise band ≈ ±0.11–0.12):
  * returning accounts vs price: no correlation outside the noise band at any lag from −8 to +8 weeks;
  * NEAR Intents volume vs price (n = 100 weeks, band ±0.20): nothing outside the band at any lag;
  * fees vs price: r = 0.38 at lag 0 and r = 0.18 at both −1 and +1 week. The pattern is symmetric: they move
    together in the same week (fees are priced in USD, so part of this is mechanical) and weekly averaging spreads
    that into the neighbouring weeks; it is not one moving before the other;
  * active accounts: r = 0.14 at lag 0 and r = 0.12 at −5 weeks (price first); nothing at positive lags;
  * transactions: four bars just outside the band with mixed signs (+0.14 at −8, −0.13 at +2, +0.11 at +4,
    −0.15 at +6 weeks), with no run of adjacent lags of one sign.

  In total 9 of 85 lag tests fall outside the band, where about 4 are expected by chance; 4 of the 9 are fees
  (lags −1, 0, +1) and active accounts (lag 0) moving with price in the same week.
* **`active − new` is only a lower bound for returning accounts.** The formula assumes every new account is also
  counted as active on its first day. That is not always true: new accounts exceeded active accounts on 234 days in
  the history, including 7 of the 90 days in the year-earlier window (0 of the last 90). True returning accounts lie
  between `active − new` and `active`: 60,746–71,693 a day now, but anywhere in 44,236–290,216 a year ago, when new
  accounts were 86% of actives. So +37% sits near the favourable end of that range; this data cannot rule out
  that returning accounts fell. What is solid: at least 83% of today's active accounts existed before the day they
  were counted.
* **The latest quarter points down.** Against the previous 90 days, returning accounts are down 30%
  (87,241 → 60,746/day) and transactions per active account are up 48% (7.6 → 11.2). The YoY comparison hides this.
* **Returning ≠ human.** In the same 90-day window of 2024 "returning" accounts averaged 525,011 a day, then fell
  to 44,236 a year later. A swing that large means the metric can be inflated by campaigns or automated accounts;
  claim 1 relies on the tx-per-account and fee checks, not on this metric alone.

## What would change our mind

* Returning accounts fall for two consecutive quarters: the "stickier core" was a pause, not a floor.
  (Status: the latest quarter is the first down quarter, −30%.)
* Tx per active account rises again while fees per account fall: automation is back.
  (Status: tx per account is rising, +48% on the previous quarter; fees per account are rising too, +96% in NEAR
  terms, so not triggered.)
* Intents volume falls back towards 2025 levels while the price rises: the price is not tracking this flow at all.
* A re-run shows a consistent positive lead (several adjacent positive lags outside the band for more than one
  metric): then usage *would* be a timing signal, contrary to our result.

## Limits

* NearBlocks counts an "active account" per signing/receiving account per day; it cannot separate people from bots.
* DefiLlama Intents data starts in December 2024, so its lead-lag test has about 100 weeks of data.
* Lead-lag scans 17 lags × 5 metrics = 85 tests; about 4 bars outside ±2/√n are expected by chance.
* YoY figures are means of 90 daily values; medians are in `docs/summary.json` (`median_pct_change`) and are
  quoted above where they differ materially.
* New accounts fell from about 135,000 to 22,000 a day and transactions from 3.5M to 0.9M a day between March and
  April 2026. A step that sharp looks like one large automated source stopping (or a change in how the data
  provider counts); most of the YoY drop in headline activity comes from it.
* The optional BigQuery cross-check (`--bq`) can measure heavy signers and cohort retention directly, but the
  dataset's upstream source (NEAR Lake) was deprecated in March 2026; the pipeline reports how fresh it is.
