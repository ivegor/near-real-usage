"""Independent-audit failures exercised through statistics, public builds and prediction rendering."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from thesis import __main__ as cli
from thesis import autumn, charts, dashboard, metrics, predictions, segments, sources
from tests.test_prediction_audit_fixes import a5_daily, score
from tests.test_predictions import bq_results, days_of_january


def build_in(tmp_path, monkeypatch, daily):
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "DOCS", tmp_path / "docs")
    monkeypatch.setattr(sources, "load_daily", lambda offline=False: daily)
    cli.build(offline=True)
    return json.loads((tmp_path / "docs/summary.json").read_text()), (tmp_path / "docs/index.html").read_text()


def test_unknown_deletions_cannot_create_an_above_reference_period(tmp_path, monkeypatch):
    daily = sources.load_daily(offline=True)
    daily.loc["2026-10-01":"2026-10-15", "deleted_accounts"] = np.nan
    s, _ = build_in(tmp_path, monkeypatch, daily)
    half = s["autumn"]["half_months"]["2026-10-01..2026-10-15"]
    assert half["deleted_accounts"] is None and half["txns_less_deleted"] is None
    assert "2026-10-01..2026-10-15" not in s["autumn"]["above_reference_top"]["txns_less_deleted"]
    assert "not a measured count" in s["autumn"]["deletion_scenario"]["limitation"]


def test_deletion_scenario_is_never_described_as_a_transaction_identity():
    root = Path(__file__).resolve().parents[1]
    assert "assumed" in autumn.COLUMNS["txns_less_deleted"]
    text = " ".join((root / "APPENDIX.md").read_text().split())
    assert "each deletion is one transaction" not in text
    assert "a transaction can produce several deletion receipts" in text


@pytest.mark.parametrize("column", list(predictions.A5_HISTORY_START))
@pytest.mark.parametrize("loss", ["early_history", "late_history", "interior_day"])
def test_a5_preserves_history_even_when_hundreds_of_observations_remain(tmp_path, column, loss):
    daily = a5_daily()
    if loss == "early_history":
        daily.loc[:"2025-06-30", column] = np.nan
    elif loss == "late_history":
        daily.loc["2025-07-01":predictions.FROZEN_DATA_THROUGH, column] = np.nan
    else:
        daily.loc["2025-06-30", column] = np.nan
    assert daily[column].count() > 120
    row, page = score(tmp_path, "A5", daily)
    assert row["status"] == "open (waiting for complete data)" and row["measured"] is None
    assert "<b>held</b>" not in page and "<b>failed</b>" not in page


def test_a5_history_contract_matches_the_saved_freeze_coverage():
    d = sources.load_daily(offline=True).loc[:predictions.FROZEN_DATA_THROUGH]
    for c, start in predictions.A5_HISTORY_START.items():
        valid = d[c].where(np.isfinite(d[c]) & ((d[c] > 0) if c == "price_usd" else True)).dropna()
        assert str(valid.index.min().date()) == start
        assert valid.index.equals(pd.date_range(start, predictions.FROZEN_DATA_THROUGH, name=valid.index.name))


def test_partial_frequency_month_never_enters_the_summary_or_chart(tmp_path, monkeypatch):
    daily = sources.load_daily(offline=True)
    frequency = segments.load()
    partial = frequency[frequency["month"] == "2026-10"].copy()
    partial["month"] = "2026-11"
    partial[["accounts", "txs", "self_paid_txs"]] //= 3
    frequency = pd.concat([frequency, partial]).assign(query_end="2026-11-11")
    path = tmp_path / "frequency.csv"
    frequency.to_csv(path, index=False)
    monkeypatch.setattr(segments, "CSV", path)
    s, page = build_in(tmp_path, monkeypatch, daily)
    sg = s["segments"]
    assert sg["latest_month"] == s["population"]["latest_month"] == "2026-10"
    assert sg["metrics"]["regular_accounts"]["latest"] == 17105
    assert sg["regular_accounts_low"] == {"month": "2026-08", "value": 7201.0}
    assert "2026-11" not in sg["regular_accounts_by_month"]
    assert "2026-11" not in sg["heavy_by_month"]
    assert "Frequency classes need a complete month; excluded months: 2026-11." in page


def test_frequency_import_preserves_the_query_end_and_requires_it_for_later_results(tmp_path):
    source, out = tmp_path / "query.csv", tmp_path / "frequency.csv"
    source.write_text("m,query_end,cells\n2027-01,2027-02-05,rest|self|n10_99|10|100|100\n"
                      "2027-02,2027-02-05,rest|self|n1|10|10|10\n")
    segments.unpack(source, out)
    loaded = segments.load(out)
    assert segments.complete_months(loaded) == ["2027-01"]
    assert loaded["query_end"].tolist() == ["2027-02-05", "2027-02-05"]
    source.write_text("m,cells\n2027-01,rest|self|n10_99|10|100|100\n")
    with pytest.raises(ValueError, match="need query_end"):
        segments.unpack(source, tmp_path / "other.csv")


@pytest.mark.parametrize("query_end", [None, "2027-01-30"])
def test_b1_needs_the_query_to_reach_month_end_even_when_totals_match(tmp_path, query_end):
    _, seg, _ = bq_results(tmp_path)
    index = pd.date_range("2027-01-01", "2027-02-01")
    daily = pd.DataFrame({"txns": days_of_january(index)}, index=index)
    full, _ = score(tmp_path, "B1", daily, seg=seg)
    assert full["status"] == "held"
    seg = seg.drop(columns="query_end") if query_end is None else seg.assign(query_end=query_end)
    row, page = score(tmp_path, "B1", daily, seg=seg)
    assert row["status"].startswith("open (needs") and row["measured"] is None
    assert "<b>held</b>" not in page


def test_one_day_is_not_an_october_mean_in_the_public_build(tmp_path, monkeypatch):
    daily = sources.load_daily(offline=True)
    daily.loc["2026-10-01":"2026-10-30", "intents_volume_usd"] = np.nan
    s, page = build_in(tmp_path, monkeypatch, daily)
    month = s["month_yoy"]["intents_volume_usd"]
    assert month["month"] == "2026-10" and month["recent"] is None
    assert month["recent_days"] == 1 and month["expected_days"] == 31
    assert "mean NEAR Intents volume for 2026-10 is unavailable" in page
    assert "inside the $63M" not in page and "$nan" not in page


@pytest.mark.parametrize("drop_row", [False, True])
def test_window_comparisons_require_calendar_days_not_equal_row_counts(drop_row):
    index = pd.date_range("2025-01-01", "2026-11-11")
    s = pd.Series(100.0, index=index)
    s.loc["2026-11-02"] = np.nan
    s.loc["2025-11-03"] = np.nan
    if drop_row:
        s = s.dropna()
    assert metrics.month_to_date_change(s) is None
    p = metrics.period_change(s)
    assert p["recent_days"] == p["prior_days"] == 89
    assert np.isnan(p["recent"]) and np.isnan(p["pct_change"])
    # A real zero is an observation, unlike a missing day.
    s = s.reindex(index).fillna(0)
    assert metrics.month_to_date_change(s)["days"] == 11
    assert metrics.period_change(s)["pct_change"] == 0


def test_calendar_rolling_mean_leaves_a_gap_for_a_missing_day():
    index = pd.date_range("2026-01-01", periods=20)
    d = pd.DataFrame({"x": 100.0}, index=index).drop(index[10])
    r = metrics.rolling(d, 7)
    assert len(r) == 20 and r.loc[index[10]:index[16], "x"].isna().all()
    assert r.loc[index[17], "x"] == 100


@pytest.mark.parametrize("r", [-1., 1., -1. - 1e-15, 1. + 1e-15])
def test_perfect_correlations_have_zero_p_value(r):
    assert metrics._p_value(r, 100) == 0
    assert np.isnan(metrics._p_value(r, 3))
    assert np.isnan(metrics._p_value(1.2, 100))


def test_isolated_perfect_lead_survives_both_scans_and_reaches_the_dashboard(tmp_path):
    levels = np.exp(np.cumsum(np.random.default_rng(31).normal(0, .1, 100)))
    x = np.repeat(levels, 7)
    price = np.repeat(np.r_[np.ones(3), levels[:-3]], 7)
    d = pd.DataFrame({"active_accounts": x, "new_accounts": 0., "txns": x, "fees_usd": x * price,
                      "price_usd": price, "intents_volume_usd": x}, index=pd.date_range("2024-01-01", periods=700))
    s = metrics.summarize(d)
    assert s["lead_vs_price_holm"]["tests"] == s["lead_vs_price_bartlett"]["holm"]["tests"] == 85
    assert s["lead_vs_price_holm"]["significant"] >= 5
    assert s["lead_vs_price_bartlett"]["holm"]["significant"] >= 5
    assert {r["lag_weeks"] for r in s["lead_vs_price_holm_leads"]} == {3}
    assert predictions.adjacent_positive_leads(s["lead_vs_price"]) == 0
    built = charts.build_all(d, s, tmp_path)
    page = dashboard.render(built, s, tmp_path).read_text()
    assert "Some positive usage lags survive Holm" in page
    assert "No usage metric leads price" not in page


def test_holm_headline_does_not_call_price_first_or_uncorrected_pairs_usage_leads():
    leads = {"x": {"lags": [-2, 1, 2], "p_values": [0., .03, .04],
                    "outside_band": [{"lag_weeks": 1, "corr": .3}, {"lag_weeks": 2, "corr": .3}]}}
    s = {"lead_vs_price": leads, "lead_vs_price_holm": {"tests": 3, "significant": 1},
         "lead_vs_price_holm_leads": metrics.holm_leading_lags(leads)}
    assert s["lead_vs_price_holm_leads"] == []
    assert "no convincing lead" in charts._takeaway("lead_lag", s)
