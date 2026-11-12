"""Full-population account census from the NEAR BigQuery dataset.

`sql/account_age.sql` scans every transaction (482.64 GB, free tier) and returns, per calendar month,
how many accounts acted and how many transactions they sent, split by account family, account age and
whether the account was also active in the previous month. The result is committed as
data/bq/account_age.csv, so the build does not need BigQuery access.

Definitions (see the SQL for the exact code):
  actor      the user behind a transaction; for a relayed (meta) transaction it is the account the
             relayer acted for, not the relayer
  family     kaiching / tg (HOT wallet) / sweat are reward and wallet apps with their own account
             namespaces; "core" below means everything else: implicit, .near and other accounts
  age        first appearance of the account in any transaction, relative to the first day of the month
  returning  the same actor was also active in the previous calendar month
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

BQ_DIR = Path(__file__).resolve().parent.parent / "data" / "bq"
CSV = BQ_DIR / "account_age.csv"
QUERY_END = "2026-11-11"  # last block_date covered by sql/account_age.sql; the month it falls in is incomplete
ONE_DAY = "2025-10-01"
ONE_DAY_CSV = BQ_DIR / f"one_day_actions_{ONE_DAY}.csv"
FAMILY_CODES = {"kaiching", "tg", "sweat", "implicit", "near", "other"}
REWARD_FAMILIES = ("kaiching", "tg", "sweat")
AGES = ["m0", "lt30", "lt1y", "lt2y", "ge2y"]
OLDER_THAN_1Y = ("lt2y", "ge2y")


def load(path: Path | None = None) -> pd.DataFrame | None:
    path = path or CSV  # looked up at call time so tests can point it elsewhere
    return pd.read_csv(path) if path.exists() else None


def unpack(result_csv: Path, out: Path | None = None) -> pd.DataFrame:
    """Turn the BigQuery result of sql/account_age.sql (columns m, cells) into the long table used here."""
    raw = pd.read_csv(result_csv)
    rows = []
    for m, cells in zip(raw["m"], raw["cells"]):
        for cell in str(cells).split(";"):
            fam, age, ret, accounts, txs, rtx, single = cell.split("|")
            assert fam in FAMILY_CODES and age in AGES + ["unknown"] and ret in "rn", cell
            rows.append((str(m)[:7], fam, age, "returning" if ret == "r" else "not_returning",
                         int(accounts), int(txs), int(rtx), int(single)))
    df = pd.DataFrame(rows, columns=["month", "family", "age", "prev_month", "accounts", "txs", "relayed_txs", "single_tx_accounts"])
    df.to_csv(out or CSV, index=False)
    return df


def one_day(daily: pd.DataFrame | None = None) -> dict | None:
    """What one day looks like on chain next to what the aggregator reports for it (sql/one_day_actions.sql)."""
    if not ONE_DAY_CSV.exists():
        return None
    t = pd.read_csv(ONE_DAY_CSV)
    first = t[t["is_first"]].set_index("action_kind")
    out = {
        "date": ONE_DAY,
        "transactions": int(first["txs"].sum()),
        "relayed_transactions": int(first.loc["DELEGATE_ACTION", "txs"]),
        "relayers": int(first.loc["DELEGATE_ACTION", "signers"]),
        "relayed_users": int(first.loc["DELEGATE_ACTION", "receivers"]),
        "direct_function_call_signers": int(first.loc["FUNCTION_CALL", "signers"]),
        "create_account_transactions": int(first.loc["CREATE_ACCOUNT", "txs"]),
        "account_creators": int(first.loc["CREATE_ACCOUNT", "signers"]),
    }
    if daily is not None and pd.Timestamp(ONE_DAY) in daily.index:
        row = daily.loc[pd.Timestamp(ONE_DAY)]
        out["nearblocks"] = {k: int(row[k]) for k in ("txns", "active_accounts", "new_accounts")}
    return out


def complete_months(df: pd.DataFrame, query_end: str | None = None) -> list[str]:
    """Months fully covered by the query: the first one has no 'previous month', the last may be partial.

    Completeness depends on where the BigQuery scan stopped (QUERY_END), not on today's date: a later rebuild
    of the dashboard must not start treating the half-scanned last month as a full one.
    """
    months = sorted(df["month"].unique())[1:]
    end = pd.Timestamp(query_end or QUERY_END)
    if months and (end + pd.Timedelta(days=1)).day != 1 and months[-1] == end.strftime("%Y-%m"):
        months = months[:-1]
    return months


def segment(df: pd.DataFrame, name: str) -> pd.DataFrame:
    if name == "core":
        return df[~df["family"].isin(REWARD_FAMILIES)]
    if name == "all":
        return df
    if name == "all_ex_kaiching":
        return df[df["family"] != "kaiching"]
    return df[df["family"] == name]


COLUMNS = ["accounts", "txs", "direct_txs", "relayed_txs", "returning_accounts", "multi_tx_accounts", "old_accounts", "old_txs"]


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Per month: accounts, transactions (paid by the sender / relayed), returning, multi-transaction and old accounts."""
    g = df.groupby("month")
    out = g[["accounts", "txs", "relayed_txs", "single_tx_accounts"]].sum()
    out["direct_txs"] = out["txs"] - out["relayed_txs"]
    out["multi_tx_accounts"] = out["accounts"] - out["single_tx_accounts"]
    out["returning_accounts"] = df[df["prev_month"] == "returning"].groupby("month")["accounts"].sum()
    old = df[df["age"].isin(OLDER_THAN_1Y)].groupby("month")[["accounts", "txs"]].sum()
    out["old_accounts"], out["old_txs"] = old["accounts"], old["txs"]
    return out.fillna(0)


