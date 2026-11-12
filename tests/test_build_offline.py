"""End-to-end: synthetic raw files -> charts + dashboard, no network."""
import json

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
    # every chart links the query or code behind it, and the page links the thesis
    assert html.count("Query / code:") == len(built) and "blob/main/THESIS.md" in html and "sql/account_age.sql" in html
