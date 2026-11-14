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

import numpy as np
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
    keeps_months(out or CSV, df)
    df.to_csv(out or CSV, index=False)
    return df


def keeps_months(path: Path, new: pd.DataFrame) -> None:
    """Refuse to replace a committed table with a result that no longer holds some of its months.

    A query is run again by moving its end date only: the new result then holds every earlier month too and replaces
    the file. A result that starts later would drop the months THESIS.md quotes, and its first month would have no
    "previous month" to compare with.
    """
    if not path.exists():
        return
    lost = sorted(set(pd.read_csv(path, usecols=["month"])["month"]) - set(new["month"]))
    if lost:
        raise SystemExit(f"{path.name} holds {lost[0]} .. {lost[-1]}, the new result does not: run the query again with "
                         "its first date unchanged and only the last one moved.")


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
        "accounts_created": int(first.loc["CREATE_ACCOUNT", "receivers"]),
        "account_creators": int(first.loc["CREATE_ACCOUNT", "signers"]),
    }
    if daily is not None and pd.Timestamp(ONE_DAY) in daily.index:
        row = daily.loc[pd.Timestamp(ONE_DAY)]
        out["nearblocks"] = {k: int(row[k]) for k in ("txns", "active_accounts", "new_accounts")}
    return out


def complete_months(df: pd.DataFrame, query_end: str | None = None) -> list[str]:
    """Months fully covered by the query: the first one has no 'previous month', the last may be partial.

    Completeness depends on where the BigQuery scan stopped (QUERY_END), not on today's date: a later rebuild
    of the dashboard must not start treating the half-scanned last month as a full one. A month counts only if the
    scan reached its last day, so a newer table committed without a newer QUERY_END does not add months either.
    """
    end = pd.Timestamp(query_end or QUERY_END)
    return [m for m in sorted(df["month"].unique())[1:] if pd.Period(m, "M").end_time.normalize() <= end]


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


def dormant_implicit(df: pd.DataFrame) -> pd.DataFrame:
    """Rows of implicit accounts older than one year that were not active the month before.

    In an ordinary month they send about 1% of the self-paid core transactions. In February 2026 millions of them
    sent one transaction each and paid for it, so a third of that month's self-paid total is a one-off burst.
    """
    return df[(df["family"] == "implicit") & df["age"].isin(OLDER_THAN_1Y) & (df["prev_month"] == "not_returning")]


def _change(now: float, then: float) -> dict:
    return {"latest": float(now), "prior": float(then), "pct_change": float((now / then - 1) * 100) if then else float("nan")}


def _change_by_window(series: pd.Series) -> dict:
    """% change of the mean of the last n months against the same n months a year earlier, for several n."""
    out = {}
    for n in (1, 3, 6, 9, 11):
        now_m = list(series.index[-n:])
        then_m = [(pd.Period(x, "M") - 12).strftime("%Y-%m") for x in now_m]
        if all(x in series.index for x in then_m):
            out[str(n)] = float((series.loc[now_m].mean() / series.loc[then_m].mean() - 1) * 100)
    return out


