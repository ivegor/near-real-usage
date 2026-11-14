"""Full-population census: metrics on a small hand-made table (no BigQuery)."""
import pandas as pd
import pytest

from thesis import charts, population

from . import snapshot


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
    # the committed table read as it was when the scan stopped on 2026-11-11: October is its last complete month
    cut = df[df["month"] <= "2026-11"]
    assert population.complete_months(cut, "2026-11-11")[-1] == "2026-10"
    s = population.summarize(cut, "2026-11-11")
    assert s["latest_month"] == "2026-10" and s["partial_month"]["month"] == "2026-11"
    # and the day the build takes as the end of the scan lies in a month the table holds
    assert population.QUERY_END[:7] in set(df["month"]) and population.QUERY_END >= snapshot.SCAN_END


def test_the_days_of_an_unfinished_month_give_a_rate_not_a_month(tmp_path):
    """Transactions add up day by day: the days the scan covers are published as a rate per day, next to whole months."""
    s = population.summarize(table(), "2026-03-11")          # every month: 825 self-paid core transactions
    pace = s["partial_month"]["core_direct_txs"]
    assert (pace["days"], pace["transactions"]) == (11, 825) and pace["per_day"] == 825 / 11
    assert pace["whole_month_at_that_rate"] == pytest.approx(825 / 11 * 31)
    assert pace["latest_complete_month"] == {"month": "2026-02", "per_day": 825 / 28, "pct_change": pytest.approx((28 / 11 - 1) * 100)}
    assert pace["same_month_a_year_earlier"]["month"] == "2025-03" and pace["same_month_a_year_earlier"]["per_day"] == 825 / 31
    assert list(pace["per_day_by_month"])[-1] == "2026-02" and "2026-03" not in pace["per_day_by_month"]
    # a scan that reaches the end of the month leaves no unfinished month to speak of
    assert "partial_month" not in population.summarize(table(), "2026-03-31")
    # the chart's caption says it in words: the rate of the days in hand against the last whole month and a year before
    c = charts._population_chart(table(), {"last_date": "2026-03-11", "population": s}, tmp_path)
    assert "In the first 11 days of 2026-03 those self-paid transactions ran at" in c.sentence
    assert "a day in 2026-02 (+155%)" in c.sentence and "in 2025-03 (+182%)" in c.sentence


def test_unpack_refuses_a_result_that_drops_months(tmp_path):
    """A query is run again with only its last date moved; a result that starts later must not replace the table."""
    out = tmp_path / "out.csv"
    full = tmp_path / "full.csv"
    full.write_text("m,cells\n2026-09-01,near|ge2y|r|10|900|5|1\n2026-10-01,tg|lt1y|n|3|4|2|2\n")
    population.unpack(full, out)
    later = tmp_path / "later.csv"
    later.write_text("m,cells\n2026-10-01,tg|lt1y|n|3|4|2|2\n2026-11-01,tg|lt1y|n|5|6|2|2\n")
    with pytest.raises(SystemExit, match="holds 2026-09 .. 2026-09"):
        population.unpack(later, out)
    assert set(population.load(out)["month"]) == {"2026-09", "2026-10"}          # the table is left as it was
    longer = tmp_path / "longer.csv"
    longer.write_text(full.read_text() + "2026-11-01,tg|lt1y|n|5|6|2|2\n")
    assert set(population.unpack(longer, out)["month"]) == {"2026-09", "2026-10", "2026-11"}


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
    real = population.summarize(snapshot.census(), snapshot.SCAN_END)["core_direct_txs_from_dormant_implicit"]
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
    real = population.summarize(snapshot.census(), snapshot.SCAN_END)["implicit_one_transaction_bursts"]
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
    # the months counted are those of every series: the table starts a month earlier, and that month has no month before it
    s = population.summarize(df, "2026-03-31")
    assert (s["table_first_month"], s["first_month"], q["first_month"], q["last_month"]) == ("2025-01", "2025-02", "2025-02", "2026-03")
    real = population.summarize(snapshot.census(), snapshot.SCAN_END)["kaiching_relayed_txs_per_day"]
    assert real["median_month_to_the_nearest_thousand"] == 2_000_000 and len(real["months_within_a_thousandth_of_it"]) >= 8
    assert (real["first_month"], real["last_month"], real["months_with_relayed_transactions"]) == ("2024-12", "2026-04", 17)


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


