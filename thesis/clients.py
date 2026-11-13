"""Who sends NEAR's transactions: the largest accounts, the apps behind them, and concentration.

Reads the committed result of sql/top_accounts.sql (data/bq/top_accounts_result.csv, straight from the
BigQuery console: columns m, sec, cells). Everything here is a full count for a calendar month.
"""
from __future__ import annotations

import zlib
from pathlib import Path

import numpy as np
import pandas as pd

from .population import REWARD_FAMILIES

CSV = Path(__file__).resolve().parent.parent / "data" / "bq" / "top_accounts_result.csv"
USDC = "17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1"

# "via" (called contract, or relayer of a relayed transaction) -> the app or function behind it.
APPS = {
    "Sweat (move-to-earn app)": ["relayer:sweat-relayer.near", "fast-auth.near"],
    "HOT wallet (Telegram)": ["relayer:0-relay.hot.tg", "relayer:relay.tg", "relayer:0here.tg", "game.hot.tg", "firedrop.hot.tg",
                              "v2-omni.firedrop.hot.tg", "v2_1.omni.hot.tg", "bridge-refuel.hot.tg", "tg"],
    "KaiChing (reward app)": ["relayer:hotwallet.kaiching", "wallet.kaiching"],
    "Meteor wallet (Harvest Moon)": ["relayer:meteor-relayer.near", "aa-harvest-moon.near"],
    "Ref Finance / Rhea (DEX, lending)": ["v2.ref-finance.near", "dclv2.ref-labs.near", "token.rhealab.near", "xtoken.rhealab.near",
                                          "meme-priceoracle.ref-labs.near", "acc.ref-labs.near", "contract.main.burrow.near"],
    "NEAR Intents": ["intents.near"],
    "Token contracts (wNEAR, USDC, USDT)": ["wrap.near", USDC, "usdt.tether-token.near"],
    "Bridges, Aurora, chain signatures": ["omni.bridge.near", "omft.near", "zec.omft.near", "btc-connector.bridge.near",
                                          "zcash-connector.bridge.near", "zcash-client.bridge.near", "v1.signer", "aurora",
                                          "0x4e454228.c.aurora", "0x4e45415a.c.aurora", "relayer:bridge-mng.near"],
}
REWARD_APPS = ("Sweat (move-to-earn app)", "HOT wallet (Telegram)", "KaiChing (reward app)", "Meteor wallet (Harvest Moon)")
FINANCE_APPS = ("Ref Finance / Rhea (DEX, lending)", "NEAR Intents", "Token contracts (wNEAR, USDC, USDT)",
                "Bridges, Aurora, chain signatures")
OTHER_TOP, TAIL = "Other contracts in the top 40", "Everything outside the top 40"
_APP_OF = {via: app for app, vias in APPS.items() for via in vias}
# The game Ember sponsored its users' transactions like the reward apps do, but it is not in REWARD_APPS: prediction B4
# (predictions.csv) was frozen with that group as it is, so the group stays and Ember's share is published next to it.
EMBER = ("relayer:mytestapi.embr.playember_reserve.near", "embr.playember_reserve.near")
EXCHANGE = "Ref Finance / Rhea (DEX, lending)"
# Two contracts of the "Other" row that the exchange's own accounts called in October 2025: pyth-oracle.near (the
# price bots pyth-bot.ref-labs.near and pyth-bot-a.ref-labs.near) and acc.toalice.near (watcher05.ref-watchdog.near,
# its only caller). They are not in the exchange's list, which is frozen with prediction B4 like the groups, so the
# figures with them filed under the exchange are published next to the frozen ones.
EXCHANGE_BOT_TARGETS = ("pyth-oracle.near", "acc.toalice.near")
# The same kind of contract in this year's "Other" row: aggregate-oracle.near, called by 8 implicit accounts with
# report_pyth_pro_prices. Its owner is not named in the tables; the keyless sample has one call of the same method to
# agg-oracle.stg.ref-dev-team.near, the exchange's staging copy, so the link to the exchange is read from a contract's
# name and is weaker than for the two above. The figures with it are a further variant, not a replacement.
EXCHANGE_BOT_TARGETS_BY_NAME = ("aggregate-oracle.near",)
# Meteor's reward game, Harvest Moon. A year ago its players called the game contract themselves and paid the fee; now
# Meteor's relayer submits those calls. A player who is still there moved from "self-paying" to "sponsored", so the fall
# of regular self-paying accounts cannot be read as users leaving (see segments.add_reward_game_bound). How many of
# them are still there the tables do not say.
GAME_CONTRACT, GAME_RELAYER = "aa-harvest-moon.near", "relayer:meteor-relayer.near"
GAME_SPONSOR = "meteor"  # the name sql/payers.sql gives the accounts that relayer pays everything for (payers.SPONSORS)
GAME_CLAIM = "claim_meteor_staking_reward"  # the game's reward claim; in the block sample it arrives in alphabetical batches
INTENTS_CONTRACT = "intents.near"  # the keyless sample is asked how the transactions sent to it ended


