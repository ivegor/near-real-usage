import numpy as np
import pandas as pd

from thesis import metrics, sources


def synthetic_raw(days: int = 800, lag_weeks: int = 3, seed: int = 0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("2024-09-01", periods=days, freq="D")
    usage = np.exp(np.cumsum(rng.normal(0, 0.03, days)))  # random walk
    # price follows usage with a lag of `lag_weeks` weeks plus noise
    shift = lag_weeks * 7
    price = np.r_[np.ones(shift), usage[:-shift]] * np.exp(rng.normal(0, 0.01, days)) * 3
    active = (50_000 * usage).astype(int)
    new = (active * 0.1).astype(int)
    charts = [
        {
            "date": d.strftime("%Y-%m-%dT00:00:00.000Z"),
            "near_price": str(p),
            "market_cap": str(p * 1e9),
            "txns": str(a * 10),
            "txn_volume_usd": str(a * 100.0),
            "txn_fee_usd": str(a * 0.05),
            "new_accounts": str(n),
            "active_accounts": str(a),
            "deleted_accounts": "1",
            "new_contracts": "5",
            "active_contracts": "100",
        }
        for d, p, a, n in zip(idx, price, active, new)
    ]
    llama = {"totalDataChart": [[int(d.timestamp()), float(a * 20)] for d, a in zip(idx[100:], active[100:])]}
    return {"charts": charts}, llama


def daily():
    nb, ll = synthetic_raw()
    return sources.parse_nearblocks(nb).join(sources.parse_defillama(ll), how="left")


def test_parse_shapes():
    d = daily()
    assert len(d) == 800
    assert {"price_usd", "active_accounts", "intents_volume_usd"} <= set(d.columns)
    assert d["intents_volume_usd"].isna().sum() == 100


def test_derived_values():
    d = metrics.add_derived(daily())
    assert np.allclose(d["returning_share"], 1 - d["new_accounts"] / d["active_accounts"])
    assert np.allclose(d["tx_per_active"], 10, atol=0.01)


def test_period_change_known():
    idx = pd.date_range("2025-01-01", periods=500, freq="D")
    s = pd.Series(np.where(idx < idx[-1] - pd.Timedelta(days=200), 100.0, 150.0), index=idx)
    out = metrics.period_change(s, days=90, lookback_days=365)
    assert round(out["pct_change"]) == 50


def test_lead_lag_recovers_known_lag():
    d = daily()
    best = metrics.best_lead(metrics.lead_lag(d["active_accounts"], d["price_usd"]))
    assert best["lag_weeks"] == 3
    assert best["significant"]


def test_checks_flag_broken_identity():
    d = daily()
    d.iloc[-3:, d.columns.get_loc("new_accounts")] = d["active_accounts"].iloc[-3:] + 1
    c = metrics.checks(d)["new_exceeds_active_days"]
    assert c == {"recent": 3, "prior": 0, "all_history": 3}
    assert (metrics.add_derived(d)["returning_accounts"].iloc[-3:] == 0).all()


def test_best_lead_lists_every_lag_outside_band():
    d = daily()
    best = metrics.best_lead(metrics.lead_lag(d["active_accounts"], d["price_usd"]))
    assert {"lag_weeks": 3, "corr": round(best["corr"], 3)} in best["outside_band"]


def test_summarize_runs():
    s = metrics.summarize(daily())
    assert s["days"] == 800
    assert "returning_accounts" in s["lead_vs_price"]


def test_month_change_uses_the_last_complete_calendar_month():
    idx = pd.date_range("2025-01-01", "2026-11-11", freq="D")
    s = pd.Series(np.where(idx >= "2026-01-01", 200.0, 100.0), index=idx)
    out = metrics.month_change(s)
    assert out["month"] == "2026-10" and out["pct_change"] == 100


def test_fees_are_tested_in_near_not_usd():
    s = metrics.summarize(daily())
    assert "fees_near" in s["lead_vs_price"] and "fees_usd" not in s["lead_vs_price"]
    assert "corr" in s["lead_fees_usd_mechanical"]


def test_build_survives_an_api_outage(tmp_path, monkeypatch):
    import json

    import pytest
    nb, ll = synthetic_raw(days=60)
    monkeypatch.setattr(sources, "RAW_DIR", tmp_path)

    def down(url, retries=3):
        raise RuntimeError("API down")

    monkeypatch.setattr(sources, "_fetch_json", down)
    with pytest.raises(RuntimeError):          # nothing saved yet: the failure is reported
        sources.fetch_all()
    (tmp_path / "nearblocks_charts.json").write_text(json.dumps(nb))
    (tmp_path / "defillama_intents.json").write_text(json.dumps(ll))
    raw = sources.fetch_all()                  # saved copies exist: they are used instead
    assert len(raw["nearblocks_charts"]["charts"]) == 60
    assert json.loads((tmp_path / "_meta.json").read_text(encoding="utf-8"))["not_refreshed"] == ["nearblocks_charts", "defillama_intents"]
    assert sources.NOT_REFRESHED == ["nearblocks_charts", "defillama_intents"]       # the build can tell that it fell back


def test_a_bad_api_reply_never_replaces_the_saved_copy(tmp_path, monkeypatch):
    import json

    import pytest
    nb, ll = synthetic_raw(days=60)
    monkeypatch.setattr(sources, "RAW_DIR", tmp_path)
    (tmp_path / "nearblocks_charts.json").write_text(json.dumps(nb))
    (tmp_path / "defillama_intents.json").write_text(json.dumps(ll))
    monkeypatch.setattr(sources, "_fetch_json", lambda url: {"message": "rate limited"})   # HTTP 200 with the wrong body
    out = sources.fetch_all(offline=False)
    assert out["nearblocks_charts"] == nb                                    # the build falls back to the saved copy
    assert json.loads((tmp_path / "nearblocks_charts.json").read_text(encoding="utf-8")) == nb          # and the file is untouched
    with pytest.raises(RuntimeError):
        sources._check_shape("defillama_intents", {"totalDataChart": []})


def test_a_host_that_does_not_answer_is_given_up_on_quickly(monkeypatch):
    """A silent host costs the short connect timeout on each attempt, not the minute a slow reply is given."""
    import pytest
    import requests
    seen, slept = [], []

    def silent(url, timeout, headers):
        seen.append(timeout)
        raise requests.ConnectTimeout("no answer")

    monkeypatch.setattr(sources.requests, "get", silent)
    monkeypatch.setattr(sources.time, "sleep", slept.append)
    with pytest.raises(RuntimeError, match="no answer"):           # the same failure the build falls back on
        sources._fetch_json("https://example.invalid/charts")
    connect, read = sources.TIMEOUT
    assert seen == [sources.TIMEOUT] * 3 and connect <= 10 < read
    assert connect * len(seen) + sum(slept) < 60                     # under a minute per source, retries included


def test_best_lead_reports_the_range_of_sample_sizes():
    """Each week of lag costs one week of data, so the text quotes the smallest and the largest n, not one of them."""
    d = daily()
    ll = metrics.lead_lag(d["active_accounts"], d["price_usd"])
    best = metrics.best_lead(ll)
    lo, hi = best["n_weeks_range"]
    assert (lo, hi) == (int(ll["n"].min()), int(ll["n"].max())) and hi - lo == 8 and lo <= best["n_weeks"] <= hi
    assert best["band_range"][0] < best["band_range"][1] and abs(best["band_range"][1] - 2 / lo ** 0.5) < 1e-12


def test_a_null_in_a_series_is_a_missing_day_not_a_crash():
    s = sources.parse_defillama({"totalDataChart": [[1_700_000_000, 1.0], [1_700_086_400, None], [1_700_172_800, 3.0]]})
    assert list(s) == [1.0, 3.0] and s.name == "intents_volume_usd"
    assert sources.parse_defillama({"totalDataChart": []}).empty


def test_month_to_date_compares_the_same_days_a_year_apart():
    """The month in progress, as far as it has come, against the same days of the same month a year earlier."""
    idx = pd.date_range("2025-01-01", "2026-11-11", freq="D")
    s = pd.Series(np.where(idx >= "2026-01-01", 200.0, 100.0), index=idx)
    out = metrics.month_to_date_change(s)
    assert (out["from"], out["through"], out["days"], out["recent"], out["prior"], out["pct_change"]) == ("2026-11-01", "2026-11-11", 11, 200.0, 100.0, 100.0)
    assert metrics.month_to_date_change(s.loc[:"2026-10-31"]) is None            # a complete month has no "so far"
    assert metrics.month_to_date_change(s.loc["2025-11-05":]) is None            # last year's days are not all there
    assert metrics.summarize(daily())["month_to_date_yoy"]["price_usd"]["days"] == 9     # the synthetic series ends on 9 November


def test_require_fresh_refuses_to_build_from_saved_copies(tmp_path, monkeypatch):
    """The scheduled build starts from the committed copies; an outage must not publish them as today's page."""
    import pytest

    from thesis import __main__ as cli
    from thesis import value
    table = sources.load_daily(offline=True)
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "DOCS", tmp_path / "docs")
    monkeypatch.setattr(sources, "load_daily", lambda offline=False: table)

    def down():
        raise RuntimeError("API down")

    monkeypatch.setattr(value, "fetch", down)
    with pytest.raises(SystemExit, match="not refreshed: defillama_intents_fees"):
        cli.build(offline=False, require_fresh=True)
    assert not (tmp_path / "docs").exists()                                       # nothing was rendered
    monkeypatch.setattr(value, "fetch", lambda: None)
    monkeypatch.setattr(sources, "NOT_REFRESHED", ["nearblocks_charts"])
    with pytest.raises(SystemExit, match="nearblocks_charts"):
        cli.build(offline=False, require_fresh=True)
    cli.build(offline=False)                                                      # without the flag the saved copies are used
    assert (tmp_path / "docs" / "index.html").exists()