def summarize(df: pd.DataFrame, query_end: str | None = None) -> dict:
    query_end = query_end or QUERY_END
    months = complete_months(df, query_end)
    latest = months[-1]
    prior = (pd.Period(latest, "M") - 12).strftime("%Y-%m")
    last3 = months[-3:]
    prior3 = [(pd.Period(m, "M") - 12).strftime("%Y-%m") for m in last3]
    out: dict = {"source": "sql/account_age.sql on bigquery-public-data.crypto_near_mainnet_us (482.64 GB scanned)",
                 "query_end": query_end, "latest_month": latest, "prior_month": prior, "first_month": months[0],
                 # the table starts a month earlier: that month has no month before it, so every series leaves it out
                 "table_first_month": str(sorted(df["month"].unique())[0]),
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
        col: (lost("all", col) - lost("core", col)) / lost("all", col) if lost("all", col) else float("nan")
        for col in ("accounts", "txs")
    }
    out["near_share_of_all_txs"] = {k: seg["near"]["txs"][k] / seg["all"]["txs"][k] for k in ("latest", "prior")}
    # The reward apps' namespaces as a share of all transactions, month by month (the unfinished month too: a share of
    # the same days is a share): one month's share is read against the months around it.
    every_month = sorted(df["month"].unique())[1:]
    all_t = df.groupby("month")["txs"].sum().reindex(every_month)
    core_t = segment(df, "core").groupby("month")["txs"].sum().reindex(every_month).fillna(0)
    by_month = (1 - core_t / all_t)
    out["reward_namespaces_share_of_txs_by_month"] = {m: float(v) for m, v in by_month.items()}
    # Transactions a day of each reward app's namespace, month by month (the unfinished month over the days scanned): a
    # rise measured from one month is read against the months before it.
    scan_end = pd.Timestamp(query_end)
    days_in = {m: (int(scan_end.day) if pd.Period(m, "M") == scan_end.to_period("M") else pd.Period(m, "M").days_in_month)
               for m in every_month}
    out["reward_namespace_txs_per_day_by_month"] = {
        f: {m: float(v / days_in[m]) for m, v in df[df["family"] == f].groupby("month")["txs"].sum().reindex(every_month).fillna(0).items()}
        for f in REWARD_FAMILIES}
    # the same through relayers only: an app that changes relayers shows here first
    out["reward_namespace_relayed_txs_per_day_by_month"] = {
        f: {m: float(v / days_in[m]) for m, v in df[df["family"] == f].groupby("month")["relayed_txs"].sum().reindex(every_month).fillna(0).items()}
        for f in REWARD_FAMILIES}
    out["reward_namespaces_share_of_txs_windows"] = {
        str(n): float(1 - core_t[months[-n:]].sum() / all_t[months[-n:]].sum()) for n in (1, 3, 6)}
    out["sweat_share_of_all_txs"] = seg["sweat"]["txs"]["latest"] / seg["all"]["txs"]["latest"]
    core_m = monthly(segment(df, "core")).reindex(months)
    out["core_accounts_last_4_months"] = {m: float(v) for m, v in core_m["accounts"].tail(4).items()}
    # self-paid core transactions month by month: the series is volatile, so the whole of it is published
    out["core_direct_txs_monthly"] = {m: int(v) for m, v in core_m["direct_txs"].items()}
    # how much the year-on-year change depends on the window: the last n months against the same n a year earlier
    series = core_m["direct_txs"]
    out["core_direct_txs_change_by_window"] = _change_by_window(series)
    best = core_m["direct_txs"].nlargest(3)
    out["core_direct_txs_top3_months"] = {m: int(v) for m, v in best.items()}
    # one-off bursts inside that series: the part sent by dormant implicit accounts, and the windows without it
    woke = monthly(dormant_implicit(df)).reindex(months).fillna(0)["direct_txs"]
    share = (woke / series).fillna(0)
    peak = str(share.idxmax())
    before = (pd.Period(peak, "M") - 1).strftime("%Y-%m")
    out["core_direct_txs_from_dormant_implicit"] = {
        "peak": {"month": peak, "txs": int(woke[peak]), "share_of_month": float(share[peak]),
                 "month_before_txs": int(woke[before]) if before in woke.index else None},
        "largest_share_in_any_other_month": float(share.drop(peak).max()) if len(share) > 1 else float("nan"),
        "monthly": {m: int(v) for m, v in woke.items()},
        "change_by_window_without_them": _change_by_window(series - woke),
    }

    # The window of twelve months needs the table's first month as the year-earlier base. That month is left out of the
    # series because it has no month before it, which matters for returning accounts, not for transactions.
    every = monthly(segment(df, "core"))["direct_txs"]
    twelve_now = months[-12:]
    twelve_then = [(pd.Period(x, "M") - 12).strftime("%Y-%m") for x in twelve_now]
    if len(twelve_now) == 12 and all(x in every.index for x in twelve_then):
        out["core_direct_txs_change_12_months_with_the_tables_first_month"] = {
            "months": [twelve_now[0], twelve_now[-1]], "base": [twelve_then[0], twelve_then[-1]],
            "pct_change": float((every[twelve_now].mean() / every[twelve_then].mean() - 1) * 100)}

    # Self-paid core transactions by account family: which family a change of the whole series comes from.
    fam_direct = segment(df, "core").assign(direct=lambda x: x["txs"] - x["relayed_txs"]).pivot_table(
        index="month", columns="family", values="direct", aggfunc="sum").reindex(months).fillna(0)
    out["core_direct_txs_by_family"] = {
        f: {"monthly": {m: int(v) for m, v in fam_direct[f].items()}, "change_by_window": _change_by_window(fam_direct[f])}
        for f in fam_direct.columns}

    # Who sends the core's transactions, by payer: the share of accounts older than a year among self-paid and among
    # relayed transactions, and the overall share at last year's mix of the two. An overall share can fall because the
    # mix changed while the share inside each part rose.
    core_rows = segment(df, "core")
    old_rows = core_rows[core_rows["age"].isin(OLDER_THAN_1Y)]

    def shares(ms: list[str]) -> dict:
        t, o = core_rows[core_rows["month"].isin(ms)], old_rows[old_rows["month"].isin(ms)]
        txs, rel, otx, orel = t["txs"].sum(), t["relayed_txs"].sum(), o["txs"].sum(), o["relayed_txs"].sum()
        return {"all": float(otx / txs) if txs else float("nan"),
                "self_paid": float((otx - orel) / (txs - rel)) if txs - rel else float("nan"),
                "relayed": float(orel / rel) if rel else float("nan"),
                "relayed_part_of_core_txs": float(rel / txs) if txs else float("nan")}

    if prior in df["month"].values and all(x in df["month"].values for x in prior3):
        by = {"latest": shares([latest]), "prior": shares([prior]), "three_months_latest": shares(last3), "three_months_prior": shares(prior3)}
        mix = by["prior"]["relayed_part_of_core_txs"]
        by["latest_at_prior_mix"] = by["latest"]["self_paid"] * (1 - mix) + by["latest"]["relayed"] * mix
        out["old_tx_share_by_payer"] = by

    # One-off bursts of accounts: implicit accounts that already existed, were not active the month before and sent
    # exactly one transaction. An ordinary month has about a hundred thousand of them. A burst is a month with more
    # than ten times the median month: an order of magnitude, not a tuned line.
    wake = df[(df["family"] == "implicit") & (df["age"] != "m0") & (df["prev_month"] == "not_returning")]
    one = wake.groupby("month")["single_tx_accounts"].sum().reindex(months).fillna(0)
    usual, bursts = float(one.median()), []
    for m in (one[one > 10 * usual].index if usual > 0 else []):
        rows = wake[wake["month"] == m]
        # accounts first seen the month before that were active in it and sent one transaction now: the rule above
        # counts only accounts that were not active the month before, so a second group of this kind passes it
        young = df[(df["family"] == "implicit") & (df["age"] == "lt30") & (df["prev_month"] == "returning") & (df["month"] == m)]
        bursts.append({"month": m, "accounts": int(one[m]), "times_the_median_month": float(one[m] / usual),
                       "older_than_2y_share": float(rows.loc[rows["age"] == "ge2y", "single_tx_accounts"].sum() / one[m]),
                       "relayed_tx_share": float(rows["relayed_txs"].sum() / rows["txs"].sum()),
                       "first_seen_the_month_before_single_tx_accounts": int(young["single_tx_accounts"].sum()),
                       "first_seen_the_month_before_relayed_tx_share": float(young["relayed_txs"].sum() / young["txs"].sum())
                       if young["txs"].sum() else float("nan")})
    out["implicit_one_transaction_bursts"] = {"median_month": usual, "bursts": bursts,
                                              "monthly": {m: int(v) for m, v in one.items()}}
    # The same rule for named accounts. The filter of the self-paid series (dormant_implicit) has the shape of the
    # February burst and does not take these out; what they change in the windows is published next to it.
    named = df[(df["family"] == "near") & (df["age"] != "m0") & (df["prev_month"] == "not_returning")]
    one_named = named.groupby("month")["single_tx_accounts"].sum().reindex(months).fillna(0)
    usual_named = float(one_named.median())
    hit = [m for m in one_named.index if usual_named > 0 and one_named[m] > 10 * usual_named]
    named_direct = monthly(named).reindex(months).fillna(0)["direct_txs"]
    excess = pd.Series(0.0, index=series.index)
    for m in hit:  # the self-paid transactions of that group above its median month
        excess[m] = max(0.0, float(named_direct[m] - named_direct.median()))
    out["named_one_transaction_bursts"] = {
        "median_month": usual_named, "months": {m: int(one_named[m]) for m in hit},
        "relayed_tx_share": {m: float(named[named["month"] == m]["relayed_txs"].sum() / named[named["month"] == m]["txs"].sum()) for m in hit},
        "self_paid_txs_above_the_median_month": {m: int(excess[m]) for m in hit},
        "change_by_window_without_them_and_the_dormant_implicit": _change_by_window(series - woke - excess)}
    out["core_direct_txs_without_bursts_monthly"] = {
        "without_dormant_implicit": {m: int(v) for m, v in (series - woke).items()},
        "without_both": {m: int(v) for m, v in (series - woke - excess).items()}}

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

    # KaiChing's relayed transactions per day of the month. People do not arrive in the same round number every day;
    # a job with a daily quota does. The level is the median month rounded to the nearest thousand, not a typed number.
    # The months are those of every other series: the table's first month has no month before it and is left out.
    relayed = df[df["family"] == "kaiching"].groupby("month")["relayed_txs"].sum().reindex(months).fillna(0)
    per_day = pd.Series({m: v / pd.Period(m, "M").days_in_month for m, v in relayed.items() if v > 0}, dtype=float)
    if len(per_day):
        level = round(float(per_day.median()), -3)
        out["kaiching_relayed_txs_per_day"] = {
            "median_month_to_the_nearest_thousand": level, "months_with_relayed_transactions": int(len(per_day)),
            "first_month": str(per_day.index[0]), "last_month": str(per_day.index[-1]),
            "months_within_a_thousandth_of_it": [m for m, v in per_day.items() if level and abs(v / level - 1) < 0.001],
            "per_day": {m: float(v) for m, v in per_day.items()},
            "in_the_month": {m: int(relayed[m]) for m in per_day.index}}

    # the partial last month is not used for comparisons, but a rebound inside it is worth a line
    all_months = sorted(df["month"].unique())
    if all_months[-1] != latest:
        part = df[df["month"] == all_months[-1]].groupby("family")["accounts"].sum()
        full = df[df["month"] == latest].groupby("family")["accounts"].sum()
        out["partial_month"] = {"month": all_months[-1], "through": query_end,
                                "accounts": {f: int(v) for f, v in part.items()},
                                "latest_complete_accounts": {f: int(v) for f, v in full.items()}}
        # what kind of accounts each reward app's namespace holds in those days: new or old, many or few transactions
        rows = df[df["month"] == all_months[-1]]
        out["partial_month"]["reward_namespaces"] = {
            f: {"accounts": int(r["accounts"].sum()), "txs": int(r["txs"].sum()),
                "txs_per_account": float(r["txs"].sum() / r["accounts"].sum()) if r["accounts"].sum() else float("nan"),
                "older_than_1y_account_share": float(r[r["age"].isin(OLDER_THAN_1Y)]["accounts"].sum() / r["accounts"].sum())
                if r["accounts"].sum() else float("nan"),
                "single_tx_account_share": float(r["single_tx_accounts"].sum() / r["accounts"].sum()) if r["accounts"].sum() else float("nan")}
            for f, r in ((f, rows[rows["family"] == f]) for f in REWARD_FAMILIES)}
        pace = _pace_so_far(df, months, all_months[-1], query_end)
        if pace:
            out["partial_month"]["core_direct_txs"] = pace
        rates = _rates_so_far(df, latest, all_months[-1], query_end)
        if rates:
            out["partial_month"]["txs_per_day"] = rates
    return out


