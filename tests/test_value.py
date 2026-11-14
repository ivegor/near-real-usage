"""Value capture: buybacks against net new supply, on a small synthetic table (no network)."""
import json

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
    assert all((tmp_path / f"{name}.json").read_text(encoding="utf-8") == '{"saved": true}' for name in names)
    monkeypatch.setattr(value.sources, "_fetch_json", lambda url: good)
    value.fetch()
    assert len(value.load()) == 40 and list(value.load().columns) == ["fees", "revenue", "holders_revenue"]


def test_missing_supply_or_files_means_no_section(tmp_path, monkeypatch):
    daily, fees = frames()
    assert value.summarize(daily.drop(columns="total_supply_yocto"), fees) is None
    monkeypatch.setattr(value.sources, "RAW_DIR", tmp_path)
    assert value.load() is None


def test_window_ends_on_the_last_day_both_series_cover():
    """A fee series that stops early must not turn 70 days of buybacks into "the last 90 days"."""
    daily, fees = frames()
    late = fees.iloc[:-20]                                       # the fee series stops 20 days before the daily table
    v = value.summarize(daily, late)
    assert v["window"][1] == str(late.index.max().date()) and v["days_behind_the_daily_series"] == 20
    assert abs(v["buyback_coverage_of_new_supply"] - 0.05) < 1e-9 and v["days_without_buyback_data"] == 0   # 90 days against 90 days
    full = value.summarize(daily, fees)
    assert full["days_behind_the_daily_series"] == 0 and full["window"][1] == str(daily.index.max().date())
    # and a month the fee series has not finished is not drawn as a complete month
    assert str(value.monthly(daily, fees.loc[:"2026-10-29"]).index[-1]) == "2026-09"
    assert value.summarize(daily, fees.assign(holders_revenue=np.nan)) is None      # no day covered by all three series


def test_a_missing_day_stays_missing(tmp_path, monkeypatch):
    """A day one series does not carry, or carries as null, is not a day with zero revenue."""
    monkeypatch.setattr(value.sources, "RAW_DIR", tmp_path)
    points = [[1_700_000_000 + 86_400 * i, 5.0] for i in range(40)]
    for name in value.URLS:
        rows = list(points)
        if name.endswith("holders_revenue"):
            rows[20] = [rows[20][0], None]                       # a null value
            del rows[10]                                         # and a day that is not there at all
        (tmp_path / f"{name}.json").write_text(json.dumps({"totalDataChart": rows}))
    fees = value.load()
    assert len(fees) == 40 and int(fees["holders_revenue"].isna().sum()) == 2 and fees["fees"].notna().all()
    assert value.covered_through(fees) == fees.index.max()
    assert value.covered_through(fees.iloc[:21]) == fees.index[19]            # the last day with all three is before the null


def test_take_splits_a_revenue_step_into_volume_and_take():
    idx = pd.date_range("2026-01-01", periods=200, freq="D")
    step = idx[100]
    volume = pd.Series(100.0, index=idx)
    volume[idx >= step] = 200.0                       # volume doubles on the step day
    revenue = volume * 2e-4                           # 2 basis points kept before the step ...
    revenue[idx >= step] = volume[idx >= step] * 3e-4  # ... 3 after it
    daily = pd.DataFrame({"intents_volume_usd": volume, "price_usd": 2.0}, index=idx)
    fees = pd.DataFrame({"fees": volume * 1e-3, "revenue": revenue, "holders_revenue": revenue}, index=idx)
    t = value.take(daily, fees, str(step.date()), days=90)
    assert (t["before"]["days"], t["after"]["days"]) == (90, 100)
    assert t["before"]["take_bps"] == pytest.approx(2.0) and t["after"]["take_bps"] == pytest.approx(3.0)
    assert t["volume_ratio"] == pytest.approx(2.0) and t["take_ratio"] == pytest.approx(1.5)
    assert t["revenue_ratio"] == pytest.approx(t["volume_ratio"] * t["take_ratio"])
    assert t["last_30_days_vs_the_30_before"]["volume_pct_change"] == pytest.approx(0.0)
    fees.loc[idx[50], "revenue"] = float("nan")       # a hole in the window before the step: no figure
    assert value.take(daily, fees, str(step.date()), days=90) is None
    assert value.take(daily, fees, None) is None


def test_issuance_cut_scales_the_gap_by_the_change_in_the_maximum():
    v = {"buyback_coverage_of_new_supply": 0.18, "growth_needed_to_cover_new_supply": 1 / 0.18}
    protocol = {"max_inflation_rate": [1, 40], "protocol_version": 88, "read_at_utc": "2026-11-14T08:11Z"}
    c = value.issuance_cut(v, protocol)
    assert c["max_issuance_in_force"] == 0.025 and not c["in_force_yet"]
    assert c["net_new_supply_scale"] == pytest.approx(0.64)
    assert c["coverage_at_target"] == pytest.approx(0.18 / 0.64)
    assert c["growth_needed_at_target"] == pytest.approx(0.64 / 0.18)
    assert value.issuance_cut(v, {**protocol, "max_inflation_rate": [2, 125]})["in_force_yet"]   # 1.6%: adopted
    assert value.issuance_cut(v, None) is None
