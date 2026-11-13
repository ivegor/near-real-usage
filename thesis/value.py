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
    buyback_year = float(f["holders_revenue"].sum() * scale)
    new_supply_value = float(quarter * scale * price)
    nonzero = fees["holders_revenue"][fees["holders_revenue"] > 0]
    out = {
        "window": [str(start.date()), str(end.date())],
        "days_behind_the_daily_series": int((daily.index.max() - end).days),
        "days_without_buyback_data": int(days - f["holders_revenue"].notna().sum()),
        "intents_gross_fees_usd": float(f["fees"].sum()),
        "captured_revenue_usd": float(f["revenue"].sum()),
        "captured_share_of_gross_fees": float(f["revenue"].sum() / f["fees"].sum()) if f["fees"].sum() else float("nan"),
        "buyback_usd": float(f["holders_revenue"].sum()),
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
