"""Incomplete revenue series must use consistent totals and identify every estimate."""
import json

import numpy as np
import pandas as pd
import pytest

from thesis import __main__ as cli
from thesis import charts, dashboard, sources, value
from .test_value import frames


@pytest.mark.parametrize("column,label", [("fees", "Intents gross fees"), ("revenue", "captured revenue"),
                                         ("holders_revenue", "buybacks"), ("fees_usd", "network transaction fees")])
@pytest.mark.parametrize("missing", [np.nan, np.inf])
def test_asymmetric_gaps_use_displayed_totals_and_label_estimates(tmp_path, column, label, missing):
    daily, fees = frames()
    # Variable revenue makes the missing day material; the other series stay complete.
    fees.loc[fees.index[-40], ["fees", "revenue", "holders_revenue"]] = [800_000., 200_000., 200_000.]
    table = daily if column == "fees_usd" else fees
    table.loc[table.index[-40], column] = missing
    v = value.summarize(daily, fees)
    key = "l1_fees" if column == "fees_usd" else column
    assert v["days_without_data"][key] == 1
    assert sum(v["days_without_data"].values()) == 1
    assert v["captured_share_of_gross_fees"] == pytest.approx(v["captured_revenue_usd"] / v["intents_gross_fees_usd"])
    assert v["intents_fees_vs_l1_fees"] == pytest.approx(v["intents_gross_fees_usd"] / v["l1_fees_usd"])
    expected = table[column].iloc[-90:].replace([np.inf, -np.inf], np.nan).dropna().sum() * 90 / 89
    total_key = {"fees": "intents_gross_fees_usd", "revenue": "captured_revenue_usd",
                 "holders_revenue": "buyback_usd", "fees_usd": "l1_fees_usd"}[column]
    assert v[total_key] == pytest.approx(expected)
    chart = charts._value_chart(daily, fees, v, tmp_path)
    lead = charts._takeaway("value_capture", {"value_capture": v})
    assert dashboard.split_sentence(lead)[0].startswith("Some fee totals and ratios are estimated;")
    page = dashboard.render([chart], {"first_date": str(daily.index.min().date()),
                                    "last_date": str(daily.index.max().date()), "days": len(daily)}, tmp_path).read_text()
    assert f"include estimates for {label} (1 missing day)" in page
    assert "ratios use those same totals" in page


def test_raw_missing_gross_fee_day_is_disclosed_by_full_build(tmp_path, monkeypatch):
    # Reproduce the audited case from raw JSON, leaving committed inputs untouched.
    raw = tmp_path / "raw"
    raw.mkdir()
    for name in value.URLS:
        data = json.loads((sources.RAW_DIR / f"{name}.json").read_text())
        if name == "defillama_intents_fees":
            omitted = int(pd.Timestamp("2026-09-21").timestamp())
            data["totalDataChart"] = [row for row in data["totalDataChart"] if row[0] != omitted]
        (raw / f"{name}.json").write_text(json.dumps(data))
    # Load the untouched daily sources before directing the fee loader to the fixture.
    daily = sources.load_daily(offline=True)
    monkeypatch.setattr(sources, "RAW_DIR", raw)
    fees = value.load()
    assert np.isnan(fees.loc["2026-09-21", "fees"])
    monkeypatch.setattr(sources, "load_daily", lambda offline=False: daily)
    monkeypatch.setattr(value, "load", lambda: fees)
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "DOCS", tmp_path / "docs")
    (tmp_path / "data").mkdir()
    cli.build(offline=True)
    summary = json.loads((tmp_path / "docs" / "summary.json").read_text())
    v = summary["value_capture"]
    assert v["days_without_buyback_data"] == 0
    assert v["days_without_data"]["fees"] == 1
    assert v["captured_share_of_gross_fees"] == pytest.approx(v["captured_revenue_usd"] / v["intents_gross_fees_usd"])
    assert "include estimates for Intents gross fees (1 missing day)" in (tmp_path / "docs" / "index.html").read_text()
    assert '<p class="lead">Some fee totals and ratios are estimated;' in (tmp_path / "docs" / "index.html").read_text()
