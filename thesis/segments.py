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

from . import population

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
    population.keeps_months(out or CSV, df)
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
    # Concentration month by month: the heavy accounts and their share of the independent self-paid transactions, and
    # the top class alone (10,000 or more a month). One month's figure is read against the months around it.
    d = df.assign(cls=df["txs_in_month"].map(CLASS))
    ind = d[(d["payer"] == "self") & ~d["namespace"].isin(APP_NAMESPACES)]
    top_class = ind[ind["txs_in_month"] == "10,000+"].groupby("month")[["accounts", "self_paid_txs"]].sum().reindex(s.index).fillna(0)
    out["heavy_by_month"] = {m: {"accounts": int(s.loc[m, "heavy_accounts"]), "self_paid_txs": int(s.loc[m, "heavy_self_paid_txs"]),
                                 "share": float(s.loc[m, "heavy_self_paid_txs"] / s.loc[m, "independent_self_paid_txs"]),
                                 "accounts_10000_plus": int(top_class.loc[m, "accounts"]),
                                 "share_10000_plus": float(top_class.loc[m, "self_paid_txs"] / s.loc[m, "independent_self_paid_txs"])}
                             for m in s.index if s.loc[m, "independent_self_paid_txs"]}
    # The regular class month by month, with the relayed transactions inside it (a frequency class counts every
    # transaction of an account; one self-paid transaction makes it self-paying): when the payer changed, by month.
    reg = ind[ind["cls"] == "regular"].groupby("month")[["accounts", "txs", "self_paid_txs"]].sum().reindex(s.index).fillna(0)
    out["regular_by_month"] = {m: {"accounts": int(r["accounts"]), "self_paid_txs": int(r["self_paid_txs"]),
                                   "relayed_txs": int(r["txs"] - r["self_paid_txs"])} for m, r in reg.iterrows()}
    if prior in reg.index and low in reg.index and prior < low:
        after = [m for m in reg.index if prior < m <= low]
        fall_txs, fall_acc = reg.loc[prior, "self_paid_txs"] - reg.loc[low, "self_paid_txs"], reg.loc[prior, "accounts"] - reg.loc[low, "accounts"]
        out["regular_fall_by_month"] = {
            m: {"share_of_the_self_paid_txs_fall": float((reg.loc[prior, "self_paid_txs"] - reg.loc[m, "self_paid_txs"]) / fall_txs) if fall_txs else float("nan"),
                "share_of_the_accounts_fall": float((reg.loc[prior, "accounts"] - reg.loc[m, "accounts"]) / fall_acc) if fall_acc else float("nan")}
            for m in after}
    # Every frequency bucket outside the app namespaces, self-paying and sponsored, in the month of the largest fall of
    # regular accounts against the month before: was that fall the regular class's own?
    if "regular_accounts_largest_monthly_fall" in out:
        f = out["regular_accounts_largest_monthly_fall"]
        rest = d[~d["namespace"].isin(APP_NAMESPACES)].groupby(["payer", "txs_in_month", "month"])["accounts"].sum()
        out["regular_accounts_largest_monthly_fall"]["every_bucket"] = {
            f"{payer} {bucket}": {"before": int(rest.get((payer, bucket, f["month_before"]), 0)), "after": int(rest.get((payer, bucket, f["month"]), 0)),
                                  "pct_change": (rest.get((payer, bucket, f["month"]), 0) / rest.get((payer, bucket, f["month_before"]), 0) - 1) * 100
                                  if rest.get((payer, bucket, f["month_before"]), 0) else float("nan")}
            for payer in ("self", "sponsored") for bucket in CLASS}
    return out


OVERLAP = ("if_one_group_holds_the_other", "if_no_account_is_in_both")  # the two ends of what the tables leave open


def players_counted_as_self_paying(direct: dict | None, relayed: dict | None, fully_sponsored: float | None,
                                   direct_txs_at_most: int | None = None) -> dict:
    """The most players of a game that one month's self-paying accounts can hold. The same rule for every month.

    A player is counted as self-paying in two ways: it called the game's contract itself and paid the fee (`direct`,
    the contract's row in the month's 40 largest), or it acted through the game's relayer and paid for at least one
    other transaction of its own (`relayed`, the relayer's row, less the accounts the relayer pays everything for).
    The tables give the size of each group, not how many accounts are in both, so the most lies between the larger
    group (one group holds the other) and the sum of the two (no account is in both). A contract that is not among the
    month's 40 largest has no count of callers, only a ceiling on its calls (`direct_txs_at_most`); its callers are
    then not counted, and the figure says so.
    """
    out: dict = {"direct_callers": int(direct["accounts"]) if direct else None}
    if not direct and direct_txs_at_most is not None:
        out["direct_txs_at_most"] = int(direct_txs_at_most)
    if relayed and fully_sponsored is not None:
        out.update({"relayer_accounts": int(relayed["accounts"]), "fully_sponsored": int(fully_sponsored),
                    "paying_through_the_relayer": int(max(0.0, float(relayed["accounts"]) - float(fully_sponsored)))})
    groups = [v for v in (out["direct_callers"], out.get("paying_through_the_relayer")) if v is not None]
    out[f"at_most_{OVERLAP[0]}"], out[f"at_most_{OVERLAP[1]}"] = max(groups, default=0), sum(groups)
    return out


