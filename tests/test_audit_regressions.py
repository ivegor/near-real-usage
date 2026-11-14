"""Regression cases from the independent audit: public scoring/rendering and isolated builds."""
import json
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from thesis import __main__ as cli
from thesis import census, charts, clients, dashboard, population, predictions, sources, value, video, wallets
from .test_value import frames
from .test_wallets import _point, _daily

ROOT = Path(__file__).resolve().parent.parent


def score(tmp_path, pid, daily, fees=None, **tables):
    path = tmp_path / "prediction.csv"
    pd.read_csv(predictions.CSV).query("id == @pid").to_csv(path, index=False)
    result = predictions.evaluate(daily, fees, path, **tables)
    page = dashboard.render([], {"first_date": str(daily.index.min().date()),
                                "last_date": str(daily.index.max().date()), "days": len(daily),
                                "predictions": result}, tmp_path)
    return result["items"][0], page.read_text()


@pytest.mark.parametrize("filename,aggregation", [("account_age.sql", "act0"), ("payer_frequency.sql", "am"),
                                                   ("payers.sql", "t"), ("top_accounts.sql", "pairs")])
def test_actual_sql_counts_mixed_delegate_once_and_matches_the_block_parser(filename, aggregation):
    # Execute the actual transaction and first aggregation CTEs offline. Only dialect functions are adapted.
    sql = (ROOT / "sql" / filename).read_text()
    flags = re.search(r"transaction_flags AS \(.*?\n\),", sql, re.S).group(0)[:-1]
    agg = re.search(rf"\b{aggregation} AS \(.*?\n\),", sql, re.S).group(0)[:-1]
    query = ("WITH " + flags + ", " + agg + " SELECT * FROM " + aggregation).replace(
        "`bigquery-public-data.crypto_near_mainnet_us.transaction_actions`", "actions").replace(
        "DATE_TRUNC(block_date, MONTH)", "substr(block_date, 1, 7)")
    for name, date in re.findall(r"DECLARE (\w+) DATE DEFAULT '([^']+)';", sql):
        query = re.sub(rf"\b{name}\b", f"'{date}'", query)
    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    db.create_function("IF", 3, lambda cond, a, b: a if cond else b)
    db.create_function("CONCAT", 2, lambda a, b: a + b)
    class CountIf:
        def __init__(self): self.n = 0
        def step(self, x): self.n += bool(x)
        def finalize(self): return self.n
    db.create_aggregate("COUNTIF", 1, CountIf)
    db.execute("CREATE TABLE actions(block_date, transaction_hash, signer_account_id, receiver_account_id, action_kind, index_in_transaction)")
    rows = []
    transactions = []
    for hash_, signer, receiver, kinds in [
        ("first", "relay.near", "alice.near", ["DELEGATE_ACTION", "TRANSFER"]),
        ("second", "relay.near", "alice.near", ["TRANSFER", "DELEGATE_ACTION"]),
        ("direct", "bob.near", "app.near", ["TRANSFER", "FUNCTION_CALL"]),
    ]:
        actions = []
        for i, kind in enumerate(kinds):
            rows.append(("2025-10-01", hash_, signer, receiver, kind, i))
            actions.append({"Delegate": {"delegate_action": {"sender_id": receiver, "receiver_id": "app.near", "actions": []}}}
                           if kind == "DELEGATE_ACTION" else {"Transfer": {"deposit": "1"}})
        transactions.append({"transaction": {"signer_id": signer, "receiver_id": receiver, "actions": actions}})
    db.executemany("INSERT INTO actions VALUES (?, ?, ?, ?, ?, ?)", rows)
    result = {r["a"]: dict(r) for r in db.execute(query)}
    assert set(result) == {"alice.near", "bob.near"}
    count = "txs" if aggregation in ("act0", "am") else "n"
    assert result["alice.near"][count] == 2 and result["bob.near"][count] == 1
    if aggregation == "act0": assert result["alice.near"]["rtx"] == 2 and result["bob.near"]["rtx"] == 0
    if aggregation == "am": assert result["alice.near"]["self_txs"] == 0 and result["bob.near"]["self_txs"] == 1
    if aggregation == "t": assert result["alice.near"]["r"] == "relay.near" and result["bob.near"]["r"] is None
    if aggregation == "pairs": assert result["alice.near"]["v"] == "relayer:relay.near"
    block = {"block": {"header": {"height": 1, "timestamp": 1}}, "shards": [{"chunk": {"transactions": transactions}}]}
    parsed = census.parse_block(block)
    assert [(r["actor"], r["relayed"]) for r in parsed] == [("alice.near", True), ("alice.near", True), ("bob.near", False)]


