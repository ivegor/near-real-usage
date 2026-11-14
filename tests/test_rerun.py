"""A later run of the account queries, end to end: the whole build on tables that hold January 2027.

Predictions B1 to B4 are scored from the committed query results once those hold the months they name. Nobody can
run those queries before February 2027, so this test extends the committed tables the way a later run will (months
are added, earlier months stay) and runs the build on them. It checks that the four are scored, that the build
compares the latest month with the one a year earlier, and that figures combining two results are left out when
only one of the queries has been run again.
"""
import json
import re

import numpy as np
import pandas as pd
import pytest

from thesis import __main__ as cli
from thesis import clients, population, segments, sources, value, video

LATER = ["2026-11", "2026-12", "2027-01"]


def later_tables(tmp_path, census=True, frequency=True, top=True):
    """Copies of the committed tables with the months of a later run added: October's rows under the new months."""
    paths = {}
    age = population.load()
    if census:
        october = age[age["month"] == "2026-10"]
        age = pd.concat([age[age["month"] != "2026-11"]] + [october.assign(month=m) for m in LATER + ["2027-02"]])   # February is unfinished
    paths["census"] = tmp_path / "account_age.csv"
    age.to_csv(paths["census"], index=False)
    freq = segments.load()
    if frequency:
        freq = pd.concat([freq] + [freq[freq["month"] == "2026-10"].assign(month=m) for m in LATER + ["2027-02"]])
        freq["query_end"] = "2027-02-05"  # the frequency query can also end inside February
    paths["frequency"] = tmp_path / "payer_frequency.csv"
    freq.to_csv(paths["frequency"], index=False)
    result = pd.read_csv(clients.CSV)
    if top:      # the query names two months a year apart; its rows are added to the file
        result = pd.concat([result, result[result["m"] == "2025-10"].assign(m="2026-01"), result[result["m"] == "2026-10"].assign(m="2027-01")])
    paths["top"] = tmp_path / "top_accounts_result.csv"
    result.to_csv(paths["top"], index=False)
    return paths


def complete_rows(daily, fees):
    """The two series cut at the last day on which every source has a value.

    The daily table follows NearBlocks; DefiLlama can end a day or more earlier (predictions._window), and a fresh
    `make build` can leave it so. Carrying forward a row whose Intents volume is empty would leave A1 and A2 open on
    data that merely ends early, so the row carried forward is the last complete one.
    """
    full = daily[["txns", "price_usd", "total_supply_yocto", "intents_volume_usd"]].dropna().index.max()
    return daily.loc[:full], fees.loc[:fees.dropna().index.max()]


def carried_forward(until="2027-02-12", daily=None, fees=None):
    """The committed daily series and fee series carried forward to a later day, with supply still growing."""
    daily, fees = complete_rows(sources.load_daily(offline=True) if daily is None else daily,
                                value.load() if fees is None else fees)
    more = pd.date_range(daily.index.max() + pd.Timedelta(days=1), until, freq="D")
    tail = pd.DataFrame([daily.iloc[-1]] * len(more), index=more)
    tail["total_supply_yocto"] = daily["total_supply_yocto"].iloc[-1] + np.arange(1, len(more) + 1) * 8.8e28
    more_fees = pd.date_range(fees.index.max() + pd.Timedelta(days=1), until, freq="D")
    daily = pd.concat([daily, tail])
    # The later tables repeat October under every month of B2's window. The independent daily totals must agree
    # for all three: a complete query end date alone cannot certify the absence of missing records inside them.
    total = clients.load()["2026-10"]["conc"]["txs"]
    for month in LATER:
        period = pd.Period(month, "M")
        in_month = daily.index.to_period("M") == period
        daily.loc[in_month, "txns"] = total / period.days_in_month
    return daily, pd.concat([fees, pd.DataFrame([fees.iloc[-1]] * len(more_fees), index=more_fees)])


def test_a_source_that_ends_early_is_cut_before_it_is_carried_forward():
    """DefiLlama a day behind NearBlocks, as after a refresh on a day it updates late: the carried rows are still complete."""
    daily, fees = sources.load_daily(offline=True), value.load()
    short = daily.copy()
    short.loc[short.index[-1], "intents_volume_usd"] = np.nan
    late = fees.copy()
    late.loc[late.index[-1], "revenue"] = np.nan
    longer, more = carried_forward(daily=short, fees=late)
    assert longer.loc[short.index[-1]:, "intents_volume_usd"].notna().all() and more.notna().all().all()
    assert longer.loc[short.index[-1], "intents_volume_usd"] == short["intents_volume_usd"].dropna().iloc[-1]


