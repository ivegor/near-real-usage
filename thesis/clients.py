"""Who sends NEAR's transactions: the largest accounts, the apps behind them, and concentration.

Reads the committed result of sql/top_accounts.sql (data/bq/top_accounts_result.csv, straight from the
BigQuery console: columns m, sec, cells). Everything here is a full count for a calendar month.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

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


def by_app(month: dict) -> pd.Series:
    """Transactions per app for one month, including the part outside the top 40 counterparties."""
    via = month["via"].assign(app=month["via"]["via"].map(_APP_OF).fillna(OTHER_TOP))
    s = via.groupby("app")["txs"].sum()
    s[TAIL] = month["conc"]["txs"] - int(via["txs"].sum())
    return s.sort_values(ascending=False)


def summarize(data: dict) -> dict:
    latest, prior = max(data), min(data)
    out: dict = {"source": "sql/top_accounts.sql on bigquery-public-data.crypto_near_mainnet_us (13.53 GB scanned)",
                 "latest_month": latest, "prior_month": prior, "months": {}}
    apps = {m: by_app(data[m]) for m in (latest, prior)}
    for m in (latest, prior):
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
    out["reward_apps_share"] = {k: sum(out["apps"][a][f"{k}_share"] for a in REWARD_APPS) for k in ("latest", "prior")}
    out["finance_share"] = {k: sum(out["apps"][a][f"{k}_share"] for a in FINANCE_APPS) for k in ("latest", "prior")}
    for name, group in (("finance_txs", FINANCE_APPS), ("reward_apps_txs", REWARD_APPS)):
        now, then = (sum(out["apps"][a][k] for a in group) for k in ("latest", "prior"))
        out[name] = {"latest": now, "prior": then, "pct_change": (now / then - 1) * 100 if then else float("nan")}
    # users behind each relayer / contract: distinct actors of selected counterparties
    def actors_of(month: str, via: str) -> int:
        v = data[month]["via"]
        hit = v.loc[v["via"] == via, "actors"]
        return int(hit.iloc[0]) if len(hit) else 0

    out["sweat_users"] = {k: actors_of(m, "relayer:sweat-relayer.near") for k, m in (("latest", latest), ("prior", prior))}
    out["intents"] = {}
    for k, m in (("latest", latest), ("prior", prior)):
        a = data[m]["actors"]
        signed = a[a["top_via"] == "intents.near"].nlargest(2, "txs")
        total = int(data[m]["via"].loc[data[m]["via"]["via"] == "intents.near", "txs"].sum())
        out["intents"][k] = {"transactions": total, "actors": actors_of(m, "intents.near"),
                             "top2_signers": list(signed["actor"]),
                             "top2_share": float(signed["txs"].sum() / total) if total else float("nan")}
    out["top_actors_latest"] = data[latest]["actors"].head(10).to_dict("records")
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