def test_largest_daily_fall_is_found_by_rule_and_set_next_to_kaiching():
    df = table()  # KaiChing sends 1,500 transactions a month through 2025-12 and nothing from 2026-01
    idx = pd.date_range("2025-01-01", "2026-03-31", freq="D")
    txns = pd.Series(1000.0, index=idx)
    txns[idx >= "2026-01-02"] = 250.0      # one step of -75%
    txns["2025-06-10"] = 600.0             # a one-day dip of -40% and back
    daily = pd.DataFrame({"txns": txns, "active_accounts": 100.0}, index=idx)
    s = population.largest_daily_fall(df, daily)
    assert (s["date"], s["day_before"]) == ("2026-01-02", "2026-01-01")
    assert s["txns"] == {"before": 1000, "after": 250} and s["pct_change"] == -75.0
    assert s["active_accounts"]["pct_change"] == 0.0
    k = s["kaiching"]
    assert (k["month_before"]["month"], k["month_before"]["txs"]) == ("2025-12", 1500)
    assert k["month_of"]["txs"] == 0 and k["month_before"]["txs_per_day"] == 1500 / 31
    # the level on either side: the median day of the month before and after, and the app's part of the difference
    level = s["median_day"]
    assert (level["month_before"], level["month_after"], level["fall"]) == (1000.0, 250.0, 750.0)
    assert level["kaiching_share_of_it"] == pytest.approx(1500 / 31 / 750)
    # the one day: the app sent nothing in the month the day before the fall lies in, so none of that day's fall is its own
    assert (s["fall_txs"], s["kaiching_share_of_the_fall_at_most"], s["other_accounts_in_the_fall_at_least"]) == (750, 0.0, 750)


def test_new_accounts_are_set_next_to_the_fall():
    """The aggregator's new accounts on the two days and in the two months, next to the app's accounts seen for the first time."""
    df = table()
    created = pd.DataFrame([("2025-12", "kaiching", "m0", "not_returning", 700, 700, 700, 700)], columns=df.columns)
    df = pd.concat([df, created])
    idx = pd.date_range("2025-01-01", "2026-03-31", freq="D")
    txns, new = pd.Series(1000.0, index=idx), pd.Series(80.0, index=idx)
    txns[idx >= "2026-01-02"], new[idx >= "2026-01-02"] = 250.0, 10.0         # both step down on 2 January
    s = population.largest_daily_fall(df, pd.DataFrame({"txns": txns, "new_accounts": new}, index=idx))
    assert s["date"] == "2026-01-02" and s["new_accounts"]["before"] == 80 and s["new_accounts"]["after"] == 10
    assert s["new_accounts"]["per_day_month_before"] == 80.0 and s["new_accounts"]["per_day_month_of"] == pytest.approx((80 + 30 * 10) / 31)
    k = s["kaiching"]
    assert (k["month_before"]["first_seen_accounts"], k["month_of"]["first_seen_accounts"]) == (700, 0)
    assert "new_accounts" not in population.largest_daily_fall(df, pd.DataFrame({"txns": txns}, index=idx))
    # the committed data: the aggregator's new accounts step down on the day of the fall, and so do KaiChing's in the census
    from thesis import sources
    real = population.largest_daily_fall(snapshot.census(), sources.load_daily(offline=True))
    n, kc = real["new_accounts"], real["kaiching"]
    assert n["after"] < 0.25 * n["before"] and n["per_day_month_of"] < 0.2 * n["per_day_month_before"]
    assert kc["month_of"]["first_seen_accounts"] < 0.05 * kc["month_before"]["first_seen_accounts"]


