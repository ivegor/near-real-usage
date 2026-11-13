"""Who pays: the grouping on a tiny hand-made result, and agreement of the committed result with the other counts."""
import pandas as pd

from thesis import clients, payers, population


def write(tmp_path):
    p = tmp_path / "payers.csv"
    rows = ["m,sec,cells"]
    for year, sweat, ember, solo in (("2025", 700, 200, 50), ("2026", 300, 0, 60)):
        for month in ("08", "09", "10"):
            rows.append(f"{year}-{month},payer,implicit|sweat|r|{sweat}|{sweat * 2}|0;implicit|ember|r|{ember}|{ember}|0;"
                        f"near|self|r|{solo}|{solo * 100}|{solo * 90};near|self|n|10|10|10;tg|self|r|500|900|800;"
                        f"kaiching|kaiching|n|9000|9000|0")
            rows.append(f"{year}-{month},relayers,sweat-relayer.near|{sweat}|{sweat * 2}")
    p.write_text("\n".join(rows) + "\n")
    return p


def test_groups_and_attribution(tmp_path):
    s = payers.summarize(payers.load(write(tmp_path)))
    m = s["month"]
    assert (s["latest_month"], s["prior_month"]) == ("2026-10", "2025-10")
    assert m["sponsored_by_sweat"] == {"latest": 300.0, "prior": 700.0, "pct_change": (300 / 700 - 1) * 100}
    assert m["independent_accounts"]["latest"] == 70 and m["independent_regular_accounts"]["latest"] == 60   # .tg payers are HOT's
    assert m["old_core_accounts"]["prior"] == 700 + 200 + 60 and m["old_core_accounts"]["latest"] == 300 + 70
    # the fall of 590 accounts outside the namespaces: 400 Sweat, 200 Ember, and independents grew by 10
    assert abs(s["old_core_fall_explained_by"]["sweat"] - 400 / 590) < 1e-9
    assert abs(s["old_core_fall_explained_by"]["ember"] - 200 / 590) < 1e-9
    assert s["reward_apps_share_of_lost_accounts"] > 1


def test_three_independent_queries_count_the_same_chain():
    """account_age.sql, top_accounts.sql and payers.sql were run separately; their monthly totals must agree."""
    pay = payers.groups(payers.load())
    census = population.load().groupby("month")["accounts"].sum()
    top = clients.load()
    for month in ("2025-10", "2026-10"):
        assert pay.loc[month, "all_accounts"] == census[month] == top[month]["conc"]["actors"]
    for month in ("2025-08", "2025-09", "2026-08", "2026-09"):
        assert pay.loc[month, "all_accounts"] == census[month]