def _in_app_namespace(account: str) -> bool:
    """True for an account inside a namespace the account census files with the reward apps (.kaiching, .tg, .sweat)."""
    return any(account == ns or account.endswith("." + ns) for ns in REWARD_FAMILIES)


# Reward-side contracts that sit outside those namespaces: Sweat's fast-auth.near, Meteor's game, Ember's contract. A
# direct call to one of them is paid by its sender, and the census files an account by its namespace, so such calls are
# inside "self-paid transactions outside the reward apps" although the app table files them with the reward side. The
# list follows from the groups above by a rule, not by hand: every reward-side entry that is a contract (not a relayer)
# and is not in an app namespace.
REWARD_SIDE_CONTRACTS_OUTSIDE_NAMESPACES = tuple(
    v for v in [via for app in REWARD_APPS for via in APPS[app]] + list(EMBER)
    if not v.startswith("relayer:") and not _in_app_namespace(v))


def load(path: Path | None = None) -> dict | None:
    """{month: {"via": DataFrame, "actors": DataFrame, "conc": dict}} or None when the file is absent."""
    path = path or CSV
    if not path.exists():
        return None
    out: dict = {}
    for m, sec, cells in pd.read_csv(path).itertuples(index=False):
        month = out.setdefault(str(m), {})
        parts = [c.split("|") for c in str(cells).split(";")]
        if sec == "via":
            month["via"] = pd.DataFrame([(v, int(n), int(a)) for v, n, a in parts], columns=["via", "txs", "actors"])
        elif sec == "actors":
            month["actors"] = pd.DataFrame([(a, int(n), v) for a, n, v in parts], columns=["actor", "txs", "top_via"])
        else:
            keys = ["txs", "actors", "heavy_actors", "heavy_txs", "top10_txs", "top25_txs", "top100_txs", "n50", "n80"]
            month["conc"] = dict(zip(keys, map(int, parts[0])))
    return out


def via_row_of(month: dict, via: str) -> dict | None:
    """One row of a month's "via" table: transactions received and the distinct accounts behind them."""
    v = month["via"]
    hit = v[v["via"] == via]
    return {"transactions": int(hit["txs"].iloc[0]), "accounts": int(hit["actors"].iloc[0])} if len(hit) else None


def by_app(month: dict) -> pd.Series:
    """Transactions per app for one month, including the part outside the top 40 counterparties."""
    via = month["via"].assign(app=month["via"]["via"].map(_APP_OF).fillna(OTHER_TOP))
    s = via.groupby("app")["txs"].sum()
    s[TAIL] = month["conc"]["txs"] - int(via["txs"].sum())
    return s.sort_values(ascending=False)


def compared_months(data: dict) -> tuple[str, str]:
    """The latest month in the file and the month it is compared with: the same month a year earlier.

    The query is run for two months a year apart, and a later run adds its two months to the file. The earliest month
    is used only when the file does not hold the one a year earlier; the summary names both months either way.
    """
    latest = max(data)
    a_year_earlier = (pd.Period(latest, "M") - 12).strftime("%Y-%m")
    return latest, a_year_earlier if a_year_earlier in data else min(data)


