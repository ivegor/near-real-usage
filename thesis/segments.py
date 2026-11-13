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
# the frequency codes sql/payer_frequency.sql writes, and the labels used in the committed table
FREQUENCY = {"n1": "1", "n2_9": "2-9", "n10_99": "10-99", "n100_999": "100-999", "n1k_9k": "1,000-9,999", "n10k": "10,000+"}
COLUMNS = ["month", "namespace", "payer", "txs_in_month", "accounts", "txs", "self_paid_txs"]


def load(path: Path | None = None) -> pd.DataFrame | None:
    path = path or CSV
    if not path.exists():
        return None
    return pd.read_csv(path, dtype={"txs_in_month": str})


def unpack(result_csv: Path, out: Path | None = None) -> pd.DataFrame:
    """Turn the BigQuery result of sql/payer_frequency.sql (columns m, cells) into the long table used here."""
    raw = pd.read_csv(result_csv)
    rows = []
    for m, cells in zip(raw["m"], raw["cells"]):
        for cell in str(cells).split(";"):
            namespace, payer, freq, accounts, txs, self_paid = cell.split("|")
            assert namespace in (*APP_NAMESPACES, "rest") and payer in ("self", "sponsored") and freq in FREQUENCY, cell
            rows.append((str(m)[:7], namespace, payer, FREQUENCY[freq], int(accounts), int(txs), int(self_paid)))
    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_csv(out or CSV, index=False)
    return df


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
    # the same frequency class inside HOT's namespace: self-paying, but users of one reward app, so not "independent"
    out["app_namespace_regular_self_paying_accounts"] = d[(d["payer"] == "self") & (d["namespace"] == "tg") & (d["cls"] == "regular")].groupby("month")["accounts"].sum()
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
    # Month by month, and the largest fall in a single month: a step that large is not a gradual slide.
    regular = s["regular_accounts"]
    out["regular_accounts_by_month"] = {m: int(v) for m, v in regular.items()}
    step = regular.diff().dropna()
    if len(step) and step.min() < 0:
        worst = step.idxmin()
        before = regular.index[regular.index.get_loc(worst) - 1]
        to_low = float(regular[prior] - regular[low]) if prior <= low else float("nan")
        out["regular_accounts_largest_monthly_fall"] = {
            "month": worst, "month_before": before, "before": int(regular[before]), "after": int(regular[worst]),
            "fall": int(regular[before] - regular[worst]),
            # how much of the fall from the comparison month a year ago to the low this one month is
            "share_of_fall_from_prior_month_to_low": float((regular[before] - regular[worst]) / to_low) if to_low > 0 else float("nan")}
    out["independent_accounts_range"] = {"min": float(s["independent_accounts"].min()), "max": float(s["independent_accounts"].max())}
    return out


def add_reward_game_bound(sg: dict, game: dict) -> None:
    """How much of the fall in regular accounts can be one game changing who pays the fee (clients.GAME_CONTRACT).

    A year ago the players of Meteor's reward game called its contract themselves, so each of them counted as
    self-paying; now a relayer submits those calls, and a player who is still there counts as sponsored. The committed
    tables say how many accounts called the game directly, not which frequency class they were in, nor how many of
    them still play. That count is therefore an upper bound on the game's players among last year's regular accounts,
    and it gives the two ends between which the change without them lies: the counted one (none of them were regular)
    and the one with all of them taken out.

    The same holds for transactions. The game's direct calls were paid by their senders, so they are inside last
    year's self-paid transactions of independent accounts and outside this year's: at most all of them, which gives
    the same two ends for the change of that series.
    """
    direct = (game.get("direct") or {}).get("prior")
    if not direct:
        return
    reg = sg["metrics"]["regular_accounts"]
    at_most = min(float(direct["accounts"]), reg["prior"])
    rest = reg["prior"] - at_most
    sg["regular_accounts_reward_game_bound"] = {
        "game_players_prior": int(direct["accounts"]),
        "share_of_prior_regular_at_most": at_most / reg["prior"] if reg["prior"] else float("nan"),
        "fall": reg["prior"] - reg["latest"],
        "pct_change_as_counted": reg["pct_change"],
        "pct_change_if_all_of_them_were_regular": (reg["latest"] / rest - 1) * 100 if rest else float("nan"),
    }
    txs = sg["metrics"].get("independent_self_paid_txs")
    if txs and direct.get("transactions"):
        calls = min(float(direct["transactions"]), txs["prior"])
        without = txs["prior"] - calls
        sg["self_paid_txs_reward_game_bound"] = {
            "game_direct_txs_prior": int(direct["transactions"]),
            "share_of_prior_self_paid_txs_at_most": calls / txs["prior"] if txs["prior"] else float("nan"),
            "pct_change_as_counted": txs["pct_change"],
            "pct_change_if_all_of_them_were_independent": (txs["latest"] / without - 1) * 100 if without else float("nan"),
        }
