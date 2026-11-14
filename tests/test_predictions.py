"""Predictions: frozen by a hash, thresholds taken from the data, scored only when the data reaches the check date."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from thesis import predictions, value

from . import snapshot

ROOT = Path(__file__).resolve().parent.parent


def test_predictions_file_matches_the_published_hash():
    quoted = re.search(r"SHA-256 of `predictions.csv`: `([0-9a-f]{64})`", (ROOT / "PREDICTIONS.md").read_text(encoding="utf-8")).group(1)
    assert predictions.sha256() == quoted


def test_thresholds_are_the_reference_levels_in_the_frozen_snapshot():
    import json
    base = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))["predictions"]["baselines"]
    p = pd.read_csv(ROOT / "predictions.csv").set_index("id")["threshold"]
    assert p["A1"] == p["A2"] == base["intents_volume_plateau_top_usd"]
    assert p["A3"] == base["buyback_plateau_top_usd"]
    assert p["B1"] == base["regular_self_paying_accounts_low"]
    assert p["B2"] == base["core_self_paid_txs_plateau_top"]


def test_the_note_on_b2_quotes_both_reference_levels():
    import json
    base = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))["predictions"]["baselines"]
    text = (ROOT / "PREDICTIONS.md").read_text(encoding="utf-8")
    assert f"the top of the range is {base['core_self_paid_txs_plateau_top_without_dormant_implicit'] / 1e6:.2f}M (June 2026)" in text
    assert f"the threshold stays at {base['core_self_paid_txs_plateau_top'] / 1e6:.2f}M" in text
    monthly = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))["population"]["core_direct_txs_monthly"]
    assert f"{monthly['2025-11'] / 1e6:.2f}M in November 2025 and {monthly['2024-12'] / 1e6:.2f}M in December 2024" in text
    assert monthly["2025-11"] > base["core_self_paid_txs_plateau_top"]          # the month just before the range was above its top
    assert base["core_self_paid_txs_plateau_top_without_dormant_implicit_month"] == "2026-06"


def test_the_notes_quote_the_frozen_snapshot():
    """The price in the step month and the note on B1 are numbers too: they come from the same frozen summary."""
    import json
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))
    text = " ".join((ROOT / "PREDICTIONS.md").read_text(encoding="utf-8").split())
    step, game = s["predictions"]["step"], s["clients"]["reward_game"]
    meteor = s["sponsors"]["sponsored_by_month"]["meteor"]
    assert (step["month"], s["segments"]["regular_accounts_low"]["month"]) == ("2026-09", "2026-08")
    assert s["signer_census"]["windows"]["recent"]["start"] == "2026-08-14"
    assert f"from ${step['price_usd']['first_day']:.2f} to ${step['price_usd']['last_day']:.2f}" in text
    assert (f"up to {game['direct']['prior']['accounts']:,} of the "
            f"{s['segments']['metrics']['regular_accounts']['prior']:,.0f} a year ago") in text
    assert (f"{meteor['2026-08']:,.0f} accounts in August 2026 and {meteor['2026-10']:,.0f} in October, against "
            f"{meteor['2025-08']:,.0f} and {meteor['2025-10']:,.0f} a year earlier") in text
    assert f"all {game['sample_calls']['recent']['calls']} calls to the game come through the relayer" in text
    assert game["sample_calls"]["recent"]["relayed"] == game["sample_calls"]["recent"]["calls"]
    # the days of B2's window that were already in the census when the file was frozen
    pace, base = s["population"]["partial_month"]["core_direct_txs"], s["predictions"]["baselines"]
    assert s["population"]["partial_month"]["month"] == "2026-11" and pace["latest_complete_month"]["month"] == "2026-10"
    over = (pace["whole_month_at_that_rate"] / base["core_self_paid_txs_plateau_top"] - 1) * 100
    assert (f"The first {pace['days']} days of B2's window were in the census when the file was frozen: self-paid transactions ran at "
            f"{pace['per_day'] / 1e3:.0f} thousand a day, a rate of {pace['whole_month_at_that_rate'] / 1e6:.2f}M a month, {over:.0f}% above the "
            f"threshold and {abs(pace['latest_complete_month']['pct_change']):.0f}% below October's rate") in text
    # what else the data held on the day the file was frozen: one day of A1's window, and where HOT was heading for B4
    a1 = pd.read_csv(ROOT / "predictions.csv").set_index("id").loc["A1"]
    assert str((pd.Timestamp(a1["check_on"]) - pd.Timedelta(days=6)).date()) == s["last_date"]       # the first of its seven days
    so_far, hot = s["month_to_date_yoy"]["intents_volume_usd"], s["population"]["partial_month"]["txs_per_day"]["tg"]
    over_a1 = (so_far["recent"] / a1["threshold"] - 1) * 100
    assert (f"one of its seven days was known, and the first {so_far['days']} days of November had averaged "
            f"${so_far['recent'] / 1e6:.1f}M a day, {over_a1:.0f}% above A1's threshold") in text
    assert (f"HOT's namespace was sending {hot['partial'] / 1e3:.0f} thousand transactions a day against "
            f"{hot['latest_complete'] / 1e3:.0f} thousand in October") in text
    clean = s["segments"]["regular_accounts_reward_game_bound"]["without_the_game"]
    assert f"up to {clean['players_still_self_paying_latest_at_most']:,} such accounts in October 2026" in text
    # the same rule a year ago: accounts that acted through the game's relayer and paid for something of their own
    assert (f"and up to {clean['players']['prior']['paying_through_the_relayer']:,} acted through its relayer and paid for "
            f"something else (how many are in both groups the tables do not say)") in text


def test_baselines_are_computed_from_data_not_typed():
    idx = pd.date_range("2025-10-01", "2026-10-31", freq="D")
    daily = pd.DataFrame({"intents_volume_usd": 50.0}, index=idx)
    daily.loc["2025-11", "intents_volume_usd"] = 500.0      # a spike before the reference range must be ignored
    daily.loc["2026-08", "intents_volume_usd"] = 90.0
    daily.loc["2026-09":, "intents_volume_usd"] = 300.0     # the step itself is not part of the range either
    assert predictions.baselines(daily, None, None) == {"intents_volume_plateau_top_usd": 90.0}


def test_reference_level_is_also_published_without_the_one_off_burst():
    """B2's threshold is the highest month of the range; the same level without dormant accounts is shown next to it."""
    idx = pd.date_range("2025-10-01", "2026-10-31", freq="D")
    daily = pd.DataFrame({"intents_volume_usd": 50.0}, index=idx)
    rows = []
    for month in pd.period_range("2025-11", "2026-10", freq="M").astype(str):
        rows.append((month, "near", "ge2y", "returning", 10, 700 if month == "2026-06" else 600, 100, 0))
        rows.append((month, "implicit", "ge2y", "not_returning", 5, 400 if month == "2026-02" else 5, 0, 5))   # a burst in February
        rows.append((month, "tg", "lt1y", "returning", 9, 9000, 0, 0))                                         # not core: ignored
    census = pd.DataFrame(rows, columns=["month", "family", "age", "prev_month", "accounts", "txs", "relayed_txs", "single_tx_accounts"])
    b = predictions.baselines(daily, None, census)
    assert (b["core_self_paid_txs_plateau_top"], b["core_self_paid_txs_plateau_top_month"]) == (900.0, "2026-02")
    assert (b["core_self_paid_txs_plateau_top_without_dormant_implicit"],
            b["core_self_paid_txs_plateau_top_without_dormant_implicit_month"]) == (600.0, "2026-06")


