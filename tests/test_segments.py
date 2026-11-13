"""Who pays and how often: the segment table on a tiny hand-made result."""
import pandas as pd

from thesis import charts, clients, population, segments

from . import snapshot


def table():
    rows = []
    for i, month in enumerate(pd.period_range("2025-08", "2026-10", freq="M").astype(str)):
        rows += [
            (month, "kaiching", "sponsored", "1", 0 if month > "2026-03" else 1000, 0 if month > "2026-03" else 1000, 0),
            (month, "rest", "sponsored", "2-9", 300 - 10 * i, 900, 0),
            (month, "tg", "self", "10-99", 50, 700, 650),
            (month, "rest", "self", "1", 40 + (500 if month == "2026-02" else 0), 40, 40),
            (month, "rest", "self", "10-99", 100 - 4 * i, 3000, 2800),
            (month, "rest", "self", "100-999", 10, 2000, 2000),
            (month, "rest", "self", "10,000+", 2, 50000 + 1000 * i, 50000 + 1000 * i),
        ]
    return pd.DataFrame(rows, columns=["month", "namespace", "payer", "txs_in_month", "accounts", "txs", "self_paid_txs"])


def test_segments_follow_the_three_questions():
    s = segments.series(table())
    assert s.loc["2025-10", "sponsored_accounts"] == 1000 + 280 and s.loc["2026-10", "sponsored_accounts"] == 160
    assert s.loc["2025-10", "regular_accounts"] == (100 - 8) + 10 and s.loc["2025-10", "heavy_accounts"] == 2
    assert s.loc["2025-10", "app_namespace_self_paying_accounts"] == 50          # HOT users are not "independent"
    assert s.loc["2025-10", "app_namespace_regular_self_paying_accounts"] == 50  # but their frequency class is published
    assert s.loc["2026-02", "occasional_accounts"] == 540                         # a one-off burst lands in "occasional"


def test_summary_and_chart(tmp_path):
    df = table()
    sg = segments.summarize(df)
    m = sg["metrics"]
    assert (sg["latest_month"], sg["prior_month"]) == ("2026-10", "2025-10")
    assert m["regular_accounts"]["latest"] == 54 and m["regular_accounts"]["prior"] == 102
    assert abs(m["regular_accounts"]["three_month_mean"]["latest"] - 58) < 1e-9
    assert sg["regular_accounts_low"] == {"month": "2026-10", "value": 54.0}
    assert 0.9 < sg["heavy_share_of_independent_self_paid_txs"]["latest"] < 1
    c = charts._segments_chart(df, sg, tmp_path)
    assert (tmp_path / "segments.png").stat().st_size > 5_000 and "nan" not in c.sentence.lower()


def test_reward_game_bound_gives_both_ends_of_the_range(tmp_path):
    """Players of a game who paid their own fees a year ago and are relayed now: at most that many of last year's regular accounts."""
    df = table()
    sg = segments.summarize(df)                    # regular accounts: 102 a year ago, 54 now
    segments.add_reward_game_bound(sg, {"direct": {"latest": None, "prior": {"transactions": 900, "accounts": 30}}})
    b = sg["regular_accounts_reward_game_bound"]
    assert b["game_players_prior"] == 30 and b["fall"] == 48 and abs(b["share_of_prior_regular_at_most"] - 30 / 102) < 1e-12
    assert abs(b["pct_change_as_counted"] - (54 / 102 - 1) * 100) < 1e-9
    assert abs(b["pct_change_if_all_of_them_were_regular"] - (54 / 72 - 1) * 100) < 1e-9
    c = charts._segments_chart(df, sg, tmp_path)   # the caption says the fall is not a clean count
    assert "up to 30 of last year's accounts" in c.sentence and "nan" not in c.sentence.lower()
    assert "With all of them taken out of last year's count the change would be -25%" in c.sentence
    assert "without_the_game" not in b             # nothing is known about this year's players without the relayer's accounts
    # more players than regular accounts: the bound is the whole class
    segments.add_reward_game_bound(sg, {"direct": {"prior": {"transactions": 9000, "accounts": 500}}})
    assert sg["regular_accounts_reward_game_bound"]["share_of_prior_regular_at_most"] == 1
    # nobody called the game directly a year ago: nothing to bound
    plain = segments.summarize(df)
    segments.add_reward_game_bound(plain, {"direct": {"latest": None, "prior": None}})
    assert "regular_accounts_reward_game_bound" not in plain


