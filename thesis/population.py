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


def complete_months(df: pd.DataFrame, last_date: str) -> list[str]:
    """Months fully covered by the query: the first one has no 'previous month', the last may be partial."""
    months = sorted(df["month"].unique())[1:]
    end = pd.Timestamp(last_date)
    if months and (end + pd.Timedelta(days=1)).day != 1 and months[-1] == end.strftime("%Y-%m"):
        months = months[:-1]
    return months


def segment(df: pd.DataFrame, name: str) -> pd.DataFrame:
    if name == "core":
        return df[~df["family"].isin(REWARD_FAMILIES)]
    if name == "all":
        return df
    return df[df["family"] == name]


def monthly(df: pd.DataFrame) -> pd.DataFrame:
    """Per month: accounts, transactions, returning accounts, accounts older than one year, one-transaction accounts."""
    g = df.groupby("month")
    out = g[["accounts", "txs", "relayed_txs", "single_tx_accounts"]].sum()
    out["returning_accounts"] = df[df["prev_month"] == "returning"].groupby("month")["accounts"].sum()
    old = df[df["age"].isin(OLDER_THAN_1Y)].groupby("month")[["accounts", "txs"]].sum()
    out["old_accounts"], out["old_txs"] = old["accounts"], old["txs"]
    return out.fillna(0)


def summarize(df: pd.DataFrame, last_date: str) -> dict:
    months = complete_months(df, last_date)
    latest = months[-1]
    prior = (pd.Period(latest, "M") - 12).strftime("%Y-%m")
    out: dict = {"source": "sql/account_age.sql on bigquery-public-data.crypto_near_mainnet_us (482.64 GB scanned)",
                 "latest_month": latest, "prior_month": prior, "first_month": months[0], "segments": {}}
    for name in ("all", "core", "near", "implicit", "kaiching", "tg"):
        m = monthly(segment(df, name)).reindex(months).fillna(0)
        a, b = m.loc[latest], m.loc[prior] if prior in m.index else None

        def pair(col: str) -> dict:
            now, then = float(a[col]), float(b[col]) if b is not None else float("nan")
            return {"latest": now, "prior": then, "pct_change": (now / then - 1) * 100 if then else float("nan")}

        out["segments"][name] = {
            **{c: pair(c) for c in ("accounts", "txs", "returning_accounts", "old_accounts", "old_txs")},
            "old_tx_share": {"latest": float(a["old_txs"] / a["txs"]) if a["txs"] else float("nan"),
                             "prior": float(b["old_txs"] / b["txs"]) if b is not None and b["txs"] else float("nan")},
            "returning_share": {"latest": float(a["returning_accounts"] / a["accounts"]) if a["accounts"] else float("nan"),
                                "prior": float(b["returning_accounts"] / b["accounts"]) if b is not None and b["accounts"] else float("nan")},
            "peak_accounts": {"month": str(m["accounts"].idxmax()), "value": float(m["accounts"].max())},
            "txs_per_account": {"latest": float(a["txs"] / a["accounts"]) if a["accounts"] else float("nan"),
                                "prior": float(b["txs"] / b["accounts"]) if b is not None and b["accounts"] else float("nan")},
        }
    seg = out["segments"]

    def lost(name: str, col: str) -> float:
        return seg[name][col]["prior"] - seg[name][col]["latest"]

    reward = [n for n in REWARD_FAMILIES if n in seg]
    # sweat is not listed as its own segment above, so take the reward apps as "all minus core"
    out["reward_apps_share_of_lost"] = {
        col: (lost("all", col) - lost("core", col)) / lost("all", col) for col in ("accounts", "txs")
    }
    out["near_share_of_all_txs"] = {k: seg["near"]["txs"][k] / seg["all"]["txs"][k] for k in ("latest", "prior")}
    recent = monthly(segment(df, "core")).reindex(months)["accounts"]
    out["core_accounts_last_4_months"] = {m: float(v) for m, v in recent.tail(4).items()}
    return out