def test_deleted_accounts_are_set_next_to_the_bursts_by_rule():
    """The aggregator's deletions in the months the census flags: a burst is ten times the median month, its days a tenth of its peak."""
    df = table()                                                           # 2025-01 .. 2026-03; complete months 2025-02 .. 2026-02
    extra = pd.DataFrame([("2025-11", "implicit", "ge2y", "not_returning", 500, 500, 0, 500),     # a burst of one-transaction accounts
                          ("2026-02", "kaiching", "lt1y", "not_returning", 300, 300, 0, 300)],   # the app's one-off in the latest month
                         columns=df.columns)
    ps = population.summarize(pd.concat([df, extra]), "2026-03-11")
    assert [b["month"] for b in ps["implicit_one_transaction_bursts"]["bursts"]] == ["2025-11"] and ps["latest_month"] == "2026-02"
    idx = pd.date_range("2025-01-01", "2026-03-20", freq="D")
    gone = pd.Series(2.0, index=idx)                                        # two deletions on an ordinary day
    gone["2025-11-05":"2025-11-09"] = 1000.0                                # the burst: five days at a thousand
    gone["2025-11-10"] = 50.0                                               # above an ordinary day, below a tenth of the peak
    gone["2026-02-10":"2026-02-11"] = 150.0                                 # the app's month: more than usual, not ten times the median
    d = population.deletions(ps, pd.DataFrame({"deleted_accounts": gone}, index=idx))
    assert len(d["monthly"]) == 13 and d["median_month"] == 62 and d["months_above_ten_times_the_median"] == ["2025-11"]
    nov, feb = d["months"]["2025-11"], d["months"]["2026-02"]
    assert nov["census_one_transaction_accounts"] == {"implicit_one_transaction_burst": 540}
    assert nov["deleted_accounts"] == 5000 + 50 + 24 * 2 and nov["per_day_month_before"] == 2.0
    assert nov["burst_days"] == {"first": "2025-11-05", "last": "2025-11-09", "days": 5, "deleted_accounts": 5000,
                                 "largest_day": {"date": "2025-11-05", "deleted_accounts": 1000}}
    assert feb["census_one_transaction_accounts"] == {"kaiching_one_off": 300} and feb["deleted_accounts"] == 26 * 2 + 300
    assert feb["burst_days"] is None and feb["times_the_median_month"] == pytest.approx(352 / 62)
    # a month without all of its days is not counted, and a series without deletions gives nothing
    short = population.deletions(ps, pd.DataFrame({"deleted_accounts": gone.drop(pd.Timestamp("2025-06-15"))}))
    assert "2025-06" not in short["monthly"] and len(short["monthly"]) == 12
    assert population.deletions(ps, pd.DataFrame({"txns": gone})) is None
    # the committed data: February's burst and October's one-off are deletions on a few days, March and April are not
    from thesis import sources
    real = population.deletions(population.summarize(snapshot.census(), snapshot.SCAN_END), sources.load_daily(offline=True))
    days = {m: (r["burst_days"] or {}) for m, r in real["months"].items()}
    # (and every other month of mass deletions, which the census's burst rule does not ask about)
    assert list(real["months"]) == ["2024-12", "2025-01", "2025-03", "2025-04", "2025-05", "2025-12", "2026-02", "2026-03", "2026-04", "2026-10"]
    assert real["months_above_ten_times_the_median"] == [m for m in real["months"] if m not in ("2026-03", "2026-04")]
    assert (days["2025-12"]["first"], days["2025-12"]["last"]) == ("2025-12-17", "2025-12-22")
    # each deleted account signed its own deletion: the day's signers rise by about one for each, on the days of a burst
    for m in ("2026-02", "2026-10", "2025-12"):
        assert 0.9 < days[m]["signers_per_deleted_account"] < 1.05 and days[m]["correlation_of_signers_with_deletions"] > 0.99, m
    assert (days["2026-02"]["first"], days["2026-02"]["last"], days["2026-10"]["first"], days["2026-10"]["last"]) == (
        "2026-02-03", "2026-02-18", "2026-10-02", "2026-10-08")
    assert days["2026-03"] == {} and days["2026-04"] == {}


