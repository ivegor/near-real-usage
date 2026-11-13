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