def _rates_so_far(df: pd.DataFrame, latest: str, partial: str, query_end: str) -> dict | None:
    """Transactions per day of every part of the chain in the days of the unfinished month, next to the last complete one.

    The rule of _pace_so_far (transactions add up day by day, so the rate of the days in hand can be set against the
    rate of a whole month) applied to all of the chain, not only to the series the thesis leans on: if the unfinished
    month is quoted where self-paid transactions slow down, it is quoted where a reward app speeds up too. The reward
    apps' namespaces together are "all minus core", as in reward_apps_share_of_lost.
    """
    end, month = pd.Timestamp(query_end), pd.Period(partial, "M")
    if not (month.start_time <= end < month.end_time.normalize()):
        return None  # the scan did not stop inside that month
    days = {partial: int(end.day), latest: pd.Period(latest, "M").days_in_month}

    def rate(name: str, m: str, col: str) -> float:
        rows = segment(df[df["month"] == m], name)
        return float(rows[col].sum() / days[m])

    out: dict = {"days": days[partial], "month": partial, "latest_complete_month": latest}
    for name in ("all", "core", *REWARD_FAMILIES):
        now, was = rate(name, partial, "txs"), rate(name, latest, "txs")
        out[name] = {"partial": now, "latest_complete": was, "pct_change": (now / was - 1) * 100 if was else float("nan"),
                     "relayed": {"partial": rate(name, partial, "relayed_txs"), "latest_complete": rate(name, latest, "relayed_txs")}}
    out["reward_namespaces_share_of_txs"] = {
        k: 1 - out["core"][k] / out["all"][k] if out["all"][k] else float("nan") for k in ("partial", "latest_complete")}
    return out