def test_holm_asks_more_of_the_smallest_p_value_the_more_tests_there_are():
    # one strong result among 85 stands; a p-value that would pass alone (0.01) does not
    strong = metrics.holm([0.0001] + [0.5] * 84)
    assert (strong["tests"], strong["significant"]) == (85, 1)
    weak = metrics.holm([0.01] + [0.5] * 84)
    assert weak["significant"] == 0 and weak["threshold_for_the_smallest_p"] == 0.05 / 85
    assert metrics.holm([0.01])["significant"] == 1
    assert metrics.holm([])["tests"] == 0


def test_p_value_of_a_correlation():
    assert metrics._p_value(0.0, 100) == 1.0
    assert 0.04 < metrics._p_value(0.2, 100) < 0.05      # just inside 2/sqrt(n) = 0.2
    assert metrics._p_value(0.5, 100) < 1e-6
    assert metrics._p_value(0.3, 3) != metrics._p_value(0.3, 3)  # too few points: not a number


def test_the_build_goes_on_from_v3_when_v1_is_switched_off(tmp_path, monkeypatch):
    """NearBlocks switches /v1 off on 2026-11-22. The daily build must then carry the table on from the v3 API for the
    columns v3 has with the same meaning, say which columns ended, and still count as fresh."""
    import json
    import shutil

    import pytest

    from thesis import __main__ as cli
    from thesis import value
    saved = sources.RAW_DIR
    raw = tmp_path / "raw"
    shutil.copytree(saved, raw)
    v1 = json.loads((raw / "nearblocks_charts.json").read_text(encoding="utf-8"))
    v1["charts"] = sorted(v1["charts"], key=lambda r: r["date"])[:-40]     # the saved copy ends 40 days earlier
    cut = v1["charts"][-1]["date"][:10]
    (raw / "nearblocks_charts.json").write_text(json.dumps(v1), encoding="utf-8")
    v3 = {url: json.loads((saved / f"{name}.json").read_text(encoding="utf-8")) for name, url in sources.NEARBLOCKS_V3.items()}
    intents = json.loads((saved / "defillama_intents.json").read_text(encoding="utf-8"))

    def fetch(url, retries=3):
        if url == sources.NEARBLOCKS_CHARTS_URL:
            raise RuntimeError("410 Gone")
        return v3.get(url, intents)

    monkeypatch.setattr(sources, "RAW_DIR", raw)
    monkeypatch.setattr(sources, "_fetch_json", fetch)
    monkeypatch.setattr(value, "fetch", lambda: None)
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "DOCS", tmp_path / "docs")
    cli.build(offline=False, require_fresh=True)                             # fresh: v3 answered
    assert sources.NOT_REFRESHED == [] and sources.CONTINUED_FROM_V3
    table = pd.read_csv(tmp_path / "data" / "daily.csv", index_col=0, parse_dates=True)
    after = table[table.index > cut]
    assert len(after) >= 40 and after["txns"].notna().all() and after["price_usd"].notna().all()
    assert after["total_supply_yocto"].notna().all() and after["fees_usd"].notna().all()
    assert after["active_accounts"].isna().all() and after["new_accounts"].isna().all()   # v3 has no such columns
    # on the days both carry, the continued columns are the saved /v1 values
    full = sources.parse_nearblocks(json.loads((saved / "nearblocks_charts.json").read_text(encoding="utf-8")))
    both = after.index.intersection(full.index)
    assert len(both) >= 38 and (after.loc[both, "txns"] == full.loc[both, "txns"]).all()
    assert (after.loc[both, "price_usd"] - full.loc[both, "price_usd"]).abs().max() < 1e-9
    summary = json.loads((tmp_path / "docs" / "summary.json").read_text(encoding="utf-8"))
    assert summary["series_ended"]["active_accounts"] == cut and "txns" not in summary["series_ended"]
    page = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    assert "Some series ended" in page and f"active accounts ({cut})" in page
    # and an offline build from the same saved replies builds the same table and summary, the v3 days included
    built = {p: p.read_bytes() for p in (tmp_path / "data" / "daily.csv", tmp_path / "docs" / "summary.json")}
    sources.CONTINUED_FROM_V3.clear()
    cli.build(offline=True)
    assert sources.CONTINUED_FROM_V3
    assert all(p.read_bytes() == b for p, b in built.items()), [p.name for p, b in built.items() if p.read_bytes() != b]
    # a saved v3 copy missing while _meta.json says the table went on from v3 is an error, not a shorter table
    (raw / "nearblocks_v3_txns.json").unlink()
    with pytest.raises(FileNotFoundError):
        sources.fetch_all(offline=True)
    sources.CONTINUED_FROM_V3.clear()


