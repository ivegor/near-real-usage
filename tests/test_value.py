"""Value capture: buybacks against net new supply, on a small synthetic table (no network)."""
import numpy as np
import pandas as pd
import pytest

from thesis import value


def frames(days=500):
    idx = pd.date_range("2025-07-01", periods=days, freq="D")
    daily = pd.DataFrame({
        "total_supply_yocto": (1_000_000_000 + 100_000 * np.arange(days)) * value.YOCTO,   # +100k NEAR a day
        "price_usd": 2.0, "fees_usd": 1_000.0, "market_cap_usd": 2_000_000_000.0}, index=idx)
    fees = pd.DataFrame({"fees": 40_000.0, "revenue": 10_000.0, "holders_revenue": 10_000.0}, index=idx)
    return daily, fees


def test_coverage_is_buybacks_over_the_value_of_new_supply():
    daily, fees = frames()
    v = value.summarize(daily, fees)
    assert abs(v["net_new_supply_near_annualized"] - 36_500_000) < 1
    assert abs(v["new_supply_value_usd_annualized"] - 73_000_000) < 1
    assert abs(v["buyback_usd_annualized"] - 3_650_000) < 1
    assert abs(v["buyback_coverage_of_new_supply"] - 0.05) < 1e-9 and abs(v["growth_needed_to_cover_new_supply"] - 20) < 1e-6
    assert abs(v["captured_share_of_gross_fees"] - 0.25) < 1e-9 and abs(v["intents_fees_vs_l1_fees"] - 40) < 1e-9


def test_monthly_keeps_complete_months_only():
    daily, fees = frames()
    m = value.monthly(daily, fees)
    assert str(m.index[-1]) == "2026-10" and len(m) == 12            # the series ends on 2026-11-12: November is partial
    assert abs(m["new_supply_value"].iloc[-1] - 31 * 100_000 * 2.0) < 1


def test_fetch_never_replaces_a_saved_copy_with_an_error_page(tmp_path, monkeypatch):
    """An HTTP 200 reply without the series (a rate-limit page) must leave all three saved files as they were."""
    monkeypatch.setattr(value.sources, "RAW_DIR", tmp_path)
    good = {"totalDataChart": [[1_700_000_000 + 86_400 * i, 5.0] for i in range(40)]}
    names = list(value.URLS)
    for name in names:
        (tmp_path / f"{name}.json").write_text('{"saved": true}')
    replies = iter([good, good, {"message": "rate limited"}])       # the third reply is the bad one
    monkeypatch.setattr(value.sources, "_fetch_json", lambda url: next(replies))
    with pytest.raises(RuntimeError, match="no usable 'totalDataChart' series"):
        value.fetch()
    assert all((tmp_path / f"{name}.json").read_text() == '{"saved": true}' for name in names)
    monkeypatch.setattr(value.sources, "_fetch_json", lambda url: good)
    value.fetch()
    assert len(value.load()) == 40 and list(value.load().columns) == ["fees", "revenue", "holders_revenue"]


def test_missing_supply_or_files_means_no_section(tmp_path, monkeypatch):
    daily, fees = frames()
    assert value.summarize(daily.drop(columns="total_supply_yocto"), fees) is None
    monkeypatch.setattr(value.sources, "RAW_DIR", tmp_path)
    assert value.load() is None
