"""Calendar coverage and zero-activity regressions from the independent follow-up audit."""
import json
import re

import numpy as np
import pandas as pd
import pytest

from thesis import autumn, population, segments, sources, video
from tests.test_independent_audit_regressions import build_in
from tests.test_population import table


@pytest.mark.parametrize("case", ["v3_one_day", "v3_fall", "v1_one_day", "sparse_month",
                                  "flat", "rising", "short_history", "after_census",
                                  "totals_gap", "price_gap", "zero_independent"])
def test_audited_boundaries_through_build_and_video(tmp_path, monkeypatch, case):
    daily, relayed, frequency = sources.load_daily(offline=True), sources.relayed_daily(), segments.load()
    if case == "v3_one_day":
        relayed.loc["2025-10-01", "relayers"] = np.nan
    elif case == "v3_fall":
        relayed.loc["2026-04-01", "relayed_users"] = np.nan
    elif case == "v1_one_day":
        daily.loc["2025-10-01", "active_accounts"] = np.nan
    elif case == "sparse_month":
        daily.loc["2026-03-02":"2026-03-31", ["fees_usd", "new_accounts"]] = np.nan
    elif case == "flat":
        daily["txns"] = 1_000_000.
    elif case == "rising":
        daily["txns"] = 1_000_000. + np.arange(len(daily))
    elif case == "short_history":
        daily = daily.loc["2026-06-01":]
    elif case == "after_census":
        daily = daily.reindex(pd.date_range(daily.index.min(), "2026-11-20")).ffill()
        daily.loc["2026-11-20", "txns"] = 0.
    elif case == "totals_gap":
        daily.loc["2026-09-02":"2026-09-30", "txns"] = np.nan
    elif case == "price_gap":
        daily.loc["2026-08-10", "price_usd"] = np.nan
    elif case == "zero_independent":
        mask = (frequency.month == "2026-10") & (frequency.namespace == "rest") & (frequency.payer == "self")
        frequency.loc[mask, ["accounts", "txs", "self_paid_txs"]] = 0
    monkeypatch.setattr(sources, "relayed_daily", lambda: relayed)
    monkeypatch.setattr(segments, "load", lambda: frequency)
    summary, page = build_in(tmp_path, monkeypatch, daily)
    slides = video.slides(summary)
    assert not re.search(r"\bnan(?:%|x|\s+times)", page)
    assert not re.search(r"\b(?:nan|None)\b", json.dumps(slides))
    pop = summary["population"]
    if case == "v3_one_day":
        row = pop["one_day"]["nearblocks_v3"]
        assert row["relayers"] is None and row["relayed_users"] > 0
    elif case == "v3_fall":
        fall = pop["largest_daily_fall"]
        assert fall["relayed_users"]["before"] is None and fall["relayed_users"]["after"] > 0
        assert fall["relayed_txns"]["before"] > 0
    elif case == "v1_one_day":
        row = pop["one_day"]["nearblocks"]
        assert row["active_accounts"] is None and row["txns"] > 0
    elif case == "sparse_month":
        fall = pop["largest_daily_fall"]
        assert fall["date"] == "2026-04-02"
        assert fall["fees_near"]["median_day"]["month_before"] is None
        assert fall["fees_near"]["median_day"]["fall"] is None
        assert fall["fees_near"]["median_day"]["month_after"] > 0
        assert fall["new_accounts"]["per_day_month_before"] is None
        assert fall["new_accounts"]["per_day_month_of"] > 0
    elif case in ("flat", "rising", "short_history", "totals_gap"):
        assert "largest_daily_fall" not in pop
        assert summary["autumn"]["reference_unavailable"]
    elif case == "after_census":
        assert pop["largest_daily_fall"]["date"] == "2026-04-02"
    elif case == "price_gap":
        context = summary["autumn"]["intents_step"]["price_usd"]
        assert context["lowest_since"] is None and context["lowest_since_unavailable"]
        assert context["first_day_at_twice_it"]["date"] == "2026-09-19"
    elif case == "zero_independent":
        assert summary["segments"]["heavy_share_of_independent_self_paid_txs"]["latest"] is None
        assert summary["segments"]["metrics"]["heavy_accounts"]["latest"] == 0
        assert "share is unavailable" in page and "share is unavailable" in slides[2]["head"]
    if case == "totals_gap":
        check = pop["totals_check"]
        assert "2026-09" not in check["difference_by_month"]
        assert check["excluded_months"]["2026-09"] == {"observed_days": 1, "expected_days": 30}
        assert "Incomplete daily coverage excluded" in page


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_optional_counts_preserve_known_zero_and_unknown(value):
    out = population.observed_counts(pd.Series({"known": 0., "unknown": value}), ("known", "unknown", "absent"))
    assert out == {"known": 0, "unknown": None, "absent": None}


