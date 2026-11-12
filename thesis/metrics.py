"""Pure metric functions. No I/O here, so everything is unit-testable."""
from __future__ import annotations

import numpy as np
import pandas as pd


def add_derived(daily: pd.DataFrame) -> pd.DataFrame:
    """Usage-quality metrics derived from the raw daily series."""
    d = daily.copy()
    d["returning_accounts"] = (d["active_accounts"] - d["new_accounts"]).clip(lower=0)
    d["returning_share"] = d["returning_accounts"] / d["active_accounts"]
    d["tx_per_active"] = d["txns"] / d["active_accounts"]
    d["fees_per_active_usd"] = d["fees_usd"] / d["active_accounts"]
    # Fees in NEAR. Fees in USD are fees in NEAR times the price, so they move with the price by construction.
    d["fees_near"] = d["fees_usd"] / d["price_usd"].where(d["price_usd"] > 0)
    # Same fees in NEAR terms: removes the mechanical effect of the token price on USD fees.
    d["fees_per_active_near"] = d["fees_usd"] / d["price_usd"].where(d["price_usd"] > 0) / d["active_accounts"]
    if "intents_volume_usd" in d:
        d["intents_per_active_usd"] = d["intents_volume_usd"] / d["active_accounts"]
    return d.replace([np.inf, -np.inf], np.nan)