def add_reward_game_bound(sg: dict, game: dict, fully_sponsored: dict | None = None) -> None:
    """How much of the fall in regular accounts can be one game changing who pays the fee (clients.GAME_CONTRACT).

    A year ago many players of Meteor's reward game called its contract themselves, so each of them counted as
    self-paying; now a relayer submits those calls, and a player who does nothing else counts as sponsored. The
    committed tables say how many accounts called the game directly, not which frequency class they were in, nor how
    many of them still play, so every count of players here is the most there can be.

    The players are taken out of both months by one rule (players_counted_as_self_paying). A frequency class counts
    every transaction of an account, the relayed ones too, and one self-paid transaction makes an account
    self-paying, so a player whose game calls go through the relayer and who pays for anything else is inside the
    regular accounts. That was true a year ago as well: the relayer already submitted calls to the game then.
    `fully_sponsored` is the number of accounts the game's relayer pays everything for (sql/payers.sql), for both
    months. The change without the game's players then lies between two ends: none of last year's regular accounts
    were players and the most are in this year's class (low), or the most were in last year's class and none are in
    this year's (high). How many of last year's direct callers also acted through the relayer the tables do not say,
    so the high end is given for both extremes, and the larger one is the bound.

    The same holds for transactions. The game's direct calls were paid by their senders, so they are inside last
    year's self-paid transactions of independent accounts and outside this year's: at most all of them
    (add_self_paid_adjustments applies it to both months).
    """
    direct = (game.get("direct") or {}).get("prior")
    if not direct:
        return
    reg = sg["metrics"]["regular_accounts"]
    at_most = min(float(direct["accounts"]), reg["prior"])
    rest = reg["prior"] - at_most
    high = (reg["latest"] / rest - 1) * 100 if rest else float("nan")
    sg["regular_accounts_reward_game_bound"] = {
        "game_players_prior": int(direct["accounts"]),
        "share_of_prior_regular_at_most": at_most / reg["prior"] if reg["prior"] else float("nan"),
        "fall": reg["prior"] - reg["latest"],
        "pct_change_as_counted": reg["pct_change"],
        "pct_change_if_all_of_them_were_regular": high,
    }
    relayed = game.get("relayed") or {}
    both = ("prior", "latest")
    if fully_sponsored and all(relayed.get(k) and fully_sponsored.get(k) is not None for k in both):
        ceiling = {"latest": game.get("smallest_of_the_40_latest")}  # a year ago the contract is among the 40 largest
        players = {k: players_counted_as_self_paying(game["direct"].get(k), relayed[k], fully_sponsored[k], ceiling.get(k))
                   for k in both}
        now = min(players["latest"][f"at_most_{OVERLAP[1]}"], reg["latest"])     # the most players in this year's class
        then = {case: min(players["prior"][f"at_most_{case}"], reg["prior"]) for case in OVERLAP}

        def change(out_now: float, out_then: float) -> float:
            base = reg["prior"] - out_then
            return ((reg["latest"] - out_now) / base - 1) * 100 if base > 0 else float("nan")

        sg["regular_accounts_reward_game_bound"]["without_the_game"] = {
            "players": players,
            "players_still_self_paying_latest_at_most": int(now),
            "players_prior_at_most": {case: int(v) for case, v in then.items()},
            "share_of_prior_regular_at_most": {case: v / reg["prior"] if reg["prior"] else float("nan") for case, v in then.items()},
            "pct_change_low": change(now, 0),
            "pct_change_high": {case: change(0, then[case]) for case in OVERLAP},
            "pct_change_with_the_most_out_of_both_months": {case: change(now, then[case]) for case in OVERLAP},
            # Only the term counted in both years, the accounts that act through the relayer and pay for something of
            # their own. The direct callers are counted a year ago only: this year the contract is not among the 40
            # largest, so who calls it directly the tables do not say, and the low end above is open below.
            "relayer_term_only": {
                "pct_change_low": change(now, 0),
                "pct_change_high": change(0, min(players["prior"]["paying_through_the_relayer"], reg["prior"])),
                "pct_change_with_both_out": change(now, min(players["prior"]["paying_through_the_relayer"], reg["prior"]))},
        }
        # The game's accounts, all of them, a year ago and now. A year ago: the relayer's accounts and the direct
        # callers; a direct caller paid for something itself, so it can be among the relayer's accounts only if it is
        # one of those the relayer did not pay everything for. Now: the relayer's accounts, and direct callers the
        # tables cannot count.
        p_, l_ = players["prior"], players["latest"]
        only_direct = max(0, p_["direct_callers"] - p_["paying_through_the_relayer"]) if p_["direct_callers"] is not None else None
        if only_direct is not None:
            low_then, high_then = p_["relayer_accounts"] + only_direct, p_["relayer_accounts"] + p_["direct_callers"]
            sg["regular_accounts_reward_game_bound"]["game_accounts"] = {
                "prior": {"at_least": int(low_then), "at_most": int(high_then), "only_direct_at_least": int(only_direct)},
                "latest_through_the_relayer": int(l_["relayer_accounts"]),
                "pct_change_if_nobody_calls_it_directly_now": [(l_["relayer_accounts"] / high_then - 1) * 100,
                                                               (l_["relayer_accounts"] / low_then - 1) * 100]}
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