def summarize(data: dict) -> dict:
    latest, prior = compared_months(data)
    out: dict = {"source": "sql/top_accounts.sql on bigquery-public-data.crypto_near_mainnet_us (13.53 GB scanned)",
                 "latest_month": latest, "prior_month": prior, "months": {}}
    apps = {m: by_app(data[m]) for m in (latest, prior)}
    # concentration for every month the file holds: the two compared ones first, then any other (an earlier run)
    for m in [latest, prior] + sorted(set(data) - {latest, prior}):
        c = data[m]["conc"]
        half_reached = c["heavy_txs"] >= 0.5 * c["txs"]
        out["months"][m] = {
            "transactions": c["txs"], "actors": c["actors"],
            "accounts_with_1000_plus_txs": c["heavy_actors"], "their_tx_share": c["heavy_txs"] / c["txs"],
            "top10_share": c["top10_txs"] / c["txs"], "top25_share": c["top25_txs"] / c["txs"],
            "top100_share": c["top100_txs"] / c["txs"],
            "accounts_for_half_of_txs": c["n50"] if half_reached else None,
        }
    out["apps"] = {
        app: {"latest": int(apps[latest].get(app, 0)), "prior": int(apps[prior].get(app, 0)),
              "latest_share": float(apps[latest].get(app, 0) / data[latest]["conc"]["txs"]),
              "prior_share": float(apps[prior].get(app, 0) / data[prior]["conc"]["txs"])}
        for app in list(APPS) + [OTHER_TOP, TAIL]
    }
    for v in out["apps"].values():
        v["pct_change"] = (v["latest"] / v["prior"] - 1) * 100 if v["prior"] else float("nan")
    both = (("latest", latest), ("prior", prior))
    groups = {name: {k: sum(out["apps"][a][k] for a in group) for k, _ in both}
              for name, group in (("finance_txs", FINANCE_APPS), ("reward_apps_txs", REWARD_APPS))}
    # shares are taken from the integer counts, so they do not depend on how a Python version adds floats
    out["reward_apps_share"] = {k: groups["reward_apps_txs"][k] / data[m]["conc"]["txs"] for k, m in both}
    out["finance_share"] = {k: groups["finance_txs"][k] / data[m]["conc"]["txs"] for k, m in both}
    for name, t in groups.items():
        out[name] = {**t, "pct_change": (t["latest"] / t["prior"] - 1) * 100 if t["prior"] else float("nan")}

    # A group is a list of contracts and relayers, and a month counts only those among its 40 largest: the others sit
    # in "Everything outside the top 40" for that month. Each of them received at most as many transactions as the
    # smallest entry of that month's list, which bounds what a group can be missing and how far its change can be off.
    def outside(month: str, group: tuple) -> dict:
        listed, floor = set(data[month]["via"]["via"]), int(data[month]["via"]["txs"].min())
        missing = [v for app in group for v in APPS[app] if v not in listed]
        return {"contracts": len(missing), "transactions_each_at_most": floor, "transactions_at_most": len(missing) * floor}

    unseen = {name: {k: outside(m, group) for k, m in both}
              for name, group in (("finance", FINANCE_APPS), ("reward_apps", REWARD_APPS))}
    out["groups_outside_the_40"] = unseen
    fin, total = groups["finance_txs"], data[latest]["conc"]["txs"]
    more_then, more_now = (unseen["finance"][k]["transactions_at_most"] for k in ("prior", "latest"))
    out["finance_txs_change_range"] = [
        (fin["latest"] / (fin["prior"] + more_then) - 1) * 100 if fin["prior"] + more_then else float("nan"),
        ((fin["latest"] + more_now) / fin["prior"] - 1) * 100 if fin["prior"] else float("nan")]
    bots = {k: int(data[m]["via"].loc[data[m]["via"]["via"].isin(EXCHANGE_BOT_TARGETS), "txs"].sum()) for k, m in both}
    ex = out["apps"][EXCHANGE]
    out["exchange_bot_targets"] = {
        "contracts": list(EXCHANGE_BOT_TARGETS), **bots,
        "exchange_pct_change_with_them": ((ex["latest"] + bots["latest"]) / (ex["prior"] + bots["prior"]) - 1) * 100
        if ex["prior"] + bots["prior"] else float("nan"),
        "finance_pct_change_with_them": ((fin["latest"] + bots["latest"]) / (fin["prior"] + bots["prior"]) - 1) * 100
        if fin["prior"] + bots["prior"] else float("nan")}
    both_years = EXCHANGE_BOT_TARGETS + EXCHANGE_BOT_TARGETS_BY_NAME
    named_bots = {k: int(data[m]["via"].loc[data[m]["via"]["via"].isin(both_years), "txs"].sum()) for k, m in both}
    out["exchange_bot_targets_with_the_oracle_by_name"] = {
        "contracts": list(both_years), **named_bots,
        "exchange_pct_change_with_them": ((ex["latest"] + named_bots["latest"]) / (ex["prior"] + named_bots["prior"]) - 1) * 100
        if ex["prior"] + named_bots["prior"] else float("nan"),
        "finance_pct_change_with_them": ((fin["latest"] + named_bots["latest"]) / (fin["prior"] + named_bots["prior"]) - 1) * 100
        if fin["prior"] + named_bots["prior"] else float("nan")}
    # Callers of the financial group's contracts that are in both months' lists: the accounts behind the transactions.
    # A contract's callers cannot be added to another's (one account calls several), so they are given one by one.
    rows = []
    for v in [x for app in FINANCE_APPS for x in APPS[app]]:
        a, b = via_row_of(data[prior], v), via_row_of(data[latest], v)
        if a and b:
            rows.append({"contract": v, "callers": {"prior": a["accounts"], "latest": b["accounts"]},
                         "transactions": {"prior": a["transactions"], "latest": b["transactions"]},
                         "callers_pct_change": (b["accounts"] / a["accounts"] - 1) * 100 if a["accounts"] else float("nan"),
                         "transactions_pct_change": (b["transactions"] / a["transactions"] - 1) * 100 if a["transactions"] else float("nan")})
    out["finance_contract_callers"] = sorted(rows, key=lambda r: -r["callers"]["prior"])
    # The "Other contracts in the top 40" row without Ember, contract by contract: is it the same activity in both months?
    named = set(_APP_OF) | set(EMBER)
    rest = {k: data[m]["via"][~data[m]["via"]["via"].isin(named)] for k, m in both}
    out["other_top_40"] = {
        **{k: [{"contract": r.via, "transactions": int(r.txs), "accounts": int(r.actors)} for r in rest[k].itertuples()] for k, _ in both},
        "in_both_months": sorted(set(rest["latest"]["via"]) & set(rest["prior"]["via"]))}
    # Direct calls to the reward-side contracts outside the app namespaces, as far as each month's 40 largest show them.
    side = {k: data[m]["via"][data[m]["via"]["via"].isin(REWARD_SIDE_CONTRACTS_OUTSIDE_NAMESPACES)] for k, m in both}
    out["reward_side_direct_calls"] = {
        "contracts": list(REWARD_SIDE_CONTRACTS_OUTSIDE_NAMESPACES),
        "outside_the_40": {k: {"contracts": len(set(REWARD_SIDE_CONTRACTS_OUTSIDE_NAMESPACES) - set(data[m]["via"]["via"])),
                               "transactions_at_most": len(set(REWARD_SIDE_CONTRACTS_OUTSIDE_NAMESPACES) - set(data[m]["via"]["via"]))
                               * int(data[m]["via"]["txs"].min())} for k, m in both},
        **{k: {"transactions": int(side[k]["txs"].sum()),
               "by_contract": {r.via: {"transactions": int(r.txs), "accounts": int(r.actors)} for r in side[k].itertuples()}}
           for k, _ in both}}
    gap = groups["reward_apps_txs"]["latest"] - fin["latest"]  # what prediction B4 is scored on, as a share of all transactions
    out["reward_minus_finance_share"] = {
        "latest": gap / total,
        "latest_range": [(gap - more_now) / total, (gap + unseen["reward_apps"]["latest"]["transactions_at_most"]) / total]}

    # one row of the "via" table: the transactions a contract or relayer received and the distinct accounts behind them
    def via_row(month: str, via: str) -> dict | None:
        v = data[month]["via"]
        hit = v[v["via"] == via]
        return {"transactions": int(hit["txs"].iloc[0]), "accounts": int(hit["actors"].iloc[0])} if len(hit) else None

    def actors_of(month: str, via: str) -> int:
        row = via_row(month, via)
        return row["accounts"] if row else 0

    out["sweat_users"] = {k: actors_of(m, "relayer:sweat-relayer.near") for k, m in (("latest", latest), ("prior", prior))}
    out["intents"] = {}
    for k, m in (("latest", latest), ("prior", prior)):
        a = data[m]["actors"]
        # The query gives each account's total and its most frequent destination, not its count per destination, so
        # the share of the two largest is an upper bound: all of their transactions are taken as sent to intents.near.
        signed = a[a["top_via"] == "intents.near"].nlargest(2, "txs")
        total = int(data[m]["via"].loc[data[m]["via"]["via"] == "intents.near", "txs"].sum())
        out["intents"][k] = {"transactions": total, "actors": actors_of(m, "intents.near"),
                             "top2_signers": list(signed["actor"]),
                             "top2_share": float(signed["txs"].sum() / total) if total else float("nan")}
    out["top_actors_latest"] = data[latest]["actors"].head(10).to_dict("records")
    # Concentration above counts a relayed transaction for the account the relayer acted for. Counted by signer the
    # starting point is another one: the largest relayer of each month and its share of all transactions.
    out["largest_relayer"] = {}
    for k, m in (("latest", latest), ("prior", prior)):
        via = data[m]["via"]
        r = via[via["via"].str.startswith("relayer:")].nlargest(1, "txs")
        if len(r):
            out["largest_relayer"][k] = {"relayer": r["via"].iloc[0].split(":", 1)[1], "transactions": int(r["txs"].iloc[0]),
                                         "share_of_all_transactions": float(r["txs"].iloc[0] / data[m]["conc"]["txs"])}
    # the exchange contract by contract: the same account may call several, so their account counts cannot be added
    v = data[latest]["via"]
    app_txs = out["apps"][EXCHANGE]["latest"]
    out["exchange_contracts_latest"] = [
        {"contract": r.via, "transactions": int(r.txs), "accounts": int(r.actors), "share_of_app_txs": float(r.txs / app_txs)}
        for r in v[v["via"].isin(APPS[EXCHANGE])].itertuples()]
    ember = {k: int(data[m]["via"].loc[data[m]["via"]["via"].isin(EMBER), "txs"].sum()) for k, m in (("latest", latest), ("prior", prior))}
    share = {k: ember[k] / data[m]["conc"]["txs"] for k, m in (("latest", latest), ("prior", prior))}
    out["ember"] = {**ember, "latest_share": float(share["latest"]), "prior_share": float(share["prior"]),
                    "reward_apps_share_with_ember": {k: float(out["reward_apps_share"][k] + share[k]) for k in ("latest", "prior")}}
    # Meteor's reward game: called directly by its players (who then pay the fee) or through Meteor's relayer
    game = {"contract": GAME_CONTRACT, "relayer": GAME_RELAYER.split(":", 1)[1],
            "direct": {k: via_row(m, GAME_CONTRACT) for k, m in both},
            "relayed": {k: via_row(m, GAME_RELAYER) for k, m in both},
            # a contract that is not in the table received fewer transactions than the smallest one that is
            "smallest_of_the_40_latest": int(data[latest]["via"]["txs"].min())}
    for row in game["direct"].values():
        if row:
            row["transactions_per_account"] = row["transactions"] / row["accounts"]
    out["reward_game"] = game
    return out


