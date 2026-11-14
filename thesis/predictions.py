"""Dated, checkable predictions (predictions.csv) and their status.

"automatic" predictions are scored by the build from the daily series once the data reaches the check date and
covers every day of the window the prediction names; until then they stay open.
"bigquery" predictions are scored by the build from the committed query results (data/bq/) once those hold the
month a prediction names, all of it: the account queries in sql/ have to be run again for it, by hand. Until then
they are reported as open. The file's SHA-256 is quoted in PREDICTIONS.md so later edits are visible.
"""
from __future__ import annotations

import hashlib
import math
import operator
import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd

from . import clients, metrics, population, segments, value

CSV = Path(__file__).resolve().parent.parent / "predictions.csv"
OPS = {">=": operator.ge, "<=": operator.le, "<": operator.lt, ">": operator.gt}


def sha256(path: Path | None = None) -> str:
    return hashlib.sha256((path or CSV).read_bytes()).hexdigest()


FROZEN_DATA_THROUGH = "2026-11-11"  # the last day of the daily data when predictions.csv was frozen
A5_CONTINUING = ("price_usd", "txns", "fees_usd", "intents_volume_usd")  # fees in NEAR are fees_usd over the price
A5_METRICS = ("returning_accounts", "active_accounts", "intents_volume_usd", "fees_near", "txns")
PLATEAU = ("2025-12", "2026-08")      # the nine complete months between the November 2025 spike and the September 2026 step
BUYBACK_PLATEAU = ("2026-03", "2026-08")  # complete months of the buyback programme before the step (it began 2026-02-23)


def adjacent_positive_leads(lead_vs_price: dict, same_sign_only: bool = True, positive_only: bool = False) -> int:
    """Metrics with two neighbouring positive lags (metric moves first) outside the noise band, with r of one sign.

    A positive lead is a positive lag: the metric moves first. Two neighbours that both move against the price are as
    much a timing signal as two that move with it, so A5 counts both signs; two neighbours of opposite signs are not one
    signal and are not counted. Until 2026-11-14 the build counted r > 0 only (`positive_only=True` gives that count).
    """
    n = 0
    for v in lead_vs_price.values():
        out = {o["lag_weeks"]: o["corr"] for o in v["outside_band"] if o["lag_weeks"] > 0 and (o["corr"] > 0 or not positive_only)}
        lags = sorted(out)
        n += any(b - a == 1 and (not same_sign_only or (out[a] > 0) == (out[b] > 0)) for a, b in zip(lags, lags[1:]))
    return n


metrics_sig = metrics._sig


def a5_chance_without_a_lead(metrics: int, lags: int = 8) -> float:
    """How often A5's rule fails when no metric leads price at all, were the lags' correlations independent and normal.

    A correlation is outside the band of 2 standard errors with probability erfc(2/√2), half of it on each side. A5
    fails when, for any metric, two neighbouring positive lags (1 to `lags` weeks) are outside it on the same side.
    The chain below carries the probability of no such pair so far, by where the last lag fell. Real weeks are not
    independent. Dependence can increase or decrease the rate: this is an illustration under an independent null,
    not a lower bound or an estimate of the actual false-positive rate.
    """
    side = 0.5 * math.erfc(2 / math.sqrt(2))
    inside, up, down = 1.0, 0.0, 0.0
    for _ in range(lags):
        inside, up, down = (inside + up + down) * (1 - 2 * side), (inside + down) * side, (inside + up) * side
    return metrics_sig(1 - (inside + up + down) ** metrics)  # erfc can differ in its last digit between C libraries


