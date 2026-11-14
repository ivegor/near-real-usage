"""Missing observations must stay missing in weekly statistics and dated daily comparisons."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from thesis import autumn, metrics
from tests.test_autumn import synthetic
from tests.test_metrics import daily


@pytest.mark.parametrize("invalid", [0.0, -1.0, np.inf, -np.inf])
def test_a_price_week_needs_seven_valid_daily_quotes(invalid):
    dates = pd.date_range("2026-10-05", periods=28)
    prices = pd.Series(np.repeat([1.0, 2.0, 4.0, 8.0], 7), index=dates)
    prices.loc["2026-10-06"] = invalid
    changes = metrics.weekly_log_diff(prices, positive_only=True)
    assert changes.index.tolist() == [pd.Timestamp("2026-10-25"), pd.Timestamp("2026-11-01")]
    assert np.allclose(changes, np.log(2))


def test_a_zero_activity_day_is_still_an_observed_day():
    dates = pd.date_range("2026-10-05", periods=21)
    activity = pd.Series(np.repeat([7.0, 14.0, 28.0], 7), index=dates)
    activity.loc["2026-10-06"] = 0
    changes = metrics.weekly_log_diff(activity)
    assert changes.index.tolist() == [pd.Timestamp("2026-10-18"), pd.Timestamp("2026-10-25")]
    assert np.allclose(changes, [np.log(14 / 6), np.log(2)])


def test_public_statistics_treat_nonpositive_prices_as_missing_quotes():
    inputs = daily()
    inputs.loc[inputs.index[:6], "price_usd"] = 0
    inputs.loc[inputs.index[300], "price_usd"] = -1
    missing = inputs.copy()
    missing["price_usd"] = missing["price_usd"].where(missing["price_usd"] > 0)
    actual, expected = metrics.summarize(inputs), metrics.summarize(missing)
    for key in ("lead_vs_price", "lead_vs_price_holm", "lead_vs_price_lag1_autocorrelation",
                "lead_vs_price_bartlett", "lead_fees_usd_mechanical"):
        assert actual[key] == expected[key], key


@pytest.mark.parametrize("drop_row", [False, True])
def test_daily_moves_do_not_bridge_an_unobserved_day(drop_row):
    dates = pd.date_range("2026-11-01", "2026-11-11")
    values = pd.Series(100.0, index=dates)
    values.loc["2026-11-03"] = 90
    values.loc["2026-11-09":] = 180
    values.loc["2026-11-08"] = np.nan
    if drop_row:
        values = values.dropna()
    out = autumn.one_day_moves(values, dates[0], dates[-1])["2026-11"]
    # The 9 November level follows a gap; the largest known daily rise is the recovery from 90 to 100.
    assert out["rise"]["date"] == "2026-11-04"
    assert out["rise"]["pct_change"] == pytest.approx(100 / 9)
    assert out["fall"]["date"] == "2026-11-03"


def test_daily_moves_need_two_adjacent_observed_dates():
    values = pd.Series([10.0, 20.0, 5.0], index=pd.to_datetime(["2026-11-01", "2026-11-03", "2026-11-05"]))
    assert autumn.one_day_moves(values, pd.Timestamp("2026-11-01"), pd.Timestamp("2026-11-05")) == {}


@pytest.mark.parametrize("missing_day,drop_row", [
    ("2026-08-18", False), ("2026-08-18", True), ("2026-09-10", False), ("2026-09-10", True), ("2026-11-11", False),
])
def test_a_continuous_step_requires_every_calendar_week(missing_day, drop_row):
    inputs, fees = synthetic()
    inputs.loc[missing_day, "intents_volume_usd"] = np.nan
    if drop_row:
        inputs = inputs.drop(pd.Timestamp(missing_day))
    assert autumn.intents_step(inputs, fees, 89.6e6, "2025-12") is None


def test_a_gap_before_the_crossing_does_not_erase_a_later_observed_step():
    inputs, fees = synthetic()
    inputs = inputs.drop(pd.Timestamp("2026-07-01"))
    step = autumn.intents_step(inputs, fees, 89.6e6, "2025-12")
    assert step["day"] == "2026-08-19" and step["weekly_mean_above_it_since"] == "2026-08-21"


def test_the_seven_day_step_search_includes_its_first_days_change():
    inputs, fees = synthetic()
    inputs.loc["2026-08-25", "intents_volume_usd"] = 150e6
    step = autumn.intents_step(inputs, fees, 149e6, "2025-12")
    assert step["weekly_mean_above_it_since"] == "2026-08-25"
    assert step["day"] == "2026-08-19"


def test_missing_prices_omit_the_price_context_without_hiding_the_volume_step():
    inputs, fees = synthetic()
    inputs.loc["2026-08-19", "price_usd"] = np.nan
    step = autumn.intents_step(inputs, fees, 89.6e6, "2025-12")
    assert step["day"] == "2026-08-19" and "price_usd" not in step


def test_a_half_month_metric_needs_every_day_of_its_labelled_span():
    inputs, fees = synthetic()
    inputs.loc["2026-11-08", "active_accounts"] = np.nan
    inputs.loc[:"2026-08-15", "gas_used"] = np.nan
    out = autumn.summarize(inputs, fees, ("2025-12", "2026-08"), "2026-04-02", line=89.6e6)
    recent = out["half_months"]["2026-11-01..2026-11-11"]
    assert recent["days"] == 11 and recent["active_accounts"] is None and recent["txns"] == 700e3
    assert "gas_tgas" not in out["reference"]["top"]
    assert "gas_tgas" not in out["above_reference_top"]


def test_an_incomplete_reference_half_cannot_lower_the_reference_top():
    inputs, fees = synthetic()
    inputs["gas_used"] = 100e12
    inputs.loc["2026-06-01":"2026-06-15", "gas_used"] = 200e12
    inputs.loc["2026-08-16":, "gas_used"] = 150e12
    complete = autumn.summarize(inputs, fees, ("2025-12", "2026-08"), "2026-04-02", line=89.6e6)
    assert complete["reference"]["top"]["gas_tgas"] == 200
    assert complete["above_reference_top"]["gas_tgas"] == []
    inputs.loc["2026-06-08", "gas_used"] = np.nan
    incomplete = autumn.summarize(inputs, fees, ("2025-12", "2026-08"), "2026-04-02", line=89.6e6)
    for field in ("top", "top_half", "top_median", "top_half_median"):
        assert "gas_tgas" not in incomplete["reference"][field]
    for field in ("above_reference_top", "above_reference_top_by_median"):
        assert "gas_tgas" not in incomplete[field]


@pytest.mark.parametrize("column,missing_day", [("active_contracts", "2026-11-08"), ("price_usd", "2026-08-19")])
def test_offline_build_survives_one_missing_daily_metric(tmp_path, monkeypatch, column, missing_day):
    from thesis import __main__ as cli, sources

    root = Path(__file__).resolve().parents[1]
    inputs = pd.read_csv(root / "data" / "daily.csv", index_col=0, parse_dates=True)
    inputs.loc[missing_day, column] = np.nan
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "DOCS", tmp_path / "docs")
    monkeypatch.setattr(sources, "load_daily", lambda offline=False: inputs)
    cli.build(offline=True)
    summary = json.loads((tmp_path / "docs" / "summary.json").read_text())
    if column == "active_contracts":
        moves = summary["autumn"]["one_day_moves"]["active_contracts"]["2026-11"]
        assert all(move["date"] != "2026-11-09" for move in moves.values())
    else:
        step = summary["autumn"]["intents_step"]
        assert step["day"] == "2026-08-19" and "price_usd" not in step
    assert summary["predictions"]["items"] and (tmp_path / "docs" / "index.html").exists()
