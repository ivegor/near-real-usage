"""Dated, checkable predictions (predictions.csv) and their status.

"automatic" predictions are scored by the build from the daily series once the data reaches the check date and
covers every day of the window the prediction names; until then they stay open.
"bigquery" predictions need the account queries in sql/ to be run again for the named month; until then they
are reported as open. The file's SHA-256 is quoted in PREDICTIONS.md so later edits are visible.
"""
from __future__ import annotations

import hashlib
import operator
from pathlib import Path

import numpy as np
import pandas as pd

from . import metrics, population, value

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
        from . import segments
        out["regular_self_paying_accounts_low"] = float(segments.series(seg)["regular_accounts"].loc[PLATEAU[0]:PLATEAU[1]].min())
    return out


def _window(s: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> pd.Series | None:
    """The values of every day from start to end, or None while a day is missing.

    The daily table is driven by NearBlocks; a DefiLlama series can end a few days earlier (a late update, or the
    saved copy used during an outage). A prediction is not scored on part of its window.
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
    if fees is None or fees.empty or fees.index.max() < on:
        return None
    f = fees.loc[:on]
    if metric == "buyback_month_usd":
        w = _window(f["holders_revenue"], on.replace(day=1), on)
        return None if w is None else float(w.sum())
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
            if measured is not None and not np.isfinite(measured):
                measured = None  # an empty or undefined measurement is not a miss
            if measured is None:
                status = "open (waiting for complete data)"
            else:
                status = "held" if OPS[p["operator"]](measured, p["threshold"]) else "failed"
        rows.append({**p, "status": status, "measured": measured})
    return {"sha256": sha256(path), "data_through": str(last.date()), "items": rows}
