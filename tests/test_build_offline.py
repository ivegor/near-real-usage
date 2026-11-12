"""End-to-end: synthetic raw files -> charts + dashboard, no network."""
import json

from thesis import charts, dashboard, metrics, sources

from .test_metrics import synthetic_raw


def test_full_build(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    nb, ll = synthetic_raw()
    (raw / "nearblocks_charts.json").write_text(json.dumps(nb))
    (raw / "defillama_intents.json").write_text(json.dumps(ll))
    monkeypatch.setattr(sources, "RAW_DIR", raw)

    daily = sources.load_daily(offline=True)
    summary = metrics.summarize(daily)
    out = tmp_path / "docs"
    built = charts.build_all(daily, summary, out)
    page = dashboard.render(built, summary, out)

    assert len(built) == 6
    for c in built:
        assert (out / f"{c.slug}.png").stat().st_size > 5_000
        assert "nan" not in c.sentence.lower()
    html = page.read_text()
    assert "NEAR Real Usage" in html and "lead_lag.png" in html
