"""Boundary failures reproduced through source parsing, frozen rules and public builds."""
from decimal import Decimal, localcontext
import json
import re

import numpy as np
import pandas as pd
import pytest

from thesis import autumn, population, sources, value, video
from tests.test_independent_audit_regressions import build_in
from tests.test_prediction_audit_fixes import score
from tests.test_predictions import bq_results


@pytest.mark.parametrize("case", ["missing_transaction", "missing_context", "later_fall", "zero_buybacks",
                                  "zero_fees", "flat_supply", "missing_l1_fees", "trailing_price",
                                  "flat_take", "month_end"])
def test_boundaries_through_build_and_video(tmp_path, monkeypatch, case):
    daily, fees = sources.load_daily(offline=True), value.load()
    if case == "missing_transaction": daily.loc["2026-04-01", "txns"] = np.nan
    elif case == "missing_context":
        daily.loc["2026-04-02", ["active_accounts", "active_contracts", "new_accounts", "fees_usd"]] = np.nan
    elif case == "later_fall": daily.loc["2026-10-20", "txns"] = 0
    elif case == "zero_buybacks": fees.loc["2026-08-14":, "holders_revenue"] = 0
    elif case == "zero_fees": fees.loc["2026-08-14":] = 0
    elif case == "flat_supply": daily.loc["2026-08-13":, "total_supply_yocto"] = daily.loc["2026-08-13", "total_supply_yocto"]
    elif case == "missing_l1_fees": daily.loc["2026-08-14":, "fees_usd"] = np.nan
    elif case == "trailing_price": daily.loc["2026-10-31":, "price_usd"] = 0
    elif case == "flat_take":
        daily["intents_volume_usd"] = 100.0
        daily.loc["2026-08-19":, "intents_volume_usd"] = 200.0
        fees["revenue"] = daily.intents_volume_usd * .0003
        fees["holders_revenue"] = fees.revenue
        fees["fees"] = daily.intents_volume_usd * .001
    else: daily, fees = daily.loc[:"2026-10-31"], fees.loc[:"2026-10-31"]
    monkeypatch.setattr(value, "load", lambda: fees)
    s, page = build_in(tmp_path, monkeypatch, daily)
    slides = video.slides(s)  # JSON nulls must be handled as well as the in-memory NaNs rendered by build.
    assert not re.search(r"\bnan(?:%|x|\s+times)", page)
    assert not re.search(r"\b(?:nan|None)\b", json.dumps(slides))
    assert all(len(slide["line"]) <= 115 for slide in slides if slide["chart"])
    if case in ("missing_transaction", "later_fall"):
        assert s["autumn"]["reference"]["top"] == {}
        assert s["autumn"]["reference_unavailable"]
        assert s["autumn"]["intents_step"]["day"] == "2026-08-19"
    if case == "missing_transaction": assert "largest_daily_fall" not in s["population"]
    if case == "missing_context":
        fall = s["population"]["largest_daily_fall"]
        assert fall["date"] == "2026-04-02"
        assert set(fall["unavailable_context"]) == {"active_accounts", "active_contracts", "new_accounts", "fees_usd"}
    if case in ("zero_fees", "zero_buybacks", "flat_supply", "missing_l1_fees"):
        assert "Ratios with zero or unknown denominators are unavailable" in page
    if case == "trailing_price":
        assert s["series_ended"]["price_usd"] == s["yoy_90d"]["price_usd"]["through"] == "2026-10-30"
        assert "price usd (2026-10-30)" in page or "price_usd (2026-10-30)" in page or "NEAR price (2026-10-30)" in page
    if case == "flat_take": assert "take_step" not in s["value_capture"]["take"]
    if case == "month_end":
        assert "2026-10" in s["value_capture"]["take"]["take_bps_by_month"]


@pytest.mark.parametrize("column", ["txns", "active_accounts", "active_contracts", "new_accounts", "fees_usd", "price_usd"])
@pytest.mark.parametrize("day", ["2026-04-01", "2026-04-02"])
def test_fall_context_missing_days_are_not_bridged_or_cast_to_int(column, day):
    daily = sources.load_daily(offline=True)
    daily.loc[day, column] = np.nan
    out = population.largest_daily_fall(population.load(), daily)
    if column == "txns": assert out is None
    else:
        assert out["date"] == "2026-04-02"
        assert column in out["unavailable_context"]


@pytest.mark.parametrize("line", [None, 89591201.70967741])
def test_later_fall_with_and_without_a_volume_step_has_no_reference(line):
    out = autumn.summarize(sources.load_daily(offline=True), value.load(), ("2025-12", "2026-08"), "2026-10-20", line)
    assert out["reference"]["top"] == {} and out["reference"]["from"] is None
    assert out["reference_unavailable"]


