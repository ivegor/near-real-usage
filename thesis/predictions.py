"""Dated, checkable predictions (predictions.csv) and their status.

"automatic" predictions are scored by the build from the daily series once the data reaches the check date.
"bigquery" predictions need the account queries in sql/ to be run again for the named month; until then they
are reported as open. The file's SHA-256 is quoted in PREDICTIONS.md so later edits are visible.
"""
from __future__ import annotations

import hashlib
import operator
from pathlib import Path

import pandas as pd

from . import metrics, value

CSV = Path(__file__).resolve().parent.parent / "predictions.csv"
OPS = {">=": operator.ge, "<=": operator.le, "<": operator.lt, ">": operator.gt}


def sha256(path: Path | None = None) -> str:
    return hashlib.sha256((path or CSV).read_bytes()).hexdigest()


def _measure(metric: str, on: pd.Timestamp, daily: pd.DataFrame, fees: pd.DataFrame | None) -> float | None:
    d = daily.loc[:on]
    if metric == "intents_volume_7d_mean_usd":
        return float(d["intents_volume_usd"].loc[on - pd.Timedelta(days=6):on].mean())
    if metric == "lags_outside_band":
        return float(sum(len(v["outside_band"]) for v in metrics.summarize(d)["lead_vs_price"].values()))
    if fees is None:
        return None
    f = fees.loc[:on]
    if metric == "buyback_month_usd":
        return float(f["holders_revenue"].loc[on.strftime("%Y-%m")].sum())
    if metric == "buyback_coverage_90d":
        v = value.summarize(d, f)
        return float(v["buyback_coverage_of_new_supply"]) if v else None
    return None


def evaluate(daily: pd.DataFrame, fees: pd.DataFrame | None, path: Path | None = None) -> dict | None:
    path = path or CSV
    if not path.exists():
        return None
    last = daily.index.max()
    rows = []
    for p in pd.read_csv(path, dtype={"threshold": float}).to_dict("records"):
        on = pd.Timestamp(p["check_on"])
        status, measured = "open", None
        if p["scoring"] == "bigquery":
            status = "open (needs the census query for that month)" if last >= on else "open"
        elif last >= on:
            measured = _measure(p["metric"], on, daily, fees)
            if measured is not None:
                status = "held" if OPS[p["operator"]](measured, p["threshold"]) else "failed"
        rows.append({**p, "status": status, "measured": measured})
    return {"sha256": sha256(path), "data_through": str(last.date()), "items": rows}
