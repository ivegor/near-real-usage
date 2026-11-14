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

from . import clients, metrics

FIRST_HALF_ENDS = 15  # day of the month on which the first half ends
NAMESPACES = (".kaiching", ".tg", ".sweat")
COLUMNS = {  # what is averaged per day in each half-month
    "txns": "transactions", "txns_less_deleted": "scenario: transactions minus deleted accounts (one transaction per deletion assumed)",
    "fees_near": "network fees in NEAR", "gas_tgas": "gas used, in Tgas",
    "intents_volume_usd": "NEAR Intents volume in USD", "buyback_usd": "buybacks in USD", "buyback_near": "buybacks in NEAR",
    "price_usd": "NEAR price", "deleted_accounts": "deleted accounts", "active_accounts": "signers (active accounts)",
    "transfer_volume_near": "native NEAR transfer volume, in NEAR", "new_contracts": "new contracts",
    "active_contracts": "NearBlocks' active_contracts (not defined in its reply; it tracks users behind relayers)",
}
NOT_COMPARED = ("price_usd", "deleted_accounts", "active_accounts", "active_contracts")  # context, not activity with a top


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


def table(daily: pd.DataFrame, fees: pd.DataFrame | None, first: str, last: pd.Timestamp, stat: str = "mean") -> pd.DataFrame:
    """Per-day means (or medians, `stat="median"`) of the daily series in each half-month from `first` to `last`.

    A mean of fifteen days can rest on one or two of them; the median day says whether the half-month as a whole moved.
    Each metric needs every calendar day of the labelled span; a gap is not a shorter half-month.
    """
    d = series(daily, fees)
    rows = {}
    for a, b in halves(pd.Timestamp(first), last):
        part = d.reindex(pd.date_range(a, b, freq="D"))
        aggregate = getattr(part, stat)().where(part.count() == len(part))
        rows[_label(a, b)] = {**aggregate.to_dict(), "days": int(len(part))}
    return pd.DataFrame(rows).T


def series(daily: pd.DataFrame, fees: pd.DataFrame | None) -> pd.DataFrame:
    """The daily series of COLUMNS, one row a day."""
    d = pd.DataFrame(index=daily.index)
    for c in ("txns", "intents_volume_usd", "price_usd", "deleted_accounts", "active_accounts", "new_contracts", "active_contracts"):
        if c in daily:
            d[c] = daily[c]
    if "deleted_accounts" in daily:
        # A conditional scenario, not a count of transactions without deletions: one transaction may create
        # several deletion receipts, on different days. Unknown deletions cannot be assumed to be zero.
        d["txns_less_deleted"] = daily["txns"] - daily["deleted_accounts"]
    price = daily["price_usd"].where(np.isfinite(daily["price_usd"]) & (daily["price_usd"] > 0))
    d["price_usd"] = price
    if "fees_usd" in daily:
        d["fees_near"] = daily["fees_usd"] / price
    if "gas_used" in daily:
        d["gas_tgas"] = daily["gas_used"] / 1e12
    if "transfer_volume_usd" in daily:  # NearBlocks' native transfer volume, kept in USD by the parser: back into NEAR
        d["transfer_volume_near"] = daily["transfer_volume_usd"] / price
    if fees is not None:
        d["buyback_usd"] = fees["holders_revenue"].reindex(d.index)
        d["buyback_near"] = d["buyback_usd"] / price
    return d.replace([np.inf, -np.inf], np.nan)


def one_day_moves(s: pd.Series, first: pd.Timestamp, last: pd.Timestamp) -> dict:
    """Per calendar month from `first` to `last`: the largest one-day rise and fall of a daily series (in percent of
    the day before), with the values either side. Missing days leave both neighbouring changes unknown."""
    s = s.reindex(pd.date_range(first - pd.Timedelta(days=1), last, freq="D"))
    out = {}
    for m in pd.period_range(first, last, freq="M"):
        part = s.loc[max(first, m.start_time) - pd.Timedelta(days=1):min(last, m.end_time.normalize())]
        move = (part / part.shift(1) - 1).iloc[1:].replace([np.inf, -np.inf], np.nan).dropna()
        if move.empty:
            continue
        row = {}
        for name, day in (("rise", move.idxmax()), ("fall", move.idxmin())):
            before = day - pd.Timedelta(days=1)
            row[name] = {"date": str(day.date()), "day_before": float(part[before]), "day": float(part[day]),
                         "pct_change": float(move[day] * 100)}
        out[str(m)] = row
    return out