def _pace_so_far(df: pd.DataFrame, months: list[str], partial: str, query_end: str) -> dict | None:
    """Self-paid core transactions in the days of the unfinished month that the scan covers, as a rate per day.

    Accounts of a part of a month cannot be set against a whole month: the same account comes back on later days.
    Transactions can, because they add up day by day. The census is monthly, so the same days of the year before are
    not available; the rate of the days in hand is set against the rate of whole months. That says where the series
    is heading, on few days: it is not a figure for the month.
    """
    end, month = pd.Timestamp(query_end), pd.Period(partial, "M")
    if not (month.start_time <= end < month.end_time.normalize()):
        return None  # the scan did not stop inside that month
    direct = monthly(segment(df, "core"))["direct_txs"]
    days = int(end.day)
    rate = float(direct[partial] / days)
    per_day = {m: float(direct[m] / pd.Period(m, "M").days_in_month) for m in months}
    out = {"days": days, "transactions": int(direct[partial]), "per_day": rate,
           "whole_month_at_that_rate": rate * month.days_in_month,
           "per_day_by_month": per_day}
    for key, m in (("latest_complete_month", months[-1]), ("same_month_a_year_earlier", (month - 12).strftime("%Y-%m"))):
        if m in per_day:
            out[key] = {"month": m, "per_day": per_day[m], "pct_change": (rate / per_day[m] - 1) * 100 if per_day[m] else float("nan")}
    # The filter applied to February (dormant_implicit) applied to these days and to the months they are set against:
    # a one-off of dormant accounts inside the days in hand would otherwise read as a pace.
    core = segment(df, "core")
    woke = monthly(dormant_implicit(core))
    calm = (direct - woke["direct_txs"].reindex(direct.index).fillna(0))
    calm_rate = float(calm[partial] / days)
    calm_day = {m: float(calm[m] / pd.Period(m, "M").days_in_month) for m in months}
    single = dormant_implicit(core).groupby("month")["single_tx_accounts"].sum()
    out["without_dormant_implicit"] = {
        "per_day": calm_rate, "whole_month_at_that_rate": calm_rate * month.days_in_month,
        "dormant_implicit_single_tx_accounts": {partial: int(single.get(partial, 0)), months[-1]: int(single.get(months[-1], 0))},
        **{key: {"month": m, "per_day": calm_day[m], "pct_change": (calm_rate / calm_day[m] - 1) * 100 if calm_day[m] else float("nan")}
           for key, m in (("latest_complete_month", months[-1]), ("same_month_a_year_earlier", (month - 12).strftime("%Y-%m")))
           if m in calm_day}}
    return out