@pytest.mark.parametrize("loss", ["leading", "trailing", "row", "nan", "inf"])
def test_largest_fall_requires_the_whole_declared_interval(loss):
    daily = pd.DataFrame({"txns": 100.}, index=pd.date_range("2025-01-01", "2026-03-31"))
    daily.loc["2026-01-02":, "txns"] = 50.
    if loss == "leading": daily = daily.iloc[1:]
    elif loss == "trailing": daily = daily.iloc[:-1]
    elif loss == "row": daily = daily.drop(pd.Timestamp("2025-06-01"))
    else: daily.loc["2025-06-01", "txns"] = np.nan if loss == "nan" else np.inf
    assert population.largest_daily_fall(table(), daily) is None


def test_partial_census_month_has_observed_day_rate_and_unknown_next_month():
    census = table()
    census.loc[(census.month == "2026-03") & (census.family == "kaiching"), "txs"] = 22
    daily = pd.DataFrame({"txns": 1000., "new_accounts": 0.}, index=pd.date_range("2025-01-01", "2026-03-11"))
    daily.loc["2026-03-10":, "txns"] = 10.
    out = population.largest_daily_fall(census, daily, "2026-03-11")
    of = out["kaiching"]["month_of"]
    assert of["through"] == "2026-03-11" and of["days"] == 11
    assert of["txs_per_day"] == of["txs"] / 11
    assert out["kaiching"]["month_after"]["txs"] is None
    assert "median_day" not in out
    assert out["new_accounts"]["per_day_month_before"] == 0
    assert out["new_accounts"]["per_day_month_of"] is None


def test_month_before_census_is_unknown_not_zero():
    daily = pd.DataFrame({"txns": 100.}, index=pd.date_range("2025-01-01", "2026-03-31"))
    daily.loc["2025-01-02":, "txns"] = 10.
    out = population.largest_daily_fall(table(), daily)
    assert out["kaiching"]["month_before"]["txs"] is None
    assert out["kaiching"]["month_after"]["txs"] == 1500


@pytest.mark.parametrize("column", ["fees_usd", "price_usd", "new_accounts"])
@pytest.mark.parametrize("bad_value", [np.nan, np.inf])
def test_monthly_context_requires_every_finite_day_without_losing_the_event(column, bad_value):
    daily = pd.DataFrame({"txns": 1000., "fees_usd": 20., "price_usd": 2., "new_accounts": 0.},
                         index=pd.date_range("2025-01-01", "2026-03-31"))
    daily.loc["2026-01-02":, "txns"] = 100.
    daily.loc["2025-12-31", column] = bad_value
    out = population.largest_daily_fall(table(), daily)
    assert out["date"] == "2026-01-02" and out["fall_txs"] == 900
    if column == "new_accounts":
        assert out["new_accounts"]["per_day_month_before"] is None
        assert out["new_accounts"]["per_day_month_of"] == 0
    else:
        fees = out["fees_near"]
        assert fees["before"] == fees["after"] == 10
        assert fees["median_day"] == {"month_before": None, "month_after": 10., "fall": None}


@pytest.mark.parametrize("loss", ["leading", "trailing", "interior", "inf"])
def test_monthly_source_check_requires_identical_days_including_partial_month(loss):
    census = table()
    daily = pd.DataFrame({"txns": 0.}, index=pd.date_range("2025-01-01", "2026-03-11"))
    for month, txs in census.groupby("month").txs.sum().items():
        daily.loc[month + "-01", "txns"] = txs
    day = {"leading": "2026-03-01", "trailing": "2026-03-11", "interior": "2026-03-05", "inf": "2026-03-05"}[loss]
    daily.loc[day, "txns"] = np.inf if loss == "inf" else np.nan
    out = population.totals_check(census, daily, "2026-03-11")
    assert "2026-03" not in out["difference_by_month"]
    assert out["excluded_months"]["2026-03"] == {"observed_days": 10, "expected_days": 11}
    assert out["last_month_through"] == "2026-02-28"
    assert set(out["difference_by_month"].values()) == {0}  # all observed zero days remain valid


@pytest.mark.parametrize("missing_day,expected", [("2026-01-02", "2026-01-05"), ("2026-01-07", None)])
def test_price_low_only_requires_complete_history_after_the_last_known_low(missing_day, expected):
    price = pd.Series(20., index=pd.date_range("2026-01-01", "2026-01-20"))
    price.loc["2026-01-05"] = 9.
    price.loc["2026-01-10"] = 10.
    price = price.drop(pd.Timestamp(missing_day))
    out = autumn._price_after(price, pd.Timestamp("2026-01-10"))
    assert out["lowest_since"] == expected
    assert out["highest_in_the_week_from_it"]["value"] == 20


@pytest.mark.parametrize("group", ["heavy", "independent", "outside"])
def test_zero_share_numerator_is_distinct_from_zero_denominator(group):
    frequency = segments.load()
    mask = (frequency.month == "2026-10") & (frequency.namespace == "rest")
    if group != "outside": mask &= frequency.payer == "self"
    if group == "heavy": mask &= frequency.txs_in_month.isin(["1,000-9,999", "10,000+"])
    frequency.loc[mask, ["accounts", "txs", "self_paid_txs"]] = 0
    out = segments.summarize(frequency)
    assert out["heavy_share_of_independent_self_paid_txs"]["latest"] == (0. if group == "heavy" else None)
    if group == "outside":
        assert out["sponsored_share_of_accounts_outside_app_namespaces"]["latest"] is None