def test_the_players_are_taken_out_of_both_months_by_one_rule(tmp_path):
    """A player who pays for one transaction is inside a year's regular accounts, whichever year: relayed calls count towards the class."""
    df = table()
    sg = segments.summarize(df)                    # regular accounts: 102 a year ago, 54 now
    game = {"direct": {"latest": None, "prior": {"transactions": 900, "accounts": 30}},
            "relayed": {"latest": {"transactions": 500, "accounts": 40}, "prior": {"transactions": 100, "accounts": 10}},
            "smallest_of_the_40_latest": 77}
    # the relayer pays everything for 28 of its 40 accounts now, and for 4 of its 10 a year ago
    segments.add_reward_game_bound(sg, game, {"latest": 28.0, "prior": 4.0})
    w = sg["regular_accounts_reward_game_bound"]["without_the_game"]
    now, then = w["players"]["latest"], w["players"]["prior"]
    assert (now["relayer_accounts"], now["fully_sponsored"], now["paying_through_the_relayer"]) == (40, 28, 12)
    assert (then["relayer_accounts"], then["fully_sponsored"], then["paying_through_the_relayer"]) == (10, 4, 6)   # the same rule a year ago
    # a year ago the 30 direct callers and the 6 can be the same accounts or different ones: 30 or 36 players at most
    assert (then["direct_callers"], then["at_most_if_one_group_holds_the_other"], then["at_most_if_no_account_is_in_both"]) == (30, 30, 36)
    # the contract is not among this year's 40 largest: its callers are not counted, and the ceiling on its calls is named
    assert now["direct_callers"] is None and now["direct_txs_at_most"] == 77 and now["at_most_if_no_account_is_in_both"] == 12
    assert w["players_still_self_paying_latest_at_most"] == 12 and w["players_prior_at_most"] == {
        "if_one_group_holds_the_other": 30, "if_no_account_is_in_both": 36}
    assert abs(w["pct_change_low"] - ((54 - 12) / 102 - 1) * 100) < 1e-9          # none were players last year, all 12 are regular now
    high, most = w["pct_change_high"], w["pct_change_with_the_most_out_of_both_months"]
    assert abs(high["if_one_group_holds_the_other"] - (54 / 72 - 1) * 100) < 1e-9  # 30 of last year's were players, none of this year's
    assert abs(high["if_no_account_is_in_both"] - (54 / 66 - 1) * 100) < 1e-9      # 36 of them: the high end is not the one above
    assert abs(most["if_one_group_holds_the_other"] - (42 / 72 - 1) * 100) < 1e-9
    assert abs(most["if_no_account_is_in_both"] - (42 / 66 - 1) * 100) < 1e-9
    assert w["pct_change_low"] < sg["regular_accounts_reward_game_bound"]["pct_change_as_counted"] < high["if_one_group_holds_the_other"]
    assert high["if_one_group_holds_the_other"] < high["if_no_account_is_in_both"]
    c = charts._segments_chart(df, sg, tmp_path)   # the caption gives the range, and does not call one end of it the bound
    assert "can be a player too: up to 6 a year ago and 12 now" in c.sentence
    # the term counted in both years first, then what last year's direct callers add, and the low end left open
    both = w["relayer_term_only"]
    assert abs(both["pct_change_low"] - w["pct_change_low"]) < 1e-9 and abs(both["pct_change_high"] - (54 / 96 - 1) * 100) < 1e-9
    assert abs(both["pct_change_with_both_out"] - (42 / 96 - 1) * 100) < 1e-9
    assert "the change lies between -59% and -44%" in c.sentence and "the high end is -25% or more (-18% if none of last year's 6 called" in c.sentence
    assert "the low end, -59%, is open below" in c.sentence
    assert "nan" not in c.sentence.lower()
    # a relayer that pays everything for all of its accounts leaves no player in this year's count
    segments.add_reward_game_bound(sg, game, {"latest": 40.0, "prior": 4.0})
    assert sg["regular_accounts_reward_game_bound"]["without_the_game"]["players_still_self_paying_latest_at_most"] == 0
    # with last year's accounts of the relayer unknown, the rule cannot be applied to both years: no one-sided range
    segments.add_reward_game_bound(sg, game, {"latest": 28.0})
    assert "without_the_game" not in sg["regular_accounts_reward_game_bound"]
    segments.add_reward_game_bound(sg, {**game, "relayed": {"latest": game["relayed"]["latest"], "prior": None}}, {"latest": 28.0, "prior": 4.0})
    assert "without_the_game" not in sg["regular_accounts_reward_game_bound"]
    # more players than the class holds: the base a year ago would be empty, and the high end has no value
    segments.add_reward_game_bound(sg, {**game, "direct": {"latest": None, "prior": {"transactions": 900, "accounts": 100}}},
                                   {"latest": 28.0, "prior": 4.0})
    w = sg["regular_accounts_reward_game_bound"]["without_the_game"]
    assert w["players_prior_at_most"]["if_no_account_is_in_both"] == 102 and w["pct_change_high"]["if_no_account_is_in_both"] != w["pct_change_high"]["if_no_account_is_in_both"]
    # the committed tables: the name sql/payers.sql gives the relayer's accounts is one the build knows
    from thesis import payers
    assert clients.GAME_SPONSOR in payers.SPONSORS and clients.GAME_RELAYER.split(":", 1)[1].startswith(clients.GAME_SPONSOR)