def add_namespace_view(cl: dict, kaiching_namespace_txs: float) -> None:
    """Reward apps counted by where the accounts come from, not only by the contract or relayer used.

    In October 2026 old KaiChing accounts sent one transaction each to contracts outside the top 40, so the app table
    files them under "everything else". Counting them by namespace raises the reward apps' share.
    """
    total = cl["months"][cl["latest_month"]]["transactions"]
    in_table = cl["apps"]["KaiChing (reward app)"]["latest"]
    extra = max(0.0, float(kaiching_namespace_txs) - in_table)
    cl["kaiching_txs_outside_its_contracts"] = extra
    cl["kaiching_share_by_namespace"] = float(kaiching_namespace_txs) / total
    cl["reward_apps_share_incl_kaiching_namespace"] = cl["reward_apps_share"]["latest"] + extra / total


def add_three_parts(cl: dict, kaiching_namespace_txs_prior: float) -> None:
    """Every transaction in one of three parts: the reward side, the finance group, and the rest of the chain.

    The two bottom rows of the app table ("Other contracts in the top 40", "Everything outside the top 40") are what is
    left after the named apps, and two reward-side flows sit inside them: the game Ember, which sponsored its users as
    the reward apps do, and transactions that KaiChing's own accounts sent to contracts outside the table (a year ago
    those of its account `users.kaiching`, in October 2026 the one-off sweep). Read without them, the two rows show
    what the rest of the chain did. REWARD_APPS and FINANCE_APPS are not changed by this: the split
    is published next to them. Call after add_namespace_view.
    """
    keys = ("latest", "prior")
    extra = {"latest": float(cl["kaiching_txs_outside_its_contracts"]),
             "prior": max(0.0, float(kaiching_namespace_txs_prior) - cl["apps"]["KaiChing (reward app)"]["prior"])}

    def change(v: dict) -> dict:
        return {"latest": float(v["latest"]), "prior": float(v["prior"]),
                "pct_change": (v["latest"] / v["prior"] - 1) * 100 if v["prior"] else float("nan")}

    other = {k: cl["apps"][OTHER_TOP][k] - cl["ember"][k] for k in keys}
    tail = {k: cl["apps"][TAIL][k] - extra[k] for k in keys}
    cl["kaiching_txs_outside_its_contracts_prior"] = extra["prior"]
    cl["reward_apps_share_incl_kaiching_namespace_prior"] = (
        cl["reward_apps_share"]["prior"] + extra["prior"] / cl["months"][cl["prior_month"]]["transactions"])
    bots = cl.get("exchange_bot_targets") or {}
    cl["three_parts"] = {
        "reward_side": change({k: cl["reward_apps_txs"][k] + cl["ember"][k] + extra[k] for k in keys}),
        "finance": change(cl["finance_txs"]),
        "rest": change({k: other[k] + tail[k] for k in keys}),
        # the same without the two contracts the exchange's own bots called (see EXCHANGE_BOT_TARGETS)
        "rest_without_exchange_bot_targets": change({k: other[k] + tail[k] - bots.get(k, 0) for k in keys}),
        # and without this year's oracle as well (EXCHANGE_BOT_TARGETS_BY_NAME)
        "rest_without_exchange_bot_targets_and_the_oracle_by_name": change(
            {k: other[k] + tail[k] - (cl.get("exchange_bot_targets_with_the_oracle_by_name") or {}).get(k, 0) for k in keys}),
        "other_top_40_without_ember": change(other),
        "outside_top_40_without_kaiching": change(tail),
    }