@pytest.mark.parametrize("heavy,lower", [(40, 210), (150, 320)])
def test_b3_uses_the_unranked_accounts_limit_and_displays_a_bound(tmp_path, heavy, lower):
    total = 1_690_000
    daily = pd.DataFrame({"txns": total / 31}, index=pd.date_range("2027-01-01", "2027-02-01"))
    top = {"2027-01": {"via": pd.DataFrame(), "conc": {"txs": total, "heavy_txs": 676000,
                                                       "heavy_actors": heavy, "n50": heavy}}}
    row, page = score(tmp_path, "B3", daily, top=top)
    assert row["status"] == "failed" and row["measured"] is None and row["measured_lower_bound"] == lower
    assert f"at least {lower} accounts (lower bound)" in page


@pytest.mark.parametrize("tail,expected", [(0, "held"), (999, "held"), (1000, "open")])
def test_b4_cannot_assign_more_than_the_known_tail(tmp_path, tail, expected):
    via = pd.DataFrame({"via": ["relayer:sweat-relayer.near", "intents.near"] + [f"other{i}.near" for i in range(38)],
                        "txs": [1000500, 999500] + [10000] * 38, "actors": 1})
    total = int(via.txs.sum()) + tail
    month = {"via": via, "conc": {"txs": total}}
    daily = pd.DataFrame({"txns": total / 31}, index=pd.date_range("2027-01-01", "2027-02-01"))
    row, page = score(tmp_path, "B4", daily, top={"2027-01": month})
    assert row["status"].startswith(expected)
    assert row["measured_range"] == [(1000-tail)/total, (1000+tail)/total]
    assert "percentage points" in page
    reward, finance = ({v for a in group for v in clients.APPS[a]} for group in (clients.REWARD_APPS, clients.FINANCE_APPS))
    assert clients.gap_range(month, reward, finance) == row["measured_range"]


@pytest.mark.parametrize("column,bad", [("price_usd", 0), ("price_usd", np.inf), ("price_usd", -np.inf),
                                      ("price_usd", np.nan), ("total_supply_yocto", np.inf),
                                      ("total_supply_yocto", -np.inf)])
def test_a4_waits_for_valid_operands_not_just_a_finite_result(tmp_path, column, bad):
    daily, fees = frames(600)
    daily.loc["2027-02-11", column] = bad
    row, page = score(tmp_path, "A4", daily, fees)
    assert row["status"] == "open (waiting for complete data)" and row["measured"] is None
    assert "<b>held</b>" not in page


@pytest.mark.parametrize("pid", ["A1", "A2"])
def test_volume_exact_threshold_equality_is_not_a_hold(tmp_path, pid):
    p = pd.read_csv(predictions.CSV).set_index("id").loc[pid]
    end = pd.Timestamp(p.check_on)
    start = end - pd.Timedelta(days=6) if pid == "A1" else end.replace(day=1)
    daily = pd.DataFrame({"intents_volume_usd": p.threshold}, index=pd.date_range(start, end))
    row, _ = score(tmp_path, pid, daily)
    assert row["status"] == "failed" and row["measured"] == p.threshold


