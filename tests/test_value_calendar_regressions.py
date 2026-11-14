"""The five follow-up findings: ratios, reference coverage, monthly shares and invalid quotes."""
import numpy as np
import pandas as pd
import pytest

from thesis import autumn, metrics, sources, value
from tests.test_autumn import synthetic
from tests.test_independent_audit_regressions import build_in


@pytest.mark.parametrize("case", ["zero_buybacks", "zero_reference_revenue", "sparse_gross_fees",
                                  "incomplete_take_reference", "incomplete_months", "negative_price"])
def test_followup_failures_through_the_public_build(tmp_path, monkeypatch, case):
    daily, fees = sources.load_daily(offline=True), value.load()
    if case == "zero_buybacks":
        fees.loc["2026-10-13":"2026-11-11", "holders_revenue"] = 0.0
    elif case == "zero_reference_revenue":
        fees.loc["2026-05-21":"2026-08-18", "revenue"] = 0.0
    elif case == "sparse_gross_fees":
        fees.loc["2026-08-14":"2026-11-10", "fees"] = np.nan
    elif case == "incomplete_take_reference":
        fees.loc["2026-05-01":"2026-05-20", "revenue"] = np.nan
    elif case == "incomplete_months":
        fees.loc["2026-08-01":"2026-08-18", "holders_revenue"] = np.nan
        fees.loc["2026-06-02":"2026-06-30", "holders_revenue"] = np.nan
    else:
        daily.loc["2026-10-13", "price_usd"] = -1.0
    monkeypatch.setattr(value, "load", lambda: fees)
    summary, page = build_in(tmp_path, monkeypatch, daily)
    assert "$nan" not in page and "nan%" not in page
    if case == "negative_price":
        month = summary["month_yoy"]["price_usd"]
        assert month["recent"] is None and month["recent_days"] == 30
        assert summary["yoy_90d"]["price_usd"]["pct_change"] is None
        return
    v = summary["value_capture"]
    w = v["windows"]
    if case == "zero_buybacks":
        threshold = w["threshold_price"]
        assert threshold["near_per_day"] == 0
        assert threshold["mean_price_that_meets_it"] is None
        assert threshold["unavailable_reason"] == "no positive buyback pace"
        assert w["by_length"]["30"]["buyback_usd_annualized"] == 0
    elif case == "zero_reference_revenue":
        assert v["take"]["before"]["revenue_usd_per_day"] == 0
        assert v["take"]["after"]["revenue_usd_per_day"] > 0
        assert v["take"]["revenue_ratio"] is None and v["take"]["take_ratio"] is None
    elif case == "sparse_gross_fees":
        # Independent calendar-total calculation: 90 times each series' observed daily mean.
        f = fees.loc["2026-08-14":"2026-11-11"]
        expected = f.revenue.mean() / f.fees.mean()
        assert v["captured_share_of_gross_fees"] == pytest.approx(expected)
        assert w["by_length"]["90"]["captured_share"] == pytest.approx(expected)
        assert w["by_length"]["90"]["days_without_data"]["fees"] == 89
    elif case == "incomplete_take_reference":
        take = v["take"]
        assert "take_step" not in take
        assert take["take_bps_by_month"]["2026-05"] is None
        assert take["take_step_unavailable"]["months"] == ["2026-05"]
        assert take["before"]["days"] == 90 and take["after"]["days"] == 85
    else:
        step = summary["autumn"]["intents_step"]
        assert step["share_of_the_month_buybacks_from_it"] is None
        assert step["month_days_without_data"]["buybacks"] == 18
        assert step["per_day_before_and_from_it"]["buyback_usd"][0] is None
        june = w["by_month"]["2026-06"]
        assert june["largest_day_near"] is None
        assert june["buyback_near_per_day"] is None and june["buyback_near_per_day_median"] is None
        assert june["days_without_data"]["holders_revenue"] == 29


