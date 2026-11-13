"""Autumn 2026 in half-months: what stepped up, on which day, and what has come back down since.

The predictions call September 2026 "the step" (predictions.PLATEAU ends in August). Read month by month, everything
seems to step up together with the price. Read by half-months, the daily series tell two events apart, and the keyless
sample says whose transactions moved. Nothing here is a chosen date or line:

* half-months are calendar halves, days 1 to 15 and 16 to the end of the month;
* the day Intents volume stepped up: its 7-day mean has stayed above the top of the predictions' reference range (the
  threshold of A1 and A2) since the day after the last day on which it was not; the step day is the largest one-day
  rise of the daily volume in the seven days that end on that first day;
* the reference is the half-months after the largest one-day fall of the daily transactions (KaiChing stopping,
  population.largest_daily_fall) and before the half-month of that step day, so that neither the reward app that left
  nor the step itself is in it; a later half-month is "above" when it is above the highest of them.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import clients

FIRST_HALF_ENDS = 15  # day of the month on which the first half ends
NAMESPACES = (".kaiching", ".tg", ".sweat")
COLUMNS = {  # what is averaged per day in each half-month
    "txns": "transactions", "fees_near": "network fees in NEAR", "gas_tgas": "gas used, in Tgas",
    "intents_volume_usd": "NEAR Intents volume in USD", "buyback_usd": "buybacks in USD", "buyback_near": "buybacks in NEAR",
    "price_usd": "NEAR price", "deleted_accounts": "deleted accounts", "active_accounts": "signers (active accounts)",
}


def halves(first: pd.Timestamp, last: pd.Timestamp) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """Calendar half-months from the one holding `first` to the one holding `last`, the last one cut at `last`."""
    out = []
    for m in pd.period_range(first, last, freq="M"):
        start, end = m.start_time, m.end_time.normalize()
        mid = start + pd.Timedelta(days=FIRST_HALF_ENDS - 1)
        for a, b in ((start, mid), (mid + pd.Timedelta(days=1), end)):
            if first <= a <= last:
                out.append((a, min(b, last)))
    return out


def _label(a: pd.Timestamp, b: pd.Timestamp) -> str:
    return f"{a.date()}..{b.date()}"


def table(daily: pd.DataFrame, fees: pd.DataFrame | None, first: str, last: pd.Timestamp) -> pd.DataFrame:
    """Per-day means of the daily series in each half-month from `first` to `last`."""
    d = pd.DataFrame(index=daily.index)
    for c in ("txns", "intents_volume_usd", "price_usd", "deleted_accounts", "active_accounts"):
        if c in daily:
            d[c] = daily[c]
    price = daily["price_usd"].where(daily["price_usd"] > 0)
    if "fees_usd" in daily:
        d["fees_near"] = daily["fees_usd"] / price
    if "gas_used" in daily:
        d["gas_tgas"] = daily["gas_used"] / 1e12
    if fees is not None:
        d["buyback_usd"] = fees["holders_revenue"].reindex(d.index)
        d["buyback_near"] = d["buyback_usd"] / price
    rows = {}
    for a, b in halves(pd.Timestamp(first), last):
        part = d.loc[a:b]
        rows[_label(a, b)] = {**part.mean().to_dict(), "days": int(len(part))}
    return pd.DataFrame(rows).T


def intents_step(daily: pd.DataFrame, fees: pd.DataFrame | None, top: float, after: str) -> dict | None:
    """The day Intents volume stepped up to its autumn level, by the rule in the module docstring."""
    vol = daily["intents_volume_usd"].dropna()
    week = vol.rolling(7).mean().loc[after:]
    not_above = week[week <= top]
    if not_above.empty or not_above.index.max() >= week.index.max():
        return None  # the weekly mean is at or below the line today: there is no level that holds
    since = not_above.index.max() + pd.Timedelta(days=1)
    seven = vol.loc[since - pd.Timedelta(days=6):since]
    rise = seven.diff().dropna()
    day = rise.idxmax()
    before = day - pd.Timedelta(days=1)
    month = vol[vol.index.to_period("M") == day.to_period("M")]
    out = {"line": float(top), "weekly_mean_above_it_since": str(since.date()), "last_day_at_or_below": str(not_above.index.max().date()),
           "lowest_weekly_mean_since": float(week.loc[since:].min()), "day": str(day.date()),
           "volume": {"day_before": float(vol[before]), "day": float(vol[day])},
           "price_usd": {"day": float(daily["price_usd"][day])},
           "month": str(day.to_period("M")), "days_of_the_month_from_it": int((month.index >= day).sum()),
           "share_of_the_month_volume_from_it": float(month[month.index >= day].sum() / month.sum())}
    if fees is not None:
        bb = fees["holders_revenue"].dropna()
        bb = bb[bb.index.to_period("M") == day.to_period("M")]
        if bb.sum():
            out["share_of_the_month_buybacks_from_it"] = float(bb[bb.index >= day].sum() / bb.sum())
        start = vol.index[vol.index.to_period("M") == day.to_period("M")].min()
        out["per_day_before_and_from_it"] = {
            "volume_usd": [float(vol.loc[start:before].mean()), float(vol.loc[day:month.index.max()].mean())],
            "buyback_usd": [float(fees["holders_revenue"].loc[start:before].mean()), float(fees["holders_revenue"].loc[day:month.index.max()].mean())]}
    return out


def sample_halves(sample: pd.DataFrame, window: dict, daily: pd.DataFrame, seed: int) -> list[dict]:
    """The keyless sample of the recent window by half-months: whose transactions moved.

    The window starts in mid-August, so its days in that month are one period; after that, calendar half-months.
    Self-paid outside the namespaces is the census's core series measured on the sample: a transaction not submitted by
    a relayer, from an account outside `.kaiching`, `.tg` and `.sweat`.
    """
    start, end = pd.Timestamp(window["start"]), pd.Timestamp(window["end"])
    first_month_end = start.to_period("M").end_time.normalize()
    periods = [(start, first_month_end)] if start.day > 1 else []
    periods += [p for p in halves(first_month_end + pd.Timedelta(days=1), end)]
    signer = sample["signer"].astype(str)
    self_paid = ~sample["relayed"].astype(bool) & ~signer.str.endswith(NAMESPACES) & ~signer.isin([n[1:] for n in NAMESPACES])
    groups = {"exchange": set(clients.APPS[clients.EXCHANGE]),
              "finance": {v for app in clients.FINANCE_APPS for v in clients.APPS[app]}}
    return clients.sampled_periods(sample, "recent", periods, daily, groups, seed,
                                   extra={"self_paid_outside_namespaces": self_paid})


def summarize(daily: pd.DataFrame, fees: pd.DataFrame | None, plateau: tuple[str, str], fall_date: str | None,
              line: float | None, sample: pd.DataFrame | None = None, windows: dict | None = None, seed: int = 0,
              census_per_day: dict | None = None) -> dict | None:
    """The half-months of the reference range after the fall and every half-month since, and the two dated events."""
    last = daily.index.max()
    step_month = pd.Period(plateau[1], "M") + 1
    if last < step_month.end_time.normalize() or not fall_date:
        return None
    fall = pd.Timestamp(fall_date)
    # the first half-month that starts after the fall day
    first = (fall.to_period("M").start_time + pd.Timedelta(days=FIRST_HALF_ENDS) if fall.day <= FIRST_HALF_ENDS
             else (fall.to_period("M") + 1).start_time)
    t = table(daily, fees, str(first.date()), last)
    step = intents_step(daily, fees, line, plateau[0]) if line is not None and "intents_volume_usd" in daily else None
    reference_end = pd.Period(plateau[1], "M").end_time.normalize()
    if step:  # the reference stops before the half-month in which Intents volume stepped up
        day = pd.Timestamp(step["day"])
        reference_end = min(reference_end, next(a for a, b in halves(first, last) if a <= day <= b) - pd.Timedelta(days=1))
    ref = t[[pd.Timestamp(k.split("..")[1]) <= reference_end for k in t.index]]
    after = t[[pd.Timestamp(k.split("..")[0]) > reference_end for k in t.index]]
    out: dict = {"rule": "calendar half-months (1-15, 16-end); reference: the half-months after the largest one-day fall of "
                         "transactions and before the one in which Intents volume stepped up; above: above the highest of them",
                 "reference": {"from": ref.index[0].split("..")[0], "through": ref.index[-1].split("..")[1],
                               "top": {c: float(ref[c].max()) for c in COLUMNS if c in ref},
                               "top_half": {c: str(ref[c].idxmax()) for c in COLUMNS if c in ref}},
                 "half_months": {k: {c: (float(v[c]) if pd.notna(v[c]) else None) for c in [*COLUMNS, "days"] if c in v}
                                 for k, v in t.iterrows()}}
    out["above_reference_top"] = {c: [k for k, v in after[c].items() if v > out["reference"]["top"][c]]
                                  for c in COLUMNS if c in after and c not in ("price_usd", "deleted_accounts", "active_accounts")}
    if step:
        out["intents_step"] = step
    if sample is not None and windows and "recent" in windows:
        cells = sample_halves(sample, windows["recent"], daily, seed)
        out["sample_halves"] = {f"{c['from']}..{c['through']}": c for c in cells}
        if census_per_day:
            # the half-months of the sample against the census's full count for the same calendar month: two halves,
            # weighted by their days, should give the month
            check = {}
            for m, full in census_per_day.items():
                parts = [c for c in cells if c["from"][:7] == m and c["through"][:7] == m]
                if len(parts) == 2 and sum(c["days"] for c in parts) == pd.Period(m, "M").days_in_month:
                    est = sum(c["self_paid_outside_namespaces"]["per_day"] * c["days"] for c in parts) / pd.Period(m, "M").days_in_month
                    check[m] = {"sample_halves": float(est), "census": float(full), "ratio": float(est / full) if full else float("nan")}
            out["sample_halves_vs_census"] = check
    return out