def signer_spike(daily: pd.DataFrame, partial: str, query_end: str) -> dict | None:
    """The day of the unfinished month with the most signers, against the median day of the rest of those days.

    A one-off of accounts that each sign one transaction shows in the aggregator's daily count of signers on the day it
    happens; the census, being monthly, cannot date it.
    """
    if "active_accounts" not in daily:
        return None
    a = daily["active_accounts"].loc[pd.Period(partial, "M").start_time:pd.Timestamp(query_end)].dropna()
    if len(a) < 3:
        return None
    day = a.idxmax()
    rest = a.drop(day)
    return {"date": str(day.date()), "signers": int(a[day]), "median_other_day": float(rest.median()),
            "above_the_median_day": float(a[day] - rest.median())}


def days_of(daily: pd.DataFrame, partial: str, query_end: str, columns=("txns", "active_accounts", "active_contracts", "deleted_accounts")) -> dict:
    """Every day of the unfinished month the census covers, for the daily columns that can date a step inside it: a rate
    over eleven days is one number, and a level that changed on one of them is two."""
    d = daily.loc[pd.Period(partial, "M").start_time:pd.Timestamp(query_end)]
    return {c: {str(k.date()): int(v) for k, v in d[c].dropna().items()} for c in columns if c in d}


def largest_daily_fall(df: pd.DataFrame, daily: pd.DataFrame) -> dict | None:
    """The largest one-day fall in the aggregator's daily transactions, and KaiChing's months on either side of it.

    Analyses built on daily aggregates see a step in the transaction count on one day and a flat count of active
    accounts across it, and cannot name the cause. The day is found by a rule (the largest relative one-day fall
    inside the months of the census), and the census says what stopped in that month.
    """
    if "txns" not in daily:
        return None
    months = sorted(df["month"].unique())
    x = daily["txns"].dropna()
    x = x[(x.index >= pd.Timestamp(months[0] + "-01")) & (x.index.to_period("M") <= pd.Period(months[-1], "M"))]
    rel = (x / x.shift(1) - 1).dropna()
    if rel.empty:
        return None
    day = rel.idxmin()
    before = day - pd.Timedelta(days=1)
    k = df[df["family"] == "kaiching"].groupby("month")[["accounts", "txs", "relayed_txs"]].sum()
    # accounts that appear in a transaction for the first time that month: for KaiChing, the accounts it created
    first_seen = df[(df["family"] == "kaiching") & (df["age"] == "m0")].groupby("month")["accounts"].sum()

    def month(m: pd.Period) -> dict:
        row = k.loc[str(m)] if str(m) in k.index else pd.Series({"accounts": 0, "txs": 0, "relayed_txs": 0})
        return {"month": str(m), "accounts": int(row["accounts"]), "txs": int(row["txs"]), "relayed_txs": int(row["relayed_txs"]),
                "txs_per_day": float(row["txs"] / m.days_in_month), "first_seen_accounts": int(first_seen.get(str(m), 0))}

    out = {"date": str(day.date()), "day_before": str(before.date()),
           "txns": {"before": int(x[before]), "after": int(x[day])}, "pct_change": float(rel[day] * 100),
           "kaiching": {"month_before": month(day.to_period("M") - 1), "month_of": month(day.to_period("M")),
                        "month_after": month(day.to_period("M") + 1)}}
    # How much of that one day can be KaiChing? The census is monthly, so the most its accounts can have stopped sending
    # between the two days is everything they sent in the month the first of the two lies in. What is left of the fall
    # was sent by other accounts that stopped on the same day.
    fall, sent = int(x[before] - x[day]), month(before.to_period("M"))["txs"]
    out["fall_txs"] = fall
    out["kaiching_share_of_the_fall_at_most"] = min(1.0, sent / fall) if fall > 0 else float("nan")
    out["other_accounts_in_the_fall_at_least"] = max(0, fall - sent)
    # The level on either side of the fall is a different question: the median day of the month before and of the month
    # after (a median is not moved by a burst of a few days), next to what KaiChing sent per day in the same two months.
    by_month = x.groupby(x.index.to_period("M")).median()
    lb, la = day.to_period("M") - 1, day.to_period("M") + 1
    if lb in by_month.index and la in by_month.index:  # (lb, la are used for the fees below as well)
        app = out["kaiching"]
        drop, less = float(by_month[lb] - by_month[la]), app["month_before"]["txs_per_day"] - app["month_after"]["txs_per_day"]
        out["median_day"] = {"month_before": float(by_month[lb]), "month_after": float(by_month[la]), "fall": drop,
                             "kaiching_share_of_it": less / drop if drop > 0 else float("nan")}
    if "active_accounts" in daily:
        a = daily["active_accounts"]
        out["active_accounts"] = {"before": int(a[before]), "after": int(a[day]), "pct_change": float((a[day] / a[before] - 1) * 100)}
    if "active_contracts" in daily:
        # NearBlocks' column `active_contracts` is not defined in the API's reply. On the one day the census has by action
        # kind it is within a fraction of a percent of the users behind relayers, so it is read as tracking them, no
        # more. Its fall over the two days is set against KaiChing's relayed transactions in the month of the fall: if
        # they match, the relayer's last day is the day before the fall.
        ac = daily["active_contracts"]
        drop = int(ac[before] - ac[day])
        k_rel = out["kaiching"]["month_of"]["relayed_txs"]
        out["active_contracts"] = {"before": int(ac[before]), "after": int(ac[day]), "fall": drop,
                                   "kaiching_relayed_txs_in_the_month_of": int(k_rel),
                                   "fall_over_kaiching_relayed": drop / k_rel if k_rel else float("nan")}
        if pd.Timestamp(ONE_DAY) in ac.index and ONE_DAY_CSV.exists():
            users = one_day()["relayed_users"]
            out["active_contracts"]["one_day"] = {"date": ONE_DAY, "value": int(ac[pd.Timestamp(ONE_DAY)]), "relayed_users": int(users),
                                                  "ratio": float(ac[pd.Timestamp(ONE_DAY)] / users)}
        # If the relayer's transactions all fell on the day before the fall, KaiChing is between its relayed
        # transactions of that month and everything it sent in that month: a share of the one-day fall.
        out["kaiching_share_of_the_fall_at_least"] = min(1.0, k_rel / fall) if fall > 0 else float("nan")
        # The burst of sponsored accounts of the month before, dated: the run of days at the end of that month above its
        # median day, and their transactions above the median of the days before the run. The column tracking relayed
        # users is given over the same days.
        prev = x[(x.index >= (day.to_period("M") - 1).start_time) & (x.index <= before)]  # the month before, to the day before
        above = prev > prev.median()
        run_start = None
        for d_ in reversed(prev.index):
            if not above[d_]:
                break
            run_start = d_
        if run_start is not None and run_start > prev.index.min():
            run = prev.loc[run_start:]
            base = prev.loc[:run_start - pd.Timedelta(days=1)].median()
            in_month = run[run.index.to_period("M") == day.to_period("M") - 1]
            out["run_before_the_fall"] = {
                "first": str(run_start.date()), "last": str(run.index.max().date()), "days": int(len(run)),
                "median_day_before_it": float(base), "transactions_above_it": int((run - base).sum()),
                "transactions_above_it_in_the_month_before": int((in_month - base).sum()),
                "active_contracts_range": [int(ac.loc[run.index].min()), int(ac.loc[run.index].max())],
                "active_contracts_range_before": [int(ac.loc[prev.index.min():run_start - pd.Timedelta(days=1)].min()),
                                                  int(ac.loc[prev.index.min():run_start - pd.Timedelta(days=1)].max())]}
    if "fees_usd" in daily and "price_usd" in daily:
        # network fees in NEAR on the two days and on the median day of the months either side, as for transactions
        f = (daily["fees_usd"] / daily["price_usd"].where(daily["price_usd"] > 0)).dropna()
        med = f.groupby(f.index.to_period("M")).median()
        out["fees_near"] = {"before": float(f[before]), "after": float(f[day])}
        if lb in med.index and la in med.index:
            out["fees_near"]["median_day"] = {"month_before": float(med[lb]), "month_after": float(med[la]),
                                              "fall": float(med[lb] - med[la])}
    if "new_accounts" in daily:
        # the accounts created each day, on the two days and as a mean per day of the two months
        n = daily["new_accounts"].dropna()
        mean = {p: n[n.index.to_period("M") == p].mean() for p in (day.to_period("M") - 1, day.to_period("M"))}
        out["new_accounts"] = {"before": int(n[before]), "after": int(n[day]),
                               "per_day_month_before": float(mean[day.to_period("M") - 1]),
                               "per_day_month_of": float(mean[day.to_period("M")])}
    return out


