"""Signer census: parsing of blocks and the pure metrics, on synthetic data (no network)."""
import numpy as np
import pandas as pd

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


def test_fetch_panel_runs_month_by_month_without_network(tmp_path, monkeypatch):
    """Smoke test of the long monthly run with the network replaced by fakes."""
    monkeypatch.setattr(census, "RAW_DIR", tmp_path / "raw")
    monkeypatch.setattr(census, "CACHE_DIR", tmp_path / "cache")
    ns_per_block = 10**9  # one block a second from 2020-01-01
    t0 = pd.Timestamp("2020-01-01").value

    def header(h):
        return h, t0 + h * ns_per_block

    top = int((pd.Timestamp("2026-11-13").value - t0) / ns_per_block)

    def rpc(method, params):
        if method == "block":
            h = top if "finality" in params else params["block_id"]
            return {"result": {"header": {"height": h, "timestamp": str(header(h)[1])}}}
        old = params["account_id"].startswith("old")
        return {"result": {}} if old else {"error": {"cause": {"name": "UNKNOWN_ACCOUNT"}}}

    def get_json(url, **kw):
        h = int(url.rsplit("/", 1)[1])
        tx = lambda who: {"signer_id": who, "receiver_id": "app.near", "actions": [{"FunctionCall": {"method_name": "go"}}]}
        return fake_block(h, [tx(f"old{h % 7}.near"), tx(f"new{h}.near")]) | {
            "block": {"header": {"height": h, "timestamp": header(h)[1]}}}

    def get_json_any(url, **kw):
        if url.endswith("/v0/account"):  # old* accounts first appeared in 2021, new* ones a day before the query
            acc = kw["json"]["account_id"]
            ts = pd.Timestamp("2021-01-01").value if acc.startswith("old") else pd.Timestamp("2026-11-10").value
            return {"account_txs": [{"tx_block_timestamp": str(ts), "tx_block_height": 1}], "txs_count": 5}
        return get_json(url, **kw)

    monkeypatch.setattr(census, "_rpc", rpc)
    monkeypatch.setattr(census, "_get_json", get_json_any)
    census.fetch_panel("2026-09", "2026-11-11", blocks_per_month=12, tx_per_month=10)
    sample = pd.read_csv(tmp_path / "raw" / census.PANEL_SAMPLE_FILE)
    exist = pd.read_csv(tmp_path / "raw" / census.PANEL_EXIST_FILE)
    assert sorted(sample["window"].unique()) == ["2026-09", "2026-10", "2026-11"]
    assert sample.groupby("window").size().max() <= 10
    assert pd.to_datetime(sample.loc[sample["window"] == "2026-11", "ts"]).max() < pd.Timestamp("2026-11-12")
    s = census.summarize(sample, exist)["windows"]
    assert all(0.2 < w["tx_share_by_account_age"]["365d+"] < 0.8 for w in s.values())
