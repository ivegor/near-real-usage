"""Top accounts and apps: parsing of the BigQuery result and the grouping, on a tiny hand-made result."""
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
    p.write_text(p.read_text().replace("mystery.near|40|1", "mystery.near|40|1;embr.playember_reserve.near|16|2;dclv2.ref-labs.near|10|7"))
    s = clients.summarize(clients.load(p))
    assert (s["ember"]["latest"], s["ember"]["prior"]) == (16, 0) and abs(s["ember"]["latest_share"] - 0.02) < 1e-9
    assert abs(s["ember"]["reward_apps_share_with_ember"]["latest"] - 0.27) < 1e-9
    assert s["apps"][clients.OTHER_TOP]["latest"] == 56 and abs(s["reward_apps_share"]["latest"] - 0.25) < 1e-9   # the group itself is unchanged
    ex = {c["contract"]: c for c in s["exchange_contracts_latest"]}
    assert ex["v2.ref-finance.near"]["accounts"] == 4 and ex["dclv2.ref-labs.near"]["accounts"] == 7
    assert abs(ex["v2.ref-finance.near"]["share_of_app_txs"] - 200 / 210) < 1e-9


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
