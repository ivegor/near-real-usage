"""Does usage reach the token? NEAR Intents revenue and buybacks against the net new supply of NEAR.

Sources: DefiLlama fee series for NEAR Intents (gross fees, NEAR's captured revenue, and "holders revenue",
which since 2026-02-23 is the captured revenue used to buy NEAR on the open market) and the daily total supply
of NEAR from NearBlocks. Net new supply is the change in total supply, so it is already net of burned fees.
"""
from __future__ import annotations

import json

import pandas as pd

from . import sources

URLS = {
    "defillama_intents_fees": "https://api.llama.fi/summary/fees/near-intents?dataType=dailyFees",
    "defillama_intents_revenue": "https://api.llama.fi/summary/fees/near-intents?dataType=dailyRevenue",
    "defillama_intents_holders_revenue": "https://api.llama.fi/summary/fees/near-intents?dataType=dailyHoldersRevenue",
}
YOCTO = 1e24


def fetch() -> None:
    """Download the three fee series into data/raw/ (network). The build only reads the saved copies.

    All three replies are checked before any file is written: an error page or an empty reply must not replace a
    committed copy, and the three files must come from the same download. Raises RuntimeError otherwise.
    """
    replies = {}
    for name, url in URLS.items():
        replies[name] = sources._fetch_json(url)
        sources._check_shape(name, replies[name], key="totalDataChart")
    sources.RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in replies.items():
        (sources.RAW_DIR / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")


def load() -> pd.DataFrame | None:
    """Daily gross fees, captured revenue and buybacks in USD, or None when the raw files are absent.

    A day that a series does not carry, or carries as null, stays empty (NaN). It is not turned into a zero: a missing
    day must not read as a day without revenue, and a prediction must be able to see that its window has a hole.
    """
    cols = {}
    for name in URLS:
        path = sources.RAW_DIR / f"{name}.json"
        if not path.exists():
            return None
        pts = json.loads(path.read_text(encoding="utf-8")).get("totalDataChart") or []
        cols[name.replace("defillama_intents_", "")] = pd.Series(
            {pd.Timestamp(int(ts), unit="s").normalize(): float(v) for ts, v in pts if v is not None}, dtype=float)
    return pd.DataFrame(cols).sort_index()


def window_total(s: pd.Series, a: pd.Timestamp, b: pd.Timestamp) -> float:
    """What a daily series adds up to over the days a to b. A day without a value is not a day without revenue: when
    days are missing, the total is the mean of the days present times the days of the window, and the summary says
    how many days were missing (days_without_buyback_data)."""
    w = s.loc[a:b]
    n = int((b - a).days) + 1
    if w.notna().sum() == n:
        return float(w.sum())
    return float(w.mean() * n) if w.notna().any() else float("nan")


def covered_through(fees: pd.DataFrame) -> pd.Timestamp | None:
    """The last day on which all three fee series have a value."""
    full = fees.dropna()
    return full.index.max() if len(full) else None


def summarize(daily: pd.DataFrame, fees: pd.DataFrame, days: int = 90) -> dict | None:
    if "total_supply_yocto" not in daily or daily["total_supply_yocto"].dropna().empty:
        return None
    last_fee_day = covered_through(fees)
    if last_fee_day is None:
        return None
    # The fee series can end before the daily table: a late update, or the saved copy used during an outage. The
    # window ends on the last day both cover, so that 90 days of buybacks are always set against 90 days of supply.
    end = min(daily.index.max(), last_fee_day)
    start = end - pd.Timedelta(days=days - 1)
    f = fees.loc[start:end]
    supply = daily["total_supply_yocto"].dropna() / YOCTO
    price = daily["price_usd"].loc[start:end].mean()
    year = supply.asof(end) - supply.asof(end - pd.Timedelta(days=365))
    quarter = supply.asof(end) - supply.asof(start - pd.Timedelta(days=1))
    scale = 365 / days
    buyback_year = window_total(fees["holders_revenue"], start, end) * scale
    new_supply_value = float(quarter * scale * price)
    nonzero = fees["holders_revenue"][fees["holders_revenue"] > 0]
    out = {
        "window": [str(start.date()), str(end.date())],
        "days_behind_the_daily_series": int((daily.index.max() - end).days),
        "days_without_buyback_data": int(days - f["holders_revenue"].notna().sum()),
        "intents_gross_fees_usd": window_total(fees["fees"], start, end),
        "captured_revenue_usd": window_total(fees["revenue"], start, end),
        "captured_share_of_gross_fees": float(f["revenue"].sum() / f["fees"].sum()) if f["fees"].sum() else float("nan"),
        "buyback_usd": window_total(fees["holders_revenue"], start, end),
        "buyback_usd_annualized": buyback_year,
        "buyback_start": str(nonzero.index.min().date()) if len(nonzero) else None,
        "l1_fees_usd": float(daily["fees_usd"].loc[start:end].sum()),
        "net_new_supply_near_365d": float(year),
        "net_new_supply_pct_365d": float(year / supply.asof(end - pd.Timedelta(days=365)) * 100),
        "net_new_supply_near_annualized": float(quarter * scale),
        "mean_price_usd": float(price),
        "new_supply_value_usd_annualized": new_supply_value,
        "buyback_coverage_of_new_supply": buyback_year / new_supply_value if new_supply_value else float("nan"),
        "market_cap_usd": float(daily["market_cap_usd"].asof(end)),
    }
    # The coverage above is a ratio of USD: buybacks in USD over the new supply valued at the window's mean price. The
    # same flow counted in NEAR (each day's buyback at that day's price, over the new NEAR) differs whenever the price
    # moves inside the window and the buybacks are not spread evenly over it. Both are published, as two measurements.
    px = daily["price_usd"].where(daily["price_usd"] > 0).reindex(fees.index)
    out["buyback_near"] = window_total(fees["holders_revenue"] / px, start, end)
    out["buyback_coverage_in_near"] = out["buyback_near"] / float(quarter) if quarter else float("nan")
    out["intents_fees_vs_l1_fees"] = out["intents_gross_fees_usd"] / out["l1_fees_usd"] if out["l1_fees_usd"] else float("nan")
    out["growth_needed_to_cover_new_supply"] = 1 / out["buyback_coverage_of_new_supply"] if out["buyback_coverage_of_new_supply"] else float("nan")
    out["market_cap_to_annual_buyback"] = out["market_cap_usd"] / buyback_year if buyback_year else float("nan")
    return out


def monthly(daily: pd.DataFrame, fees: pd.DataFrame, months: int = 12) -> pd.DataFrame:
    """Complete calendar months: gross fees, captured revenue, buybacks and the USD value of net new supply."""
    last_fee_day = covered_through(fees)
    end = min(daily.index.max(), last_fee_day) if last_fee_day is not None else daily.index.max()
    last = (end + pd.Timedelta(days=1)).to_period("M") - 1  # the last month complete in both the daily and the fee series
    supply = daily["total_supply_yocto"].dropna() / YOCTO
    m = fees.resample("ME").sum()
    m.index = m.index.to_period("M")
    eom = supply.resample("ME").last()
    eom.index = eom.index.to_period("M")
    price = daily["price_usd"].resample("ME").mean()
    price.index = price.index.to_period("M")
    m["new_supply_value"] = eom.diff().reindex(m.index) * price.reindex(m.index)
    return m.loc[:last].tail(months)


def windows(daily: pd.DataFrame, fees: pd.DataFrame, step_day: str | None = None, days: int = 90,
            threshold_month_usd: float | None = None, threshold_month: str | None = None,
            reference: tuple[str, str] | None = None) -> dict | None:
    """How much the buyback coverage depends on the window, and the buybacks in NEAR as well as in USD.

    The coverage quoted in THESIS.md is one 90-day window ending on the last day both series cover. Here it is set
    against every 90-day window since the buybacks began, against other lengths ending on the same day and against
    calendar months, all by the method of summarize (annualised buybacks over the annualised value of net new supply
    at the window's mean price). The captured share of gross fees is given for the same windows.

    `step_day` (autumn.intents_step) splits the programme in two for the buybacks per day. A buyback threshold in USD
    can be met by the price alone, so for `threshold_month_usd` the mean price at which the last 30 days' buybacks in
    NEAR, over the days of `threshold_month`, reach the threshold is published too.
    """
    last_fee_day = covered_through(fees)
    if last_fee_day is None or "total_supply_yocto" not in daily:
        return None
    end = min(daily.index.max(), last_fee_day)
    supply = daily["total_supply_yocto"].dropna() / YOCTO
    price = daily["price_usd"].where(daily["price_usd"] > 0)
    nonzero = fees["holders_revenue"][fees["holders_revenue"] > 0]
    if nonzero.empty:
        return None
    start = nonzero.index.min()

    def cover(a: pd.Timestamp, b: pd.Timestamp) -> float:
        bought = window_total(fees["holders_revenue"], a, b)
        new = float(supply.asof(b) - supply.asof(a - pd.Timedelta(days=1))) * float(price.loc[a:b].mean())
        return bought / new if new else float("nan")

    def captured(a: pd.Timestamp, b: pd.Timestamp) -> float:
        f = fees.loc[a:b]
        return float(f["revenue"].sum() / f["fees"].sum()) if f["fees"].sum() else float("nan")

    rolling = pd.Series({b: cover(b - pd.Timedelta(days=days - 1), b)
                         for b in pd.date_range(start + pd.Timedelta(days=days - 1), end, freq="D")}, dtype=float)
    latest = float(rolling.iloc[-1])
    out: dict = {"window_days": days, "end": str(end.date()), "programme_start": str(start.date()),
                 f"rolling_{days}d": {"windows": int(len(rolling)), "latest": latest,
                                      "rank_of_the_latest": int((rolling > latest).sum()) + 1,
                                      "median": float(rolling.median()), "min": float(rolling.min()), "max": float(rolling.max())}}
    if step_day:
        before = rolling[rolling.index < pd.Timestamp(step_day)]
        if len(before):
            out[f"rolling_{days}d"]["ending_before_the_step"] = {"windows": int(len(before)), "min": float(before.min()),
                                                                  "max": float(before.max())}
    lengths = {}
    for n in (7, 30, 60, 90, 180):
        a = end - pd.Timedelta(days=n - 1)
        if a >= start:
            lengths[str(n)] = {"coverage": cover(a, end), "captured_share": captured(a, end),
                               "buyback_usd_annualized": window_total(fees["holders_revenue"], a, end) * 365 / n}
    n_all = int((end - start).days) + 1
    lengths["programme"] = {"days": n_all, "coverage": cover(start, end), "captured_share": captured(start, end),
                            "buyback_usd_annualized": window_total(fees["holders_revenue"], start, end) * 365 / n_all}
    out["by_length"] = lengths
    months = {}
    for m in pd.period_range(start, end, freq="M"):
        a, b = max(start, m.start_time), min(end, m.end_time.normalize())
        bb = fees["holders_revenue"].loc[a:b]
        bn = (bb / price.reindex(bb.index)).dropna()
        months[str(m)] = {"from": str(a.date()), "through": str(b.date()), "coverage": cover(a, b), "captured_share": captured(a, b),
                          "buyback_usd_per_day": float(bb.mean()), "buyback_near_per_day": float(bn.mean()),
                          # a month's mean can rest on one day: the median day, and the largest day with its share
                          "buyback_near_per_day_median": float(bn.median()),
                          "largest_day_near": {"date": str(bn.idxmax().date()), "value": float(bn.max()),
                                               "share_of_the_month": float(bn.max() / bn.sum()) if bn.sum() else float("nan")},
                          "price_usd": float(price.loc[a:b].mean())}
    out["by_month"] = months
    if step_day:
        day = pd.Timestamp(step_day)
        bb = fees["holders_revenue"].loc[start:end]
        near = bb / price.reindex(bb.index)
        a_usd, b_usd = float(bb.loc[:day - pd.Timedelta(days=1)].mean()), float(bb.loc[day:].mean())
        a_near, b_near = float(near.loc[:day - pd.Timedelta(days=1)].mean()), float(near.loc[day:].mean())
        out["buybacks_per_day_before_and_from_the_step"] = {
            "step_day": step_day, "usd": [a_usd, b_usd], "near": [a_near, b_near],
            "usd_ratio": b_usd / a_usd if a_usd else float("nan"), "near_ratio": b_near / a_near if a_near else float("nan"),
            "last_30_days_near": float(near.loc[end - pd.Timedelta(days=29):end].mean())}
        if threshold_month_usd and threshold_month:
            d = pd.Period(threshold_month, "M").days_in_month
            pace = out["buybacks_per_day_before_and_from_the_step"]["last_30_days_near"]
            out["threshold_price"] = {"month": threshold_month, "threshold_usd": float(threshold_month_usd),
                                      "near_per_day": pace, "mean_price_that_meets_it": float(threshold_month_usd / (pace * d)),
                                      "price_on_the_step_day": float(price[day])}
    if reference:
        a, b = pd.Period(reference[0], "M").start_time, pd.Period(reference[1], "M").end_time.normalize()
        out["reference_months"] = {"from": reference[0], "through": reference[1], "captured_share": captured(a, b),
                                   "coverage": cover(a, b)}
    return out


def take(daily: pd.DataFrame, fees: pd.DataFrame, step_day: str | None, days: int = 90) -> dict | None:
    """What NEAR keeps from each dollar of NEAR Intents volume, before and after the step in volume.

    Revenue can grow because more volume passes or because more is kept from each dollar of it. The two are separated
    here on the day the volume stepped up (`step_day`, found by the rule in thesis/autumn.py): the `days` before it
    against every day from it to the last day all series cover. Revenue = volume x take, so the ratio of revenue per
    day is the ratio of volume per day times the ratio of the take.

    The last 30 days are also set against the 30 before them, for volume, gross fees and captured revenue (in USD and
    in NEAR at each day's price): a level that "has held" above an old range can still be falling inside the new one.
    """
    if step_day is None or "intents_volume_usd" not in daily:
        return None
    last = covered_through(fees)
    volume = daily["intents_volume_usd"].dropna()
    if last is None or volume.empty:
        return None
    end = min(last, volume.index.max())
    step = pd.Timestamp(step_day)
    frame = pd.DataFrame({"volume": volume, "fees": fees["fees"], "revenue": fees["revenue"]}).loc[:end]
    frame["revenue_near"] = frame["revenue"] / daily["price_usd"].reindex(frame.index)

    def part(a: pd.Timestamp, b: pd.Timestamp) -> dict | None:
        w = frame.loc[a:b]
        n = int((b - a).days) + 1
        if len(w.dropna(subset=["volume", "fees", "revenue"])) != n or not w["volume"].sum():
            return None  # a hole in a series: no figure
        return {"from": str(a.date()), "through": str(b.date()), "days": n,
                "volume_usd_per_day": float(w["volume"].mean()), "revenue_usd_per_day": float(w["revenue"].mean()),
                "take_bps": float(w["revenue"].sum() / w["volume"].sum() * 1e4),
                "gross_fee_bps": float(w["fees"].sum() / w["volume"].sum() * 1e4),
                "captured_share_of_gross_fees": float(w["revenue"].sum() / w["fees"].sum()) if w["fees"].sum() else float("nan")}

    before, after = part(step - pd.Timedelta(days=days), step - pd.Timedelta(days=1)), part(step, end)
    if not before or not after:
        return None
    out = {"step_day": str(step.date()), "before": before, "after": after,
           "volume_ratio": after["volume_usd_per_day"] / before["volume_usd_per_day"],
           "revenue_ratio": after["revenue_usd_per_day"] / before["revenue_usd_per_day"],
           "take_ratio": after["take_bps"] / before["take_bps"]}
    monthly = frame.resample("MS").sum()
    monthly = monthly[(monthly.index >= step.to_period("M").start_time - pd.DateOffset(months=3)) & (monthly.index < end.to_period("M").start_time)]
    out["take_bps_by_month"] = {str(m.to_period("M")): float(r["revenue"] / r["volume"] * 1e4) for m, r in monthly.iterrows() if r["volume"]}
    recent, earlier = frame.loc[end - pd.Timedelta(days=29):end], frame.loc[end - pd.Timedelta(days=59):end - pd.Timedelta(days=30)]
    if len(recent.dropna()) == 30 and len(earlier.dropna()) == 30:
        out["last_30_days_vs_the_30_before"] = {
            "through": str(end.date()),
            **{f"{k}_pct_change": float((recent[c].sum() / earlier[c].sum() - 1) * 100)
               for k, c in (("volume", "volume"), ("gross_fees", "fees"), ("revenue_usd", "revenue"), ("revenue_near", "revenue_near"))}}
    return out


# House of Stake proposal HSP-029: the maximum annual issuance goes from 2.5% to 1.6% on a 24-month per-epoch ramp
# that starts one quarter after ratification. Status "Succeeded" in the proposal's own header on 2026-11-14.
ISSUANCE_PROPOSAL = {
    "id": "HSP-029", "target_max_issuance": 0.016, "ramp_months": 24, "grace_days": 90,
    "source": "https://gov.near.org/t/hsp-029-establish-a-24-month-issuance-ramp-to-a-1-6-target-rate-of-near-token-emissions/42644",
}


def issuance_cut(v: dict, protocol: dict | None) -> dict | None:
    """What the buyback coverage would be at the issuance the proposal ends at, everything else unchanged.

    The maximum issuance in force is read from the protocol's own configuration (`protocol`, see wallets.fetch_protocol),
    not typed in. Net new supply is taken to scale with the maximum: the measured 2.48% a year is the 2.5% maximum less
    burned fees, and the burn is small. This is arithmetic on one parameter, not a forecast: revenue, price and the
    burn are held where they are, and the ramp takes 24 months to reach its end.
    """
    if not protocol or not v.get("buyback_coverage_of_new_supply"):
        return None
    num, den = protocol["max_inflation_rate"]
    now = num / den
    scale = ISSUANCE_PROPOSAL["target_max_issuance"] / now
    return {**ISSUANCE_PROPOSAL, "max_issuance_in_force": now, "read_at_utc": protocol["read_at_utc"],
            "protocol_version": protocol["protocol_version"], "in_force_yet": bool(abs(now - ISSUANCE_PROPOSAL["target_max_issuance"]) < 1e-9),
            "net_new_supply_scale": scale,
            "coverage_at_target": v["buyback_coverage_of_new_supply"] / scale,
            "growth_needed_at_target": v["growth_needed_to_cover_new_supply"] * scale}
