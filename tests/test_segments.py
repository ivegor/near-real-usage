"""Who pays and how often: the segment table on a tiny hand-made result."""
import pandas as pd

from thesis import charts, clients, population, segments


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
    # more players than regular accounts: the bound is the whole class
    segments.add_reward_game_bound(sg, {"direct": {"prior": {"transactions": 9000, "accounts": 500}}})
    assert sg["regular_accounts_reward_game_bound"]["share_of_prior_regular_at_most"] == 1
    # nobody called the game directly a year ago: nothing to bound
    plain = segments.summarize(df)
    segments.add_reward_game_bound(plain, {"direct": {"latest": None, "prior": None}})
    assert "regular_accounts_reward_game_bound" not in plain


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
    real = segments.summarize(segments.load())["regular_accounts_largest_monthly_fall"]
    assert real["month"] == "2026-02" and 0.4 < real["share_of_fall_from_prior_month_to_low"] < 0.5


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
    left = a.groupby("month")[["accounts", "txs"]].sum()
    right = b.groupby("month")[["accounts", "txs"]].sum().reindex(left.index)
    assert (left == right).all().all()


def test_namespace_view_adds_the_transactions_the_app_table_misses():
    cl = {"latest_month": "m", "months": {"m": {"transactions": 1000}}, "apps": {"KaiChing (reward app)": {"latest": 10}},
          "reward_apps_share": {"latest": 0.40}}
    clients.add_namespace_view(cl, 60)
    assert cl["kaiching_txs_outside_its_contracts"] == 50 and abs(cl["reward_apps_share_incl_kaiching_namespace"] - 0.45) < 1e-9