def add_self_paid_adjustments(sg: dict, cl: dict) -> None:
    """Self-paid transactions of independent accounts without two things the committed tables show inside them.

    The first is reward-side traffic: direct calls to the reward-side contracts that sit outside the app namespaces
    (clients.REWARD_SIDE_CONTRACTS_OUTSIDE_NAMESPACES). Whoever sends them pays the fee and is filed by namespace, so
    the calls are in this series in both months; add_reward_game_bound takes them out of last year only, which gives
    the upper end. The second is a sender whose sampled calls all failed (clients.add_failing_senders), in this
    year's month. Each amount is the most that can be inside the series: the tables give a contract's direct calls
    and an account's total, not the namespace of every sender. The figures are published next to the counted one.

    A direct call from an account inside the app namespaces is not in this series at all, and the keyless sample has
    one (a `.tg` account calling the game a year ago). How many of the calls came from there the tables do not say,
    from none to all of them, so the change without the calls is published with both ends of that as well
    (`..._both_ends`): the most taken out of this year and none of last year's, and the other way round. The figure
    that takes every call out of both years is the one for "every caller is outside the namespaces", not a bound.
    """
    txs = sg["metrics"].get("independent_self_paid_txs")
    side = cl.get("reward_side_direct_calls")
    if not txs or not side:
        return
    then, now = side["prior"]["transactions"], side["latest"]["transactions"]
    failed = (cl.get("failing_senders") or {}).get("transactions_latest_all", 0)

    def change(a: float, b: float) -> float:
        return (a / b - 1) * 100 if b else float("nan")

    out = {"pct_change_as_counted": txs["pct_change"],
           "reward_side_direct_txs": {"latest": int(now), "prior": int(then)},
           "pct_change_without_reward_side_direct_txs": change(txs["latest"] - now, txs["prior"] - then)}
    # Reward-side contracts that are not among a month's 40 largest received at most as many calls as the smallest of
    # them each: what the figure above can be missing, in either month, and the range that leaves.
    unseen = side.get("outside_the_40") or {}
    more_then = more_now = 0
    if unseen:
        more_then, more_now = (unseen[k]["transactions_at_most"] for k in ("prior", "latest"))
        out["reward_side_direct_txs_outside_the_40_at_most"] = {"prior": int(more_then), "latest": int(more_now)}
        out["pct_change_without_reward_side_direct_txs_range"] = [
            change(txs["latest"] - now - more_now, txs["prior"] - then), change(txs["latest"] - now, txs["prior"] - then - more_then)]
    # and with the namespace of the callers left open, from none of the calls in the series to all of them
    out["pct_change_without_reward_side_direct_txs_both_ends"] = [
        change(txs["latest"] - now - more_now, txs["prior"]), change(txs["latest"], txs["prior"] - then - more_then)]
    if failed:
        out.update({"failing_sender_txs_latest": int(failed),
                    "pct_change_without_failing_senders": change(txs["latest"] - failed, txs["prior"]),
                    "pct_change_without_both": change(txs["latest"] - now - failed, txs["prior"] - then),
                    "pct_change_without_both_both_ends": [change(txs["latest"] - now - more_now - failed, txs["prior"]),
                                                          change(txs["latest"] - failed, txs["prior"] - then - more_then)]})
    sg["self_paid_txs_adjustments"] = out