def test_one_rule_counts_the_players_of_a_month():
    """Direct callers and accounts that pay for something besides relayed calls: their overlap is unknown, so both ends are given."""
    both = segments.players_counted_as_self_paying({"accounts": 5}, {"accounts": 20}, 12)
    assert both == {"direct_callers": 5, "relayer_accounts": 20, "fully_sponsored": 12, "paying_through_the_relayer": 8,
                    "at_most_if_one_group_holds_the_other": 8, "at_most_if_no_account_is_in_both": 13}
    # a relayer that pays for more accounts than act through it (another relayer was their main one) leaves none
    assert segments.players_counted_as_self_paying(None, {"accounts": 5}, 9)["paying_through_the_relayer"] == 0
    # nothing known about the relayer: the direct callers alone
    alone = segments.players_counted_as_self_paying({"accounts": 5}, None, None, direct_txs_at_most=50)
    assert alone == {"direct_callers": 5, "at_most_if_one_group_holds_the_other": 5, "at_most_if_no_account_is_in_both": 5}


def test_reward_game_bound_covers_the_transactions_too():
    """The game's direct calls were self-paid: they sit in last year's self-paid transactions and not in this year's."""
    sg = segments.summarize(table())
    segments.add_reward_game_bound(sg, {"direct": {"latest": None, "prior": {"transactions": 900, "accounts": 30}}})
    b, txs = sg["self_paid_txs_reward_game_bound"], sg["metrics"]["independent_self_paid_txs"]
    assert b["game_direct_txs_prior"] == 900 and abs(b["share_of_prior_self_paid_txs_at_most"] - 900 / txs["prior"]) < 1e-12
    assert abs(b["pct_change_as_counted"] - txs["pct_change"]) < 1e-12
    assert abs(b["pct_change_if_all_of_them_were_independent"] - (txs["latest"] / (txs["prior"] - 900) - 1) * 100) < 1e-9
    assert b["pct_change_if_all_of_them_were_independent"] > b["pct_change_as_counted"]


def test_the_largest_monthly_fall_of_regular_accounts_is_published():
    """A slide that loses a third of its accounts in one month is a step, and the text has to be able to say so."""
    df = table()
    late = (df["month"] >= "2026-02") & (df["namespace"] == "rest") & (df["payer"] == "self") & (df["txs_in_month"] == "10-99")
    df.loc[late, "accounts"] -= 30
    sg = segments.summarize(df)
    fall = sg["regular_accounts_largest_monthly_fall"]
    assert (fall["month"], fall["month_before"], fall["before"], fall["after"], fall["fall"]) == ("2026-02", "2026-01", 90, 56, 34)
    assert sg["regular_accounts_by_month"]["2026-01"] == 90 and len(sg["regular_accounts_by_month"]) == 15
    # from 102 a year before the latest month to the low of 24: this one month is 34 of those 78
    assert abs(fall["share_of_fall_from_prior_month_to_low"] - 34 / 78) < 1e-12
    real = segments.summarize(snapshot.frequency())["regular_accounts_largest_monthly_fall"]
    assert real["month"] == "2026-02" and 0.4 < real["share_of_fall_from_prior_month_to_low"] < 0.5


def test_self_paid_transactions_are_also_published_without_what_is_not_independent_use(tmp_path):
    """Reward-side direct calls sit in both months and a failing sender in the latest: the change without them, next to the counted one."""
    df = table()
    sg = segments.summarize(df)
    txs = sg["metrics"]["independent_self_paid_txs"]                     # 56,840 a year ago, 68,840 now
    cl = {"reward_side_direct_calls": {"prior": {"transactions": 6_840}, "latest": {"transactions": 3_840}},
          "failing_senders": {"transactions_latest_all": 5_000}}
    segments.add_self_paid_adjustments(sg, cl)
    a = sg["self_paid_txs_adjustments"]
    assert a["pct_change_as_counted"] == txs["pct_change"] and a["reward_side_direct_txs"] == {"latest": 3_840, "prior": 6_840}
    assert abs(a["pct_change_without_reward_side_direct_txs"] - (65_000 / 50_000 - 1) * 100) < 1e-9
    assert abs(a["pct_change_without_failing_senders"] - ((txs["latest"] - 5_000) / txs["prior"] - 1) * 100) < 1e-9
    assert abs(a["pct_change_without_both"] - (60_000 / 50_000 - 1) * 100) < 1e-9
    c = charts._segments_chart(df, sg, tmp_path)                         # and the caption says so
    assert "Without them the change is +20%" in c.sentence and "nan" not in c.sentence.lower()
    # no failing sender known: only the reward-side figure; no reward-side table: nothing at all
    plain = segments.summarize(df)
    segments.add_self_paid_adjustments(plain, {"reward_side_direct_calls": cl["reward_side_direct_calls"]})
    assert set(plain["self_paid_txs_adjustments"]) == {"pct_change_as_counted", "reward_side_direct_txs", "pct_change_without_reward_side_direct_txs"}
    none = segments.summarize(df)
    segments.add_self_paid_adjustments(none, {})
    assert "self_paid_txs_adjustments" not in none