def test_b2_empty_core_in_a_complete_month_is_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(population, "QUERY_END", "2027-02-01")
    table = pd.DataFrame([(m, "tg" if m == "2026-12" else "near", 1000, 0)
                          for m in ["2026-10", "2026-11", "2026-12", "2027-01"]],
                         columns=["month", "family", "txs", "relayed_txs"])
    daily = pd.DataFrame({"txns": 1}, index=pd.date_range("2026-10-01", "2027-02-01"))
    row, _ = score(tmp_path, "B2", daily, census=table)
    assert row["status"] == "failed" and row["measured"] == pytest.approx(2000 / 3)


def test_cached_partial_fee_day_waits_until_a_completed_download(tmp_path, monkeypatch):
    monkeypatch.setattr(sources, "RAW_DIR", tmp_path / "raw")
    idx = pd.date_range("2026-12-01", "2026-12-31")
    reply = {"totalDataChart": [[int(d.timestamp()), 23000. if d.day < 31 else 1000.] for d in idx]}
    monkeypatch.setattr(sources, "_fetch_json", lambda url: reply)
    monkeypatch.setattr(value, "_utc_now", lambda: pd.Timestamp("2026-12-31T12:00Z"))
    value.fetch()
    monkeypatch.setattr(value, "_utc_now", lambda: pd.Timestamp("2027-01-01T12:00Z"))
    daily = pd.DataFrame({"intents_volume_usd": 1e8}, index=idx)
    row, _ = score(tmp_path, "A3", daily, value.load())
    assert row["status"] == "open (waiting for complete data)"
    reply["totalDataChart"][-1][1] = 50000.
    value.fetch()
    row, _ = score(tmp_path, "A3", daily, value.load())
    assert row["status"] == "held" and row["measured"] == 740000.


@pytest.mark.parametrize("column", ["price_usd", "total_supply_yocto"])
def test_value_window_moves_all_operands_when_a_source_stops(column):
    daily, fees = frames()
    daily.loc[daily.index[-30:], column] = np.nan
    v = value.summarize(daily, fees)
    assert v["window"][1] == str(daily.index[-31].date()) and v["days_behind_the_daily_series"] == 30
    assert v["buyback_coverage_of_new_supply"] == pytest.approx(.05)
    assert value.windows(daily, fees)["end"] == v["window"][1]


@pytest.mark.parametrize("column", ["price_usd", "total_supply_yocto"])
def test_value_does_not_substitute_a_missing_denominator_inside_the_window(column):
    daily, fees = frames()
    at = daily.index[-40] if column == "price_usd" else daily.index[-91]
    daily.loc[at, column] = np.nan
    assert value.summarize(daily, fees) is None
    if column == "price_usd":
        assert np.isnan(value.monthly(daily, fees).loc[at.to_period("M"), "new_supply_value"])


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0])
def test_wallet_cross_check_requires_each_converted_day(bad):
    daily = _daily()
    data = {"rpc": "test", "wallets": wallets.WALLETS, "points": [
        _point("2026-01-11T00:00Z", 100, [(0., 0.)]*3), _point("2026-01-31T00:00Z", 300, [(100., 0.)]*3)]}
    fees = pd.DataFrame({"revenue": 50.}, index=daily.index)
    daily.loc["2026-01-20", "price_usd"] = bad
    result = wallets.summarize(data, daily, fees)
    assert "defillama_revenue_near" not in result and "defillama_revenue_near_all_time" not in result
    daily.loc["2026-01-30", "total_supply_yocto"] = np.nan
    assert wallets.summarize(data, daily, fees) is None


def test_missing_buyback_month_is_not_zero_and_has_no_largest_day():
    daily, fees = frames()
    fees.loc["2026-07", "holders_revenue"] = np.nan
    assert np.isnan(value.monthly(daily, fees).loc["2026-07", "holders_revenue"])
    assert value.windows(daily, fees)["by_month"]["2026-07"]["largest_day_near"] is None