def test_step_reports_the_price_next_to_what_stepped_up():
    """The month after the reference range: the series that stepped up and the NEAR price, which rose in the same month."""
    idx = pd.date_range("2026-07-01", "2026-10-20", freq="D")
    daily = pd.DataFrame({"intents_volume_usd": 50.0, "price_usd": 2.0}, index=idx)
    daily.loc["2026-09", "intents_volume_usd"] = 120.0
    daily.loc["2026-09", "price_usd"] = np.linspace(2.0, 5.0, 30)
    daily.loc["2026-10-05", "price_usd"] = 6.0
    fees = pd.DataFrame({"holders_revenue": 10.0}, index=idx)
    fees.loc["2026-09", "holders_revenue"] = 30.0
    s = predictions.step(daily, fees)
    assert (s["month"], s["month_before"]) == ("2026-09", "2026-08")
    price = s["price_usd"]
    assert (price["first_day"], price["last_day"], price["mean_before"]) == (2.0, 5.0, 2.0)
    assert price["peak_since"] == {"date": "2026-10-05", "value": 6.0} and price["latest"] == {"date": "2026-10-20", "value": 2.0}
    assert s["intents_volume_usd_a_day"] == {"before": 50.0, "month": 120.0}
    assert s["buyback_usd"] == {"before": 310.0, "month": 900.0}
    assert "core_self_paid_txs" not in s                       # no census given: nothing is said about it
    assert predictions.step(daily.loc[:"2026-09-20"]) == {}    # the month has to be complete first