def test_the_app_is_at_most_what_it_sent_in_the_month_of_the_fall():
    """A monthly census cannot date a transaction, but it bounds the app's part of one day's fall: all it sent that month."""
    df = table()
    late = (df["family"] == "kaiching") & (df["month"] == "2026-01")
    df.loc[late, ["accounts", "txs"]] = [300, 300]                       # its last month: 300 transactions, then nothing
    idx = pd.date_range("2025-01-01", "2026-03-31", freq="D")
    txns = pd.Series(1000.0, index=idx)
    txns[idx >= "2026-01-11"] = 200.0                                    # the chain loses 800 transactions a day on 11 January
    s = population.largest_daily_fall(df, pd.DataFrame({"txns": txns}, index=idx))
    assert (s["date"], s["fall_txs"]) == ("2026-01-11", 800)
    assert s["kaiching_share_of_the_fall_at_most"] == 300 / 800 and s["other_accounts_in_the_fall_at_least"] == 500
    # and the committed data: KaiChing's whole April is about half of what the chain lost between 1 and 2 April 2026
    from thesis import sources
    real = population.largest_daily_fall(snapshot.census(), sources.load_daily(offline=True))
    assert real["date"] == "2026-04-02" and 0.45 < real["kaiching_share_of_the_fall_at_most"] < 0.55
    assert 0.85 < real["median_day"]["kaiching_share_of_it"] < 0.95       # while the level on either side is its own
    # The least it can be is conditional: if the relayer sent all of April's relayed transactions on 1 April, the rest of
    # April's transactions may still have come on 2 April. It is not a bound and is not named as one.
    of = real["kaiching"]["month_of"]
    assert "kaiching_share_of_the_fall_at_least" not in real
    assert real["kaiching_share_of_the_fall_at_least_if_relayer_ended_the_day_before"] == pytest.approx(
        (of["relayed_txs"] - (of["txs"] - of["relayed_txs"])) / real["fall_txs"])


def test_the_unfinished_month_is_given_for_every_part_of_the_chain(tmp_path):
    """The days in hand as rates per day for each namespace: quoted where a reward app speeds up, not only where the core slows down."""
    df = table()
    hot = pd.DataFrame([("2026-02", "tg", "ge2y", "returning", 50, 280_000, 140_000, 0),
                        ("2026-03", "tg", "ge2y", "returning", 90, 330_000, 220_000, 0)], columns=df.columns)
    s = population.summarize(pd.concat([df, hot]), "2026-03-11")          # every month: 1,000 core transactions, 175 of them relayed
    r = s["partial_month"]["txs_per_day"]
    assert (r["days"], r["month"], r["latest_complete_month"]) == (11, "2026-03", "2026-02")
    assert r["tg"]["partial"] == 30_000 and r["tg"]["latest_complete"] == 10_000 and r["tg"]["pct_change"] == pytest.approx(200)
    assert r["tg"]["relayed"] == {"partial": 20_000.0, "latest_complete": 5_000.0}
    assert r["core"]["partial"] == pytest.approx(1000 / 11) and r["core"]["latest_complete"] == pytest.approx(1000 / 28)
    assert r["all"]["partial"] == pytest.approx(331_000 / 11) and r["kaiching"]["partial"] == 0
    share = r["reward_namespaces_share_of_txs"]
    assert share["partial"] == pytest.approx(330 / 331) and share["latest_complete"] == pytest.approx(280 / 281)
    # the caption names the namespace next to the self-paid rate of the same days
    c = charts._population_chart(pd.concat([df, hot]), {"last_date": "2026-03-11", "population": s}, tmp_path)
    assert "HOT's namespace (.tg) sent 30K transactions a day against 10K in 2026-02 (+200%)" in c.sentence
    assert "the reward apps' namespaces 100% of all transactions against 100%" in c.sentence
    # without the namespace in the table the caption says nothing about it, and a scan that reached the month's end leaves no rates
    plain = population.summarize(df, "2026-03-11")
    assert plain["partial_month"]["txs_per_day"]["tg"]["partial"] == 0
    assert "HOT's namespace" not in charts._population_chart(df, {"last_date": "2026-03-11", "population": plain}, tmp_path).sentence
    assert "partial_month" not in population.summarize(df, "2026-03-31")
