"""Predictions: frozen by a hash, thresholds taken from the data, scored only when the data reaches the check date."""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from thesis import predictions

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
    result = tmp_path / "top.csv"
    heavy_txs = 700 if half_reached else 400
    result.write_text("m,sec,cells\n"
                      "2027-01,actors,intents.near|350|intents.near;oracle.sweat|300|relayer:sweat-relayer.near\n"
                      f"2027-01,conc,1000|500|{heavy}|{heavy_txs}|{heavy_txs}|{heavy_txs}|{heavy_txs}|2|{heavy}\n"
                      "2027-01,via,intents.near|350|12;relayer:sweat-relayer.near|300|30;mystery.near|40|1\n")
    from thesis import clients
    return census, seg, clients.load(result)


def test_bigquery_predictions_are_scored_once_the_committed_results_hold_the_month(tmp_path, monkeypatch):
    """B1 to B4 stay open until the queries are run again; then the build scores them like the others, misses included."""
    from thesis import clients, population, segments
    p = tmp_path / "p.csv"
    p.write_text(BQ_HEADER
                 + "B1,q,2027-02-01,regular_self_paying_accounts_2027_01,>,7201,b,bigquery,the rebound holds\n"
                 + "B2,q,2027-02-01,core_self_paid_txs_mean_2026_11_to_2027_01,>,10380688,b,bigquery,a new level\n"
                 + "B3,q,2027-02-01,accounts_for_half_of_txs_2027_01,<,100,b,bigquery,a few dozen accounts\n"
                 + "B4,q,2027-02-01,reward_minus_finance_tx_share_2027_01,>,0,b,bigquery,reward apps are larger\n"
                 + "B9,q,2027-02-01,something_else_2027_01,>,0,b,bigquery,no rule for this one\n")
    daily = pd.DataFrame({"intents_volume_usd": 1.0, "price_usd": 1.0}, index=pd.date_range("2026-06-01", "2027-02-05", freq="D"))

    def status(**kw):
        return {r["id"]: (r["status"], r["measured"]) for r in predictions.evaluate(daily, None, p, **kw)["items"]}

    waiting = ("open (needs the census query for that month)", None)
    assert set(status().values()) == {waiting}                                            # no results at all
    committed = dict(census=population.load(), seg=segments.load(), top=clients.load())   # today's results end in October 2026
    assert set(status(**committed).values()) == {waiting}

    census, seg, top = bq_results(tmp_path)
    assert status(census=census, seg=seg, top=top)["B2"] == waiting       # the scan is still marked as ending on 2026-11-11
    monkeypatch.setattr(population, "QUERY_END", "2027-02-10")
    out = status(census=census, seg=seg, top=top)
    assert out["B1"] == ("held", 9500.0)                                  # 9,000 + 500 regular accounts outside the app namespaces
    assert out["B2"][0] == "held" and abs(out["B2"][1] - 32_000_000 / 3) < 1e-6          # mean of 12M, 11M and 9M
    assert out["B3"] == ("held", 2.0)
    assert out["B4"][0] == "failed" and abs(out["B4"][1] - (300 - 350) / 1000) < 1e-12   # a miss is scored as a miss
    assert out["B9"] == waiting
    # before the check date nothing is scored, whatever the files hold
    early = predictions.evaluate(daily.loc[:"2027-01-31"], None, p, census=census, seg=seg, top=top)["items"]
    assert {r["status"] for r in early} == {"open"}
    # a census that stops before the last month of the window is not enough
    monkeypatch.setattr(population, "QUERY_END", "2027-01-20")
    assert status(census=census, seg=seg, top=top)["B2"] == waiting


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
    daily, fees = sources.load_daily(offline=True), value.load()
    until = pd.Timestamp(frozen["check_on"].max()) + pd.Timedelta(days=3)
    more = pd.date_range(daily.index.max() + pd.Timedelta(days=1), until, freq="D")
    tail = pd.DataFrame([daily.iloc[-1]] * len(more), index=more)
    tail["total_supply_yocto"] = daily["total_supply_yocto"].iloc[-1] + np.arange(1, len(more) + 1) * 8.8e28
    more_fees = pd.date_range(fees.index.max() + pd.Timedelta(days=1), until, freq="D")
    daily, fees = pd.concat([daily, tail]), pd.concat([fees, pd.DataFrame([fees.iloc[-1]] * len(more_fees), index=more_fees)])
    census, seg, top = bq_results(tmp_path)
    monkeypatch.setattr(population, "QUERY_END", "2027-02-10")
    out = predictions.evaluate(daily, fees, census=census, seg=seg, top=top)["items"]
    assert len(out) == 9 and all(r["status"] in ("held", "failed") and r["measured"] is not None for r in out), out
    # and with today's files the four that wait for the queries say so
    monkeypatch.undo()
    from thesis import clients, segments
    now = predictions.evaluate(daily, fees, census=population.load(), seg=segments.load(), top=clients.load())["items"]
    assert [r["id"] for r in now if r["status"].startswith("open (needs")] == ["B1", "B2", "B3", "B4"]


def test_accounts_for_half_is_a_lower_bound_when_the_ranked_group_is_too_small(tmp_path):
    """The query ranks accounts with 1,000+ transactions. If they send less than half, the count is only bounded from below."""
    p = tmp_path / "p.csv"
    p.write_text(BQ_HEADER + "B3,q,2027-02-01,accounts_for_half_of_txs_2027_01,<,100,b,bigquery,a few dozen accounts\n")
    daily = pd.DataFrame({"intents_volume_usd": 1.0, "price_usd": 1.0}, index=pd.date_range("2026-06-01", "2027-02-05", freq="D"))
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
    assert full["W3"] == ("failed", 31.0) and full["W4"][0] == "held" and abs(full["W4"][1] - 0.001) < 1e-12
    hole = fees.copy()
    hole.loc["2025-12-15", "holders_revenue"] = np.nan             # inside December and inside the 90 days to 10 January
    assert status(hole) == {"W3": waiting, "W4": waiting}
    other = fees.copy()
    other.loc["2025-11-20", "fees"] = np.nan                       # another series, another month: only the coverage waits
    assert status(other)["W3"] == ("failed", 31.0) and status(other)["W4"] == waiting
    assert status(fees.loc[:"2026-01-08"])["W4"] == waiting       # the series stops two days short of the window


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


def test_adjacent_positive_leads_counts_only_neighbouring_positive_lags():
    def lv(*pairs):
        return {"outside_band": [{"lag_weeks": k, "corr": c} for k, c in pairs]}
    assert predictions.adjacent_positive_leads({"a": lv((2, 0.2), (3, 0.2)), "b": lv((2, 0.2), (4, 0.2)),
                                               "c": lv((-2, 0.2), (-1, 0.2)), "d": lv((5, 0.2), (6, -0.2))}) == 1


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
