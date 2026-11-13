"""Is the captured revenue really held in NEAR? The balances of NEAR's three revenue wallets, read from the chain.

DefiLlama's "revenue" and "buyback" series for NEAR Intents count the NEAR and wNEAR that arrive at three wallets;
its adapter names them (https://github.com/DefiLlama/dimension-adapters/blob/master/fees/near-intents) and reads the
arrivals from Dune tables. This module measures the same money a second way, with no key and no Dune: it asks an
archival RPC node what the three wallets hold at the start and at the end of a window, and 30 days before the end.

The two measurements are not the same thing. DefiLlama adds up what came in; a change in balance is what came in
minus what went out. If the wallets were spending the NEAR, the balances would grow by less than the reported revenue.
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

import pandas as pd

from . import census, sources

# The wallets and their roles as the DefiLlama adapter gives them (its FEE_WALLETS list and comments).
WALLETS = {
    "buybacks.multisignature.near": "buyback wallet",
    "fefundsadmin.sputnik-dao.near": "front-end fund",
    "1csfundsadmin.sputnik-dao.near": "1Click fund",
}
BUYBACK_WALLET = "buybacks.multisignature.near"
WNEAR = "wrap.near"
OFFSETS_DAYS = (90, 30, 0)  # points before the end of the last full day: the window of value.py, its last 30 days
PATH = sources.RAW_DIR / "revenue_wallets.json"
YOCTO = 10**24


def _native(account: str, height: int) -> int:
    res = census._rpc("query", {"request_type": "view_account", "account_id": account, "block_id": height})
    if "result" not in res:
        raise RuntimeError(f"view_account {account}@{height}: {json.dumps(res)[:200]}")
    return int(res["result"]["amount"]) + int(res["result"]["locked"])


def _wnear(account: str, height: int) -> int:
    args = base64.b64encode(json.dumps({"account_id": account}).encode()).decode()
    res = census._rpc("query", {"request_type": "call_function", "account_id": WNEAR, "method_name": "ft_balance_of",
                                "args_base64": args, "block_id": height})
    if "result" not in res or "result" not in res["result"]:
        raise RuntimeError(f"ft_balance_of {account}@{height}: {json.dumps(res)[:200]}")
    return int(json.loads(bytes(res["result"]["result"]).decode()))


def fetch(last_date: str) -> None:
    """Network part (about 40 paced requests): write data/raw/revenue_wallets.json for the window ending on last_date."""
    end = pd.Timestamp(last_date) + pd.Timedelta(days=1)  # the end of the last full day, UTC
    hd = census._rpc("block", {"finality": "final"})["result"]["header"]
    top = (int(hd["height"]), int(hd["timestamp"]))
    floor = census._block_header(top[0] - 30_000_000)  # more than the 90 days of the window, at any block time so far
    points = []
    for days in OFFSETS_DAYS:
        at = end - pd.Timedelta(days=days)
        height = census.height_at(int(at.value), floor, top)
        got = census._block_header(height)
        points.append({
            "at_utc": at.strftime("%Y-%m-%dT%H:%MZ"), "height": got[0], "timestamp_ns": got[1],
            # yoctoNEAR as text: the numbers do not fit a float
            "balances": {w: {"near_yocto": str(_native(w, got[0])), "wnear_yocto": str(_wnear(w, got[0]))} for w in WALLETS},
        })
    data = {"fetched_at_utc": datetime.now(timezone.utc).isoformat(), "rpc": census.RPC_URL, "wnear_contract": WNEAR,
            "wallets": WALLETS, "points": points}
    PATH.parent.mkdir(parents=True, exist_ok=True)
    PATH.write_text(json.dumps(data, indent=1), encoding="utf-8")


def load() -> dict | None:
    return json.loads(PATH.read_text(encoding="utf-8")) if PATH.exists() else None


def _held(point: dict, wallet: str) -> float:
    b = point["balances"][wallet]
    return (int(b["near_yocto"]) + int(b["wnear_yocto"])) / YOCTO


def _window(first: dict, last: dict, daily: pd.DataFrame, fees: pd.DataFrame | None) -> dict | None:
    """Growth of the three balances between two points, set against the new supply of the same days."""
    start = pd.Timestamp(first["at_utc"][:10])                       # the first day of the window
    end = pd.Timestamp(last["at_utc"][:10]) - pd.Timedelta(days=1)   # its last full day
    supply = daily["total_supply_yocto"].dropna() / YOCTO
    if supply.empty or supply.index.max() < end or supply.index.min() > start - pd.Timedelta(days=1):
        return None
    days = int((end - start).days) + 1
    new_supply = float(supply.asof(end) - supply.asof(start - pd.Timedelta(days=1)))
    change = {w: _held(last, w) - _held(first, w) for w in WALLETS}
    total = float(sum(change.values()))
    out = {
        "window": [str(start.date()), str(end.date())], "days": days,
        "change_near": {w: float(v) for w, v in change.items()},
        "change_near_all_wallets": total,
        "change_near_all_wallets_annualized": total * 365 / days,
        "net_new_supply_near": new_supply,
        "coverage_of_new_supply": total / new_supply if new_supply else float("nan"),
        "buyback_wallet_coverage_of_new_supply": change[BUYBACK_WALLET] / new_supply if new_supply else float("nan"),
    }
    if fees is not None and "revenue" in fees:
        # DefiLlama's captured revenue of the same days in NEAR, each day at that day's price
        f = fees["revenue"].loc[start:end]
        price = daily["price_usd"].reindex(f.index)
        reported = float((f / price).sum())
        if f.notna().sum() == days and reported:
            out["defillama_revenue_near"] = reported
            out["balance_growth_over_defillama_revenue"] = total / reported
    return out


def summarize(data: dict, daily: pd.DataFrame, fees: pd.DataFrame | None) -> dict | None:
    if "total_supply_yocto" not in daily:
        return None
    points = sorted(data["points"], key=lambda p: p["height"])
    full = _window(points[0], points[-1], daily, fees)
    if full is None:
        return None
    last = points[-1]
    held = {w: _held(last, w) for w in WALLETS}
    out = {
        "source": data["rpc"], "wallets": data["wallets"],
        "heights": {p["at_utc"]: p["height"] for p in points},
        **full,
        "held_near_at_end": {w: float(v) for w, v in held.items()},
        "held_near_at_end_all_wallets": float(sum(held.values())),
        "buyback_wallet_share_of_held": float(held[BUYBACK_WALLET] / sum(held.values())) if sum(held.values()) else float("nan"),
    }
    if fees is not None and "revenue" in fees:
        # everything the series ever counted as captured revenue, in NEAR at each day's price, to the window's last day
        end = pd.Timestamp(full["window"][1])
        f = fees["revenue"].loc[:end].dropna()
        f = f[f.index >= f[f > 0].index.min()] if (f > 0).any() else f
        price = daily["price_usd"].reindex(f.index)
        if len(f) and price.notna().all():
            ever = float((f / price).sum())
            out["defillama_revenue_near_all_time"] = {"from": str(f.index.min().date()), "through": str(end.date()), "near": ever,
                                                      "held_at_end_over_it": float(sum(held.values()) / ever) if ever else float("nan")}
    if len(points) > 2:
        tail = _window(points[-2], last, daily, fees)
        if tail:
            out["last_days"] = tail
    return out