def test_not_scored_on_part_of_its_window(tmp_path):
    """NearBlocks can be ahead of DefiLlama (a late update, or the saved copy during an outage): wait, do not guess."""
    p = tmp_path / "p.csv"
    p.write_text("id,question,check_on,metric,operator,threshold,baseline,scoring,statement\n"
                 "W1,q,2026-01-10,intents_volume_7d_mean_usd,>,100,b,automatic,volume holds\n"
                 "W2,q,2025-12-31,intents_volume_month_mean_usd,>,100,b,automatic,december level\n"
                 "W3,q,2025-12-31,buyback_month_usd,>,100,b,automatic,december buybacks\n"
                 "W4,q,2026-01-10,buyback_coverage_90d,<,0.5,b,automatic,coverage\n")
    idx = pd.date_range("2025-06-01", "2026-01-20", freq="D")
    daily = pd.DataFrame({"intents_volume_usd": 200.0, "price_usd": 1.0}, index=idx)
    daily.loc["2026-01-10":, "intents_volume_usd"] = np.nan      # the volume series stops one day short of the window
    daily.loc["2025-12-25", "intents_volume_usd"] = np.nan       # and December has a hole
    fees = pd.DataFrame({"fees": 4.0, "revenue": 1.0, "holders_revenue": 1.0}, index=pd.date_range("2025-06-01", "2025-12-30", freq="D"))
    out = {r["id"]: r for r in predictions.evaluate(daily, fees, p)["items"]}
    for r in out.values():
        assert r["status"] == "open (waiting for complete data)" and r["measured"] is None, r
    # once every day of the window is there, the same predictions are scored
    daily["intents_volume_usd"] = 200.0
    fees = pd.DataFrame({"fees": 4.0, "revenue": 1.0, "holders_revenue": 1.0}, index=pd.date_range("2025-06-01", "2025-12-31", freq="D"))
    out = {r["id"]: r for r in predictions.evaluate(daily, fees, p)["items"]}
    assert (out["W1"]["status"], out["W1"]["measured"]) == ("held", 200.0)
    assert (out["W2"]["status"], out["W2"]["measured"]) == ("held", 200.0)
    assert (out["W3"]["status"], out["W3"]["measured"]) == ("failed", 31.0)
    assert out["W4"]["status"] == "open (waiting for complete data)"          # the fee series still ends before 2026-01-10


BQ_HEADER = "id,question,check_on,metric,operator,threshold,baseline,scoring,statement\n"
JANUARY_TXS = 1_690_000      # what the frequency table and the table of largest accounts below both count in January 2027


def bq_results(tmp_path, half_reached=True, heavy=3):
    """Query results that hold the months the "bigquery" predictions name, in the formats the build reads."""
    months = pd.period_range("2026-10", "2027-02", freq="M").astype(str)
    self_paid = {"2026-10": 12_000_000, "2026-11": 12_000_000, "2026-12": 11_000_000, "2027-01": 9_000_000, "2027-02": 1_000_000}
    rows = []
    for month in months:
        rows.append((month, "near", "ge2y", "returning", 10, self_paid[month] + 500, 500, 0))    # 500 of them relayed
        rows.append((month, "tg", "lt1y", "returning", 9, 90_000_000, 0, 0))                     # not core: ignored
    census = pd.DataFrame(rows, columns=["month", "family", "age", "prev_month", "accounts", "txs", "relayed_txs", "single_tx_accounts"])
    seg = pd.DataFrame([("2027-01", "rest", "self", "10-99", 9_000, 200_000, 190_000), ("2027-01", "rest", "self", "100-999", 500, 90_000, 90_000),
                        ("2027-01", "tg", "self", "10-99", 70_000, 900_000, 800_000), ("2027-01", "rest", "sponsored", "10-99", 40_000, 500_000, 0)],
                       columns=["month", "namespace", "payer", "txs_in_month", "accounts", "txs", "self_paid_txs"])
    assert seg["txs"].sum() == JANUARY_TXS
    result = tmp_path / "top.csv"
    k = JANUARY_TXS // 1000      # the same month in the other table: the shares below are thousandths of it
    heavy_txs = (700 if half_reached else 400) * k
    result.write_text("m,sec,cells\n"
                      f"2027-01,actors,intents.near|{350 * k}|intents.near;oracle.sweat|{300 * k}|relayer:sweat-relayer.near\n"
                      f"2027-01,conc,{JANUARY_TXS}|500|{heavy}|{heavy_txs}|{heavy_txs}|{heavy_txs}|{heavy_txs}|2|{heavy}\n"
                      f"2027-01,via,intents.near|{350 * k}|12;relayer:sweat-relayer.near|{300 * k}|30;mystery.near|{40 * k}|1;"
                      f"tiny.near|1|1\n")  # the smallest listed entry bounds what an unlisted contract can have received
    from thesis import clients
    return census, seg, clients.load(result)


def days_of_january(index, total=JANUARY_TXS):
    """The aggregator's daily transaction counts: January 2027 adds up to `total`, with one quiet day; other days do not matter."""
    txns = pd.Series(1.0, index=index)
    january = index[(index >= "2027-01-01") & (index <= "2027-01-31")]
    txns[january] = (total - 30_000) / 30
    txns[january[0]] = 30_000        # the quietest day: a result short by this much or more has missed a day
    return txns


