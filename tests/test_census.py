"""Signer census: parsing of blocks and the pure metrics, on synthetic data (no network)."""
import json

import numpy as np
import pandas as pd
import pytest

from thesis import census, charts


def fake_block(height, txs):
    return {"block": {"header": {"height": height, "timestamp": height * 10**9}},
            "shards": [{"chunk": {"transactions": [{"transaction": t} for t in txs]}}, {"chunk": None}]}


def test_parse_block_reads_the_user_behind_a_relayer():
    plain = {"signer_id": "alice.near", "receiver_id": "dex.near",
             "actions": [{"FunctionCall": {"method_name": "swap", "args": "", "gas": 1, "deposit": "0"}}]}
    relayed = {"signer_id": "relay.near", "receiver_id": "bob.tg", "actions": [{"Delegate": {"delegate_action": {
        "sender_id": "bob.tg", "receiver_id": "game.near",
        "actions": [{"FunctionCall": {"method_name": "claim", "args": "", "gas": 1, "deposit": "0"}}]}, "signature": "x"}}]}
    created = {"signer_id": "factory.near", "receiver_id": "new.near", "actions": ["CreateAccount", {"Transfer": {"deposit": "1"}}]}
    rows = census.parse_block(fake_block(7, [plain, relayed, created]))
    assert [(r["actor"], r["target"], r["method"], r["relayed"]) for r in rows] == [
        ("alice.near", "dex.near", "swap", False),
        ("bob.tg", "game.near", "claim", True),
        ("factory.near", "new.near", "CreateAccount", False),
    ]
    assert census.parse_block(None) == []


@pytest.mark.parametrize("kind", ["Delegate", "DelegateV2"])
@pytest.mark.parametrize("prefix", [[], [{"Transfer": {"deposit": "1"}}]])
def test_parse_block_reads_both_archived_delegate_formats_in_any_position(kind, prefix):
    """The historical V2 RPC view wraps the same inner actor/receiver in a versioned payload."""
    delegated = {"sender_id": "alice.near", "receiver_id": "game.near",
                 "actions": [{"FunctionCall": {"method_name": "claim", "args": "", "gas": 1, "deposit": "0"}}]}
    payload = {"V2": delegated} if kind == "DelegateV2" else delegated
    tx = {"signer_id": "payer.near", "receiver_id": "alice.near",
          "actions": prefix + [{kind: {"delegate_action": payload, "signature": "x"}}]}
    (row,) = census.parse_block(fake_block(42, [tx]))
    assert row == {"height": 42, "ts": 42 * 10**9, "actor": "alice.near", "signer": "payer.near",
                   "target": "game.near", "method": "claim", "relayed": True}


def test_unknown_delegate_payload_does_not_silently_become_self_paid():
    tx = {"signer_id": "payer.near", "receiver_id": "alice.near",
          "actions": [{"DelegateV2": {"delegate_action": {"V3": {}}, "signature": "x"}}]}
    with pytest.raises(ValueError, match="Unsupported DelegateV2 payload"):
        census.parse_block(fake_block(42, [tx]))


def test_block_cache_does_not_reuse_rows_from_the_old_parser(tmp_path, monkeypatch):
    """The cache contains parsed rows rather than original blocks, so a parser fix needs a new cache key."""
    monkeypatch.setattr(census, "CACHE_DIR", tmp_path)
    (tmp_path / "blocks").mkdir()
    old = tmp_path / "blocks" / "42.json"
    old.write_text(json.dumps({"found": True, "rows": [{"actor": "wrong-relayer.near"}]}))
    tx = {"signer_id": "payer.near", "receiver_id": "alice.near", "actions": [{"DelegateV2": {
        "delegate_action": {"V2": {"sender_id": "alice.near", "receiver_id": "game.near", "actions": []}},
        "signature": "x"}}]}
    calls = []

    def get(url):
        calls.append(url)
        return fake_block(42, [tx])

    monkeypatch.setattr(census, "_get_json", get)
    assert census._block_rows(42)["rows"][0]["actor"] == "alice.near"
    assert census._block_rows(42)["rows"][0]["relayed"] is True
    assert len(calls) == 1  # the new cache remains resumable
    assert json.loads(old.read_text())["rows"][0]["actor"] == "wrong-relayer.near"