def _price_after(price: pd.Series, day: pd.Timestamp) -> dict | None:
    """The price on the step day, its highest day in the seven days from it (the span of the weekly mean above), and the
    first day it stood at twice the step day's price: did the step come before the price moved, or with it?"""
    price = price.asfreq("D").where(np.isfinite(price) & (price > 0))
    week = price.reindex(pd.date_range(day, day + pd.Timedelta(days=6)))
    if week.isna().any() or price.loc[day:].isna().any():
        return None  # unknown prices cannot establish the week's high or the first later crossing
    top = week.idxmax()
    twice = price.loc[day:][price.loc[day:] >= 2 * price[day]]
    out = {"day": float(price[day]), "highest_in_the_week_from_it": {"date": str(top.date()), "value": float(week[top]),
                                                                     "pct_change": float((week[top] / price[day] - 1) * 100),
                                                                     "days_after": int((top - day).days)}}
    prev = price.loc[:day - pd.Timedelta(days=1)].dropna()
    if len(prev):  # the day of the step against the day before, and the last earlier day at or below its price
        if prev.index[-1] == day - pd.Timedelta(days=1):
            out["day_before"] = {"date": str(prev.index[-1].date()), "value": float(prev.iloc[-1]),
                                 "pct_change_to_the_day": float((price[day] / prev.iloc[-1] - 1) * 100)}
        low = prev[prev <= price[day]]
        last_low = low.index[-1] if len(low) else None
        # An unknown intervening price could be a more recent low. Earlier gaps cannot invalidate a later known low.
        history = price.loc[last_low:day] if last_low is not None else price.loc[:day]
        out["lowest_since"] = str(last_low.date()) if last_low is not None and history.notna().all() else None
        if history.isna().any():
            out["lowest_since_unavailable"] = "Missing earlier daily prices prevent dating the previous low."
    later = price.loc[day + pd.Timedelta(days=1):]
    if len(later):  # how low the price went after the step: the volume after it was not seen at the step day's price
        out["lowest_after_it"] = {"date": str(later.idxmin().date()), "value": float(later.min()),
                                  "pct_above_the_day": float((later.min() / price[day] - 1) * 100)}
    if len(twice):
        out["first_day_at_twice_it"] = {"date": str(twice.index[0].date()), "value": float(twice.iloc[0]),
                                        "days_after": int((twice.index[0] - day).days)}
    return out