def _change(now: float, then: float) -> dict:
    return {"latest": float(now), "prior": float(then), "pct_change": float((now / then - 1) * 100) if then else float("nan")}


def summarize(df: pd.DataFrame, query_end: str | None = None) -> dict:
    query_end = query_end or QUERY_END
    months = complete_months(df, query_end)
    latest = months[-1]
    prior = (pd.Period(latest, "M") - 12).strftime("%Y-%m")
    last3 = months[-3:]
    prior3 = [(pd.Period(m, "M") - 12).strftime("%Y-%m") for m in last3]
    out: dict = {"source": "sql/account_age.sql on bigquery-public-data.crypto_near_mainnet_us (482.64 GB scanned)",
                 "query_end": query_end, "latest_month": latest, "prior_month": prior, "first_month": months[0],
                 "three_months": {"latest": last3, "prior": prior3}, "segments": {}}
    for name in ("all", "all_ex_kaiching", "core", "near", "implicit", "kaiching", "tg", "sweat"):
        full = monthly(segment(df, name))
        m = full.reindex(months).fillna(0)
        a = m.loc[latest]
        b = m.loc[prior] if prior in m.index else m.loc[latest] * float("nan")
        have3 = all(x in full.index for x in prior3)
        out["segments"][name] = {
            **{c: _change(a[c], b[c]) for c in COLUMNS},
            # the same comparison on three-month means: one month alone can be an outlier
            "three_month_mean": {c: _change(m.loc[last3, c].mean(), full.loc[prior3, c].mean() if have3 else float("nan"))
                                 for c in COLUMNS},
            "accounts_range_12m": {"min": float(m["accounts"].tail(12).min()), "max": float(m["accounts"].tail(12).max())},
            "old_tx_share": {"latest": float(a["old_txs"] / a["txs"]) if a["txs"] else float("nan"),
                             "prior": float(b["old_txs"] / b["txs"]) if b["txs"] else float("nan")},
            "returning_share": {"latest": float(a["returning_accounts"] / a["accounts"]) if a["accounts"] else float("nan"),
                                "prior": float(b["returning_accounts"] / b["accounts"]) if b["accounts"] else float("nan")},
            "peak_accounts": {"month": str(m["accounts"].idxmax()), "value": float(m["accounts"].max())},
            "txs_per_account": {"latest": float(a["txs"] / a["accounts"]) if a["accounts"] else float("nan"),
                                "prior": float(b["txs"] / b["accounts"]) if b["accounts"] else float("nan")},
        }
    seg = out["segments"]

    def lost(name: str, col: str) -> float:
        return seg[name][col]["prior"] - seg[name][col]["latest"]

    # the reward apps as "all minus core", so the .sweat service accounts are included
    out["reward_apps_share_of_lost"] = {
        col: (lost("all", col) - lost("core", col)) / lost("all", col) for col in ("accounts", "txs")
    }
    out["near_share_of_all_txs"] = {k: seg["near"]["txs"][k] / seg["all"]["txs"][k] for k in ("latest", "prior")}
    out["sweat_share_of_all_txs"] = seg["sweat"]["txs"]["latest"] / seg["all"]["txs"]["latest"]
    core_m = monthly(segment(df, "core")).reindex(months)
    out["core_accounts_last_4_months"] = {m: float(v) for m, v in core_m["accounts"].tail(4).items()}
    # self-paid core transactions month by month: the series is volatile, so the whole of it is published
    out["core_direct_txs_monthly"] = {m: int(v) for m, v in core_m["direct_txs"].items()}
    best = core_m["direct_txs"].nlargest(3)
    out["core_direct_txs_top3_months"] = {m: int(v) for m, v in best.items()}

    # Is "more transactions per core account" a change in behaviour or in who is left? Hold the mix of account
    # types at last year's shares and apply this year's per-account rates.
    fam = segment(df, "core").groupby(["month", "family"])[["accounts", "txs"]].sum()
    if prior in fam.index.get_level_values(0):
        now, then = fam.loc[latest], fam.loc[prior]
        mix_then = then["accounts"] / then["accounts"].sum()
        rate_now = (now["txs"] / now["accounts"]).reindex(mix_then.index).fillna(0)
        out["core_txs_per_account_at_prior_mix"] = float((rate_now * mix_then).sum())
        out["core_txs_per_account_by_family"] = {
            f: {"latest": float(now.loc[f, "txs"] / now.loc[f, "accounts"]), "prior": float(then.loc[f, "txs"] / then.loc[f, "accounts"])}
            for f in ("implicit", "near") if f in now.index and f in then.index}

    # one-off in the latest month: reward-app accounts that sent a single transaction and were not active before
    k = df[(df["family"] == "kaiching") & (df["month"] == latest) & (df["prev_month"] == "not_returning")]
    out["kaiching_one_off"] = {"accounts": int(k["accounts"].sum()), "single_tx_accounts": int(k["single_tx_accounts"].sum()),
                               "share_of_all_accounts": float(k["accounts"].sum() / seg["all"]["accounts"]["latest"])}

    # the partial last month is not used for comparisons, but a rebound inside it is worth a line
    all_months = sorted(df["month"].unique())
    if all_months[-1] != latest:
        part = df[df["month"] == all_months[-1]].groupby("family")["accounts"].sum()
        full = df[df["month"] == latest].groupby("family")["accounts"].sum()
        out["partial_month"] = {"month": all_months[-1], "through": query_end,
                                "accounts": {f: int(v) for f, v in part.items()},
                                "latest_complete_accounts": {f: int(v) for f, v in full.items()}}
    return out