def baselines(daily: pd.DataFrame, fees: pd.DataFrame | None, census: pd.DataFrame | None,
              seg: pd.DataFrame | None = None) -> dict:
    """The reference levels the thresholds in predictions.csv are taken from. Nothing here is a chosen number."""
    out = {"intents_volume_plateau_top_usd": float(daily["intents_volume_usd"].resample("ME").mean().loc[PLATEAU[0]:PLATEAU[1]].max())}
    if fees is not None:
        out["buyback_plateau_top_usd"] = float(fees["holders_revenue"].resample("ME").sum().loc[BUYBACK_PLATEAU[0]:BUYBACK_PLATEAU[1]].max())
    if census is not None:
        core = census[~census["family"].isin(["kaiching", "tg", "sweat"])]
        g = core.groupby("month")[["txs", "relayed_txs", "accounts"]].sum()
        direct = (g["txs"] - g["relayed_txs"]).loc[PLATEAU[0]:PLATEAU[1]]
        out["core_self_paid_txs_plateau_top"] = float(direct.max())
        if len(direct):
            out["core_self_paid_txs_plateau_top_month"] = str(direct.idxmax())
            # Not a threshold, a disclosure: the top month of that range holds a one-off burst of dormant accounts.
            # Without them the top of the range is lower, so the published threshold of B2 is the harder one to hold.
            w = population.dormant_implicit(core).groupby("month")[["txs", "relayed_txs"]].sum().reindex(direct.index).fillna(0)
            calm = direct - (w["txs"] - w["relayed_txs"])
            out["core_self_paid_txs_plateau_top_without_dormant_implicit"] = float(calm.max())
            out["core_self_paid_txs_plateau_top_without_dormant_implicit_month"] = str(calm.idxmax())
    if seg is not None:
        out["regular_self_paying_accounts_low"] = float(segments.series(seg)["regular_accounts"].loc[PLATEAU[0]:PLATEAU[1]].min())
    return out


