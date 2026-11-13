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


def test_baselines_are_computed_from_data_not_typed():
    idx = pd.date_range("2025-10-01", "2026-10-31", freq="D")
    daily = pd.DataFrame({"intents_volume_usd": 50.0}, index=idx)
    daily.loc["2025-11", "intents_volume_usd"] = 500.0      # a spike before the reference range must be ignored
    daily.loc["2026-08", "intents_volume_usd"] = 90.0
    daily.loc["2026-09":, "intents_volume_usd"] = 300.0     # the step itself is not part of the range either
    assert predictions.baselines(daily, None, None) == {"intents_volume_plateau_top_usd": 90.0}


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