def deletions(ps: dict, daily: pd.DataFrame) -> dict | None:
    """The aggregator's count of deleted accounts in the months where the census finds accounts sending one transaction.

    The census sees one-off bursts of accounts that send exactly one transaction in a month (the bursts of implicit
    accounts in summarize, and KaiChing's one-off in the latest month) but not what that transaction did. NearBlocks
    counts the accounts deleted on each day. The two are different measurements of different things, so they are set
    side by side and not equated: where they agree in size and in date, that is all the figure says.

    A month counts as a burst of deletions when it has more than ten times the median month of the census, as for the
    bursts of the census itself, and the days of the burst are the days with at least a tenth of its largest day: an
    order of magnitude each time, not a tuned line. The month before is given as deletions per day.
    """
    if "deleted_accounts" not in daily:
        return None
    x = daily["deleted_accounts"].dropna()
    per_month = x.groupby(x.index.to_period("M")).agg(["sum", "size"])
    full = [p for p in pd.period_range(ps["first_month"], ps["latest_month"], freq="M")
            if p in per_month.index and per_month.loc[p, "size"] == p.days_in_month]  # a month counts only if every day is there
    if not full:
        return None
    monthly = {str(p): int(per_month.loc[p, "sum"]) for p in full}
    usual = float(pd.Series(monthly).median())
    # the months the census asks about, each with what it found there: accounts that sent one transaction
    asked: dict[str, dict] = {}
    for b in ps["implicit_one_transaction_bursts"]["bursts"]:
        asked.setdefault(b["month"], {})["implicit_one_transaction_burst"] = int(b["accounts"])
    one_off = (ps.get("kaiching_one_off") or {}).get("single_tx_accounts")
    if one_off:
        asked.setdefault(ps["latest_month"], {})["kaiching_one_off"] = int(one_off)
    months = {}
    # the months the census asks about, and every other month of deletions above ten times the median month
    for m in sorted(set(asked) | {m for m, v in monthly.items() if v > 10 * usual}):
        census = asked.get(m, {})
        p = pd.Period(m, "M")
        if m not in monthly:
            continue
        days = x[x.index.to_period("M") == p]
        prev = x[x.index.to_period("M") == p - 1]
        row = {"census_one_transaction_accounts": census, "deleted_accounts": monthly[m],
               "times_the_median_month": monthly[m] / usual if usual else float("nan"),
               "per_day_month_before": float(prev.mean()) if len(prev) else None, "burst_days": None}
        if monthly[m] > 10 * usual:
            top = days.max()
            hit = days[days >= top / 10]
            row["burst_days"] = {"first": str(hit.index.min().date()), "last": str(hit.index.max().date()), "days": int(len(hit)),
                                 "deleted_accounts": int(hit.sum()),
                                 "largest_day": {"date": str(days.idxmax().date()), "deleted_accounts": int(top)}}
            if "active_accounts" in daily and len(hit) > 2:
                # Who signed the deletions: if each deleted account signed its own, the day's signers rise by one for
                # each of them. The slope of signers on deletions over the days of the burst, and how close the fit is.
                sig = daily["active_accounts"].reindex(hit.index).astype(float)
                slope = float(np.polyfit(hit.astype(float).to_numpy(), sig.to_numpy(), 1)[0])
                row["burst_days"]["signers_per_deleted_account"] = round(slope, 4)
                row["burst_days"]["correlation_of_signers_with_deletions"] = round(float(np.corrcoef(hit.astype(float), sig)[0, 1]), 4)
        months[m] = row
    return {"source": "NearBlocks daily charts (deleted_accounts)", "median_month": usual,
            "months_above_ten_times_the_median": [m for m, v in monthly.items() if v > 10 * usual],
            "monthly": monthly, "months": months}