@pytest.mark.parametrize("column", ["volume", "fees", "revenue"])
@pytest.mark.parametrize("loss", ["day", "infinity", "month"])
def test_take_reference_needs_each_full_month(column, loss):
    daily, fees = sources.load_daily(offline=True), value.load()
    frame, col = (daily, "intents_volume_usd") if column == "volume" else (fees, column)
    if loss == "month":
        frame = frame.drop(frame.loc["2026-05"].index)
        if column == "volume":
            daily = frame
        else:
            fees = frame
        # Keep the independently reported before/after window inside intact June onward.
        step, days = "2026-08-19", 60
    else:
        frame.loc["2026-05-01", col] = np.nan if loss == "day" else np.inf
        step, days = "2026-08-19", 90
    take = value.take(daily, fees, step, days=days)
    assert take is not None and "take_step" not in take
    assert take["take_step_unavailable"]["months"] == ["2026-05"]


def test_zero_reference_months_and_zero_recent_denominators_are_valid_observations():
    daily, fees = sources.load_daily(offline=True), value.load()
    fees.loc["2026-05-01":"2026-07-31", "revenue"] = 0.0
    take = value.take(daily, fees, "2026-08-19")
    assert take["take_step"]["reference_top_bps"] == 0
    assert "take_step_unavailable" not in take
    fees.loc["2026-09-13":"2026-10-12", ["revenue", "fees"]] = 0.0
    changes = value.take(daily, fees, "2026-08-19")["last_30_days_vs_the_30_before"]
    assert np.isnan(changes["gross_fees_pct_change"]) and np.isnan(changes["revenue_usd_pct_change"])
    assert np.isfinite(changes["volume_pct_change"])


@pytest.mark.parametrize("loss", ["day", "row", "infinity", "partial_month", "zero"])
def test_step_month_share_needs_full_coverage_but_zero_is_known(loss):
    daily, fees = synthetic()
    if loss == "partial_month":
        daily, fees = daily.loc[:"2026-08-28"], fees.loc[:"2026-08-28"]
    elif loss == "row":
        fees = fees.drop(pd.Timestamp("2026-08-10"))
    else:
        fees.loc["2026-08-10", "holders_revenue"] = {"day": np.nan, "infinity": np.inf, "zero": 0.0}[loss]
    step = autumn.intents_step(daily, fees, 89.6e6, "2025-12")
    assert step["day"] == "2026-08-19"
    if loss == "zero":
        expected = fees.loc["2026-08-19":"2026-08-31", "holders_revenue"].sum() / fees.loc["2026-08", "holders_revenue"].sum()
        assert step["share_of_the_month_buybacks_from_it"] == pytest.approx(expected)
        assert "month_days_without_data" not in step
    else:
        assert np.isnan(step["share_of_the_month_buybacks_from_it"])
        assert step["month_days_without_data"]["buybacks"] > 0
    if loss == "partial_month":
        assert np.isnan(step["share_of_the_month_volume_from_it"])
        assert np.isnan(step["per_day_before_and_from_it"]["volume_usd"][1])


@pytest.mark.parametrize("invalid", [0.0, -1.0, np.inf, -np.inf])
def test_invalid_price_is_missing_in_daily_means_and_chart_inputs(invalid):
    daily = sources.load_daily(offline=True)
    daily.loc["2026-10-13", "price_usd"] = invalid
    daily.loc["2026-10-13", "txns"] = 0.0
    derived = metrics.add_derived(daily)
    assert np.isnan(derived.loc["2026-10-13", "price_usd"])
    assert derived.loc["2026-10-13", "txns"] == 0
    assert np.isnan(autumn.series(daily, None).loc["2026-10-13", "price_usd"])
    assert metrics.rolling(derived).loc["2026-10-13":"2026-11-11", "price_usd"].isna().all()


def test_historical_month_gap_and_last_30_gap_do_not_create_observed_day_means():
    daily, fees = sources.load_daily(offline=True), value.load()
    fees = fees.drop(pd.Timestamp("2026-06-10"))
    fees.loc["2026-10-20", "holders_revenue"] = np.nan
    w = value.windows(daily, fees, "2026-08-19", threshold_month_usd=100, threshold_month="2027-01")
    assert w["by_month"]["2026-06"]["largest_day_near"] is None
    assert np.isnan(w["threshold_price"]["mean_price_that_meets_it"])
    assert "incomplete last 30 days" in w["threshold_price"]["unavailable_reason"]
    assert np.isnan(w["buybacks_per_day_before_and_from_the_step"]["usd"]).all()