def test_v3_carries_the_same_values_as_v1_for_the_columns_it_continues():
    """The two committed copies, day by day from 2025-10-01: the columns continued from v3 are the /v1 values."""
    import json
    raw = {k: json.loads((sources.RAW_DIR / f"{k}.json").read_text(encoding="utf-8")) for k in sources.NEARBLOCKS_V3}
    v3 = sources.parse_nearblocks_v3(raw)
    v1 = sources.parse_nearblocks(json.loads((sources.RAW_DIR / "nearblocks_charts.json").read_text(encoding="utf-8")))
    days = v1.index.intersection(v3.index)
    days = days[days >= "2025-10-01"]
    assert len(days) > 400
    for col in ("total_supply_yocto", "gas_used", "txns", "price_usd", "market_cap_usd"):
        a, b = v1.loc[days, col].astype(float), v3.loc[days, col].astype(float)
        assert ((a - b).abs() <= 1e-9 * a.abs()).all(), col
    same = (v1.loc[days, "active_contracts"] == v3.loc[days, "active_contracts"]).mean()
    assert same > 0.98
    close = ((v3.loc[days, "fees_usd"] / v1.loc[days, "fees_usd"] - 1).abs() < 0.001).mean()
    assert close > 0.9
    # what is NOT continued: v3 counts the accounts relayers acted for as active, /v1 counted signers
    assert "active_accounts" not in v3.columns and "new_accounts" not in v3.columns
    relayed = sources.relayed_daily()
    assert (relayed.loc[days, "accounts_with_relayed_users"] > v1.loc[days, "active_accounts"]).all()


