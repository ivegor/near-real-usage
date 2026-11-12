"""Full-population census: metrics on a small hand-made table (no BigQuery)."""
import pandas as pd

from thesis import charts, population


def table():
    rows = []
    for i, month in enumerate(pd.period_range("2025-01", "2026-03", freq="M").astype(str)):
        late = month >= "2026-01"
        rows += [
            (month, "kaiching", "lt1y", "returning", 0 if late else 1000, 0 if late else 1500, 0, 0),
            (month, "near", "ge2y", "returning", 30, 900, 100, 1),
            (month, "near", "m0", "not_returning", 10, 20, 5, 8),
            (month, "implicit", "lt2y", "not_returning", 60 - 2 * i, 80, 70, 40),
        ]
    return pd.DataFrame(rows, columns=["month", "family", "age", "prev_month", "accounts", "txs", "relayed_txs", "single_tx_accounts"])


def test_complete_months_drop_first_and_partial_last():
    df = table()
    assert population.complete_months(df, "2026-03-11") == sorted(df.month.unique())[1:-1]
    assert population.complete_months(df, "2026-03-31")[-1] == "2026-03"


def test_summary_separates_reward_apps_from_core():
    s = population.summarize(table(), "2026-03-11")
    assert (s["latest_month"], s["prior_month"]) == ("2026-02", "2025-02")
    seg = s["segments"]
    assert seg["kaiching"]["accounts"] == {"latest": 0.0, "prior": 1000.0, "pct_change": -100.0}
    assert seg["core"]["accounts"]["prior"] == 30 + 10 + 58 and seg["core"]["accounts"]["latest"] == 30 + 10 + 34
    assert seg["core"]["returning_accounts"]["latest"] == 30
    assert abs(seg["core"]["old_tx_share"]["latest"] - 980 / 1000) < 1e-9
    assert seg["near"]["txs"]["pct_change"] == 0


def test_population_chart_renders(tmp_path, monkeypatch):
    df = table()
    summary = {"last_date": "2026-03-11", "population": population.summarize(df, "2026-03-11")}
    c = charts._population_chart(df, summary, tmp_path)
    assert (tmp_path / "population.png").stat().st_size > 5_000
    assert "nan" not in c.sentence.lower() and "2026-02" in c.sentence


def test_unpack_reads_the_bigquery_result_format(tmp_path):
    src = tmp_path / "result.csv"
    src.write_text("m,cells\n2026-09-01,near|ge2y|r|10|900|5|1;kaiching|m0|n|7|7|7|7\n2026-10-01,tg|lt1y|n|3|4|2|2\n")
    df = population.unpack(src, tmp_path / "out.csv")
    assert df.to_dict("records")[0] == {"month": "2026-09", "family": "near", "age": "ge2y", "prev_month": "returning",
                                        "accounts": 10, "txs": 900, "relayed_txs": 5, "single_tx_accounts": 1}
    assert len(df) == 3 and (tmp_path / "out.csv").exists()


def test_one_day_matches_the_aggregator_transaction_count():
    import pandas as pd
    daily = pd.DataFrame({"txns": [4632736], "active_accounts": [288151], "new_accounts": [267015]}, index=[pd.Timestamp("2025-10-01")])
    d = population.one_day(daily)
    assert d["transactions"] == d["nearblocks"]["txns"]          # two independent sources agree exactly
    assert d["relayed_users"] > 9 * d["nearblocks"]["active_accounts"]   # relayed users are not in "active accounts"
    assert d["account_creators"] == 12


def test_last_month_depends_on_the_query_not_on_todays_date():
    """A dashboard rebuilt in December must not treat the half-scanned November as a full month."""
    df = population.load()
    assert df is not None
    assert population.complete_months(df)[-1] == "2026-10"
    s = population.summarize(df)
    assert s["latest_month"] == "2026-10" and s["partial_month"]["month"] == "2026-11"


def test_summary_reports_robust_and_decomposed_figures():
    s = population.summarize(table(), "2026-03-11")
    core = s["segments"]["core"]
    assert core["direct_txs"]["latest"] == core["txs"]["latest"] - core["relayed_txs"]["latest"]
    assert core["multi_tx_accounts"]["latest"] == core["accounts"]["latest"] - (1 + 8 + 40)
    # the mix of account types is held at last year's shares: 30+10 named accounts out of 98, the rest implicit
    near_rate, implicit_rate = (900 + 20) / 40, 80 / 34
    assert abs(s["core_txs_per_account_at_prior_mix"] - (near_rate * 40 / 98 + implicit_rate * 58 / 98)) < 1e-9
    assert s["segments"]["near"]["accounts_range_12m"] == {"min": 40.0, "max": 40.0}


def test_cross_check_compares_the_same_months():
    df = table()
    sample = {"windows": {"recent": {"start": "2025-12-14", "end": "2026-03-11", "transactions": 100, "relayed_tx_share": 0.2,
                                     "tx_share_by_account_age": {"365d+": 0.9}, "tx_share_ci95": {"365d+": [0.8, 0.95]},
                                     "top10_accounts_tx_share": 0.5}}}
    top = {"months": {"2026-02": {"top10_share": 0.4}}}
    c = population.cross_check(sample, df, top)["recent"]
    assert c["bigquery_months"] == ["2026-01", "2026-02"]          # only the calendar months fully inside the window
    assert abs(c["older_than_1y_tx_share"]["bigquery"] - 980 / 1000) < 1e-9
    assert abs(c["relayed_tx_share"]["bigquery"] - 175 / 1000) < 1e-9
    assert c["top10_tx_share"] == {"sample": 0.5, "bigquery_month": "2026-02", "bigquery": 0.4}