def totals_check(df: pd.DataFrame, daily: pd.DataFrame, query_end: str | None = None) -> dict | None:
    """BigQuery's transaction count for every month of the census next to the aggregator's count for the same days.

    The two are independent: a scan of the public dataset against NearBlocks' own indexer. The months fall into two
    groups with nothing in between, differences of a few transactions and differences of hundreds of thousands. The
    line between the groups is put at the largest jump in the sorted differences, so no tolerance is chosen; the size
    of that jump is published too, and a small one would mean there are no two groups.
    """
    end = pd.Timestamp(query_end or QUERY_END)
    bq = df.groupby("month")["txs"].sum()
    d = daily.loc[:end, "txns"].dropna()
    nb = d.groupby(d.index.strftime("%Y-%m")).sum().reindex(bq.index).dropna()
    if len(nb) < 2:
        return None
    diff = (bq.reindex(nb.index) - nb).astype(int)
    size = diff.abs().sort_values(kind="stable")
    jumps = (size.iloc[1:].to_numpy() + 1) / (size.iloc[:-1].to_numpy() + 1)
    cut = int(jumps.argmax()) + 1
    close, apart = list(size.index[:cut]), sorted(size.index[cut:])
    return {
        "months": int(len(nb)), "first_month": str(nb.index.min()), "last_month": str(nb.index.max()),
        "last_month_through": str(min(end, d.index.max()).date()),
        "agree": {"months": len(close), "largest_difference_txs": int(size[close].max()),
                  "largest_difference_share": float((size[close] / nb[close]).max())},
        "differ": {m: {"bigquery_minus_nearblocks": int(diff[m]), "share": float(diff[m] / nb[m])} for m in apart},
        "jump_between_the_groups": float(jumps.max()),
        "difference_by_month": {m: int(v) for m, v in diff.items()},
    }