def exact_supply_daily(version):
    dates = pd.date_range("2026-11-13", "2027-02-11")
    with localcontext() as context:
        context.prec = 60
        supplies = [str(int((Decimal("1000000000.123456") + i * 100000) * 10**24)) for i in range(len(dates))]
    raw = {"charts": [{"date": str(d.date()), "total_supply": supply, "near_price": "2", "market_cap": "2000000000",
                       "txn_fee_usd": "1"} for d, supply in zip(dates, supplies)]}
    v1 = sources.parse_nearblocks(raw)
    if version == "v1": return v1
    raw_v3 = {k: {"data": []} for k in sources.NEARBLOCKS_V3}
    for d, supply in zip(dates, supplies):
        common = {"date": str(d.date())}
        raw_v3["nearblocks_v3_blocks"]["data"].append({**common, "total_supply": supply, "gas_used": "1"})
        raw_v3["nearblocks_v3_txns"]["data"].append({**common, "txns": "1", "txn_fee": "1", "txn_volume": "1"})
        raw_v3["nearblocks_v3_addresses"]["data"].append({**common, "active_contracts": "1"})
        raw_v3["nearblocks_v3_prices"]["data"].append({**common, "near_price": "2", "market_cap": "2000000000"})
    v3 = sources.parse_nearblocks_v3(raw_v3)
    return v3 if version == "v3" else sources.continue_with_v3(v1.loc[:"2026-11-30"], v3)


@pytest.mark.parametrize("version", ["v1", "v3", "continued"])
@pytest.mark.parametrize("cent_change,status", [(-1, "held"), (0, "failed"), (1, "failed")])
def test_a4_exact_half_and_one_cent_either_side(tmp_path, version, cent_change, status):
    daily = exact_supply_daily(version)
    fees = pd.DataFrame({"fees": 400000., "revenue": 100000., "holders_revenue": 100000.}, index=daily.index)
    fees.loc["2027-02-11", "holders_revenue"] += cent_change / 100
    row, page = score(tmp_path, "A4", daily, fees)
    expected = float((Decimal(9000000) + Decimal(cent_change) / 100) / Decimal(18000000))
    assert row["measured_range"] == [expected, expected]
    assert row["status"] == status and f"<b>{status}</b>" in page


def test_changed_supply_cannot_reuse_stale_source_decimals(tmp_path):
    daily = exact_supply_daily("v1")
    daily.loc["2027-02-11", "total_supply_yocto"] += 100000 * 1e24
    fees = pd.DataFrame({"fees": 400000., "revenue": 100000., "holders_revenue": 100000.}, index=daily.index)
    row, _ = score(tmp_path, "A4", daily, fees)
    assert row["status"] == "held"


@pytest.mark.parametrize("pid", ["B1", "B2", "B3", "B4"])
def test_complete_query_with_a_zero_day_is_not_left_waiting(tmp_path, monkeypatch, pid):
    _, seg, top = bq_results(tmp_path)
    seg.loc[seg.payer == "sponsored", "txs"] -= 40000
    top["2027-01"]["conc"]["txs"] = 1650000
    dates = pd.date_range("2026-10-01", "2027-02-01")
    daily = pd.DataFrame({"txns": 55000}, index=dates)
    daily.loc["2027-01-01", "txns"] = 0
    rows = [(m, "near", "ge2y", "returning", 100, int(daily.loc[m, "txns"].sum()), 0, 0)
            for m in ("2026-10", "2026-11", "2026-12", "2027-01")]
    census = pd.DataFrame(rows, columns=["month", "family", "age", "prev_month", "accounts", "txs", "relayed_txs", "single_tx_accounts"])
    monkeypatch.setattr(population, "QUERY_END", "2027-01-31")
    row, _ = score(tmp_path, pid, daily, census=census, seg=seg, top=top)
    assert "needs the census" not in row["status"]
    assert row["status"] in ("held", "failed") or "undecided" in row["status"]


def test_exact_supply_survives_loading_and_joining():
    daily = sources.load_daily(offline=True)
    for day in ("2026-08-13", "2026-11-11"):
        raw, parsed = daily.attrs["exact_supply"][day]
        assert Decimal(raw).is_finite() and parsed == daily.at[pd.Timestamp(day), "total_supply_yocto"]


@pytest.mark.parametrize("pid", ["B3", "B4"])
def test_a_wholly_idle_month_has_no_concentration_or_app_share(tmp_path, pid):
    _, _, top = bq_results(tmp_path)
    top["2027-01"]["conc"].update(txs=0, heavy_txs=0, n50=0)
    daily = pd.DataFrame({"txns": 0}, index=pd.date_range("2027-01-01", "2027-02-01"))
    row, _ = score(tmp_path, pid, daily, top=top)
    assert row["status"].startswith("open") and row["measured"] is None