def test_bigquery_predictions_are_scored_once_the_committed_results_hold_the_month(tmp_path, monkeypatch):
    """B1 to B4 stay open until the queries are run again; then the build scores them like the others, misses included."""
    from thesis import population
    p = tmp_path / "p.csv"
    p.write_text(BQ_HEADER
                 + "B1,q,2027-02-01,regular_self_paying_accounts_2027_01,>,7201,b,bigquery,the rebound holds\n"
                 + "B2,q,2027-02-01,core_self_paid_txs_mean_2026_11_to_2027_01,>,10380688,b,bigquery,a new level\n"
                 + "B3,q,2027-02-01,accounts_for_half_of_txs_2027_01,<,100,b,bigquery,a few dozen accounts\n"
                 + "B4,q,2027-02-01,reward_minus_finance_tx_share_2027_01,>,0,b,bigquery,reward apps are larger\n"
                 + "B9,q,2027-02-01,something_else_2027_01,>,0,b,bigquery,no rule for this one\n")
    idx = pd.date_range("2026-06-01", "2027-02-05", freq="D")
    daily = pd.DataFrame({"intents_volume_usd": 1.0, "price_usd": 1.0, "txns": days_of_january(idx)}, index=idx)

    def status(**kw):
        return {r["id"]: (r["status"], r["measured"]) for r in predictions.evaluate(daily, None, p, **kw)["items"]}

    waiting = ("open (needs the census query for that month)", None)
    assert set(status().values()) == {waiting}                                            # no results at all
    # the results as they stood when the predictions were written: they end in October 2026
    monkeypatch.setattr(population, "QUERY_END", snapshot.SCAN_END)
    committed = dict(census=snapshot.census(), seg=snapshot.frequency(), top=snapshot.top())
    assert set(status(**committed).values()) == {waiting}

    census, seg, top = bq_results(tmp_path)
    assert status(census=census, seg=seg, top=top)["B2"] == waiting       # the scan is still marked as ending on 2026-11-11
    monkeypatch.setattr(population, "QUERY_END", "2027-02-10")
    out = status(census=census, seg=seg, top=top)
    assert out["B1"] == ("held", 9500.0)                                  # 9,000 + 500 regular accounts outside the app namespaces
    assert out["B2"][0] == "held" and abs(out["B2"][1] - 32_000_000 / 3) < 1e-6          # mean of 12M, 11M and 9M
    assert out["B3"] == ("held", 2.0)
    assert out["B4"] == ("failed", None)                                  # a miss is scored as a miss, with a range
    b4 = next(r for r in predictions.evaluate(daily, None, p, census=census, seg=seg, top=top)["items"] if r["id"] == "B4")
    low, high = b4["measured_range"]
    assert low < (300 - 350) / 1000 < high and high - low < 1e-4
    assert out["B9"] == waiting
    # before the check date nothing is scored, whatever the files hold
    early = predictions.evaluate(daily.loc[:"2027-01-31"], None, p, census=census, seg=seg, top=top)["items"]
    assert {r["status"] for r in early} == {"open"}
    # a census that stops before the last month of the window is not enough
    monkeypatch.setattr(population, "QUERY_END", "2027-01-20")
    assert status(census=census, seg=seg, top=top)["B2"] == waiting


