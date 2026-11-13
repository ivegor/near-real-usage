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
    assert (d["create_account_transactions"], d["accounts_created"]) == (238403, 238399)   # four transactions repeat an account


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


def test_a_burst_of_dormant_accounts_is_split_out_of_the_self_paid_series():
    """Old implicit accounts that wake up for one month are published separately, with the windows recomputed without them."""
    df = table()
    burst = pd.DataFrame([("2026-02", "implicit", "ge2y", "not_returning", 500, 500, 0, 500)], columns=df.columns)
    s = population.summarize(pd.concat([df, burst]), "2026-03-11")
    d = s["core_direct_txs_from_dormant_implicit"]
    # every month the table's old implicit accounts pay for 80 - 70 = 10 transactions out of 825 self-paid core ones
    assert d["peak"] == {"month": "2026-02", "txs": 510, "share_of_month": 510 / 1325, "month_before_txs": 10}
    assert abs(d["largest_share_in_any_other_month"] - 10 / 825) < 1e-12
    assert d["monthly"]["2026-01"] == 10 and d["monthly"]["2026-02"] == 510
    assert s["core_direct_txs_change_by_window"]["1"] > 60 and d["change_by_window_without_them"] == {"1": 0.0}
    # and the committed census: February 2026 is the only month where they are more than a few percent
    real = population.summarize(population.load())["core_direct_txs_from_dormant_implicit"]
    assert real["peak"]["month"] == "2026-02" and real["peak"]["share_of_month"] > 0.3 > 0.05 > real["largest_share_in_any_other_month"]


def test_one_transaction_bursts_are_the_months_ten_times_the_median():
    """Existing accounts that wake up for a single transaction: an ordinary month has few, a burst has ten times as many."""
    df = table()                                              # every month: 40 implicit accounts with one transaction
    burst = pd.DataFrame([("2026-02", "implicit", "ge2y", "not_returning", 500, 500, 0, 500)], columns=df.columns)
    s = population.summarize(pd.concat([df, burst]), "2026-03-11")["implicit_one_transaction_bursts"]
    assert s["median_month"] == 40 and s["monthly"]["2026-01"] == 40 and [b["month"] for b in s["bursts"]] == ["2026-02"]
    b = s["bursts"][0]
    assert b["accounts"] == 540 and abs(b["times_the_median_month"] - 13.5) < 1e-12
    assert abs(b["older_than_2y_share"] - 500 / 540) < 1e-12 and abs(b["relayed_tx_share"] - 70 / 580) < 1e-12
    assert population.summarize(df, "2026-03-11")["implicit_one_transaction_bursts"]["bursts"] == []
    # the committed census: three months in a row, and no other month comes near
    real = population.summarize(population.load())["implicit_one_transaction_bursts"]
    assert [b["month"] for b in real["bursts"]] == ["2026-02", "2026-03", "2026-04"]
    rest = [v for m, v in real["monthly"].items() if m not in ("2026-02", "2026-03", "2026-04")]
    assert max(rest) < 5 * real["median_month"]


def test_a_relayer_with_a_daily_quota_is_visible_in_the_monthly_totals():
    """The same number of relayed transactions every day of every month: the median month gives the level, no number is typed."""
    rows = []
    for month in pd.period_range("2025-01", "2026-03", freq="M"):
        relayed = 5_000 * month.days_in_month if str(month) != "2025-07" else 4_000 * month.days_in_month      # one slower month
        rows.append((str(month), "kaiching", "lt1y", "returning", 100, relayed + 50, relayed, 0))
        rows.append((str(month), "near", "ge2y", "returning", 30, 900, 100, 1))
    df = pd.DataFrame(rows, columns=["month", "family", "age", "prev_month", "accounts", "txs", "relayed_txs", "single_tx_accounts"])
    q = population.summarize(df, "2026-03-31")["kaiching_relayed_txs_per_day"]
    assert q["median_month_to_the_nearest_thousand"] == 5_000 and q["months_with_relayed_transactions"] == 14
    assert "2025-07" not in q["months_within_a_thousandth_of_it"] and len(q["months_within_a_thousandth_of_it"]) == 13
    assert q["in_the_month"]["2025-02"] == 5_000 * 28 and abs(q["per_day"]["2025-07"] - 4_000) < 1e-9
    assert "kaiching_relayed_txs_per_day" not in population.summarize(table(), "2026-03-11")      # no relayed transactions: nothing to say
    real = population.summarize(population.load())["kaiching_relayed_txs_per_day"]
    assert real["median_month_to_the_nearest_thousand"] == 2_000_000 and len(real["months_within_a_thousandth_of_it"]) >= 8


def test_totals_check_separates_the_months_that_agree_from_those_that_do_not():
    """BigQuery against the aggregator, month by month: a few transactions apart is agreement, hundreds are not."""
    df = table()                                              # 15 months, 2025-01 .. 2026-03
    per_month = df.groupby("month")["txs"].sum()
    daily = pd.DataFrame({"txns": 0.0}, index=pd.date_range("2025-01-01", "2026-03-20", freq="D"))
    for month, total in per_month.items():
        daily.loc[f"{month}-01", "txns"] = total              # the aggregator's month, all on its first day
    daily.loc["2025-05-01", "txns"] += 3                      # three transactions apart
    daily.loc["2025-09-01", "txns"] += 400                    # BigQuery is short by 400
    daily.loc["2026-03-15", "txns"] = 777                     # after the query stopped: not compared
    c = population.totals_check(df, daily, "2026-03-11")
    assert (c["months"], c["first_month"], c["last_month"], c["last_month_through"]) == (15, "2025-01", "2026-03", "2026-03-11")
    assert c["agree"] == {"months": 14, "largest_difference_txs": 3, "largest_difference_share": 3 / (per_month["2025-05"] + 3)}
    assert c["differ"] == {"2025-09": {"bigquery_minus_nearblocks": -400, "share": -400 / (per_month["2025-09"] + 400)}}
    assert c["difference_by_month"]["2025-05"] == -3 and c["difference_by_month"]["2026-03"] == 0
    assert c["jump_between_the_groups"] > 100                 # the two groups are far apart, so the line is not a choice
    assert population.totals_check(df, daily.loc[:"2025-01-31"], "2026-03-11") is None      # one month is nothing to compare


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