def test_unpack_reads_what_the_query_returns(tmp_path):
    """sql/payer_frequency.sql returns one row per month: m, and cells of namespace|payer|frequency|accounts|txs|self-paid."""
    result = tmp_path / "result.csv"
    result.write_text('m,cells\n2026-09,"rest|self|n10_99|3|90|80;tg|sponsored|n1|7|7|0"\n2026-10,rest|self|n1k_9k|2|5000|4900\n')
    df = segments.unpack(result, tmp_path / "out.csv")
    assert list(df.columns) == segments.COLUMNS and len(df) == 3
    assert df.iloc[0].tolist() == ["2026-09", "rest", "self", "10-99", 3, 90, 80]
    assert df.iloc[2].tolist() == ["2026-10", "rest", "self", "1,000-9,999", 2, 5000, 4900]
    assert set(segments.FREQUENCY.values()) == set(segments.CLASS)          # every code maps to a class the build knows
    assert segments.load(tmp_path / "out.csv").equals(df)


def test_unpack_rebuilds_the_committed_table_byte_for_byte(tmp_path):
    """Pack the committed table the way the query prints it, unpack it, and get the same file back."""
    code = {label: c for c, label in segments.FREQUENCY.items()}
    df = segments.load()
    lines = ["m,cells"]
    for month, g in df.groupby("month", sort=False):
        lines.append(f"{month}," + ";".join(f"{r.namespace}|{r.payer}|{code[r.txs_in_month]}|{r.accounts}|{r.txs}|{r.self_paid_txs}"
                                            for r in g.itertuples()))
    result = tmp_path / "result.csv"
    result.write_text("\n".join(lines) + "\n")
    # the query orders the cells by namespace, payer and frequency code; the committed table keeps that order
    for line in lines[1:]:
        keys = [c.split("|")[:3] for c in line.split(",", 1)[1].split(";")]
        assert keys == sorted(keys)
    segments.unpack(result, tmp_path / "out.csv")
    assert (tmp_path / "out.csv").read_bytes() == segments.CSV.read_bytes()


def test_the_committed_table_agrees_with_the_account_census():
    """Two separate BigQuery runs must count the same accounts and transactions in every month they share."""
    a, b = segments.load(), population.load()
    # a month the census scan has not finished is not a month: one table may be run again before the other
    shared = [m for m in sorted(a["month"].unique()) if m in population.complete_months(b)]
    assert len(shared) >= 15
    left = a[a["month"].isin(shared)].groupby("month")[["accounts", "txs"]].sum()
    right = b.groupby("month")[["accounts", "txs"]].sum().reindex(left.index)
    assert (left == right).all().all()


def test_unpack_refuses_a_result_that_drops_months(tmp_path):
    out = tmp_path / "out.csv"
    first = tmp_path / "first.csv"
    first.write_text("m,cells\n2026-09,rest|self|n10_99|3|90|80\n2026-10,rest|self|n1k_9k|2|5000|4900\n")
    segments.unpack(first, out)
    later = tmp_path / "later.csv"
    later.write_text("m,cells\n2026-10,rest|self|n1k_9k|2|5000|4900\n2026-11,rest|self|n1|4|4|4\n")
    import pytest
    with pytest.raises(SystemExit, match="first date unchanged"):
        segments.unpack(later, out)
    assert list(segments.load(out)["month"]) == ["2026-09", "2026-10"]


def test_namespace_view_adds_the_transactions_the_app_table_misses():
    cl = {"latest_month": "m", "months": {"m": {"transactions": 1000}}, "apps": {"KaiChing (reward app)": {"latest": 10}},
          "reward_apps_share": {"latest": 0.40}}
    clients.add_namespace_view(cl, 60)
    assert cl["kaiching_txs_outside_its_contracts"] == 50 and abs(cl["reward_apps_share_incl_kaiching_namespace"] - 0.45) < 1e-9
