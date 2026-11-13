"""End-to-end: synthetic raw files -> charts + dashboard, no network."""
import html
import json
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
    html = page.read_text()
    assert "NEAR Real Usage" in html and "lead_lag.png" in html
    # every card prints the request or query behind its chart on the page itself, and the page links the thesis
    assert html.count("behind this chart") == len(built) and "GET https://api.nearblocks.io/v1/charts" in html
    assert html.count('<p class="lead">') == len(built) and "blob/main/THESIS.md" in html and "sql/account_age.sql" in html


def test_every_card_of_the_real_dashboard_prints_its_query(tmp_path):
    """Built from the committed data, every card carries the query or the requests behind its chart."""
    root = Path(__file__).resolve().parent.parent
    daily = sources.load_daily(offline=True)
    summary = json.loads((root / "docs" / "summary.json").read_text())
    built = charts.build_all(daily, summary, tmp_path)
    cards = {c.slug: dashboard.query_block(c) for c in built}
    assert list(cards)[:4] == ["population", "segments", "clients", "value_capture"] and len(cards) == 11
    for slug, query in (("population", "sql/account_age.sql"), ("segments", "sql/payer_frequency.sql"), ("clients", "sql/top_accounts.sql")):
        assert html.escape((root / query).read_text()) in cards[slug], slug       # the SQL text itself, not only a link
    for slug, block in cards.items():
        assert "behind this chart" in block and charts.CHART_SOURCE[slug] in block, slug
    assert "GET https://api.llama.fi/summary/fees/near-intents" in cards["value_capture"]


def test_dashboard_card_shows_one_sentence_and_prints_the_query(tmp_path):
    lead, rest = dashboard.split_sentence("In 2026-10, 1.38M accounts acted on NEAR (-97%). 560K of them are old. Third one.")
    assert lead == "In 2026-10, 1.38M accounts acted on NEAR (-97%)." and rest.startswith("560K of them")
    assert dashboard.split_sentence("Only one sentence at $3.58 here.") == ("Only one sentence at $3.58 here.", "")
    sql = charts.Chart("population", "t", "One. Two.", "m", source="sql/account_age.sql")
    api = charts.Chart("intents", "t", "One.", "m")
    page = dashboard.render([sql, api], {"first_date": "a", "last_date": "b", "days": 1}, tmp_path).read_text()
    assert "FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`" in page      # the SQL itself is on the page
    assert "GET https://api.llama.fi/summary/dexs/near-intents" in page                   # and the API request
    assert '<p class="lead">One.</p>' in page and "<summary>More numbers</summary><p>Two.</p>" in page
    # the page links the summary built with it, not the snapshot committed in the repository
    assert '<a href="summary.json">' in page and "blob/main/docs/summary.json" not in page
