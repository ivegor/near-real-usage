"""The on-chain check of captured revenue: balances of the revenue wallets against new supply and DefiLlama."""
import pandas as pd
import pytest

from thesis import value, wallets, sources

YOCTO = 10**24


def _point(at, height, near):
    return {"at_utc": at, "height": height, "timestamp_ns": 0,
            "balances": {w: {"near_yocto": str(int(n * YOCTO)), "wnear_yocto": str(int(wn * YOCTO))}
                         for w, (n, wn) in zip(wallets.WALLETS, near)}}


def _daily(first="2026-01-01", days=40, supply0=1_000_000.0, per_day=1_000.0, price=2.0):
    idx = pd.date_range(first, periods=days, freq="D")
    return pd.DataFrame({"total_supply_yocto": [(supply0 + per_day * i) * YOCTO for i in range(days)],
                         "price_usd": price}, index=idx)


def test_balance_growth_is_set_against_the_new_supply_of_the_same_days():
    daily = _daily()
    data = {"rpc": "test", "wallets": wallets.WALLETS, "points": [
        _point("2026-01-11T00:00Z", 100, [(100.0, 0.0), (50.0, 10.0), (400.0, 0.0)]),
        _point("2026-01-31T00:00Z", 300, [(900.0, 0.0), (150.0, 10.0), (0.0, 0.0)]),
    ]}
    fees = pd.DataFrame({"revenue": 50.0}, index=daily.index)  # $50 a day at $2 = 25 NEAR a day
    s = wallets.summarize(data, daily, fees)
    assert s["window"] == ["2026-01-11", "2026-01-30"] and s["days"] == 20
    # +800 in the buyback wallet, +100 in the front-end fund, -400 in the 1Click fund: a move between wallets cancels
    assert s["change_near_all_wallets"] == pytest.approx(500.0)
    assert s["net_new_supply_near"] == pytest.approx(20_000.0)
    assert s["coverage_of_new_supply"] == pytest.approx(0.025)
    assert s["buyback_wallet_coverage_of_new_supply"] == pytest.approx(0.04)
    assert s["defillama_revenue_near"] == pytest.approx(500.0)
    assert s["balance_growth_over_defillama_revenue"] == pytest.approx(1.0)
    assert s["held_near_at_end_all_wallets"] == pytest.approx(1060.0)
    assert s["buyback_wallet_share_of_held"] == pytest.approx(900 / 1060)
    assert "last_days" not in s  # two points give one window


def test_a_third_point_gives_the_last_days_and_wnear_counts():
    daily = _daily()
    data = {"rpc": "test", "wallets": wallets.WALLETS, "points": [
        _point("2026-01-11T00:00Z", 100, [(0.0, 0.0), (0.0, 0.0), (0.0, 0.0)]),
        _point("2026-01-21T00:00Z", 200, [(10.0, 0.0), (0.0, 5.0), (0.0, 0.0)]),
        _point("2026-01-31T00:00Z", 300, [(10.0, 0.0), (0.0, 105.0), (0.0, 0.0)]),
    ]}
    s = wallets.summarize(data, daily, None)
    assert s["change_near_all_wallets"] == pytest.approx(115.0)
    assert s["last_days"]["window"] == ["2026-01-21", "2026-01-30"] and s["last_days"]["change_near_all_wallets"] == pytest.approx(100.0)
    assert "defillama_revenue_near" not in s


def test_no_figure_when_the_daily_series_does_not_cover_the_window():
    data = {"rpc": "test", "wallets": wallets.WALLETS, "points": [
        _point("2026-01-11T00:00Z", 100, [(0.0, 0.0)] * 3), _point("2026-03-31T00:00Z", 300, [(1.0, 0.0)] * 3)]}
    assert wallets.summarize(data, _daily(), None) is None


def test_the_committed_wallet_file_matches_the_window_of_the_value_summary():
    data = wallets.load()
    daily = sources.load_daily(offline=True)
    fees = value.load()
    s = wallets.summarize(data, daily, fees)
    assert set(data["wallets"]) == set(wallets.WALLETS)
    assert [p["at_utc"] for p in data["points"]] == sorted(p["at_utc"] for p in data["points"])
    assert s["days"] == 90 and s["last_days"]["days"] == 30
    # every point is the first block at or after midnight UTC, within the five minutes the height search allows
    for p in data["points"]:
        assert abs(p["timestamp_ns"] - pd.Timestamp(p["at_utc"][:16]).value) <= 5 * 60 * 10**9