def test_a_result_that_misses_a_day_of_its_month_is_not_scored(tmp_path):
    """The frequency and top-accounts queries name whole months. Run before the month ended, their result is short of the
    aggregator's daily counts by a day or more, and the prediction waits for a run that holds the whole month."""
    p = tmp_path / "p.csv"
    p.write_text(BQ_HEADER
                 + "B1,q,2027-02-01,regular_self_paying_accounts_2027_01,>,7201,b,bigquery,the rebound holds\n"
                 + "B3,q,2027-02-01,accounts_for_half_of_txs_2027_01,<,100,b,bigquery,a few dozen accounts\n"
                 + "B4,q,2027-02-01,reward_minus_finance_tx_share_2027_01,>,0,b,bigquery,reward apps are larger\n")
    idx = pd.date_range("2026-06-01", "2027-02-05", freq="D")
    _, seg, top = bq_results(tmp_path)

    def status(txns):
        daily = pd.DataFrame({"intents_volume_usd": 1.0, "price_usd": 1.0, "txns": txns}, index=idx)
        return {r["id"]: r["status"] for r in predictions.evaluate(daily, None, p, seg=seg, top=top)["items"]}

    waiting = "open (needs the census query for that month)"
    assert status(days_of_january(idx)) == {"B1": "held", "B3": "held", "B4": "failed"}
    # the aggregator counted a day's worth more than the results hold: the quietest day of the month (30,000) is the line
    assert set(status(days_of_january(idx, JANUARY_TXS + 31_000)).values()) == {waiting}
    # short by less than a day is how two sources differ in a month they both hold: scored
    assert status(days_of_january(idx, JANUARY_TXS + 29_000)) == {"B1": "held", "B3": "held", "B4": "failed"}
    # a day missing from the aggregator's count: nothing shows the result holds the whole month, so it waits too
    gap = days_of_january(idx)
    gap["2027-01-15"] = np.nan
    assert set(status(gap).values()) == {waiting}
    # the rule itself: nothing to compare with means the result is not scored yet
    days = pd.DataFrame({"txns": days_of_january(idx)}, index=idx)
    assert predictions.holds_the_whole_month(JANUARY_TXS, "2027-01", days)
    assert not predictions.holds_the_whole_month(JANUARY_TXS - 31_000, "2027-01", days)
    assert not predictions.holds_the_whole_month(1, "2027-01", None)
    assert not predictions.holds_the_whole_month(1, "2027-01", days[["txns"]].rename(columns={"txns": "x"}))
    assert not predictions.holds_the_whole_month(1, "2027-03", days)         # the daily series does not reach that month
    # and the committed results as they stand: every month the frequency table holds is a whole one
    from thesis import sources
    real, table = sources.load_daily(offline=True), snapshot.frequency()
    for month, counted in table.groupby("month")["txs"].sum().items():
        assert predictions.holds_the_whole_month(counted, month, real), month
    assert all(predictions.holds_the_whole_month(v["conc"]["txs"], m, real) for m, v in snapshot.top().items())
    # while a result that stopped one day short would not pass: October without the transactions of its last day
    october = snapshot.census()
    october = october[october["month"] == "2026-10"]["txs"].sum()
    assert predictions.holds_the_whole_month(october, "2026-10", real)
    assert not predictions.holds_the_whole_month(october - real.loc["2026-10-31", "txns"], "2026-10", real)


def test_every_prediction_in_the_frozen_file_can_be_scored(tmp_path, monkeypatch):
    """All nine: five from the daily series, four from query results that hold the months they name. None is left without a rule."""
    from thesis import population, sources, value
    frozen = pd.read_csv(ROOT / "predictions.csv")
    for row in frozen.itertuples():
        if row.scoring == "bigquery":
            named = predictions.BQ_METRIC.match(row.metric)
            assert named and named["name"] in predictions.COMMITTED, row.metric
        else:
            assert row.scoring == "automatic" and row.metric in predictions.AUTOMATIC, row.metric
    # the committed daily series carried forward past the last check date, with supply still growing
    # (cut first at the last day every source covers: DefiLlama can end a day before NearBlocks, see tests/test_rerun.py)
    from .test_rerun import carried_forward
    daily, fees = carried_forward(str((pd.Timestamp(frozen["check_on"].max()) + pd.Timedelta(days=3)).date()))
    january = (daily.index >= "2027-01-01") & (daily.index <= "2027-01-31")
    daily.loc[january, "txns"] = JANUARY_TXS / 31          # the aggregator's January: the month the two tables below hold in full
    census, seg, top = bq_results(tmp_path)
    monkeypatch.setattr(population, "QUERY_END", "2027-02-10")
    out = predictions.evaluate(daily, fees, census=census, seg=seg, top=top)["items"]
    assert len(out) == 9 and all(r["status"] in ("held", "failed") for r in out), out
    assert all(r["measured"] is not None or r.get("measured_range") is not None for r in out), out
    # and with the results as they stood when the file was frozen, the four that wait for the queries say so
    monkeypatch.setattr(population, "QUERY_END", snapshot.SCAN_END)
    now = predictions.evaluate(daily, fees, census=snapshot.census(), seg=snapshot.frequency(), top=snapshot.top())["items"]
    assert [r["id"] for r in now if r["status"].startswith("open (needs")] == ["B1", "B2", "B3", "B4"]


def test_accounts_for_half_is_a_lower_bound_when_the_ranked_group_is_too_small(tmp_path):
    """The query ranks accounts with 1,000+ transactions. If they send less than half, the count is only bounded from below."""
    p = tmp_path / "p.csv"
    p.write_text(BQ_HEADER + "B3,q,2027-02-01,accounts_for_half_of_txs_2027_01,<,100,b,bigquery,a few dozen accounts\n")
    idx = pd.date_range("2026-06-01", "2027-02-05", freq="D")
    daily = pd.DataFrame({"intents_volume_usd": 1.0, "price_usd": 1.0, "txns": days_of_january(idx)}, index=idx)
    _, _, many = bq_results(tmp_path, half_reached=False, heavy=150)      # 150 accounts send 40%: more than 150 are needed
    out = predictions.evaluate(daily, None, p, top=many)["items"][0]
    assert (out["status"], out["measured"]) == ("failed", 151.0)
    _, _, few = bq_results(tmp_path, half_reached=False, heavy=40)        # more than 40 are needed: under or over 100, unknown
    out = predictions.evaluate(daily, None, p, top=few)["items"][0]
    assert (out["status"], out["measured"]) == ("open (needs the census query for that month)", None)


