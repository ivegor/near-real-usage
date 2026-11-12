"""Static dashboard: docs/index.html (GitHub Pages-ready). Each chart shows its method and one sentence."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .charts import Chart
from .sources import SOURCES


def render(charts: list[Chart], summary: dict, out: Path, bq_note: str | None = None) -> Path:
    cards = []
    for c in charts:
        cards.append(f"""
<section class="card">
  <h2>{html.escape(c.title)}</h2>
  <p class="lead">{html.escape(c.sentence)}</p>
  <img src="{c.slug}.png" alt="{html.escape(c.title)}">
  <p class="method"><b>Method:</b> {html.escape(c.method)}</p>
</section>""")
    src = "".join(f'<li><code>{html.escape(k)}</code>: <a href="{html.escape(v)}">{html.escape(v)}</a></li>' for k, v in SOURCES.items())
    bq = f'<section class="card"><h2>BigQuery cross-check</h2><p>{html.escape(bq_note)}</p></section>' if bq_note else ""
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEAR Real Usage: evidence dashboard</title>
<style>
body{{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#1f2328;max-width:900px;margin:0 auto;padding:24px}}
h1{{font-size:24px;margin:0 0 4px}} .sub{{color:#57606a;margin:0 0 24px}}
.card{{border:1px solid #e6e8eb;border-radius:10px;padding:16px 18px;margin:0 0 18px}}
.card h2{{font-size:17px;margin:0 0 6px}} .lead{{margin:0 0 10px}}
img{{width:100%;height:auto}} .method{{color:#57606a;font-size:13px;margin:8px 0 0}}
code{{background:#f6f8fa;padding:1px 4px;border-radius:4px}}
</style></head><body>
<h1>NEAR Real Usage</h1>
<p class="sub">Data {summary['first_date']} → {summary['last_date']} ({summary['days']} days). Rebuilt by <code>python -m thesis build</code>. Thesis: see THESIS.md in the repo.</p>
{''.join(cards)}
{bq}
<section class="card"><h2>Sources</h2><ul>{src}</ul>
<p class="method">Raw responses are committed in <code>data/raw/</code>; summary numbers in <code>docs/summary.json</code>.</p></section>
</body></html>"""
    out.mkdir(parents=True, exist_ok=True)
    p = out / "index.html"
    p.write_text(page)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return p