@pytest.mark.parametrize("case", ["supply_stopped", "price_hole", "fee_month_hole"])
def test_incomplete_sources_through_the_full_build(tmp_path, monkeypatch, case):
    daily, fees = sources.load_daily(offline=True), value.load()
    if case == "supply_stopped": daily.loc[daily.index[-30:], "total_supply_yocto"] = np.nan
    if case == "price_hole": daily.loc["2026-09-04", "price_usd"] = np.nan
    if case == "fee_month_hole": fees.loc["2026-07", "holders_revenue"] = np.nan
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "DOCS", tmp_path / "docs")
    monkeypatch.setattr(sources, "load_daily", lambda offline=False: daily)
    monkeypatch.setattr(value, "load", lambda: fees)
    cli.build(offline=True)
    s = json.loads((tmp_path / "docs" / "summary.json").read_text())
    page = (tmp_path / "docs" / "index.html").read_text()
    assert len(s["predictions"]["items"]) == 9
    assert "nan%" not in page and "None accounts" not in page
    if case == "supply_stopped":
        v = s["value_capture"]
        assert v["window"][1] == "2026-10-12" and v["days_behind_the_daily_series"] == 30
    if case == "price_hole":
        assert "value_capture" not in s
        assert "Value capture is unavailable" in page and "positive price on every day" in page
    if case == "fee_month_hole": assert s["value_capture"]["windows"]["by_month"]["2026-07"]["largest_day_near"] is None


def test_headlines_and_video_follow_reversed_evidence(tmp_path):
    s = json.loads((ROOT / "docs" / "summary.json").read_text())
    s["population"]["segments"]["all"]["accounts"]["pct_change"] = 25
    s["segments"]["metrics"]["sponsored_accounts"]["pct_change"] = 30
    s["lead_vs_price_holm"]["significant"] = 3
    s["lead_vs_price_holm_leads"] = [{"metric": "txns", "lag_weeks": 1, "p": .00001}]
    s["lead_vs_price"]["txns"]["outside_band"] = [{"lag_weeks": k, "corr": .5} for k in (1, 2)]
    month = s["clients"]["months"][s["clients"]["latest_month"]]
    month["accounts_for_half_of_txs"] = None
    month["accounts_for_half_of_txs_at_least"] = 210
    built = charts.build_all(sources.load_daily(offline=True), s, tmp_path)
    page = dashboard.render(built, s, tmp_path).read_text()
    assert "NEAR gained 25%" in page and "Almost all of the lost" not in page
    assert "At least 210 accounts are needed" in page
    text = " ".join(x["head"] + " " + x["line"] for x in video.slides(s))
    assert "NEAR gained 25%" in text and "Sponsored accounts changed +30%" in text
    assert "3 survive Holm" in text and "Some positive usage lags survive Holm" in text
    assert "None accounts" not in text and "none survives" not in text


def test_independent_null_probability_is_not_described_as_a_bound():
    # The recurrence can be checked on two lags directly: either both above or both below the band.
    import math
    side = .5 * math.erfc(2 / math.sqrt(2))
    assert predictions.a5_chance_without_a_lead(1, lags=2) == pytest.approx(2 * side**2)
    for filename in ("THESIS.md", "PREDICTIONS.md"):
        text = (ROOT / filename).read_text()
        assert "not a lower bound" in text
        assert "more often since the weeks are not" not in text and "more since\n  the weeks are not" not in text


def test_missing_rolling_windows_are_not_ranked_or_counted():
    daily, fees = frames()
    complete = value.windows(daily, fees)["rolling_90d"]
    daily.loc[daily.index[-40], "price_usd"] = np.nan
    missing = value.windows(daily, fees)["rolling_90d"]
    assert missing["windows"] == complete["windows"] - 40
    assert missing["rank_of_the_latest"] is None and np.isnan(missing["latest"])