def step(daily: pd.DataFrame, fees: pd.DataFrame | None = None, census: pd.DataFrame | None = None,
         seg: pd.DataFrame | None = None, deletion_months: list[str] | None = None) -> dict:
    """The month after the reference range (September 2026): what stepped up, and what the NEAR price did meanwhile.

    Rule 1 of PREDICTIONS.md calls that month "the step". The price rose in the same month, so the step may be the
    rally itself. The figures are published side by side so that a reader sees both; nothing here is a threshold.
    """
    before = pd.Period(PLATEAU[1], "M")
    month = before + 1
    price = daily["price_usd"].dropna() if "price_usd" in daily else pd.Series(dtype=float)
    by_month = price.index.to_period("M") if len(price) else None
    if by_month is None or not (by_month == month).any() or price.index.max() < month.end_time.normalize():
        return {}  # the month is not in the data, or not complete yet
    in_month, since = price[by_month == month], price[by_month >= month]
    out = {"month": str(month), "month_before": str(before),
           "price_usd": {"first_day": float(in_month.iloc[0]), "last_day": float(in_month.iloc[-1]),
                         "mean_before": float(price[by_month == before].mean()), "mean": float(in_month.mean()),
                         "peak_since": {"date": str(since.idxmax().date()), "value": float(since.max())},
                         "latest": {"date": str(price.index.max().date()), "value": float(price.iloc[-1])}}}

    def pair(s: pd.Series) -> dict | None:
        s = s.copy()
        s.index = pd.PeriodIndex(s.index, freq="M")
        return {"before": float(s[before]), "month": float(s[month])} if before in s.index and month in s.index else None

    first, year = pd.Period(PLATEAU[0], "M"), 12
    out["reference_range"] = {"first": str(first), "last": str(before), "months": int((before - first).n + 1)}
    if "intents_volume_usd" in daily:
        monthly = daily["intents_volume_usd"].resample("ME").mean()
        monthly.index = monthly.index.to_period("M")
        out["intents_volume_usd_a_day"] = pair(monthly)
        days = daily["intents_volume_usd"].dropna()
        in_range = days[(days.index.to_period("M") >= first) & (days.index.to_period("M") <= before)]
        if out["intents_volume_usd_a_day"] and len(in_range) and first - 1 in monthly.index:
            # The level between the spike a year ago and the step: what "growth" has to be measured against once the
            # year-on-year base has moved through the ramp-up of autumn 2025.
            out["intents_volume_usd_a_day"].update({
                "range_mean": float(in_range.mean()), "range_low": float(monthly[first:before].min()),
                "range_top": float(monthly[first:before].max()),
                "month_before_range": {"month": str(first - 1), "value": float(monthly[first - 1])}})
    if fees is not None and not fees.empty:
        out["buyback_usd"] = pair(fees["holders_revenue"].resample("ME").sum())
    if census is not None:
        core = census[~census["family"].isin(["kaiching", "tg", "sweat"])].groupby("month")[["txs", "relayed_txs"]].sum()
        direct = core["txs"] - core["relayed_txs"]
        out["core_self_paid_txs"] = pair(direct)
        months = [str(m) for m in pd.period_range(first, before, freq="M")]
        earlier = [str(pd.Period(m, "M") - year) for m in months]
        if out["core_self_paid_txs"] and set(months) | set(earlier) <= set(direct.index):
            # The months of the range against the same months a year earlier: what the series did before the step.
            woke = population.dormant_implicit(census[~census["family"].isin(["kaiching", "tg", "sweat"])]).groupby("month")[["txs", "relayed_txs"]].sum()
            calm = direct - (woke["txs"] - woke["relayed_txs"]).reindex(direct.index).fillna(0)
            now, then = direct[months], direct[earlier]
            out["core_self_paid_txs"].update({
                "range_mean": float(now.mean()), "range_mean_a_year_earlier": float(then.mean()),
                "range_pct_change": float((now.mean() / then.mean() - 1) * 100),
                "range_pct_change_without_dormant_implicit": float((calm[months].mean() / calm[earlier].mean() - 1) * 100),
                "range_months_below_a_year_earlier": int((now.to_numpy() < then.to_numpy()).sum()),
                # an average below the year before is not every month below it: the months that were above, by how much
                "range_months_above_a_year_earlier": {m: float((now[m] / then[e] - 1) * 100)
                                                      for m, e in zip(months, earlier) if now[m] > then[e]}})
            # the same comparison by account family: which family the change of the whole series comes from
            core_rows = census[~census["family"].isin(["kaiching", "tg", "sweat"])]
            fam = (core_rows.assign(d=core_rows["txs"] - core_rows["relayed_txs"])
                   .pivot_table(index="month", columns="family", values="d", aggfunc="sum").fillna(0))
            woke_fam = (population.dormant_implicit(core_rows).assign(d=lambda x: x["txs"] - x["relayed_txs"])
                        .groupby("month")["d"].sum().reindex(fam.index).fillna(0))
            by_family = {}
            for f in fam.columns:
                a_, b_ = fam.loc[months, f], fam.loc[earlier, f]
                by_family[f] = {"range_pct_change": float((a_.mean() / b_.mean() - 1) * 100) if b_.mean() else float("nan"),
                                "range_change_txs": int(a_.sum() - b_.sum()),
                                "range_months_below_a_year_earlier": int((a_.to_numpy() < b_.to_numpy()).sum())}
            if "implicit" in fam.columns:
                a_, b_ = (fam["implicit"] - woke_fam)[months], (fam["implicit"] - woke_fam)[earlier]
                by_family["implicit"]["range_pct_change_without_dormant_implicit"] = (
                    float((a_.mean() / b_.mean() - 1) * 100) if b_.mean() else float("nan"))
            # Inside each family, by age and by activity the month before: who sent the transactions that changed. A
            # fall in accounts under a year old that is not made up among the older ones fits a smaller inflow; a rise
            # in one age class matched by a fall in the class below fits one cohort growing older. Class totals, not accounts.
            young = core_rows["age"].isin(["m0", "lt30", "lt1y"])
            part = {"under_a_year": young,
                    "older_active_the_month_before": ~young & (core_rows["prev_month"] == "returning"),
                    "older_not_active_the_month_before": ~young & (core_rows["prev_month"] == "not_returning")}
            d_rows = core_rows["txs"] - core_rows["relayed_txs"]
            for f in fam.columns:
                is_f = core_rows["family"] == f
                cut = {}
                for name, mask in [*part.items(), *((f"age_{a}", core_rows["age"] == a) for a in population.AGES)]:
                    x = d_rows[is_f & mask].groupby(core_rows["month"]).sum()
                    a_, b_ = float(x.reindex(months).fillna(0).sum()), float(x.reindex(earlier).fillna(0).sum())
                    cut[name] = {"range": int(a_), "a_year_earlier": int(b_), "change": int(a_ - b_),
                                 "pct_change": float((a_ / b_ - 1) * 100) if b_ else float("nan")}
                by_family[f]["by_age_and_activity"] = cut
            out["core_self_paid_txs"]["range_by_family"] = by_family
            out["core_self_paid_txs"]["range_change_txs"] = int(now.sum() - then.sum())
            # The months that were above the year before: where their base months stood among the months of the base,
            # and among every month of the series, lowest first; and the price month by month across the range.
            base = then.sort_values()
            every = direct[[m for m in direct.index if str(first - year) <= m <= str(before)]].sort_values()
            out["core_self_paid_txs"]["base_of_the_months_above"] = {
                m: {"base_month": e, "base": int(then[e]), "rank_lowest_first_among_base_months": int(list(base.index).index(e)) + 1,
                    "base_months": int(len(base)), "rank_lowest_first_among_all_months": int(list(every.index).index(e)) + 1,
                    "all_months": int(len(every))}
                for m, e in zip(months, earlier) if now[m] > then[e]}
            if len(price):
                pm = price.groupby(price.index.to_period("M")).mean()
                out["core_self_paid_txs"]["price_usd_by_month"] = {m: float(pm[pd.Period(m, "M")]) for m in months
                                                                    if pd.Period(m, "M") in pm.index}
            if seg is not None and deletion_months:
                # Mass deletions are paid by the accounts deleted, so a month of them sits in the self-paid series. The
                # payer table counts self-paying accounts outside the app namespaces with exactly one transaction; in a
                # month of deletions the excess over its median month is the size of the one-off. The table starts later
                # than the base year, so this can be taken out of the range only, and is published as one end.
                one = seg[(seg["namespace"] == "rest") & (seg["payer"] == "self") & (seg["txs_in_month"].astype(str) == "1")]
                one = one.groupby("month")["accounts"].sum()
                usual = float(one.median()) if len(one) else float("nan")
                hit = {m: {"accounts": int(one[m]), "median_month": usual, "above_the_median_month": int(one[m] - usual),
                           "share_of_the_month": float((one[m] - usual) / direct[m])}
                       for m in months if m in deletion_months and m in one.index and one[m] > usual}
                # February's burst is the dormant-implicit filter's: listed, but not taken out a second time here
                feb = out["core_self_paid_txs"].get("range_pct_change_without_dormant_implicit")
                dormant_peak = (woke["txs"] - woke["relayed_txs"]).reindex(months).fillna(0).idxmax()
                take = {m: v for m, v in hit.items() if m != dormant_peak}
                less = now.copy()
                for m, v in take.items():
                    less[m] -= v["above_the_median_month"]
                out["core_self_paid_txs"]["deletions_in_the_range"] = {
                    "months": hit, "taken_out": list(take), "left_to_the_dormant_filter": [m for m in hit if m not in take],
                    "base_months_with_deletions": [m for m in earlier if m in deletion_months],
                    "payer_table_first_month": str(one.index.min()) if len(one) else None,
                    "range_pct_change_without_them": float((less.mean() / then.mean() - 1) * 100)}
    if seg is not None:
        s = segments.series(seg)
        out["regular_self_paying_accounts"] = pair(s["regular_accounts"])
        out["heavy_self_paying_accounts"] = pair(s["heavy_accounts"])
    return {k: v for k, v in out.items() if v is not None}


