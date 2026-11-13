"""Who pays for an account's transactions: the account itself or an app's relayer.

Reads the committed result of sql/payers.sql (data/bq/payers_result.csv). This is the split the thesis rests on:

  sponsored account     every transaction of the account in the month was paid by a relayer; the account is
                        counted for the app that runs the relayer (KaiChing, HOT, Sweat, Ember, Meteor, other)
  self-paying account   the account paid the fee of at least one of its own transactions in the month
  independent           self-paying and outside the namespaces of the reward apps (.tg is HOT, .kaiching is KaiChing,
                        .sweat is Sweat's service accounts): the accounts no app is paying or routing for
  regular               also active in the previous calendar month
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

CSV = Path(__file__).resolve().parent.parent / "data" / "bq" / "payers_result.csv"
APP_NAMESPACES = ("kaiching", "tg", "sweat")
SPONSORS = ["kaiching", "hot", "sweat", "ember", "meteor", "other"]
COLUMNS = ["month", "family", "payer", "ret", "accounts", "txs", "self_paid_txs"]


def load(path: Path | None = None) -> pd.DataFrame | None:
    path = path or CSV
    if not path.exists():
        return None
    rows = []
    for m, sec, cells in pd.read_csv(path).itertuples(index=False):
        if sec != "payer":
            continue
        for cell in str(cells).split(";"):
            fam, payer, ret, accounts, txs, direct = cell.split("|")
            rows.append((str(m), fam, payer, ret, int(accounts), int(txs), int(direct)))
    return pd.DataFrame(rows, columns=COLUMNS)


def groups(df: pd.DataFrame) -> pd.DataFrame:
    """Per month: accounts and transactions of each group defined in the module docstring."""
    d = df.copy()
    d["independent"] = (d["payer"] == "self") & ~d["family"].isin(APP_NAMESPACES)
    out = {}
    for month, g in d.groupby("month"):
        ind = g[g["independent"]]
        row = {
            "all_accounts": g["accounts"].sum(),
            "sponsored_accounts": g.loc[g["payer"] != "self", "accounts"].sum(),
            "self_paying_accounts": g.loc[g["payer"] == "self", "accounts"].sum(),
            "independent_accounts": ind["accounts"].sum(),
            "independent_regular_accounts": ind.loc[ind["ret"] == "r", "accounts"].sum(),
            "independent_self_paid_txs": ind["self_paid_txs"].sum(),
            "independent_regular_self_paid_txs": ind.loc[ind["ret"] == "r", "self_paid_txs"].sum(),
            # the earlier drafts' "core": every account outside the three namespaces, whoever pays
            "old_core_accounts": g.loc[~g["family"].isin(APP_NAMESPACES), "accounts"].sum(),
        }
        for s in SPONSORS:
            row[f"sponsored_by_{s}"] = g.loc[g["payer"] == s, "accounts"].sum()
            row[f"old_core_sponsored_by_{s}"] = g.loc[(g["payer"] == s) & ~g["family"].isin(APP_NAMESPACES), "accounts"].sum()
        out[month] = row
    return pd.DataFrame(out).T.astype(float)


def _change(now: float, then: float) -> dict:
    return {"latest": float(now), "prior": float(then), "pct_change": float((now / then - 1) * 100) if then else float("nan")}


def summarize(df: pd.DataFrame) -> dict:
    g = groups(df)
    latest = g.index.max()
    prior = (pd.Period(latest, "M") - 12).strftime("%Y-%m")
    q_now = [(pd.Period(latest, "M") - k).strftime("%Y-%m") for k in (2, 1, 0)]
    q_then = [(pd.Period(prior, "M") - k).strftime("%Y-%m") for k in (2, 1, 0)]
    out: dict = {"source": "sql/payers.sql on bigquery-public-data.crypto_near_mainnet_us (53.23 GB scanned)",
                 "latest_month": latest, "prior_month": prior, "three_months": [q_now[0], q_now[-1]], "month": {}, "three_month_mean": {}}
    for col in g.columns:
        out["month"][col] = _change(g.loc[latest, col], g.loc[prior, col])
        out["three_month_mean"][col] = _change(g.loc[q_now, col].mean(), g.loc[q_then, col].mean())
    m = out["month"]
    core_lost = m["old_core_accounts"]["prior"] - m["old_core_accounts"]["latest"]
    out["old_core_fall_explained_by"] = {
        s: (m[f"old_core_sponsored_by_{s}"]["prior"] - m[f"old_core_sponsored_by_{s}"]["latest"]) / core_lost for s in ("sweat", "ember")}
    out["old_core_sponsored_share"] = {
        k: sum(m[f"old_core_sponsored_by_{s}"][k] for s in SPONSORS) / m["old_core_accounts"][k] for k in ("latest", "prior")}
    lost_all = m["all_accounts"]["prior"] - m["all_accounts"]["latest"]
    lost_independent = m["independent_accounts"]["prior"] - m["independent_accounts"]["latest"]
    lost_other_sponsor = m["sponsored_by_other"]["prior"] - m["sponsored_by_other"]["latest"]
    out["reward_apps_share_of_lost_accounts"] = float((lost_all - lost_independent - lost_other_sponsor) / lost_all)
    out["independent_accounts_by_month"] = {k: float(v) for k, v in g["independent_accounts"].items()}
    out["independent_regular_accounts_by_month"] = {k: float(v) for k, v in g["independent_regular_accounts"].items()}
    return out