def add_failing_senders(cl: dict, data: dict, window: tuple[str, str] | None = None) -> None:
    """A sender whose sampled calls to NEAR Intents all failed, taken out of the counts it sits in.

    None of the queries here reads how a transaction ended: a failed one is counted like any other. The keyless sample
    knows how the transactions sent to NEAR Intents ended (census.fetch_outcomes, in cl["intents_outcomes"]). A sender
    named there whose sampled transactions all failed is taken out of the latest month. The query gives an account's
    transactions of the month and its most frequent destination, not its count per destination, so all of them are
    taken: at most that many went to NEAR Intents. Nothing is taken out of the month a year earlier: the sample says
    nothing about it, and an account that is not among that month's 40 largest sent fewer than the smallest of them.

    `window` is the first and last day the outcomes were sampled in; the latest month has to lie inside it, otherwise
    nothing is said. The counted figures stay as they are: these are published next to them.
    """
    ended = cl.get("intents_outcomes") or {}
    if ended.get("target") != INTENTS_CONTRACT:
        return
    latest, prior = cl["latest_month"], cl["prior_month"]
    month = pd.Period(latest, "M")
    if window and not (pd.Timestamp(window[0]) <= month.start_time and month.end_time.normalize() <= pd.Timestamp(window[1])):
        return
    failing = [s for s, v in (ended.get("senders") or {}).items() if v["transactions"] and v["failed"] == v["transactions"]]

    def sent(m: str, account: str) -> int | None:
        a = data[m]["actors"]
        hit = a[(a["actor"] == account) & (a["top_via"] == INTENTS_CONTRACT)]
        return int(hit["txs"].iloc[0]) if len(hit) else None

    now = {s: sent(latest, s) for s in failing}
    total = sum(v for v in now.values() if v)
    if not total:
        return

    def change(a: float, b: float) -> float:
        return (a / b - 1) * 100 if b else float("nan")

    fin, received, bots = cl["finance_txs"], cl["intents"], cl.get("exchange_bot_targets") or {}
    cl["failing_senders"] = {
        "target": INTENTS_CONTRACT,
        "sampled": {s: ended["senders"][s] for s in failing},
        "transactions_latest": now, "transactions_latest_all": total,
        "transactions_prior": {s: sent(prior, s) for s in failing},
        "smallest_of_the_40_accounts_prior": int(data[prior]["actors"]["txs"].min()),
        "share_of_target_txs_latest": total / received["latest"]["transactions"],
        "target_pct_change_without_them": change(received["latest"]["transactions"] - total, received["prior"]["transactions"]),
        "finance_pct_change_without_them": change(fin["latest"] - total, fin["prior"]),
        # and with the two contracts the exchange's own bots called a year earlier filed with the exchange as well
        "finance_pct_change_without_them_and_with_the_exchange_bot_targets": change(
            fin["latest"] - total + bots.get("latest", 0), fin["prior"] + bots.get("prior", 0)),
        "finance_pct_change_without_them_and_with_the_oracle_by_name": change(
            fin["latest"] - total + (cl.get("exchange_bot_targets_with_the_oracle_by_name") or {}).get("latest", 0),
            fin["prior"] + (cl.get("exchange_bot_targets_with_the_oracle_by_name") or {}).get("prior", 0)),
    }