def _window(s: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series | None:
    """The values of every day from start to end, or None while a day is missing.

    The daily table is driven by NearBlocks; a DefiLlama series can end a few days earlier (a late update, or the
    saved copy used during an outage), or miss a day in the middle. A prediction is not scored on part of its window.
    """
    w = s.reindex(pd.date_range(start, end, freq="D"))
    return None if not np.isfinite(w).all() else w


def _decimal_total(w: pd.Series) -> Decimal:
    """Sum decimal observations without a floating-point overshoot at a strict threshold."""
    return sum((Decimal(str(x)) for x in w), Decimal(0))


def _decimal_mean(w: pd.Series) -> float:
    """Average decimal observations without summation noise moving an exact threshold equality."""
    return float(_decimal_total(w) / len(w))


def _measure(metric: str, on: pd.Timestamp, daily: pd.DataFrame, fees: pd.DataFrame | None) -> float | None:
    """What a prediction is scored on, from data up to its check date only; None while that data is incomplete."""
    d = daily.loc[:on]
    if metric in ("intents_volume_7d_mean_usd", "intents_volume_month_mean_usd"):
        start = on - pd.Timedelta(days=6) if metric == "intents_volume_7d_mean_usd" else on.replace(day=1)
        w = _window(d["intents_volume_usd"], start, on)
        return None if w is None else _decimal_mean(w)
    if metric == "metrics_with_adjacent_positive_leads":
        # Require an actual weekly change for every completed week after the snapshot. This checks all seven days
        # and the preceding week needed by the difference. The unfinished week containing the check date is excluded.
        # The two series that end with /v1 are still scored as they stand, as PREDICTIONS.md says.
        first = (pd.Timestamp(FROZEN_DATA_THROUGH) + pd.Timedelta(days=1)).to_period("W-SUN").end_time.normalize()
        weeks = pd.date_range(first, on, freq="W-SUN")
        if not len(weeks) or any(c not in d for c in (*A5_CONTINUING, "active_accounts", "new_accounts")):
            return None
        derived = metrics.add_derived(d)
        for c in A5_CONTINUING:
            have = metrics.weekly_log_diff(derived["fees_near" if c == "fees_usd" else c],
                                           positive_only=(c == "price_usd")).index
            if not set(weeks) <= set(have):
                return None
        leads = metrics.summarize(d)["lead_vs_price"]
        # A successful download can still truncate a series' old history. The general scan omits short series;
        # A5 must not turn that omission (or an undefined correlation) into evidence of no lead. Its family stays
        # the five metrics present when the prediction was frozen, including the two that later stop with /v1.
        if not set(A5_METRICS) <= set(leads) or any(not np.isfinite(leads[c]["corr"]) for c in A5_METRICS):
            return None
        return float(adjacent_positive_leads({c: leads[c] for c in A5_METRICS}))
    if fees is None or fees.empty:
        return None
    f = fees.loc[:on]
    if metric == "buyback_month_usd":
        w = _window(f["holders_revenue"], on.replace(day=1), on)
        return None if w is None else float(_decimal_total(w))
    if metric == "buyback_coverage_90d":
        start = on - pd.Timedelta(days=89)
        if any(_window(f[c], start, on) is None for c in f.columns):
            return None  # a day without fee data inside the 90 days: wait for it, do not score on part of the window
        # The other side of the ratio: the mean price of the 90 days and the supply on the day before them and on the
        # last day. A missing price would leave a mean of fewer days, a missing supply the value of an earlier day.
        if "price_usd" not in d or _window(d["price_usd"], start, on) is None:
            return None
        if (d["price_usd"].reindex(pd.date_range(start, on)) <= 0).any():
            return None
        if "total_supply_yocto" not in d or _window(d["total_supply_yocto"], start - pd.Timedelta(days=1), start - pd.Timedelta(days=1)) is None \
                or _window(d["total_supply_yocto"], on, on) is None:
            return None
        v = value.summarize(d, f)
        # Two measurements of one flow: the ratio of USD (as the threshold was written) and the ratio of NEAR (each
        # day's buyback at that day's price over the new NEAR). From 2026-11-14 A4 is scored on both and left open
        # when they give different verdicts (PREDICTIONS.md).
        return (float(v["buyback_coverage_of_new_supply"]), float(v["buyback_coverage_in_near"])) if v else None
    return None


# What the build can measure. An "automatic" metric is read from the daily series (_measure). A "bigquery" metric
# names what it counts and the month or months it covers, regular_self_paying_accounts_2027_01 or
# core_self_paid_txs_mean_2026_11_to_2027_01, and is read from the committed query results (_measure_committed).
AUTOMATIC = ("intents_volume_7d_mean_usd", "intents_volume_month_mean_usd", "metrics_with_adjacent_positive_leads",
             "buyback_month_usd", "buyback_coverage_90d")
COMMITTED = ("regular_self_paying_accounts", "core_self_paid_txs_mean", "accounts_for_half_of_txs", "reward_minus_finance_tx_share")
BQ_METRIC = re.compile(r"^(?P<name>[a-z_]+?)_(?P<first>\d{4}_\d{2})(?:_to_(?P<last>\d{4}_\d{2}))?$")


def holds_the_whole_month(table_txs: float, month: str, daily: pd.DataFrame | None) -> bool:
    """False when a query result is short of the aggregator's transaction count for a month by a day or more.

    A query's end date does not establish that its source held every day: it may have been run early, or its source
    may have missing records. NearBlocks counts the same transactions day by day, so every query result is checked
    against it, in addition to the census scan's end date (population.QUERY_END). A result that misses a day is short
    by at least the month's quietest day, so that is the line; no tolerance is chosen. Without a daily count for every
    day of the month there is nothing to compare with, so nothing shows that the result holds the whole month:
    it is not scored (False) until the daily series has every day of it. After /v1 is switched off the count goes on
    from v3 (thesis/sources.py).
    """
    if daily is None or "txns" not in daily:
        return False
    period = pd.Period(month, "M")
    days = daily["txns"].reindex(pd.date_range(period.start_time, period.end_time.normalize(), freq="D"))
    if not np.isfinite(days).all() or not np.isfinite(table_txs):
        return False
    return float(days.sum() - table_txs) < float(days.min())


@dataclass(frozen=True)
class LowerBound:
    value: int


def _measure_committed(p: dict, census: pd.DataFrame | None, seg: pd.DataFrame | None, top: dict | None,
                       daily: pd.DataFrame | None = None) -> float | tuple[float, float] | LowerBound | None:
    """A "bigquery" prediction measured from the committed query results; None while they do not hold its months.

    The queries cover whole calendar months and are run by hand: sql/payer_frequency.sql for the frequency classes,
    sql/account_age.sql for the census (with QUERY_END in thesis/population.py), sql/top_accounts.sql for the largest
    accounts and the apps. Once a result that holds the named month is committed, the build scores the prediction
    with the same definitions its threshold was taken from. Every month must pass the comparison with the daily series
    (holds_the_whole_month); the census additionally requires QUERY_END to reach the month's last day.
    B4 returns both bounds: the contracts outside the top 40 leave a range, not an exact measurement.
    """
    m = BQ_METRIC.match(str(p["metric"]))
    if not m or m["name"] not in COMMITTED:
        return None
    first, last = m["first"].replace("_", "-"), (m["last"] or m["first"]).replace("_", "-")
    months = [str(x) for x in pd.period_range(first, last, freq="M")]
    name = m["name"]
    if name == "regular_self_paying_accounts" and seg is not None:
        regular = segments.series(seg)["regular_accounts"]
        if not set(months) <= set(regular.index):
            return None
        counted = seg.groupby("month")["txs"].sum()
        if not all(holds_the_whole_month(counted[x], x, daily) for x in months):
            return None  # the query was run before the month ended: wait for a run that holds all of it
        return float(regular[months].mean())
    if name == "core_self_paid_txs_mean" and census is not None:
        if not set(months) <= set(population.complete_months(census)):
            return None  # a month the scan has not finished is not a month
        counted = census.groupby("month")["txs"].sum()
        if not all(holds_the_whole_month(counted[x], x, daily) for x in months):
            return None  # an end date alone cannot detect missing records inside a completed month
        core = census[~census["family"].isin(population.REWARD_FAMILIES)].groupby("month")[["txs", "relayed_txs"]].sum()
        return float((core["txs"] - core["relayed_txs"]).reindex(months, fill_value=0).mean())
    if top and len(months) == 1 and {"via", "conc"} <= set(top.get(months[0], {})):
        month = top[months[0]]
        c = month["conc"]
        if not holds_the_whole_month(c["txs"], months[0], daily):
            return None  # the same for the largest accounts and the apps
        if name == "accounts_for_half_of_txs":
            if c["heavy_txs"] >= 0.5 * c["txs"]:
                return float(c["n50"])
            # The query ranks only the accounts with 1,000 or more transactions. If together they send less than
            # half, more accounts than that whole group are needed. This is a lower bound, so it is used only when
            # it already decides the prediction.
            return LowerBound(clients.half_txs_lower_bound(c))
        if name == "reward_minus_finance_tx_share":
            apps = clients.by_app(month)
            reward, finance = (sum(int(apps.get(a, 0)) for a in group) for group in (clients.REWARD_APPS, clients.FINANCE_APPS))
            # The groups' contracts outside the month's 40 largest are not in the count, and each can have received up to
            # the smallest listed entry. Return both bounds for scoring and display; neither is an exact count.
            low = (reward - finance - clients.outside_the_40(month, clients.FINANCE_APPS)["transactions_at_most"]) / c["txs"]
            high = (reward - finance + clients.outside_the_40(month, clients.REWARD_APPS)["transactions_at_most"]) / c["txs"]
            return low, high
    return None


def evaluate(daily: pd.DataFrame, fees: pd.DataFrame | None, path: Path | None = None, census: pd.DataFrame | None = None,
             seg: pd.DataFrame | None = None, top: dict | None = None) -> dict | None:
    path = path or CSV
    if not path.exists():
        return None
    last = daily.index.max()
    rows = []
    for p in pd.read_csv(path, dtype={"threshold": float}).to_dict("records"):
        on = pd.Timestamp(p["check_on"])
        status, measured = "open", None
        if last >= on:
            if p["scoring"] == "bigquery":
                measured, waiting = _measure_committed(p, census, seg, top, daily), "open (needs the census query for that month)"
            else:
                measured, waiting = _measure(p["metric"], on, daily, fees), "open (waiting for complete data)"
            if isinstance(measured, LowerBound):
                # A lower bound can refute an upper limit or establish a lower limit; it cannot give an exact count.
                passes = OPS[p["operator"]](measured.value, p["threshold"])
                decided = (p["operator"] in ("<", "<=") and not passes) or (p["operator"] in (">", ">=") and passes)
                status = ("held" if passes else "failed") if decided else "open (undecided: only a lower bound is known)"
                rows.append({**p, "status": status, "measured": None, "measured_lower_bound": measured.value})
                continue
            if measured is not None and not np.isfinite(measured).all():
                measured = None  # neither a scalar nor a pair of measurements can be scored while undefined
            if isinstance(measured, tuple):
                holds = [OPS[p["operator"]](end, p["threshold"]) for end in measured]
                why = ("the ratio in USD and the ratio in NEAR give different verdicts" if p["metric"] == "buyback_coverage_90d"
                       else "the group's contracts outside the 40 largest could reverse it")
                status = ("held" if holds[0] else "failed") if holds[0] == holds[1] else f"open (undecided: {why})"
                rows.append({**p, "status": status, "measured": None, "measured_range": list(measured)})
                continue
            if measured is None:
                status = waiting
            else:
                status = "held" if OPS[p["operator"]](measured, p["threshold"]) else "failed"
        rows.append({**p, "status": status, "measured": measured})
    return {"sha256": sha256(path), "data_through": str(last.date()), "items": rows}
