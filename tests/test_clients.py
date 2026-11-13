"""Top accounts and apps: parsing of the BigQuery result and the grouping, on a tiny hand-made result."""
import math

import pandas as pd

from thesis import charts, clients


def write(tmp_path):
    p = tmp_path / "result.csv"
    p.write_text(
        "m,sec,cells\n"
        "2025-10,actors,bot.near|300|v2.ref-finance.near;intents.near|100|intents.near\n"
        "2025-10,conc,1000|500|2|400|400|400|400|2|2\n"
        "2025-10,via,relayer:hotwallet.kaiching|500|450;v2.ref-finance.near|300|3;intents.near|100|9\n"
        "2026-10,actors,intents.near|240|intents.near;escrow.ai.near|50|intents.near;bot.near|200|v2.ref-finance.near\n"
        "2026-10,conc,800|60|3|490|490|490|490|2|3\n"
        "2026-10,via,intents.near|300|12;v2.ref-finance.near|200|4;relayer:sweat-relayer.near|200|30;mystery.near|40|1\n")
    return p


def test_apps_cover_every_transaction(tmp_path):
    data = clients.load(write(tmp_path))
    apps = clients.by_app(data["2026-10"])
    assert apps.sum() == 800
    assert apps["NEAR Intents"] == 300 and apps[clients.OTHER_TOP] == 40 and apps[clients.TAIL] == 60


def test_ember_and_the_exchange_contracts_are_published_separately(tmp_path):
    p = write(tmp_path)
    p.write_text(p.read_text(encoding="utf-8").replace("mystery.near|40|1", "mystery.near|40|1;embr.playember_reserve.near|16|2;dclv2.ref-labs.near|10|7"))
    s = clients.summarize(clients.load(p))
    assert (s["ember"]["latest"], s["ember"]["prior"]) == (16, 0) and abs(s["ember"]["latest_share"] - 0.02) < 1e-9
    assert abs(s["ember"]["reward_apps_share_with_ember"]["latest"] - 0.27) < 1e-9
    assert s["apps"][clients.OTHER_TOP]["latest"] == 56 and abs(s["reward_apps_share"]["latest"] - 0.25) < 1e-9   # the group itself is unchanged
    ex = {c["contract"]: c for c in s["exchange_contracts_latest"]}
    assert ex["v2.ref-finance.near"]["accounts"] == 4 and ex["dclv2.ref-labs.near"]["accounts"] == 7
    assert abs(ex["v2.ref-finance.near"]["share_of_app_txs"] - 200 / 210) < 1e-9


def test_group_shares_come_from_the_integer_counts(tmp_path):
    """A share is one division of two integers, so every Python version writes the same digits."""
    s = clients.summarize(clients.load(write(tmp_path)))
    assert s["reward_apps_share"] == {"latest": 200 / 800, "prior": 500 / 1000}
    assert s["finance_share"] == {"latest": 500 / 800, "prior": 400 / 1000}
    assert s["finance_txs"] == {"latest": 500, "prior": 400, "pct_change": 25.0}


def test_group_contracts_outside_a_months_40_bound_the_change(tmp_path):
    """A month counts a group's contracts only if they are among its 40 largest; the rest are bounded by the smallest entry."""
    s = clients.summarize(clients.load(write(tmp_path)))
    members = sum(len(clients.APPS[app]) for app in clients.FINANCE_APPS)
    out = s["groups_outside_the_40"]["finance"]      # both months list two finance contracts; their smallest entries are 40 and 100
    assert out["latest"] == {"contracts": members - 2, "transactions_each_at_most": 40, "transactions_at_most": (members - 2) * 40}
    assert out["prior"]["transactions_at_most"] == (members - 2) * 100
    lo, hi = s["finance_txs_change_range"]
    assert abs(lo - (500 / (400 + (members - 2) * 100) - 1) * 100) < 1e-9 and abs(hi - ((500 + (members - 2) * 40) / 400 - 1) * 100) < 1e-9
    assert lo < s["finance_txs"]["pct_change"] < hi
    gap = s["reward_minus_finance_share"]
    assert abs(gap["latest"] - (200 - 500) / 800) < 1e-12 and gap["latest_range"][0] < gap["latest"] < gap["latest_range"][1]
    # the committed result: neither the growth of the finance group nor the sign of the gap depends on what the 40 hide
    real = clients.summarize(clients.load())
    assert real["finance_txs_change_range"][0] > 0 and real["reward_minus_finance_share"]["latest_range"][0] > 0
    assert real["finance_txs"] == {k: real["finance_txs"][k] for k in ("latest", "prior", "pct_change")}   # the frozen figures keep their shape