def test_a_day_is_left_out_for_its_date_not_for_its_size():
    """A day that had not ended when the data was downloaded is partial; a real fall on the last day is not."""
    idx = pd.date_range("2026-03-20", "2026-04-02", freq="D")
    daily = pd.DataFrame({"txns": 3_700_000.0}, index=idx)
    daily.loc["2026-04-02", "txns"] = 1_063_375.0                        # the day KaiChing stopped, as the last day
    kept = sources.drop_unfinished_days(daily, pd.Timestamp("2026-04-03"))
    assert kept.index.max() == pd.Timestamp("2026-04-02")                # a finished day stays, however small
    assert sources.drop_unfinished_days(daily, pd.Timestamp("2026-04-02")).index.max() == pd.Timestamp("2026-04-01")
    assert sources.drop_unfinished_days(daily, None).equals(daily)       # no download date: nothing to go by


def test_a_saved_unfinished_day_stays_out_when_a_later_download_fails(tmp_path, monkeypatch):
    """The day a saved reply was downloaded on is that reply's, not the day of the build that fell back to it. And when
    the table goes on from v3, the finished v3 day replaces the unfinished last day of the saved /v1 copy."""
    import json

    nb, ll = synthetic_raw(days=60)
    today = pd.Timestamp.now(tz="UTC").tz_localize(None).normalize()
    days = pd.date_range(end=today - pd.Timedelta(days=1), periods=60, freq="D")   # the copy ends yesterday
    for row, d in zip(nb["charts"], days):
        row["date"] = d.strftime("%Y-%m-%dT00:00:00.000Z")
    nb["charts"][-1]["txns"] = "7"                                  # yesterday was not over when the copy was saved
    ll = {"totalDataChart": [[int(d.timestamp()), 1.0] for d in days]}
    monkeypatch.setattr(sources, "RAW_DIR", tmp_path)
    (tmp_path / "nearblocks_charts.json").write_text(json.dumps(nb))
    (tmp_path / "defillama_intents.json").write_text(json.dumps(ll))
    saved_at = (days[-1] + pd.Timedelta(hours=15)).tz_localize("UTC").isoformat()
    meta = {name: {"url": url, "fetched_at_utc": saved_at} for name, url in sources.SOURCES.items()}
    (tmp_path / "_meta.json").write_text(json.dumps(meta))
    assert sources.load_daily(offline=True).index.max() == days[-2]           # the saved build left it out

    def down(url, retries=3):
        raise RuntimeError("API down")
    monkeypatch.setattr(sources, "_fetch_json", down)
    assert sources.load_daily().index.max() == days[-2]                       # so does a build that cannot download
    assert json.loads((tmp_path / "_meta.json").read_text())["nearblocks_charts"]["fetched_at_utc"] == saved_at

    # /v1 is gone and v3 answers: yesterday comes from v3, finished
    rows = [{"date": d.strftime("%Y-%m-%d"), "total_supply": "1", "gas_used": "1", "txns": "500",
             "txn_fee": "1", "txn_volume": "1", "near_price": "3", "market_cap": "3", "active_contracts": "1"} for d in days]
    v3 = {url: {"data": rows} for url in sources.NEARBLOCKS_V3.values()}
    monkeypatch.setattr(sources, "_fetch_json", lambda url, retries=3: v3[url] if url in v3 else down(url))
    table = sources.load_daily()
    assert table.index.max() == days[-1] and table.loc[days[-1], "txns"] == 500
    assert sources.CONTINUED_FROM_V3 and "nearblocks_charts" not in sources.NOT_REFRESHED
    sources.CONTINUED_FROM_V3.clear()