def sampled_per_day(rows: pd.DataFrame, hit: pd.Series, per_day: float, rng: np.random.Generator, n_boot: int = 4000) -> dict:
    """Transactions a day of the sampled transactions marked by `hit`, with a 95% interval that resamples whole blocks.

    The share of the sample times the aggregator's transactions a day for the same days estimates the count; blocks
    are resampled, not transactions, because the transactions of one block are not independent. The figures are
    rounded to whole transactions: they are estimates from a few hundred transactions at most.
    """
    blocks = rows.groupby("height").size()
    num = hit.groupby(rows["height"]).sum().reindex(blocks.index).to_numpy(float)
    den = blocks.to_numpy(float)
    pick = rng.integers(0, len(den), size=(n_boot, len(den)))
    lo, hi = np.percentile(num[pick].sum(axis=1) / den[pick].sum(axis=1), [2.5, 97.5])
    return {"per_day": int(round(float(hit.mean()) * per_day)), "per_day_ci95": [int(round(lo * per_day)), int(round(hi * per_day))],
            "sampled": int(hit.sum())}


SAMPLE_PARTS = {"finance": FINANCE_APPS, "reward_apps": REWARD_APPS,
                # the finance group in two parts: what moves with trading and what moves with cross-chain flows
                "exchange_and_tokens": (EXCHANGE, "Token contracts (wNEAR, USDC, USDT)"),
                "intents_and_bridges": ("NEAR Intents", "Bridges, Aurora, chain signatures")}