def test_fetch_checks_both_historical_states_after_account_recreation(tmp_path, monkeypatch):
    """An ID can exist at the older date, be absent at the nearer date, and act again in the sampled block."""
    monkeypatch.setattr(census, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(census, "CACHE_DIR", tmp_path / "cache")
    census.CACHE_DIR.mkdir()
    bounds = {"recent": {"start": "2026-08-14", "end": "2026-11-11", "height_start": 100, "height_end": 101,
                         "ref_heights": {"30d_before_start": 30, "365d_before_start": 10}}}
    (census.CACHE_DIR / "bounds_2026-11-11.json").write_text(json.dumps(bounds))
    monkeypatch.setattr(census, "_block_rows", lambda height: {"found": True, "rows": [{
        "height": height, "ts": pd.Timestamp("2026-10-01").value, "actor": "again.parent.near",
        "signer": "again.parent.near", "target": "app.near", "method": "call", "relayed": False}]})
    calls = []

    def rpc(method, params):
        assert method == "query" and params["request_type"] == "view_account"
        assert params["account_id"] == "again.parent.near"
        height = params["block_id"]
        calls.append(height)
        return {"result": {}} if height == 10 else {"error": {"cause": {"name": "UNKNOWN_ACCOUNT"}}}

    monkeypatch.setattr(census, "_rpc", rpc)
    census.fetch("2026-11-11", blocks={"recent": 1})
    sample, exist, meta = census.load()
    assert calls == [30, 10]
    assert exist.to_dict("records") == [{"window": "recent", "actor": "again.parent.near",
                                         "existed_30d": False, "existed_365d": True}]
    assert meta["age_check_mode"] == "independent" and meta["block_parser_version"] == census.BLOCK_PARSER_VERSION
    summary = census.summarize(sample, exist, meta)
    assert summary["windows"]["recent"]["tx_share_by_account_age"] == {"365d+": 1, "30-365d": 0, "new": 0}
    assert summary["windows"]["recent"]["age_checks"] == {
        "inferred_false_365d_accounts": 0, "inferred_false_365d_transactions": 0}
    assert "age_check_note" not in summary and "relay_parser_note" not in summary


def test_legacy_sample_preserves_age_assignments_without_claiming_revalidation():
    sample, exist = synthetic()
    before = census.classify(sample, exist)
    summary = census.summarize(sample, exist)
    assert summary["age_check_mode"] == "legacy_30d_shortcut"
    assert "have not been revalidated" in summary["age_check_note"]
    assert "has not been refreshed" in summary["relay_parser_note"]
    for label, rows in before.groupby("window"):
        inferred = rows.loc[~rows["existed_30d"]]
        window = summary["windows"][label]
        assert window["age_checks"] == {"inferred_false_365d_accounts": inferred["actor"].nunique(),
                                         "inferred_false_365d_transactions": len(inferred)}
        assert window["tx_share_by_account_age"]["365d+"] == rows["existed_365d"].mean()


def test_calls_to_says_how_many_calls_a_relayer_submitted():
    rows = [("prior", "game.near", False), ("prior", "game.near", False), ("prior", "game.near", True), ("prior", "dex.near", False),
            ("recent", "game.near", True), ("recent", "game.near", True)]
    sample = pd.DataFrame(rows, columns=["window", "target", "relayed"])
    assert census.calls_to(sample, "game.near") == {"prior": {"calls": 3, "relayed": 1}, "recent": {"calls": 2, "relayed": 2}}
    assert census.calls_to(sample, "dex.near")["recent"] == {"calls": 0, "relayed": 0}


def test_batched_calls_finds_claims_that_line_up_alphabetically_in_a_block():
    rows = [("recent", 10, "abel.near", "relay.near", "claim", True), ("recent", 10, "abby.near", "relay.near", "claim", True),
            ("recent", 10, "abdul.tg", "relay.near", "claim", True), ("recent", 10, "zoe.near", "relay.near", "claim", True),
            ("recent", 11, "abner.near", "relay.near", "claim", True),                       # alone in its block
            ("recent", 12, "mona.near", "relay.near", "claim", True), ("recent", 12, "moe.near", "relay.near", "claim", True),
            ("recent", 12, "mo.near", "relay.near", "harvest", True),                        # another method
            ("recent", 12, "morgan.near", "other.near", "claim", True),                      # another relayer
            ("prior", 5, "abel.near", "abel.near", "claim", False)]                          # not relayed
    sample = pd.DataFrame(rows, columns=["window", "height", "actor", "signer", "method", "relayed"])
    out = census.batched_calls(sample, "relay.near", "claim")
    assert out["recent"] == {"calls": 7, "in_batches": 5, "blocks_with_a_batch": 2, "largest_batch": 3, "shared_first_letters": ["ab", "mo"]}
    assert out["prior"] == {"calls": 0, "in_batches": 0, "blocks_with_a_batch": 0, "largest_batch": 0, "shared_first_letters": []}
    # the committed sample: most of the game's reward claims come in such batches now
    real = census.batched_calls(census.load()[0], "meteor-relayer.near", "claim_meteor_staking_reward")["recent"]
    assert real["in_batches"] > real["calls"] / 2 and real["blocks_with_a_batch"] >= 3


def test_self_deletions_counts_accounts_that_delete_themselves():
    rows = [("recent", "a.users.app", "a.users.app", "DeleteAccount", 1_759_400_000_000_000_000),      # 2025-10-02
            ("recent", "b.users.app", "b.users.app", "DeleteAccount", 1_759_500_000_000_000_000),      # 2025-10-03
            ("recent", "c.users.app", "game.near", "claim", 1_759_500_000_000_000_000),
            ("recent", "d.near", "d.near", "DeleteAccount", 1_759_500_000_000_000_000),                # another namespace
            ("prior", "e.users.app", "game.near", "claim", 1_727_900_000_000_000_000)]
    sample = pd.DataFrame(rows, columns=["window", "actor", "target", "method", "ts"])
    out = census.self_deletions(sample, ".users.app")
    assert out["recent"] == {"transactions": 3, "delete_account": 2, "first_day": "2025-10-02", "last_day": "2025-10-03"}
    assert out["prior"] == {"transactions": 1, "delete_account": 0, "first_day": None, "last_day": None}
    # the committed sample: every transaction of an old KaiChing user account in autumn 2026 deletes that account
    real = census.self_deletions(census.load()[0], ".users.kaiching")["recent"]
    assert real["transactions"] == real["delete_account"] > 0


def synthetic(old_share_recent=0.8, old_share_prior=0.2, seed=1):
    rng = np.random.default_rng(seed)
    rows, exist = [], []
    for label, old_share in (("prior", old_share_prior), ("recent", old_share_recent)):
        for b in range(200):
            for _ in range(5):
                old = rng.random() < old_share
                actor = f"{label}-{'old' if old else 'new'}-{rng.integers(0, 300)}"
                rows.append({"window": label, "height": b, "ts": b, "actor": actor, "signer": actor,
                             "target": "app.near" if old else "farm.near", "method": "m", "relayed": False})
        for a in {r["actor"] for r in rows if r["window"] == label}:
            exist.append({"window": label, "actor": a, "existed_30d": "-old-" in a, "existed_365d": "-old-" in a})
    return pd.DataFrame(rows), pd.DataFrame(exist)


def test_summarize_recovers_planted_shares_with_interval():
    s = census.summarize(*synthetic())["windows"]
    for label, truth in (("recent", 0.8), ("prior", 0.2)):
        w = s[label]
        lo, hi = w["tx_share_ci95"]["365d+"]
        assert lo <= truth <= hi and hi - lo < 0.1
        assert abs(sum(w["tx_share_by_account_age"].values()) - 1) < 1e-9
        assert w["transactions"] == 1000
    assert list(s["recent"]["top_targets"])[0] == "app.near"


def test_census_chart_renders(tmp_path):
    cs = census.summarize(*synthetic(), meta={"seed": 1, "windows": {
        k: {"start": "2026-01-01", "end": "2026-03-31", "blocks_found": 200} for k in ("prior", "recent")}})
    c = charts._census_chart(cs, tmp_path)
    assert (tmp_path / "signer_census.png").stat().st_size > 5_000
    assert "nan" not in c.sentence.lower() and "80%" in c.sentence
    assert "have not been revalidated" in c.method and "DelegateV2" in c.method
    checks = cs["windows"]["prior"]["age_checks"]
    assert f"prior: {checks['inferred_false_365d_accounts']} accounts / {checks['inferred_false_365d_transactions']} transactions" in c.method


def test_height_at_finds_the_block_in_a_few_requests(monkeypatch):
    calls = []

    def header(h):  # block time changes from 1.2 s to 0.6 s at height 500_000
        calls.append(h)
        t = h * 1.2 if h < 500_000 else 500_000 * 1.2 + (h - 500_000) * 0.6
        return h, int(t * 1e9)

    monkeypatch.setattr(census, "_block_header", header)
    lo, hi = header(0), header(2_000_000)
    calls.clear()
    target = int(1_200_000 * 1e9)  # seconds 1.2M -> height 1_500_000
    h = census.height_at(target, lo, hi)
    assert abs(header(h)[1] - target) <= census.BOUND_TOLERANCE_NS
    assert len(calls) <= 12


def test_outcomes_by_sender():
    df = pd.DataFrame({"window": "recent", "height": [1, 1, 2, 3, 3, 4], "target": "intents.near",
                       "signer": ["a.near", "bot.near", "bot.near", "a.near", "c.near", "bot.near"],
                       "relayed": False, "success": [True, False, False, True, True, False]})
    s = census.outcomes(df, top=2)
    assert (s["transactions"], s["failed"], s["blocks"]) == (6, 3, 4)
    assert s["senders"] == {"bot.near": {"transactions": 3, "failed": 3}, "a.near": {"transactions": 2, "failed": 0}}
    assert s["other_senders"] == {"transactions": 1, "failed": 0, "accounts": 1}


def test_one_block_transfers_finds_a_sweep_and_not_two_payments_in_two_blocks():
    a, b, c, to = ("a" * 64), ("b" * 64), ("c" * 64), ("d" * 64)
    ts = 1762767000 * 10**9
    sample = pd.DataFrame([
        {"window": "recent", "height": 10, "ts": ts, "actor": a, "signer": a, "target": to, "method": "Transfer", "relayed": False},
        {"window": "recent", "height": 10, "ts": ts, "actor": b, "signer": b, "target": to, "method": "Transfer", "relayed": False},
        {"window": "recent", "height": 11, "ts": ts + 10**9, "actor": c, "signer": c, "target": to, "method": "Transfer", "relayed": False},
        {"window": "recent", "height": 12, "ts": ts + 2 * 10**9, "actor": "x.near", "signer": "x.near", "target": to, "method": "Transfer", "relayed": False},
        {"window": "prior", "height": 5, "ts": ts, "actor": a, "signer": a, "target": to, "method": "Transfer", "relayed": False},
    ])
    exist = pd.DataFrame({"window": ["recent"] * 2, "actor": [a, b], "existed_30d": [True, True], "existed_365d": [True, False]})
    out = census.one_block_transfers(sample, exist)
    assert out["prior"] == []
    (row,) = out["recent"]
    assert (row["height"], row["senders"], row["implicit_senders"], row["senders_older_than_a_year"]) == (10, 2, 2, 1)
    assert row["blocks_sampled_that_day"] == 3 and row["receiver"] == to