def intents_step(daily: pd.DataFrame, fees: pd.DataFrame | None, top: float, after: str) -> dict | None:
    """The day Intents volume stepped up to its autumn level, by the rule in the module docstring."""
    # Seven observations need not be seven calendar days. A gap leaves every weekly mean touching it unknown, and
    # cannot support the claim that the weekly mean has stayed above the line continuously since the crossing.
    vol = daily["intents_volume_usd"].asfreq("D").replace([np.inf, -np.inf], np.nan)
    week = vol.rolling(7).mean().loc[after:]
    not_above = week[week <= top]
    if not_above.empty or not_above.index.max() >= week.index.max():
        return None  # the weekly mean is at or below the line today: there is no level that holds
    since = not_above.index.max() + pd.Timedelta(days=1)
    if week.loc[since:].isna().any():
        return None
    rise = vol.diff().loc[since - pd.Timedelta(days=6):since].dropna()
    if rise.empty:
        return None
    day = rise.idxmax()
    before = day - pd.Timedelta(days=1)
    period = day.to_period("M")
    start, end = period.start_time, period.end_time.normalize()
    month = metrics.calendar_window(vol, start, end)
    out = {"line": float(top), "weekly_mean_above_it_since": str(since.date()), "last_day_at_or_below": str(not_above.index.max().date()),
           "lowest_weekly_mean_since": float(week.loc[since:].min()), "day": str(day.date()),
           "volume": {"day_before": float(vol[before]), "day": float(vol[day])},
           "month": str(day.to_period("M")), "days_of_the_month_from_it": int((month.index >= day).sum()),
           "share_of_the_month_volume_from_it": metrics.finite_ratio(month.loc[day:].sum(), month.sum()) if month.notna().all() else float("nan")}
    missing = {"volume": int(month.isna().sum())}
    price = _price_after(daily["price_usd"], day)
    if price is not None:
        out["price_usd"] = price
    if fees is not None:
        bb = metrics.calendar_window(fees["holders_revenue"], start, end)
        missing["buybacks"] = int(bb.isna().sum())
        out["share_of_the_month_buybacks_from_it"] = (metrics.finite_ratio(bb.loc[day:].sum(), bb.sum())
                                                       if bb.notna().all() else float("nan"))
        out["per_day_before_and_from_it"] = {
            "volume_usd": [metrics.complete_mean(month.loc[:before]), metrics.complete_mean(month.loc[day:])],
            "buyback_usd": [metrics.complete_mean(bb.loc[:before]), metrics.complete_mean(bb.loc[day:])]}
    if any(missing.values()):
        out["month_days_without_data"] = missing
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
    if last < step_month.end_time.normalize():
        return None
    step = intents_step(daily, fees, line, plateau[0]) if line is not None and "intents_volume_usd" in daily else None

    def unavailable(reason: str) -> dict:
        return {"reference": {"from": None, "through": None, "top": {}}, "reference_unavailable": reason,
                **({"intents_step": step} if step else {})}

    if not fall_date:
        return unavailable("A complete transaction history is needed to date the largest daily fall.")
    fall = pd.Timestamp(fall_date)
    # the first half-month that starts after the fall day
    first = (fall.to_period("M").start_time + pd.Timedelta(days=FIRST_HALF_ENDS) if fall.day <= FIRST_HALF_ENDS
             else (fall.to_period("M") + 1).start_time)
    t = table(daily, fees, str(first.date()), last)
    reference_end = pd.Period(plateau[1], "M").end_time.normalize()
    if step:  # the reference stops before the half-month in which Intents volume stepped up
        day = pd.Timestamp(step["day"])
        half_start = day.replace(day=1 if day.day <= FIRST_HALF_ENDS else FIRST_HALF_ENDS + 1)
        reference_end = min(reference_end, half_start - pd.Timedelta(days=1))
    if first > min(reference_end, last):
        return unavailable("No complete half-month lies after the largest fall and before the reference end.")
    ref = t[[pd.Timestamp(k.split("..")[1]) <= reference_end for k in t.index]]
    after = t[[pd.Timestamp(k.split("..")[0]) > reference_end for k in t.index]]
    out: dict = {"rule": "calendar half-months (1-15, 16-end); reference: the half-months after the largest one-day fall of "
                         "transactions and before the one in which Intents volume stepped up; above: above the highest of them",
                 "reference": {"from": ref.index[0].split("..")[0], "through": ref.index[-1].split("..")[1],
                               # An unknown half may contain the reference maximum; skipping it would lower the
                               # threshold and turn later observations into unsupported "above reference" claims.
                               "top": {c: float(ref[c].max()) for c in COLUMNS if c in ref and ref[c].notna().all()},
                               "top_half": {c: str(ref[c].idxmax()) for c in COLUMNS if c in ref and ref[c].notna().all()}},
                 "half_months": {k: {c: (float(v[c]) if pd.notna(v[c]) else None) for c in [*COLUMNS, "days"] if c in v}
                                 for k, v in t.iterrows()}}
    out["deletion_scenario"] = {
        "metric": "txns_less_deleted", "formula": "transactions - deleted_accounts",
        "assumption": "one transaction per deleted account, counted on the same day",
        "limitation": "Receipts can delete several accounts per transaction or execute on another day. "
                      "This scenario is not a measured count of transactions without deletions; missing deletions stay unknown.",
    }
    out["above_reference_top"] = {c: [k for k, v in after[c].items() if v > out["reference"]["top"][c]]
                                  for c in COLUMNS if c in out["reference"]["top"] and c not in NOT_COMPARED}
    # The same by the median day. A half-month's mean can rest on a day or two, the reference top's too: the largest
    # day of the half-month that sets each top is published, with its share of that half-month's total.
    tm = table(daily, fees, str(first.date()), last, stat="median")
    ref_m = tm.loc[ref.index]
    after_m = tm.loc[after.index]
    d = series(daily, fees)
    out["reference"]["top_median"] = {c: float(ref_m[c].max()) for c in COLUMNS if c in ref_m and ref_m[c].notna().all()}
    out["reference"]["top_half_median"] = {c: str(ref_m[c].idxmax()) for c in COLUMNS if c in ref_m and ref_m[c].notna().all()}
    largest = {}
    for c, half in out["reference"]["top_half"].items():
        a, b = (pd.Timestamp(x) for x in half.split(".."))
        part = d.loc[a:b, c].dropna()
        if len(part) and part.sum():
            largest[c] = {"date": str(part.idxmax().date()), "value": float(part.max()), "share_of_the_half": float(part.max() / part.sum())}
    out["reference"]["top_half_largest_day"] = largest
    out["half_months_median"] = {k: {c: (float(v[c]) if pd.notna(v[c]) else None) for c in [*COLUMNS, "days"] if c in v}
                                 for k, v in tm.iterrows()}
    out["above_reference_top_by_median"] = {c: [k for k, v in after_m[c].items() if v > out["reference"]["top_median"][c]]
                                            for c in COLUMNS if c in out["reference"]["top_median"] and c not in NOT_COMPARED}
    out["one_day_moves"] = {c: one_day_moves(d[c].dropna(), first, last) for c in ("active_contracts", "active_accounts", "txns")
                            if c in d and d[c].notna().any()}
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
