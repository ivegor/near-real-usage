"""Dated, checkable predictions (predictions.csv) and their status.

"automatic" predictions are scored by the build from the daily series once the data reaches the check date and
covers every day of the window the prediction names; until then they stay open.
"bigquery" predictions are scored by the build from the committed query results (data/bq/) once those hold the
month a prediction names, all of it: the account queries in sql/ have to be run again for it, by hand. Until then
they are reported as open. The file's SHA-256 is quoted in PREDICTIONS.md so later edits are visible.
"""
from __future__ import annotations

import hashlib
import operator
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import clients, metrics, population, segments, value

CSV = Path(__file__).resolve().parent.parent / "predictions.csv"
OPS = {">=": operator.ge, "<=": operator.le, "<": operator.lt, ">": operator.gt}


def sha256(path: Path | None = None) -> str:
    return hashlib.sha256((path or CSV).read_bytes()).hexdigest()


PLATEAU = ("2025-12", "2026-08")      # the nine complete months between the November 2025 spike and the September 2026 step
BUYBACK_PLATEAU = ("2026-03", "2026-08")  # complete months of the buyback programme before the step (it began 2026-02-23)


def adjacent_positive_leads(lead_vs_price: dict) -> int:
    """Metrics with two neighbouring positive lags (metric moves first) outside the noise band, both with r > 0."""
    n = 0
    for v in lead_vs_price.values():
        lags = sorted(o["lag_weeks"] for o in v["outside_band"] if o["lag_weeks"] > 0 and o["corr"] > 0)
        n += any(b - a == 1 for a, b in zip(lags, lags[1:]))
    return n


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
         seg: pd.DataFrame | None = None) -> dict:
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
            out["core_self_paid_txs"]["range_by_family"] = by_family
            out["core_self_paid_txs"]["range_change_txs"] = int(now.sum() - then.sum())
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
    return None if w.isna().any() else w


def _measure(metric: str, on: pd.Timestamp, daily: pd.DataFrame, fees: pd.DataFrame | None) -> float | None:
    """What a prediction is scored on, from data up to its check date only; None while that data is incomplete."""
    d = daily.loc[:on]
    if metric in ("intents_volume_7d_mean_usd", "intents_volume_month_mean_usd"):
        start = on - pd.Timedelta(days=6) if metric == "intents_volume_7d_mean_usd" else on.replace(day=1)
        w = _window(d["intents_volume_usd"], start, on)
        return None if w is None else float(w.mean())
    if metric == "metrics_with_adjacent_positive_leads":
        return float(adjacent_positive_leads(metrics.summarize(d)["lead_vs_price"]))
    if fees is None or fees.empty:
        return None
    f = fees.loc[:on]
    if metric == "buyback_month_usd":
        w = _window(f["holders_revenue"], on.replace(day=1), on)
        return None if w is None else float(w.sum())
    if metric == "buyback_coverage_90d":
        start = on - pd.Timedelta(days=89)
        if any(_window(f[c], start, on) is None for c in f.columns):
            return None  # a day without fee data inside the 90 days: wait for it, do not score on part of the window
        v = value.summarize(d, f)
        return float(v["buyback_coverage_of_new_supply"]) if v else None
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

    The census says where its scan stopped (population.QUERY_END). The other two queries name whole months, so their
    result is partial only when the query was run before the month ended, and the result itself does not say so. The
    aggregator does: NearBlocks counts the same transactions day by day, and the two sources agree to a few hundred
    transactions in a month (population.totals_check). A result that misses a day is short by at least the month's
    quietest day, so that is the line; no tolerance is chosen. Without a daily count for every day of the month there
    is nothing to compare with, and the result is taken as it is.
    """
    if daily is None or "txns" not in daily:
        return True
    period = pd.Period(month, "M")
    days = daily["txns"].reindex(pd.date_range(period.start_time, period.end_time.normalize(), freq="D"))
    if days.isna().any():
        return True
    return float(days.sum() - table_txs) < float(days.min())


def _measure_committed(p: dict, census: pd.DataFrame | None, seg: pd.DataFrame | None, top: dict | None,
                       daily: pd.DataFrame | None = None) -> float | None:
    """A "bigquery" prediction measured from the committed query results; None while they do not hold its months.

    The queries cover whole calendar months and are run by hand: sql/payer_frequency.sql for the frequency classes,
    sql/account_age.sql for the census (with QUERY_END in thesis/population.py), sql/top_accounts.sql for the largest
    accounts and the apps. Once a result that holds the named month is committed, the build scores the prediction
    with the same definitions its threshold was taken from. A month counts only when the result holds all of it: for
    the census that is QUERY_END, for the other two results the comparison with the daily series (holds_the_whole_month).
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
        core = census[~census["family"].isin(population.REWARD_FAMILIES)].groupby("month")[["txs", "relayed_txs"]].sum()
        return float((core["txs"] - core["relayed_txs"])[months].mean())
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
            at_least = c["heavy_actors"] + 1
            return float(at_least) if at_least >= p["threshold"] else None
        if name == "reward_minus_finance_tx_share":
            apps = clients.by_app(month)
            reward, finance = (sum(int(apps.get(a, 0)) for a in group) for group in (clients.REWARD_APPS, clients.FINANCE_APPS))
            return (reward - finance) / c["txs"]
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
            if measured is not None and not np.isfinite(measured):
                measured = None  # an empty or undefined measurement is not a miss
            if measured is None:
                status = waiting
            else:
                status = "held" if OPS[p["operator"]](measured, p["threshold"]) else "failed"
        rows.append({**p, "status": status, "measured": measured})
    return {"sha256": sha256(path), "data_through": str(last.date()), "items": rows}
