"""End-to-end: synthetic raw files -> charts + dashboard, no network."""
import html
import json
import math
from pathlib import Path

from thesis import charts, clients, dashboard, metrics, population, sources

from .test_metrics import synthetic_raw


def test_full_build(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    nb, ll = synthetic_raw()
    (raw / "nearblocks_charts.json").write_text(json.dumps(nb))
    (raw / "defillama_intents.json").write_text(json.dumps(ll))
    monkeypatch.setattr(sources, "RAW_DIR", raw)
    monkeypatch.setattr(population, "CSV", tmp_path / "no_bigquery_table.csv")
    monkeypatch.setattr(clients, "CSV", tmp_path / "no_top_accounts.csv")

    daily = sources.load_daily(offline=True)
    summary = metrics.summarize(daily)
    out = tmp_path / "docs"
    built = charts.build_all(daily, summary, out)
    page = dashboard.render(built, summary, out)

    assert [c.slug for c in built] == ["accounts", "usage_vs_price", "tx_per_active", "fees_per_active", "intents", "lead_lag"]
    for c in built:
        assert (out / f"{c.slug}.png").stat().st_size > 5_000
        assert "nan" not in c.sentence.lower()
    html = page.read_text(encoding="utf-8")
    assert "NEAR Real Usage" in html and "lead_lag.png" in html
    # every card prints the request or query behind its chart on the page itself, and the page links the thesis
    assert html.count("behind this chart") == len(built) and "GET https://api.nearblocks.io/v1/charts" in html
    assert html.count('<p class="lead">') == len(built) and "blob/main/THESIS.md" in html and "sql/account_age.sql" in html


def test_every_card_of_the_real_dashboard_prints_its_query(tmp_path):
    """Built from the committed data, every card carries the query or the requests behind its chart."""
    root = Path(__file__).resolve().parent.parent
    daily = sources.load_daily(offline=True)
    summary = json.loads((root / "docs" / "summary.json").read_text(encoding="utf-8"))
    built = charts.build_all(daily, summary, tmp_path)
    cards = {c.slug: dashboard.query_block(c) for c in built}
    assert list(cards)[:4] == ["population", "segments", "clients", "value_capture"] and len(cards) == 11
    for slug, query in (("population", "sql/account_age.sql"), ("segments", "sql/payer_frequency.sql"), ("clients", "sql/top_accounts.sql")):
        assert html.escape((root / query).read_text(encoding="utf-8")) in cards[slug], slug       # the SQL text itself, not only a link
    for slug, block in cards.items():
        assert "behind this chart" in block and charts.CHART_SOURCE[slug] in block, slug
    # the aggregator's proxies are method notes: after the evidence and the predictions, under their own heading
    page = dashboard.render(built, summary, tmp_path).read_text(encoding="utf-8")
    at = {slug: page.index(f'src="{slug}.png"') for slug in cards}
    heading, preds = page.index("Method notes: the daily aggregates"), page.index("<h2>Predictions</h2>")
    assert all(at[s] > heading > preds for s in dashboard.METHOD_NOTES)
    assert all(at[s] < preds for s in cards if s not in dashboard.METHOD_NOTES)
    assert "GET https://api.llama.fi/summary/fees/near-intents" in cards["value_capture"]


def test_dashboard_card_shows_one_sentence_and_prints_the_query(tmp_path):
    lead, rest = dashboard.split_sentence("In 2026-10, 1.38M accounts acted on NEAR (-97%). 560K of them are old. Third one.")
    assert lead == "In 2026-10, 1.38M accounts acted on NEAR (-97%)." and rest.startswith("560K of them")
    assert dashboard.split_sentence("Only one sentence at $3.58 here.") == ("Only one sentence at $3.58 here.", "")
    sql = charts.Chart("population", "t", "One. Two.", "m", source="sql/account_age.sql")
    api = charts.Chart("intents", "t", "One.", "m")
    page = dashboard.render([sql, api], {"first_date": "a", "last_date": "b", "days": 1}, tmp_path).read_text(encoding="utf-8")
    assert "FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`" in page      # the SQL itself is on the page
    assert "GET https://api.llama.fi/summary/dexs/near-intents" in page                   # and the API request
    assert '<p class="lead">One.</p>' in page and "<summary>More numbers</summary><p>Two.</p>" in page
    # the page links the summary built with it, not the snapshot committed in the repository
    assert '<a href="summary.json">' in page and "blob/main/docs/summary.json" not in page


def test_summary_json_is_valid_for_strict_parsers(tmp_path):
    """A change from zero has no percentage. It must reach the file as null: NaN is not JSON, and a browser refuses the file."""
    def refuse(token):
        raise ValueError(f"{token} is not JSON")

    summary = {"first_date": "a", "last_date": "b", "days": 1,
               "x": {"pct_change": float("nan"), "ratio": float("inf"), "series": [1.5, float("nan")], "n": 3}}
    dashboard.render([], summary, tmp_path)
    written = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"), parse_constant=refuse)
    assert written["x"] == {"pct_change": None, "ratio": None, "series": [1.5, None], "n": 3}
    assert math.isnan(summary["x"]["pct_change"])                    # the summary in memory is left as it was
    root = Path(__file__).resolve().parent.parent
    for committed in ("docs/summary.json", "data/snapshot/thesis_summary.json"):
        json.loads((root / committed).read_text(encoding="utf-8"), parse_constant=refuse)


def test_dashboard_reads_on_a_phone_and_names_what_was_measured(tmp_path):
    """Long links wrap, a chart opens at full size, and a scored prediction shows its value in the unit of its statement."""
    def item(pid, metric, status, measured):
        return {"id": pid, "check_on": "2026-11-17", "statement": "s", "metric": metric, "status": status, "measured": measured}

    pred = {"data_through": "2026-11-18", "items": [
        item("A1", "intents_volume_7d_mean_usd", "held", 113846395.71), item("A3", "buyback_month_usd", "held", 1724014.0),
        item("A4", "buyback_coverage_90d", "held", 0.146), item("A5", "metrics_with_adjacent_positive_leads", "held", 0.0),
        item("B1", "regular_self_paying_accounts_2027_01", "held", 17105.0),
        item("B2", "core_self_paid_txs_mean_2026_11_to_2027_01", "failed", 9876543.0),
        item("B4", "reward_minus_finance_tx_share_2027_01", "held", 0.0199), item("B3", "accounts_for_half_of_txs_2027_01", "open", None)]}
    card = charts.Chart("population", "t", "One. Two.", "m", source="sql/account_age.sql")
    page = dashboard.render([card], {"first_date": "a", "last_date": "b", "days": 1, "predictions": pred}, tmp_path).read_text(encoding="utf-8")
    assert '<a href="population.png"' in page and '<img src="population.png"' in page and "overflow-wrap:anywhere" in page
    for shown in ("<b>held</b> ($113.8M a day)", "<b>held</b> ($1.72M)", "<b>held</b> (15% of net new supply)", "<b>held</b> (0)",
                  "<b>held</b> (17,105)", "<b>failed</b> (9.88M a month)", "<b>held</b> (+2.0 points of all transactions)",
                  "<b>open</b></td>"):
        assert shown in page, shown


def test_the_page_names_the_date_of_the_frozen_snapshot_and_every_source():
    """The subtitle quotes the snapshot's date, and the Sources card lists what the hand-run commands read as well."""
    from thesis import __main__ as cli
    from thesis import census, value
    root = Path(__file__).resolve().parent.parent
    frozen = json.loads((root / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))
    assert dashboard.SNAPSHOT == frozen["last_date"]
    page = (root / "docs" / "index.html").read_text(encoding="utf-8")
    for url in (*sources.SOURCES.values(), *value.URLS.values(), census.RPC_URL, census.TX_URL, census.BLOCK_URL):
        assert html.escape(url) in page, url
    # figures that combine two query results are computed only while both compare the same months
    a = {"latest_month": "2026-10", "prior_month": "2025-10"}
    assert cli.same_months(a, dict(a)) and not cli.same_months(a, {"latest_month": "2027-01", "prior_month": "2026-01"})
    assert not cli.same_months(a, {"latest_month": "2026-10", "prior_month": "2025-09"})
    assert "not_combined_with" not in frozen["clients"]            # today all the results compare October with October


def test_one_sentence_takeaways_follow_the_data():
    """The dashboard is rebuilt every day for months: a sentence that was true on the day it was written must not stay when it stops being true."""
    s = {"yoy_90d": {"returning_accounts": {"pct_change": 37.0}},
         "population": {"segments": {"core": {"returning_accounts": {"pct_change": -73.0}}}},
         "month_yoy": {"intents_volume_usd": {"month": "2026-10", "recent": 128.6e6, "pct_change": 131.0}},
         "predictions": {"step": {"reference_range": {"first": "2025-12", "last": "2026-08"},
                                  "intents_volume_usd_a_day": {"range_low": 63.2e6, "range_top": 89.6e6}}}}
    assert charts._takeaway("accounts", s) == "The usual proxy for returning accounts points the wrong way."
    s["yoy_90d"]["returning_accounts"]["pct_change"] = -5.0          # the proxy turns negative as its base rises
    assert charts._takeaway("accounts", s) == "The usual proxy for returning accounts is not a count of them."
    above = "In 2026-10 NEAR Intents volume averaged $129M a day, above the $63M to $90M range it held from 2025-12 to 2026-08."
    assert charts._takeaway("intents", s) == above
    s["month_yoy"]["intents_volume_usd"]["recent"] = 70e6
    assert ", inside the $63M to $90M range" in charts._takeaway("intents", s)
    s["month_yoy"]["intents_volume_usd"]["recent"] = 50e6
    assert ", below the $63M to $90M range" in charts._takeaway("intents", s)
    del s["predictions"]
    assert charts._takeaway("intents", s) == "NEAR Intents volume changed +131% against the same month a year earlier."