def test_buyback_predictions_wait_for_a_day_that_is_missing(tmp_path):
    """A hole in the buyback series must not be read as a day without buybacks, in the month's sum or in the 90-day coverage."""
    p = tmp_path / "p.csv"
    p.write_text(BQ_HEADER + "W3,q,2025-12-31,buyback_month_usd,>,100,b,automatic,december buybacks\n"
                 + "W4,q,2026-01-10,buyback_coverage_90d,<,0.5,b,automatic,coverage\n")
    idx = pd.date_range("2025-06-01", "2026-01-20", freq="D")
    daily = pd.DataFrame({"intents_volume_usd": 200.0, "price_usd": 1.0, "fees_usd": 10.0, "market_cap_usd": 1e9,
                          "total_supply_yocto": (1e9 + 1000.0 * np.arange(len(idx))) * 1e24}, index=idx)
    fees = pd.DataFrame({"fees": 4.0, "revenue": 1.0, "holders_revenue": 1.0}, index=idx)

    def status(f):
        return {r["id"]: (r["status"], r["measured"]) for r in predictions.evaluate(daily, f, p)["items"]}

    waiting = ("open (waiting for complete data)", None)
    full = status(fees)
    assert full["W3"] == ("failed", 31.0) and full["W4"] == ("held", None)     # A4 is scored on two measurements
    w4 = {r["id"]: r for r in predictions.evaluate(daily, fees, p)["items"]}["W4"]
    assert w4["measured_range"] == pytest.approx([0.001, 0.001])     # a constant price: USD and NEAR give the same ratio
    hole = fees.copy()
    hole.loc["2025-12-15", "holders_revenue"] = np.nan             # inside December and inside the 90 days to 10 January
    assert status(hole) == {"W3": waiting, "W4": waiting}
    other = fees.copy()
    other.loc["2025-11-20", "fees"] = np.nan                       # another series, another month: only the coverage waits
    assert status(other)["W3"] == ("failed", 31.0) and status(other)["W4"] == waiting
    assert status(fees.loc[:"2026-01-08"])["W4"] == waiting       # the series stops two days short of the window
    # the other side of the ratio: the price of every day and the supply on the day before the 90 days and on the last
    full_daily = daily.copy()
    daily.loc["2025-10-13":"2026-01-09", "price_usd"] = np.nan    # 89 of the 90 prices missing
    assert status(fees)["W4"] == waiting
    for day in ("2025-10-12", "2026-01-10"):
        daily = full_daily.copy()
        daily.loc[day, "total_supply_yocto"] = np.nan
        assert status(fees)["W4"] == waiting, day
    daily = full_daily.copy()
    daily.loc["2025-11-20", "total_supply_yocto"] = np.nan         # a supply missing inside the window is not read
    assert status(fees)["W4"][0] == "held"


def test_step_reports_what_the_series_did_in_the_range_before_it():
    """The nine months before the step: the level a "new level" is measured against, and the same months a year earlier."""
    idx = pd.date_range("2025-10-01", "2026-10-20", freq="D")
    daily = pd.DataFrame({"intents_volume_usd": 60.0, "price_usd": 2.0}, index=idx)
    daily.loc["2025-11", "intents_volume_usd"] = 120.0             # the spike a year before
    daily.loc["2026-08", "intents_volume_usd"] = 90.0
    daily.loc["2026-09":, "intents_volume_usd"] = 160.0
    rows = [(month, "near", "ge2y", "returning", 10, 1000 if month < "2025-12" else 800, 0, 0)
            for month in pd.period_range("2024-12", "2026-10", freq="M").astype(str)]
    rows += [("2026-02", "implicit", "ge2y", "not_returning", 90, 900, 0, 90)]       # a one-off burst of dormant accounts
    census = pd.DataFrame(rows, columns=["month", "family", "age", "prev_month", "accounts", "txs", "relayed_txs", "single_tx_accounts"])
    s = predictions.step(daily, None, census)
    assert s["reference_range"] == {"first": "2025-12", "last": "2026-08", "months": 9}
    v = s["intents_volume_usd_a_day"]
    assert (v["before"], v["month"], v["range_low"], v["range_top"]) == (90.0, 160.0, 60.0, 90.0)
    assert v["month_before_range"] == {"month": "2025-11", "value": 120.0}
    assert abs(v["range_mean"] - (60.0 * (274 - 31) + 90.0 * 31) / 274) < 1e-9         # 274 days from 1 December to 31 August
    c = s["core_self_paid_txs"]
    assert (c["range_mean"], c["range_mean_a_year_earlier"]) == (900.0, 1000.0) and abs(c["range_pct_change"] + 10) < 1e-9
    assert abs(c["range_pct_change_without_dormant_implicit"] + 20) < 1e-9 and c["range_months_below_a_year_earlier"] == 8
    # an average below the year before is not every month below it: the month above is named, with by how much
    assert list(c["range_months_above_a_year_earlier"]) == ["2026-02"] and abs(c["range_months_above_a_year_earlier"]["2026-02"] - 70) < 1e-9
    # inside a family, by age and activity: the three parts add up to the family's change, and the burst is the older
    # accounts that were not active the month before
    for f, fam in c["range_by_family"].items():
        parts = fam["by_age_and_activity"]
        assert sum(parts[k]["change"] for k in ("under_a_year", "older_active_the_month_before", "older_not_active_the_month_before")) == fam["range_change_txs"]
    imp = c["range_by_family"]["implicit"]["by_age_and_activity"]
    assert imp["older_not_active_the_month_before"]["change"] == 900 and imp["under_a_year"]["change"] == 0
    assert c["base_of_the_months_above"]["2026-02"]["base_month"] == "2025-02"


