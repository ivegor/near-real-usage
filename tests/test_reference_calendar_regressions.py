"""The historical reference and step need the same daily coverage as current comparisons."""
import numpy as np
import pandas as pd
import pytest

from thesis import metrics, predictions, sources, value
from tests.test_independent_audit_regressions import build_in


@pytest.mark.parametrize("loss", ["one_day_per_month", "one_day_missing", "whole_month_missing", "infinite_day"])
def test_incomplete_reference_cannot_rewrite_the_range_or_crossing(tmp_path, monkeypatch, loss):
    daily = sources.load_daily(offline=True)
    october_mean = daily.loc["2026-10", "intents_volume_usd"].sum() / 31
    if loss == "one_day_per_month":
        mask = (daily.index >= "2025-12-01") & (daily.index <= "2026-08-31") & (daily.index.day != 1)
        daily.loc[mask, "intents_volume_usd"] = np.nan
    elif loss == "one_day_missing":
        daily = daily.drop(pd.Timestamp("2026-06-05"))
    elif loss == "whole_month_missing":
        daily.loc["2026-06", "intents_volume_usd"] = np.nan
    else:
        daily.loc["2026-06-05", "intents_volume_usd"] = np.inf
    s, page = build_in(tmp_path, monkeypatch, daily)
    assert s["predictions"]["baselines"]["intents_volume_plateau_top_usd"] is None
    step = s["predictions"]["step"]
    assert "range_top" not in step.get("intents_volume_usd_a_day", {})
    assert "range_low" not in step.get("intents_volume_usd_a_day", {})
    assert "range_mean" not in step.get("intents_volume_usd_a_day", {})
    assert "reference range is unavailable" in page
    assert "inside the $30M to $135M" not in page
    assert s["autumn"].get("intents_step") is None
    assert "intents_volume_usd" not in s["autumn"]["reference"]["top"]
    assert s["month_yoy"]["intents_volume_usd"]["recent"] == pytest.approx(october_mean)


def test_one_september_day_is_not_a_monthly_step(tmp_path, monkeypatch):
    daily = sources.load_daily(offline=True)
    daily.loc["2026-09-01":"2026-09-29", "intents_volume_usd"] = np.nan
    s, page = build_in(tmp_path, monkeypatch, daily)
    volume = s["predictions"]["step"]["intents_volume_usd_a_day"]
    assert "month" not in volume
    assert volume["range_top"] == pytest.approx(89591201.70967741)  # the intact reference remains usable
    assert "monthly Intents step is unavailable" in page
    assert "The step up in 2026-09" not in page
    assert "above the $63M to $90M range" in page


def test_missing_month_before_the_reference_does_not_hide_the_valid_range(tmp_path, monkeypatch):
    daily = sources.load_daily(offline=True)
    daily.loc["2025-11", "intents_volume_usd"] = np.nan
    s, page = build_in(tmp_path, monkeypatch, daily)
    volume = s["predictions"]["step"]["intents_volume_usd_a_day"]
    assert "range_top" in volume and "month_before_range" not in volume
    assert "above the $63M to $90M range" in page
    assert "2025-11 already averaged" not in page and "$nan" not in page


@pytest.mark.parametrize("missing", [True, False])
def test_missing_buyback_month_is_unknown_but_observed_zero_is_zero(tmp_path, monkeypatch, missing):
    daily, fees = sources.load_daily(offline=True), value.load()
    fees.loc["2026-09", "holders_revenue"] = np.nan if missing else 0.0
    monkeypatch.setattr(value, "load", lambda: fees)
    s, page = build_in(tmp_path, monkeypatch, daily)
    step = s["predictions"]["step"]
    if missing:
        assert "buyback_usd" not in step
        assert "monthly buyback step is unavailable" in page
    else:
        assert step["buyback_usd"]["month"] == 0
        assert "buyback_months" not in step.get("unavailable", {})


@pytest.mark.parametrize("day,key", [("2026-09-01", "first_day"), ("2026-09-30", "last_day")])
def test_price_context_uses_exact_month_endpoints_in_the_build(tmp_path, monkeypatch, day, key):
    daily = sources.load_daily(offline=True)
    daily.loc[day, "price_usd"] = np.nan
    s, page = build_in(tmp_path, monkeypatch, daily)
    step = s["predictions"]["step"]
    assert step["price_usd"][key] is None and step["price_usd"]["mean"] is None
    assert "peak_since" not in step["price_usd"]
    assert step["intents_volume_usd_a_day"]["month"] == pytest.approx(160103145.9)
    assert "month the NEAR price went from" not in page
    assert "exact first and last days" in page and "$nan" not in page


@pytest.mark.parametrize("day", ["2026-08-01", "2026-09-01", "2026-09-15", "2026-09-30"])
@pytest.mark.parametrize("invalid", [0.0, -1.0, np.inf, -np.inf])
def test_invalid_quotes_never_form_monthly_price_context(day, invalid):
    daily = sources.load_daily(offline=True)
    daily.loc[day, "price_usd"] = invalid
    price = predictions.step(daily)["price_usd"]
    assert np.isnan(price["mean_before" if day.startswith("2026-08") else "mean"])
    if day == "2026-09-01": assert np.isnan(price["first_day"])
    if day == "2026-09-30": assert np.isnan(price["last_day"])
    if day.startswith("2026-09"): assert "peak_since" not in price


def test_missing_reference_day_invalidates_the_buyback_maximum():
    daily, fees = sources.load_daily(offline=True), value.load()
    fees = fees.drop(pd.Timestamp("2026-03-15"))  # even a gap outside the known maximum month matters
    assert predictions.baselines(daily, fees, None)["buyback_plateau_top_usd"] is None


def test_monthly_coverage_includes_leap_day_and_does_not_bridge_an_absent_month():
    s = pd.Series(2.0, index=pd.date_range("2024-01-01", "2024-03-31"))
    assert metrics.calendar_months(s, "2024-01", "2024-03", "sum").tolist() == [62, 58, 62]
    s = s.drop(pd.date_range("2024-02-01", "2024-02-29"))
    actual = metrics.calendar_months(s, "2024-01", "2024-03", "sum")
    assert actual.iloc[0] == actual.iloc[2] == 62 and np.isnan(actual.iloc[1])