def sampled_periods(sample: pd.DataFrame, label: str, periods: list[tuple[pd.Timestamp, pd.Timestamp]], daily: pd.DataFrame,
                    groups: dict[str, set], seed: int, extra: dict[str, pd.Series] | None = None) -> list[dict]:
    """The groups of one window of the keyless sample over the given periods (first and last day of each).

    `extra` holds further marks of the sampled transactions (True or False for each row), estimated the same way. The
    resampling of each estimate is seeded by the period and the group's name, so that the same group over the same
    days gets the same interval wherever it is published.
    """
    via = pd.Series(np.where(sample["relayed"], "relayer:" + sample["signer"], sample["target"]), index=sample.index)
    day = pd.to_datetime(sample["ts"], unit="ns").dt.normalize()
    rows_all = sample[sample["window"] == label]
    out = []
    for a, b in periods:
        rows = rows_all[(day[rows_all.index] >= a) & (day[rows_all.index] <= b)]
        span = daily.loc[a:b, "txns"].dropna()
        if rows.empty or span.empty:
            continue
        per_day = float(span.mean())
        cell = {"from": str(a.date()), "through": str(b.date()), "days": int(len(span)), "sample_transactions": int(len(rows)),
                "blocks": int(rows["height"].nunique()), "all_transactions_per_day": int(round(per_day))}
        def rng(name: str) -> np.random.Generator:
            return np.random.default_rng([seed, a.toordinal(), b.toordinal(), zlib.crc32(name.encode())])

        for name, vias in groups.items():
            cell[name] = sampled_per_day(rows, via[rows.index].isin(vias), per_day, rng(name))
        for name, mark in (extra or {}).items():
            cell[name] = sampled_per_day(rows, mark[rows.index].astype(bool), per_day, rng(name))
        out.append(cell)
    return out