def test_adjacent_positive_leads_counts_neighbouring_positive_lags_of_one_sign():
    def lv(*pairs):
        return {"outside_band": [{"lag_weeks": k, "corr": c} for k, c in pairs]}
    cases = {"a": lv((2, 0.2), (3, 0.2)), "b": lv((2, 0.2), (4, 0.2)), "c": lv((-2, 0.2), (-1, 0.2)),
             "d": lv((5, 0.2), (6, -0.2)), "e": lv((1, -0.9), (2, -0.9))}
    # a pair that moves against the price is a timing signal too (e); a pair of opposite signs is not one signal (d)
    assert predictions.adjacent_positive_leads(cases) == 2
    assert predictions.adjacent_positive_leads(cases, positive_only=True) == 1  # the count until 2026-11-14


def test_a5_is_zero_on_the_frozen_data_either_way():
    lead = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))["lead_vs_price"]
    assert predictions.adjacent_positive_leads(lead) == predictions.adjacent_positive_leads(lead, positive_only=True) == 0


def test_scored_only_after_the_check_date(tmp_path):
    p = tmp_path / "p.csv"
    p.write_text("id,question,check_on,metric,operator,threshold,baseline,scoring,statement\n"
                 "X1,q,2026-01-10,intents_volume_7d_mean_usd,>,100,b,automatic,volume holds\n"
                 "X2,q,2026-01-10,intents_volume_7d_mean_usd,>,500,b,automatic,volume doubles\n"
                 "X3,q,2026-03-01,intents_volume_7d_mean_usd,>,100,b,automatic,later\n"
                 "X4,q,2026-01-05,core_accounts,<,5,b,bigquery,needs a query\n"
                 "X5,q,2025-12-31,intents_volume_month_mean_usd,>,150,b,automatic,december level\n")
    idx = pd.date_range("2025-06-01", "2026-01-20", freq="D")
    daily = pd.DataFrame({"intents_volume_usd": 200.0, "price_usd": 1 + np.arange(len(idx)) * 0.0}, index=idx)
    daily.loc["2026-01-11":, "intents_volume_usd"] = 0.0     # later data must not change a past check
    out = {r["id"]: r for r in predictions.evaluate(daily, None, p)["items"]}
    assert out["X1"]["status"] == "held" and out["X1"]["measured"] == 200.0
    assert out["X2"]["status"] == "failed"
    assert out["X3"]["status"] == "open" and out["X3"]["measured"] is None
    assert out["X4"]["status"].startswith("open (needs")
    assert out["X5"]["status"] == "held"