def rolling(d: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    return d.rolling(window, min_periods=max(1, window // 2)).mean()


def period_change(series: pd.Series, days: int = 90, lookback_days: int = 365) -> dict:
    """Mean over the last `days` vs the same window `lookback_days` earlier.

    Medians of the same two windows are reported too, as a check that a few extreme days
    do not drive the change.
    """
    s = series.dropna()
    if s.empty:
        return {"recent": np.nan, "prior": np.nan, "pct_change": np.nan, "median_pct_change": np.nan}
    end = s.index.max()
    recent = s[(s.index > end - pd.Timedelta(days=days)) & (s.index <= end)]
    p_end = end - pd.Timedelta(days=lookback_days)
    prior = s[(s.index > p_end - pd.Timedelta(days=days)) & (s.index <= p_end)]
    r, p = recent.mean(), prior.mean()
    pct = (r / p - 1) * 100 if prior.size and pd.notna(p) and p != 0 else np.nan
    rm, pm = recent.median(), prior.median()
    mpct = (rm / pm - 1) * 100 if prior.size and pd.notna(pm) and pm != 0 else np.nan
    return {
        "recent": float(r),
        "prior": float(p) if pd.notna(p) else np.nan,
        "pct_change": float(pct) if pd.notna(pct) else np.nan,
        "median_pct_change": float(mpct) if pd.notna(mpct) else np.nan,
    }


def weekly_log_diff(series: pd.Series) -> pd.Series:
    w = series.resample("W-SUN").mean()
    w = w.where(w > 0)
    return np.log(w).diff().dropna()


def lead_lag(x: pd.Series, price: pd.Series, max_lag: int = 8) -> pd.DataFrame:
    """Correlation of weekly log-changes of x with price shifted by k weeks.

    k > 0  -> corr(x_t, price_{t+k}): x LEADS price by k weeks.
    k < 0  -> price leads x.
    `band` is the approximate 95% noise band 2/sqrt(n) for a zero true correlation.
    """
    dx, dp = weekly_log_diff(x), weekly_log_diff(price)
    rows = []
    for k in range(-max_lag, max_lag + 1):
        pair = pd.concat([dx, dp.shift(-k)], axis=1, keys=["x", "p"], sort=True).dropna()
        n = len(pair)
        corr = pair["x"].corr(pair["p"]) if n > 5 else np.nan
        rows.append({"lag_weeks": k, "corr": corr, "n": n, "band": 2 / np.sqrt(n) if n else np.nan})
    return pd.DataFrame(rows)


def best_lead(ll: pd.DataFrame) -> dict:
    ll = ll.dropna(subset=["corr"])
    if ll.empty:
        return {"lag_weeks": None, "corr": np.nan, "significant": False, "outside_band": []}
    row = ll.loc[ll["corr"].abs().idxmax()]
    outside = ll[ll["corr"].abs() > ll["band"]]
    return {
        "lag_weeks": int(row["lag_weeks"]),
        "corr": float(row["corr"]),
        "band": float(row["band"]),
        "n_weeks": int(row["n"]),
        "significant": bool(abs(row["corr"]) > row["band"]),
        # every lag whose correlation is outside the noise band, not only the largest one
        "outside_band": [
            {"lag_weeks": int(k), "corr": round(float(c), 3)} for k, c in zip(outside["lag_weeks"], outside["corr"])
        ],
    }


def decoupling_table(d: pd.DataFrame, days: int = 90, lookback_days: int = 365) -> pd.DataFrame:
    cols = [
        "price_usd",
        "active_accounts",
        "new_accounts",
        "returning_accounts",
        "returning_share",
        "txns",
        "tx_per_active",
        "fees_usd",
        "fees_near",
        "fees_per_active_usd",
        "fees_per_active_near",
        "intents_volume_usd",
        "intents_per_active_usd",
    ]
    rows = []
    for c in cols:
        if c in d:
            rows.append({"metric": c, **period_change(d[c], days=days, lookback_days=lookback_days)})
    return pd.DataFrame(rows)


def checks(daily: pd.DataFrame, days: int = 90) -> dict:
    """Sanity checks on the `returning = active - new` identity.

    The identity assumes every new account is also counted as active on its first day. Days where
    new_accounts > active_accounts show it does not always hold; on such days `returning` is clipped
    to 0 and, more generally, `active - new` is a LOWER bound for returning accounts.
    """
    d = add_derived(daily)
    bad = daily["new_accounts"] > daily["active_accounts"]
    end = d.index.max()

    def window(lookback: int) -> pd.Series:
        e = end - pd.Timedelta(days=lookback)
        return (d.index > e - pd.Timedelta(days=days)) & (d.index <= e)

    return {
        "new_exceeds_active_days": {
            "recent": int(bad[window(0)].sum()),
            "prior": int(bad[window(365)].sum()),
            "all_history": int(bad.sum()),
        },
        "returning_accounts_two_years_earlier": float(d["returning_accounts"][window(730)].mean()),
    }


def month_change(series: pd.Series) -> dict:
    """Mean of the last complete calendar month vs the same month a year earlier (a fixed, dated comparison)."""
    s = series.dropna()
    if s.empty:
        return {"month": None, "recent": np.nan, "prior": np.nan, "pct_change": np.nan}
    end = s.index.max()
    month = end.to_period("M") if (end + pd.Timedelta(days=1)).day == 1 else end.to_period("M") - 1
    r = s[s.index.to_period("M") == month].mean()
    p = s[s.index.to_period("M") == month - 12].mean()
    pct = (r / p - 1) * 100 if pd.notna(p) and p else np.nan
    return {"month": str(month), "recent": float(r), "prior": float(p) if pd.notna(p) else np.nan,
            "pct_change": float(pct) if pd.notna(pct) else np.nan}


LEAD_METRICS = ["returning_accounts", "active_accounts", "intents_volume_usd", "fees_near", "txns"]


def summarize(daily: pd.DataFrame) -> dict:
    d = add_derived(daily)
    table = decoupling_table(d)
    leads = {}
    for c in LEAD_METRICS:
        if c in d and d[c].notna().sum() > 120:
            leads[c] = best_lead(lead_lag(d[c], d["price_usd"]))
    return {
        "first_date": str(d.index.min().date()),
        "last_date": str(d.index.max().date()),
        "days": int(len(d)),
        "yoy_90d": table.set_index("metric").to_dict(orient="index"),
        # last 90 days vs the 90 days just before them: is the YoY direction still the current direction?
        "qoq_90d": decoupling_table(d, lookback_days=90).set_index("metric").to_dict(orient="index"),
        "month_yoy": {c: month_change(d[c]) for c in ("price_usd", "txns", "active_accounts", "fees_usd", "fees_near",
                                                       "intents_volume_usd") if c in d},
        "lead_vs_price": leads,
        # reported apart from the scan above: USD fees contain the price, so this correlation is mechanical
        "lead_fees_usd_mechanical": best_lead(lead_lag(d["fees_usd"], d["price_usd"])),
        "checks": checks(daily),
    }