def test_other_contracts_and_the_exchange_bot_targets_are_published(tmp_path):
    """The residual rows are listed contract by contract, and two contracts the exchange's own bots called are shown both ways."""
    p = write(tmp_path)
    text = p.read_text(encoding="utf-8").replace("intents.near|100|9\n", "intents.near|100|9;pyth-oracle.near|60|2;near|20|5\n")
    p.write_text(text.replace("mystery.near|40|1", "mystery.near|40|1;near|10|4"))
    s = clients.summarize(clients.load(p))
    assert s["other_top_40"]["in_both_months"] == ["near"]
    assert [c["contract"] for c in s["other_top_40"]["prior"]] == ["pyth-oracle.near", "near"]
    assert s["other_top_40"]["latest"][0] == {"contract": "mystery.near", "transactions": 40, "accounts": 1}
    bots = s["exchange_bot_targets"]
    assert (bots["prior"], bots["latest"]) == (60, 0)
    assert abs(bots["exchange_pct_change_with_them"] - (200 / 360 - 1) * 100) < 1e-9       # the exchange: 300 + 60 then, 200 now
    assert abs(bots["finance_pct_change_with_them"] - (500 / 460 - 1) * 100) < 1e-9
    assert s["finance_txs"]["pct_change"] == 25.0                                           # the frozen group is untouched
    clients.add_namespace_view(s, 0)
    clients.add_three_parts(s, 500)
    rest, alt = s["three_parts"]["rest"], s["three_parts"]["rest_without_exchange_bot_targets"]
    assert alt["prior"] == rest["prior"] - 60 and alt["latest"] == rest["latest"]
    # the committed result: of the unnamed contracts among the 40 largest, one is in both months
    real = clients.summarize(clients.load())
    assert real["other_top_40"]["in_both_months"] == ["near"] and real["exchange_bot_targets"]["latest"] == 0
    callers = clients.load()["2025-10"]["actors"].set_index("actor")["top_via"]
    assert callers["pyth-bot.ref-labs.near"] == callers["pyth-bot-a.ref-labs.near"] == "pyth-oracle.near"
    assert callers["watcher05.ref-watchdog.near"] == "acc.toalice.near"


def test_reward_game_is_read_in_both_months(tmp_path):
    """A year ago the players call the game themselves; now the same calls come through the wallet's relayer."""
    p = write(tmp_path)
    text = p.read_text(encoding="utf-8").replace("intents.near|100|9\n", "intents.near|100|9;aa-harvest-moon.near|70|20;relayer:meteor-relayer.near|30|5\n")
    p.write_text(text.replace("mystery.near|40|1", "mystery.near|40|1;relayer:meteor-relayer.near|50|25"))
    game = clients.summarize(clients.load(p))["reward_game"]
    assert game["direct"] == {"latest": None, "prior": {"transactions": 70, "accounts": 20, "transactions_per_account": 3.5}}
    assert game["relayed"] == {"latest": {"transactions": 50, "accounts": 25}, "prior": {"transactions": 30, "accounts": 5}}
    assert game["smallest_of_the_40_latest"] == 40          # a contract outside the table received fewer than this