def test_the_timestamp_proof_is_for_this_predictions_file():
    """predictions.csv.ots is an OpenTimestamps proof; a detached proof starts with the digest of the file it is for."""
    import hashlib
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    digest = hashlib.sha256((root / "predictions.csv").read_bytes()).digest()
    proof = (root / "predictions.csv.ots").read_bytes()
    assert proof.startswith(b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94")
    assert digest in proof[:80]


def test_the_timestamp_proof_names_the_bitcoin_block_quoted_in_the_notes():
    """After `ots upgrade` the proof carries a Bitcoin block header attestation; PREDICTIONS.md names its block."""
    root = Path(__file__).resolve().parent.parent
    proof = (root / "predictions.csv.ots").read_bytes()
    tag = bytes.fromhex("0588960d73d71901")          # BitcoinBlockHeaderAttestation in the OpenTimestamps format
    assert tag in proof

    def varuint(buf: bytes, i: int) -> tuple[int, int]:
        value, shift = 0, 0
        while True:
            b = buf[i]
            value |= (b & 0x7F) << shift
            i, shift = i + 1, shift + 7
            if not b & 0x80:
                return value, i

    i = proof.index(tag) + len(tag)
    _, i = varuint(proof, i)                         # the length of the attestation's payload
    height, _ = varuint(proof, i)
    notes = " ".join((root / "PREDICTIONS.md").read_text(encoding="utf-8").split())
    assert f"it holds the attestation of Bitcoin block {height}" in notes


def test_a5_waits_for_the_usage_series_to_reach_its_check_date():
    """Prices alone up to the check date must not score A5: the usage series it tests have to reach it too."""
    from thesis import sources
    daily = sources.load_daily(offline=True)
    later = pd.date_range(daily.index.max() + pd.Timedelta(days=1), "2027-02-11", freq="D")
    only_prices = pd.concat([daily, pd.DataFrame({"price_usd": 3.0}, index=later)])
    assert predictions._measure("metrics_with_adjacent_positive_leads", pd.Timestamp("2027-02-11"), only_prices, None) is None
    full = only_prices.copy()
    for c in ("txns", "fees_usd", "intents_volume_usd"):
        full.loc[later, c] = daily[c].dropna().iloc[-1]
    assert predictions._measure("metrics_with_adjacent_positive_leads", pd.Timestamp("2027-02-11"), full, None) is not None


def test_b4_is_scored_only_when_the_contracts_outside_the_40_cannot_reverse_it(tmp_path):
    """Each side has one unlisted contract with at most 101 transactions. Keep both bounds, even when undecided;
    for the frozen > 0 rule, touching zero from above is undecided and touching it from below is a miss."""
    from thesis import clients
    reward, finance = ([v for app in group for v in clients.APPS[app]][:-1]
                       for group in (clients.REWARD_APPS, clients.FINANCE_APPS))
    via = pd.DataFrame({"via": reward + finance + ["filler.near"], "txs": 200, "actors": 1})
    via.loc[via["via"] == "filler.near", "txs"] = 101
    path = tmp_path / "p.csv"
    path.write_text(BQ_HEADER + "B4,q,2027-02-01,reward_minus_finance_tx_share_2027_01,>,0,b,bigquery,reward apps are larger\n")
    undecided = "open (undecided: the group's contracts outside the 40 largest could reverse it)"
    for gap, status in ((102, "held"), (100, undecided), (-102, "failed"), (-101, "failed"), (101, undecided)):
        via.loc[via["via"] == reward[0], "txs"] = (len(finance) - len(reward) + 1) * 200 + gap
        total = int(via["txs"].sum()) + 1_000
        top = {"2027-01": {"via": via, "conc": {"txs": total}}}
        daily = pd.DataFrame({"txns": total / 31}, index=pd.date_range("2027-01-01", "2027-02-01"))
        result, = predictions.evaluate(daily, None, path, top=top)["items"]
        assert result["status"] == status, (gap, result)
        assert result["measured"] is None
        assert result["measured_range"] == [(gap - 101) / total, (gap + 101) / total]


def test_a4_is_scored_on_the_ratio_in_usd_and_in_near(tmp_path):
    """Buybacks in USD over the new supply at the mean price, and buybacks in NEAR at each day's price over the new NEAR,
    differ when the price moves inside the window. A4 holds only if both are below the line, and is open if they differ."""
    p = tmp_path / "p.csv"
    p.write_text(BQ_HEADER + "W4,q,2026-01-10,buyback_coverage_90d,<,0.5,b,automatic,coverage\n")
    idx = pd.date_range("2025-06-01", "2026-01-20", freq="D")
    price = pd.Series(1.0, index=idx)
    price.loc["2025-12-01":] = 4.0                     # the price quadruples for the last 41 days of the window
    daily = pd.DataFrame({"intents_volume_usd": 200.0, "price_usd": price, "fees_usd": 10.0, "market_cap_usd": 1e9,
                          "total_supply_yocto": (1e9 + 1000.0 * np.arange(len(idx))) * 1e24}, index=idx)
    hr = pd.Series(0.0, index=idx)
    hr.loc["2025-12-01":] = 3300.0                     # all the buybacks arrive at the high price
    fees = pd.DataFrame({"fees": 4.0, "revenue": hr, "holders_revenue": hr}, index=idx)
    v = value.summarize(daily.loc[:"2026-01-10"], fees.loc[:"2026-01-10"])
    usd, near = v["buyback_coverage_of_new_supply"], v["buyback_coverage_in_near"]
    assert near == pytest.approx(41 * 3300 / 4 / 90_000)
    assert usd == pytest.approx(41 * 3300 / (90_000 * (49 * 1 + 41 * 4) / 90))
    assert near < 0.5 < usd                            # the two give different verdicts
    row = predictions.evaluate(daily, fees, p)["items"][0]
    assert row["status"].startswith("open (undecided: the ratio in USD and the ratio in NEAR")
    assert row["measured"] is None and row["measured_range"] == pytest.approx([usd, near])
