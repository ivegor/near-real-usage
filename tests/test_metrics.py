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


def test_month_change_uses_the_last_complete_calendar_month():
    idx = pd.date_range("2025-01-01", "2026-11-11", freq="D")
    s = pd.Series(np.where(idx >= "2026-01-01", 200.0, 100.0), index=idx)
    out = metrics.month_change(s)
    assert out["month"] == "2026-10" and out["pct_change"] == 100


def test_fees_are_tested_in_near_not_usd():
    s = metrics.summarize(daily())
    assert "fees_near" in s["lead_vs_price"] and "fees_usd" not in s["lead_vs_price"]
    assert "corr" in s["lead_fees_usd_mechanical"]


def test_build_survives_an_api_outage(tmp_path, monkeypatch):
    import json

    import pytest
    nb, ll = synthetic_raw(days=60)
    monkeypatch.setattr(sources, "RAW_DIR", tmp_path)

    def down(url, retries=3):
        raise RuntimeError("API down")

    monkeypatch.setattr(sources, "_fetch_json", down)
    with pytest.raises(RuntimeError):          # nothing saved yet: the failure is reported
        sources.fetch_all()
    (tmp_path / "nearblocks_charts.json").write_text(json.dumps(nb))
    (tmp_path / "defillama_intents.json").write_text(json.dumps(ll))
    raw = sources.fetch_all()                  # saved copies exist: they are used instead
    assert len(raw["nearblocks_charts"]["charts"]) == 60
    assert json.loads((tmp_path / "_meta.json").read_text())["not_refreshed"] == ["nearblocks_charts", "defillama_intents"]


def test_a_bad_api_reply_never_replaces_the_saved_copy(tmp_path, monkeypatch):
    import json

    import pytest
    nb, ll = synthetic_raw(days=60)
    monkeypatch.setattr(sources, "RAW_DIR", tmp_path)
    (tmp_path / "nearblocks_charts.json").write_text(json.dumps(nb))
    (tmp_path / "defillama_intents.json").write_text(json.dumps(ll))
    monkeypatch.setattr(sources, "_fetch_json", lambda url: {"message": "rate limited"})   # HTTP 200 with the wrong body
    out = sources.fetch_all(offline=False)
    assert out["nearblocks_charts"] == nb                                    # the build falls back to the saved copy
    assert json.loads((tmp_path / "nearblocks_charts.json").read_text()) == nb          # and the file is untouched
    with pytest.raises(RuntimeError):
        sources._check_shape("defillama_intents", {"totalDataChart": []})
