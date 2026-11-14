"""Prediction regressions through the frozen rules, public evaluator, and rendered dashboard."""
from decimal import Decimal

import numpy as np
import pandas as pd
import pytest

from thesis import dashboard, population, predictions


def score(tmp_path, pid, daily, fees=None, **tables):
    path = tmp_path / "prediction.csv"
    pd.read_csv(predictions.CSV).query("id == @pid").to_csv(path, index=False)
    result = predictions.evaluate(daily, fees, path, **tables)
    page = dashboard.render([], {"first_date": str(daily.index.min().date()),
                                "last_date": str(daily.index.max().date()), "days": len(daily),
                                "predictions": result}, tmp_path).read_text()
    return result["items"][0], page


@pytest.mark.parametrize("cent_change,expected", [(-1, "failed"), (0, "failed"), (1, "held")])
def test_a3_decimal_total_at_the_frozen_threshold(tmp_path, cent_change, expected):
    # These cents sum exactly to the frozen $723,262 threshold; binary float summation overshoots it.
    last = Decimal("33261.40") + Decimal(cent_change) / 100
    amounts = [Decimal("23000.02")] * 30 + [last]
    total = sum(amounts)
    index = pd.date_range("2026-12-01", "2026-12-31")
    daily = pd.DataFrame({"intents_volume_usd": 1e8}, index=index)
    fees = pd.DataFrame({"holders_revenue": [float(v) for v in amounts]}, index=index)
    row, page = score(tmp_path, "A3", daily, fees)
    assert row["measured"] == float(total)
    assert row["status"] == expected and f"<b>{expected}</b>" in page


def a5_daily():
    index = pd.date_range("2025-01-01", "2027-02-11")
    weeks = pd.date_range("2024-12-30", "2027-02-22", freq="W-MON")
    returns = np.random.default_rng(2).normal(0, .12, len(weeks))

    def levels(changes, scale):
        return pd.Series(scale * np.exp(np.cumsum(changes)), index=weeks).reindex(index, method="ffill")

    price = levels(returns, 1)
    # Planted neighbouring positive leads. Independent varying activity keeps every other correlation defined.
    volume = levels(np.roll(returns, -1) + np.roll(returns, -2), 1e8)
    rng = np.random.default_rng(12)
    active = levels(rng.normal(0, .08, len(weeks)), 10_000)
    txns = levels(rng.normal(0, .08, len(weeks)), 100_000)
    fees_near = levels(rng.normal(0, .08, len(weeks)), 100)
    return pd.DataFrame({"price_usd": price, "txns": txns, "fees_usd": fees_near * price,
                         "active_accounts": active, "new_accounts": active * .2,
                         "intents_volume_usd": volume}, index=index)


@pytest.mark.parametrize("column", ["intents_volume_usd", "txns", "fees_usd", "active_accounts", "new_accounts"])
def test_a5_does_not_silently_drop_a_shortened_metric(tmp_path, column):
    daily = a5_daily()
    full, _ = score(tmp_path, "A5", daily)
    assert full["status"] == "failed" and full["measured"] >= 1
    # All required post-snapshot weeks and their preceding week remain. The shortened column has 102 days,
    # below the general scan's 120-day minimum; that must not shrink A5's frozen family of five metrics.
    daily.loc[:"2026-11-01", column] = np.nan
    row, page = score(tmp_path, "A5", daily)
    assert row["status"] == "open (waiting for complete data)" and row["measured"] is None
    assert "<b>held</b>" not in page and "<b>failed</b>" not in page


@pytest.mark.parametrize("column", ["active_accounts", "new_accounts"])
def test_a5_waits_when_a_historical_source_column_is_absent(tmp_path, column):
    row, page = score(tmp_path, "A5", a5_daily().drop(columns=column))
    assert row["status"] == "open (waiting for complete data)" and row["measured"] is None
    assert "<b>held</b>" not in page


def test_a5_requires_defined_correlations_but_allows_the_two_ended_series(tmp_path):
    daily = a5_daily()
    daily.loc["2026-11-22":, ["active_accounts", "new_accounts"]] = np.nan
    row, _ = score(tmp_path, "A5", daily)
    assert row["status"] == "failed" and row["measured"] >= 1
    daily["txns"] = 100_000.0
    row, page = score(tmp_path, "A5", daily)
    assert row["status"] == "open (waiting for complete data)" and row["measured"] is None
    assert "<b>held</b>" not in page


def b2_tables():
    daily = pd.DataFrame({"txns": 1_000_000.0}, index=pd.date_range("2026-10-01", "2027-02-01"))
    rows = []
    for month in ("2026-10", "2026-11", "2026-12", "2027-01"):
        sponsored = pd.Period(month, "M").days_in_month * 1_000_000 - 10_400_000
        rows.extend([(month, "near", 10_400_000, 0), (month, "tg", sponsored, sponsored)])
    return daily, pd.DataFrame(rows, columns=["month", "family", "txs", "relayed_txs"])


@pytest.mark.parametrize("month", ["2026-11", "2026-12", "2027-01"])
def test_b2_checks_the_totals_of_every_month_even_with_a_complete_scan_date(tmp_path, monkeypatch, month):
    monkeypatch.setattr(population, "QUERY_END", "2027-01-31")
    daily, census = b2_tables()
    complete, _ = score(tmp_path, "B2", daily, census=census)
    assert complete["status"] == "held" and complete["measured"] == 10_400_000
    # The source is missing an interior day (400k core direct + 600k sponsored). Its last date still exists,
    # so QUERY_END is correct; only the independent monthly total exposes the missing observations.
    core = (census["month"] == month) & (census["family"] == "near")
    reward = (census["month"] == month) & (census["family"] == "tg")
    census.loc[core, "txs"] -= 400_000
    census.loc[reward, ["txs", "relayed_txs"]] -= 600_000
    row, page = score(tmp_path, "B2", daily, census=census)
    assert row["status"].startswith("open (needs") and row["measured"] is None
    assert "<b>failed</b>" not in page and "<b>held</b>" not in page


def test_b2_waits_when_the_independent_daily_check_is_incomplete(tmp_path, monkeypatch):
    monkeypatch.setattr(population, "QUERY_END", "2027-01-31")
    daily, census = b2_tables()
    daily = daily.drop(pd.Timestamp("2026-11-15"))
    row, page = score(tmp_path, "B2", daily, census=census)
    assert row["status"].startswith("open (needs") and row["measured"] is None
    assert "<b>held</b>" not in page
