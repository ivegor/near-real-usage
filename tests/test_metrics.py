import numpy as np
import pandas as pd

from thesis import metrics, sources


def synthetic_raw(days: int = 800, lag_weeks: int = 3, seed: int = 0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-09-01", periods=days, freq="D")
    usage = np.exp(np.cumsum(rng.normal(0, 0.03, days)))  # random walk
    # price follows usage with a lag of `lag_weeks` weeks plus noise
    shift = lag_weeks * 7
    price = np.r_[np.ones(shift), usage[:-shift]] * np.exp(rng.normal(0, 0.01, days)) * 3
    active = (50_000 * usage).astype(int)
    new = (active * 0.1).astype(int)
    charts = [
        {
            "date": d.strftime("%Y-%m-%dT00:00:00.000Z"),
            "near_price": str(p),
            "market_cap": str(p * 1e9),
            "txns": str(a * 10),
            "txn_volume_usd": str(a * 100.0),
            "txn_fee_usd": str(a * 0.05),
            "new_accounts": str(n),
            "active_accounts": str(a),
            "deleted_accounts": "1",
            "new_contracts": "5",
            "active_contracts": "100",
        }
        for d, p, a, n in zip(idx, price, active, new)
    ]
    llama = {"totalDataChart": [[int(d.timestamp()), float(a * 20)] for d, a in zip(idx[100:], active[100:])]}
    return {"charts": charts}, llama


def daily():
    nb, ll = synthetic_raw()
    return sources.parse_nearblocks(nb).join(sources.parse_defillama(ll), how="left")


def test_parse_shapes():
    d = daily()
    assert len(d) == 800
    assert {"price_usd", "active_accounts", "intents_volume_usd"} <= set(d.columns)
    assert d["intents_volume_usd"].isna().sum() == 100


def test_derived_values():
    d = metrics.add_derived(daily())
    assert np.allclose(d["returning_share"], 1 - d["new_accounts"] / d["active_accounts"])
    assert np.allclose(d["tx_per_active"], 10, atol=0.01)


def test_period_change_known():
    idx = pd.date_range("2025-01-01", periods=500, freq="D")
    s = pd.Series(np.where(idx < idx[-1] - pd.Timedelta(days=200), 100.0, 150.0), index=idx)
    out = metrics.period_change(s, days=90, lookback_days=365)
    assert round(out["pct_change"]) == 50


def test_lead_lag_recovers_known_lag():
    d = daily()
    best = metrics.best_lead(metrics.lead_lag(d["active_accounts"], d["price_usd"]))
    assert best["lag_weeks"] == 3
    assert best["significant"]


def test_checks_flag_broken_identity():
    d = daily()
    d.iloc[-3:, d.columns.get_loc("new_accounts")] = d["active_accounts"].iloc[-3:] + 1
    c = metrics.checks(d)["new_exceeds_active_days"]
    assert c == {"recent": 3, "prior": 0, "all_history": 3}
    assert (metrics.add_derived(d)["returning_accounts"].iloc[-3:] == 0).all()


def test_best_lead_lists_every_lag_outside_band():
    d = daily()
    best = metrics.best_lead(metrics.lead_lag(d["active_accounts"], d["price_usd"]))
    assert {"lag_weeks": 3, "corr": round(best["corr"], 3)} in best["outside_band"]


def test_summarize_runs():
    s = metrics.summarize(daily())
    assert s["days"] == 800
    assert "returning_accounts" in s["lead_vs_price"]
