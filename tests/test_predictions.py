"""Predictions: the file is frozen by its hash and scored only when the data reaches the check date."""
import re
from pathlib import Path

import numpy as np
import pandas as pd

from thesis import predictions

ROOT = Path(__file__).resolve().parent.parent


def test_predictions_file_matches_the_published_hash():
    quoted = re.search(r"SHA-256 of `predictions.csv`: `([0-9a-f]{64})`", (ROOT / "PREDICTIONS.md").read_text()).group(1)
    assert predictions.sha256() == quoted


def test_scored_only_after_the_check_date(tmp_path):
    p = tmp_path / "p.csv"
    p.write_text("id,check_on,metric,operator,threshold,scoring,statement\n"
                 "X1,2026-01-10,intents_volume_7d_mean_usd,>=,100,automatic,volume holds\n"
                 "X2,2026-01-10,intents_volume_7d_mean_usd,>=,500,automatic,volume doubles\n"
                 "X3,2026-03-01,intents_volume_7d_mean_usd,>=,100,automatic,later\n"
                 "X4,2026-01-05,core_accounts,<,5,bigquery,needs a query\n")
    idx = pd.date_range("2025-06-01", "2026-01-20", freq="D")
    daily = pd.DataFrame({"intents_volume_usd": 200.0, "price_usd": 1 + np.arange(len(idx)) * 0.0}, index=idx)
    daily.loc["2026-01-11":, "intents_volume_usd"] = 0.0     # later data must not change a past check
    out = {r["id"]: r for r in predictions.evaluate(daily, None, p)["items"]}
    assert out["X1"]["status"] == "held" and out["X1"]["measured"] == 200.0
    assert out["X2"]["status"] == "failed"
    assert out["X3"]["status"] == "open" and out["X3"]["measured"] is None
    assert out["X4"]["status"].startswith("open (needs")