def cross_check(sample: dict, df: pd.DataFrame, top: dict | None = None) -> dict:
    """Put the keyless block sample (thesis/census.py) next to the full BigQuery count for the same period.

    The two were collected independently: random blocks from the FastNEAR archive with account ages from an
    archival RPC node, against a scan of every transaction in BigQuery. They use slightly different definitions
    (age at the start of a 90-day window vs at the start of each month; "the account existed" vs "first seen in
    a transaction"), so the comparison is about agreement in size and direction, not equality.
    """
    out: dict = {}
    for label, w in sample["windows"].items():
        start, end = pd.Timestamp(w["start"]), pd.Timestamp(w["end"])
        months = [str(m) for m in pd.period_range(start, end, freq="M") if m.start_time >= start and m.end_time.normalize() <= end]
        d = df[df["month"].isin(months)]
        total = d["txs"].sum()
        row = {
            "sample_window": [w["start"], w["end"]], "sample_transactions": w["transactions"], "bigquery_months": months,
            "relayed_tx_share": {"sample": w["relayed_tx_share"], "bigquery": float(d["relayed_txs"].sum() / total)},
            "older_than_1y_tx_share": {"sample": w["tx_share_by_account_age"]["365d+"], "sample_ci95": w["tx_share_ci95"]["365d+"],
                                       "bigquery": float(d[d["age"].isin(OLDER_THAN_1Y)]["txs"].sum() / total)},
        }
        hit = [m for m in months if top and m in top.get("months", {})]
        if hit:
            row["top10_tx_share"] = {"sample": w["top10_accounts_tx_share"], "bigquery_month": hit[-1],
                                     "bigquery": top["months"][hit[-1]]["top10_share"]}
        out[label] = row
    return out


def cell_that_left(df: pd.DataFrame, month: str) -> dict | None:
    """For a month of mass deletions that the census's burst rule does not catch: the cell of the core (family, age,
    active the month before) that lost the most accounts from that month to the next, with the months either side.

    A deleted account signs one last transaction and is not seen again, so a cell that held them shrinks the month
    after. Accounts that were active the month before are not "dormant", and the rule of
    implicit_one_transaction_bursts does not see them; this says where in the census they are.
    """
    core = segment(df, "core")
    p = pd.Period(month, "M")
    keys = ["family", "age", "prev_month"]
    now = core[core["month"] == month].groupby(keys)["accounts"].sum()
    after = core[core["month"] == str(p + 1)].groupby(keys)["accounts"].sum().reindex(now.index).fillna(0)
    if now.empty:
        return None
    family, age, prev_month = (now - after).idxmax()
    cell = core[(core["family"] == family) & (core["age"] == age) & (core["prev_month"] == prev_month)]
    out = {"family": str(family), "age": str(age), "prev_month": str(prev_month)}
    for key, m in (("month_before", p - 1), ("month", p), ("month_after", p + 1)):
        r = cell[cell["month"] == str(m)]
        out[key] = {"month": str(m), "accounts": int(r["accounts"].sum()), "single_tx_accounts": int(r["single_tx_accounts"].sum()),
                    "txs": int(r["txs"].sum()), "relayed_txs": int(r["relayed_txs"].sum())}
    return out
