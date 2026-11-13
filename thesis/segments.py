"""Accounts by who pays and how often: the product view (sql/payer_frequency.sql, data/bq/payer_frequency.csv).

Three questions define the segments, and none of the lines between them is a number we picked:
  who pays?      sponsored: an app's relayer paid for every transaction of the account that month;
                 self: the account paid for at least one itself
  whose account? app namespaces (.kaiching, .tg): accounts a reward app creates for its users; the rest
  how often?     transactions in the month by powers of ten. Fewer than 10: occasional. 10 to 999: regular.
                 1,000 or more (over 30 a day, every day): no person does that by hand, so heavy = automated or
                 institutional.
"Independent" below = pays for itself and is not in a reward app's namespace.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CSV = Path(__file__).resolve().parent.parent / "data" / "bq" / "payer_frequency.csv"
CLASS = {"1": "occasional", "2-9": "occasional", "10-99": "regular", "100-999": "regular",
         "1,000-9,999": "heavy", "10,000+": "heavy"}
APP_NAMESPACES = ("kaiching", "tg")


def load(path: Path | None = None) -> pd.DataFrame | None:
    path = path or CSV
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"txs_in_month": str})


def series(df: pd.DataFrame) -> pd.DataFrame:
    """One row per month with the segment counts used in the thesis."""
    d = df.assign(cls=df["txs_in_month"].map(CLASS))
    sponsored = d[d["payer"] == "sponsored"]
    ind = d[(d["payer"] == "self") & ~d["namespace"].isin(APP_NAMESPACES)]
    out = pd.DataFrame({
        "sponsored_accounts": sponsored.groupby("month")["accounts"].sum(),
        "sponsored_accounts_outside_app_namespaces": sponsored[~sponsored["namespace"].isin(APP_NAMESPACES)].groupby("month")["accounts"].sum(),
        "app_namespace_self_paying_accounts": d[(d["payer"] == "self") & (d["namespace"] == "tg")].groupby("month")["accounts"].sum(),
        "independent_accounts": ind.groupby("month")["accounts"].sum(),
        "independent_self_paid_txs": ind.groupby("month")["self_paid_txs"].sum(),
    })
    for c in ("occasional", "regular", "heavy"):
        out[f"{c}_accounts"] = ind[ind["cls"] == c].groupby("month")["accounts"].sum()
        out[f"{c}_self_paid_txs"] = ind[ind["cls"] == c].groupby("month")["self_paid_txs"].sum()
    out["accounts_outside_app_namespaces"] = d[~d["namespace"].isin(APP_NAMESPACES)].groupby("month")["accounts"].sum()
    return out.fillna(0).sort_index()


def _change(now: float, then: float) -> dict:
    return {"latest": float(now), "prior": float(then), "pct_change": (now / then - 1) * 100 if then else float("nan")}


def summarize(df: pd.DataFrame) -> dict:
    s = series(df)
    latest = s.index.max()
    prior = (pd.Period(latest, "M") - 12).strftime("%Y-%m")
    now3 = [(pd.Period(latest, "M") - k).strftime("%Y-%m") for k in range(3)]
    then3 = [(pd.Period(prior, "M") - k).strftime("%Y-%m") for k in range(3)]
    out: dict = {"source": "sql/payer_frequency.sql on bigquery-public-data.crypto_near_mainnet_us (91.28 GB scanned)",
                 "latest_month": latest, "prior_month": prior, "first_month": s.index.min(), "metrics": {}}
    for col in s.columns:
        out["metrics"][col] = {**_change(s.loc[latest, col], s.loc[prior, col]),
                               "three_month_mean": _change(s.loc[now3, col].mean(), s.loc[then3, col].mean())}
    out["heavy_share_of_independent_self_paid_txs"] = {
        k: float(s.loc[m, "heavy_self_paid_txs"] / s.loc[m, "independent_self_paid_txs"]) for k, m in (("latest", latest), ("prior", prior))}
    out["sponsored_share_of_accounts_outside_app_namespaces"] = {
        k: float(s.loc[m, "sponsored_accounts_outside_app_namespaces"] / s.loc[m, "accounts_outside_app_namespaces"])
        for k, m in (("latest", latest), ("prior", prior))}
    low = s["regular_accounts"].idxmin()
    out["regular_accounts_low"] = {"month": low, "value": float(s.loc[low, "regular_accounts"])}
    out["independent_accounts_range"] = {"min": float(s["independent_accounts"].min()), "max": float(s["independent_accounts"].max())}
    return out
