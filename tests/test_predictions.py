"""Predictions: frozen by a hash, thresholds taken from the data, scored only when the data reaches the check date."""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from thesis import predictions

ROOT = Path(__file__).resolve().parent.parent


def test_predictions_file_matches_the_published_hash():
    quoted = re.search(r"SHA-256 of `predictions.csv`: `([0-9a-f]{64})`", (ROOT / "PREDICTIONS.md").read_text()).group(1)
    assert predictions.sha256() == quoted


def test_thresholds_are_the_reference_levels_in_the_frozen_snapshot():
    import json
    base = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text())["predictions"]["baselines"]
    p = pd.read_csv(ROOT / "predictions.csv").set_index("id")["threshold"]
    assert p["A1"] == p["A2"] == base["intents_volume_plateau_top_usd"]
    assert p["A3"] == base["buyback_plateau_top_usd"]
    assert p["B1"] == base["regular_self_paying_accounts_low"]
    assert p["B2"] == base["core_self_paid_txs_plateau_top"]


def test_the_note_on_b2_quotes_both_reference_levels():
    import json
    base = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text())["predictions"]["baselines"]
    text = (ROOT / "PREDICTIONS.md").read_text()
    assert f"the top of the range is {base['core_self_paid_txs_plateau_top_without_dormant_implicit'] / 1e6:.2f}M (June 2026)" in text
    assert f"the threshold stays at {base['core_self_paid_txs_plateau_top'] / 1e6:.2f}M" in text
    assert base["core_self_paid_txs_plateau_top_without_dormant_implicit_month"] == "2026-06"


def test_the_notes_quote_the_frozen_snapshot():
    """The price in the step month and the note on B1 are numbers too: they come from the same frozen summary."""
    import json
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text())
    text = " ".join((ROOT / "PREDICTIONS.md").read_text().split())
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