def sampled_months(sample: pd.DataFrame, windows: dict, daily: pd.DataFrame, seed: int = 0, split: str | None = None) -> dict:
    """The groups of the keyless sample month by month inside each window: a calendar month cut to the window's days.

    A 90-day window that starts in mid-August holds the second half of that month, so the sample says something about
    the weeks before the price rally of September 2026, and about the same weeks a year earlier. With `split` (a month,
    the step month of the predictions), each window is also cut in two there: the days before it and the days from it.
    """
    groups = {name: {v for app in group for v in APPS[app]} for name, group in SAMPLE_PARTS.items()}
    out: dict = {"by_month": {}, "split": {}}
    for label, w in sorted(windows.items()):
        start, end = pd.Timestamp(w["start"]), pd.Timestamp(w["end"])
        months = list(pd.period_range(start, end, freq="M"))
        cells = sampled_periods(sample, label, [(max(start, m.start_time), min(end, m.end_time.normalize())) for m in months],
                                daily, groups, seed)
        out["by_month"][label] = {c["from"][:7]: c for c in cells}
        if split:
            cut = pd.Period(split, "M").start_time - pd.DateOffset(years=0 if label == "recent" else 1)
            if start < cut <= end:
                before, after = sampled_periods(sample, label, [(start, cut - pd.Timedelta(days=1)), (cut, end)], daily, groups, seed)
                out["split"][label] = {"before": before, "from": after,
                                       "pct_change": {name: (after[name]["per_day"] / before[name]["per_day"] - 1) * 100
                                                      if before[name]["per_day"] else float("nan") for name in groups}}
    return out


def sample_view(sample: pd.DataFrame, windows: dict, daily: pd.DataFrame, seed: int = 0, n_boot: int = 4000) -> dict | None:
    """The reward and finance groups measured a second way, on the keyless block sample (thesis/census.py).

    The app table is two calendar months. The sample covers two 90-day windows, so it shows whether the same change
    appears over a longer period. A sampled transaction is filed as a row of the table is: by the contract it calls,
    or by its relayer when it was relayed. The group's share of the sample times the aggregator's transaction count
    for the window estimates its transactions; the 95% interval resamples whole blocks (transactions in a block are
    not independent).
    """
    labels = ("prior", "recent")
    if not set(labels) <= set(windows) or not set(labels) <= set(sample["window"]):
        return None
    via = pd.Series(np.where(sample["relayed"], "relayer:" + sample["signer"], sample["target"]), index=sample.index)
    out: dict = {"windows": {}, "groups": {}}
    per_day, draws = {}, {}
    for i, label in enumerate(labels):
        w = sample[sample["window"] == label]
        span = daily.loc[windows[label]["start"]:windows[label]["end"], "txns"].dropna()
        if span.empty:
            return None
        per_day[label] = float(span.sum() / len(span))
        out["windows"][label] = {"window": [windows[label]["start"], windows[label]["end"]], "sample_transactions": int(len(w)),
                                 "all_transactions": int(span.sum())}
        blocks = w.groupby("height").size()
        pick = np.random.default_rng([seed, i]).integers(0, len(blocks), size=(n_boot, len(blocks)))
        draws[label] = (w, blocks, pick)
    for name, group in (("finance", FINANCE_APPS), ("reward_apps", REWARD_APPS)):
        vias = {v for app in group for v in APPS[app]}
        row, boot = {}, {}
        for label in labels:
            w, blocks, pick = draws[label]
            hit = via[w.index].isin(vias)
            in_block = hit.groupby(w["height"]).sum().reindex(blocks.index).to_numpy(float)
            boot[label] = in_block[pick].sum(axis=1) / blocks.to_numpy(float)[pick].sum(axis=1) * per_day[label] * 30
            lo, hi = np.percentile(boot[label], [2.5, 97.5]) / (per_day[label] * 30)
            row[label] = {"share": float(hit.mean()), "share_ci95": [round(float(lo), 4), round(float(hi), 4)],
                          "transactions_per_30_days": float(hit.mean() * per_day[label] * 30)}
        then = row["prior"]["transactions_per_30_days"]
        lo, hi = np.nanpercentile(boot["recent"] / np.where(boot["prior"] > 0, boot["prior"], np.nan), [2.5, 97.5])
        out["groups"][name] = {**row, "pct_change": (row["recent"]["transactions_per_30_days"] / then - 1) * 100 if then else float("nan"),
                               "pct_change_ci95": [float((lo - 1) * 100), float((hi - 1) * 100)]}
    return out