def test_three_parts_cover_every_transaction(tmp_path):
    """Ember and the transactions of KaiChing's own accounts leave the two bottom rows; what is left is the rest of the chain."""
    p = write(tmp_path)
    p.write_text(p.read_text(encoding="utf-8").replace("intents.near|100|9\n", "intents.near|100|9;relayer:mytestapi.embr.playember_reserve.near|40|30\n"))
    s = clients.summarize(clients.load(p))
    clients.add_namespace_view(s, 15)     # KaiChing accounts sent 15 transactions this month, none to the app's own contracts
    clients.add_three_parts(s, 530)       # and 530 a year ago, 500 of them through its relayer
    t = s["three_parts"]
    for k, total in (("latest", 800), ("prior", 1000)):
        assert t["reward_side"][k] + t["finance"][k] + t["rest"][k] == total
    assert (t["reward_side"]["latest"], t["reward_side"]["prior"]) == (200 + 0 + 15, 500 + 40 + 30)
    assert t["rest"] == {"latest": 85.0, "prior": 30.0, "pct_change": (85 / 30 - 1) * 100}
    assert t["outside_top_40_without_kaiching"]["latest"] == 45 and t["outside_top_40_without_kaiching"]["prior"] == 30
    assert t["other_top_40_without_ember"]["prior"] == 0 and math.isnan(t["other_top_40_without_ember"]["pct_change"])
    assert s["kaiching_txs_outside_its_contracts_prior"] == 30
    assert abs(s["reward_apps_share_incl_kaiching_namespace_prior"] - 0.53) < 1e-12
    assert s["reward_apps_share"]["prior"] == 0.5 and s["apps"][clients.OTHER_TOP]["prior"] == 40    # the frozen groups are untouched


def block_sample():
    """Two windows of 40 identical blocks: 1 finance transaction in 10 a year ago, 5 in 10 now."""
    rows = []
    for label, finance in (("prior", 1), ("recent", 5)):
        for block in range(40):
            for i in range(10):
                if i < finance:
                    rows.append((label, block, "bot.near", "bot.near", "intents.near", False))
                elif i == 9:      # relayed to a token contract: filed under its relayer, as in the table, so not finance
                    rows.append((label, block, "user.near", "relay.near", "wrap.near", True))
                else:
                    rows.append((label, block, "walker.near", "sweat-relayer.near", "token.sweat", True))
    return pd.DataFrame(rows, columns=["window", "height", "actor", "signer", "target", "relayed"])


def test_sample_view_files_transactions_like_the_table_and_scales_by_the_window():
    windows = {"prior": {"start": "2025-01-01", "end": "2025-03-31"}, "recent": {"start": "2026-01-01", "end": "2026-03-31"}}
    daily = pd.DataFrame({"txns": 1000.0}, index=pd.date_range("2025-01-01", "2026-03-31", freq="D"))
    daily.loc["2026-01-01":, "txns"] = 400.0
    v = clients.sample_view(block_sample(), windows, daily, seed=1, n_boot=200)
    assert v["windows"]["prior"] == {"window": ["2025-01-01", "2025-03-31"], "sample_transactions": 400, "all_transactions": 90_000}
    fin, reward = v["groups"]["finance"], v["groups"]["reward_apps"]
    assert abs(fin["prior"]["share"] - 0.1) < 1e-12 and abs(fin["recent"]["share"] - 0.5) < 1e-12
    assert abs(fin["prior"]["transactions_per_30_days"] - 3_000) < 1e-6 and abs(fin["recent"]["transactions_per_30_days"] - 6_000) < 1e-6
    assert abs(fin["pct_change"] - 100) < 1e-9 and abs(reward["pct_change"] + 80) < 1e-9
    # every block is the same, so resampling blocks cannot move the estimate
    assert all(abs(x - 100) < 1e-6 for x in fin["pct_change_ci95"]) and fin["recent"]["share_ci95"] == [0.5, 0.5]
    assert clients.sample_view(block_sample().query("window == 'recent'"), windows, daily) is None    # one window is not a comparison


def test_summary_and_chart(tmp_path):
    s = clients.summarize(clients.load(write(tmp_path)))
    assert (s["latest_month"], s["prior_month"]) == ("2026-10", "2025-10")
    assert s["months"]["2026-10"]["accounts_for_half_of_txs"] == 2
    assert s["months"]["2025-10"]["accounts_for_half_of_txs"] is None      # the 1000+ group holds only 40%
    assert abs(s["reward_apps_share"]["prior"] - 0.5) < 1e-9 and abs(s["reward_apps_share"]["latest"] - 0.25) < 1e-9
    assert s["intents"]["latest"]["top2_signers"] == ["intents.near", "escrow.ai.near"]
    assert abs(s["intents"]["latest"]["top2_share"] - 290 / 300) < 1e-9
    assert s["sweat_users"] == {"latest": 30, "prior": 0}
    c = charts._clients_chart(s, tmp_path)
    assert (tmp_path / "clients.png").stat().st_size > 5_000 and "nan" not in c.sentence.lower()