@pytest.fixture
def later(tmp_path, monkeypatch):
    """Point the build at a scratch directory and at the daily series of February 2027."""
    daily, fees = carried_forward()
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "DOCS", tmp_path / "docs")
    monkeypatch.setattr(sources, "load_daily", lambda offline=False: daily)
    monkeypatch.setattr(value, "load", lambda: fees)

    def build(scan_end=None, **which):
        paths = later_tables(tmp_path, **which)
        monkeypatch.setattr(population, "CSV", paths["census"])
        monkeypatch.setattr(segments, "CSV", paths["frequency"])
        monkeypatch.setattr(clients, "CSV", paths["top"])
        if scan_end:
            monkeypatch.setattr(population, "QUERY_END", scan_end)
        cli.build(offline=True)
        return json.loads((tmp_path / "docs" / "summary.json").read_text(encoding="utf-8"))

    return build


def test_a_later_run_of_all_three_queries_scores_the_four_predictions(later, capsys, tmp_path):
    s = later(scan_end="2027-02-05")
    printed = capsys.readouterr().out
    # the build prints a digest a reader can take in at once: one sentence per chart and the nine statuses, not the summary
    # the statuses, whatever they are: A1 is scored on the days carried forward, and the data that ends the committed
    # series decides whether it holds; that it is scored at all is what this test is about
    assert re.search(r"Predictions: A1 (held|failed), ", printed) and "B4 held" in printed and "Dashboard: " in printed
    assert len(printed) < 4000 and '"yoy_90d"' not in printed and printed.count("\n- ") == 11
    status = {p["id"]: (p["status"], p["measured"]) for p in s["predictions"]["items"]}
    assert len(status) == 9 and all(st in ("held", "failed") for st, v in status.values()), status
    assert all(p["measured"] is not None or p.get("measured_range") is not None for p in s["predictions"]["items"])
    # the tables repeat October, so the four are measured at October's values
    assert status["B1"] == ("held", 17105.0) and status["B3"] == ("held", 30.0)
    assert status["B2"][0] == "held" and status["B4"][0] == "held"
    b4 = next(p for p in s["predictions"]["items"] if p["id"] == "B4")
    assert b4["measured"] is None and b4["measured_range"] == s["clients"]["reward_minus_finance_share"]["latest_range"]
    page = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    assert "held</b> (+1.3 to +2.8 percentage points of all transactions (range))" in page
    # every result compares January 2027 with January 2026, so they are still combined
    for part in ("population", "segments", "clients"):
        assert (s[part]["latest_month"], s[part]["prior_month"]) == ("2027-01", "2026-01"), part
    assert "not_combined_with" not in s["clients"] and "three_parts" in s["clients"]
    assert s["segments"]["excluded_months"] == ["2027-02"]
    assert "2027-02" not in s["segments"]["heavy_by_month"]
    assert "Frequency classes need a complete month; excluded months: 2027-02." in page
    assert s["population"]["partial_month"]["month"] == "2027-02" and s["population"]["partial_month"]["core_direct_txs"]["days"] == 5
    # the sample of autumn 2026 is still set against the months it covers: the file kept its October rows
    assert s["cross_check"]["recent"]["top10_tx_share"]["bigquery_month"] == "2026-10"
    assert list(s["clients"]["months"])[:2] == ["2027-01", "2026-01"] and "2026-10" in s["clients"]["months"]
    # but what that sample says about one sender is not carried over to a month it did not cover
    assert "failing_senders" not in s["clients"] and "failing_sender_txs_latest" not in s["segments"]["self_paid_txs_adjustments"]
    assert len(video.slides(s)) >= 6


def test_a_later_run_of_one_query_alone_is_not_mixed_with_the_others(later, capsys):
    """Only the cheapest query has been run again: B3 and B4 are scored, and nothing combines January with October."""
    s = later(census=False, frequency=False)
    assert "[clients] months differ from population, segments" in capsys.readouterr().out
    status = {p["id"]: p["status"] for p in s["predictions"]["items"]}
    assert status["B3"] == status["B4"] == "held" and status["B1"] == status["B2"] == "open (needs the census query for that month)"
    assert (s["clients"]["latest_month"], s["population"]["latest_month"], s["segments"]["latest_month"]) == ("2027-01", "2026-10", "2026-10")
    assert s["clients"]["not_combined_with"] == ["population", "segments"]
    for combined in ("three_parts", "kaiching_share_by_namespace", "reward_apps_share_incl_kaiching_namespace"):
        assert combined not in s["clients"], combined
    assert "regular_accounts_reward_game_bound" not in s["segments"] and "self_paid_txs_adjustments" not in s["segments"]
    assert len(video.slides(s)) >= 6
