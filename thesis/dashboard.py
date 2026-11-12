"""Static dashboard: docs/index.html (GitHub Pages-ready). Each chart shows its method and one sentence."""
from __future__ import annotations

import html
import json
from pathlib import Path

from .charts import Chart
from .sources import SOURCES


REPO_URL = "https://github.com/ivegor/near-real-usage"
SNAPSHOT = "2026-11-11"  # THESIS.md quotes the numbers as of this date; the page itself is rebuilt daily


def _repo_link(path: str) -> str:
    return f'<a href="{REPO_URL}/blob/main/{html.escape(path)}"><code>{html.escape(path)}</code></a>'


def render(charts: list[Chart], summary: dict, out: Path) -> Path:
    cards = []
    for c in charts:
        query = f'<br><b>Query / code:</b> {_repo_link(c.source)}' if c.source else ""
        cards.append(f"""
<section class="card">
  <h2>{html.escape(c.title)}</h2>
  <p class="lead">{html.escape(c.sentence)}</p>
  <img src="{c.slug}.png" alt="{html.escape(c.title)}">
  <p class="method"><b>Method:</b> {html.escape(c.method)}{query}</p>
</section>""")
    src = "".join(f'<li><code>{html.escape(k)}</code>: <a href="{html.escape(v)}">{html.escape(v)}</a></li>' for k, v in SOURCES.items())
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
<p class="sub">Daily data {summary['first_date']} → {summary['last_date']} ({summary['days']} days); account census through
{html.escape(summary.get('population', {}).get('query_end', 'n/a'))}. Rebuilt daily by <code>python -m thesis build</code>.
The argument: {_repo_link('THESIS.md')} (its numbers are a snapshot as of {SNAPSHOT}; the daily figures on this page move on).
Code and data: <a href="{REPO_URL}">{REPO_URL.split('//')[1]}</a>.</p>
{''.join(cards)}
<section class="card"><h2>Sources</h2><ul>{src}
<li><code>bigquery</code>: NEAR public dataset <code>bigquery-public-data.crypto_near_mainnet_us</code>, queries in {_repo_link('sql/account_age.sql')}, {_repo_link('sql/top_accounts.sql')} and {_repo_link('sql/one_day_actions.sql')}; results in <code>data/bq/</code></li></ul>
<p class="method">Raw API responses are committed in <code>data/raw/</code>; every number on this page is in {_repo_link('docs/summary.json')}.</p></section>
</body></html>"""
    out.mkdir(parents=True, exist_ok=True)
    p = out / "index.html"
    p.write_text(page)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    return p
