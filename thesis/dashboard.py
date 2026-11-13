"""Static dashboard: docs/index.html (GitHub Pages-ready).

Each card shows the chart, one plain sentence, the method, and the query behind it printed on the page itself
(the SQL text, or the API request for charts built from the daily aggregates), so nothing depends on a link.
"""
from __future__ import annotations

import html
import json
import math
import re
from pathlib import Path

from . import census, value
from .charts import Chart
from .sources import SOURCES

ROOT = Path(__file__).resolve().parent.parent
NEARBLOCKS, DEFILLAMA = SOURCES["nearblocks_charts"], SOURCES["defillama_intents"]
# Charts that are not built from a SQL file: the requests they are computed from.
REQUESTS = {
    "accounts": [NEARBLOCKS], "usage_vs_price": [NEARBLOCKS], "tx_per_active": [NEARBLOCKS], "fees_per_active": [NEARBLOCKS],
    "intents": [DEFILLAMA, NEARBLOCKS], "lead_lag": [NEARBLOCKS, DEFILLAMA],
    "value_capture": [*value.URLS.values(), NEARBLOCKS,
                      f"{census.RPC_URL}  (JSON-RPC query view_account and wrap.near ft_balance_of at a past block)"],
    "signer_census": [census.BLOCK_URL, f"{census.RPC_URL}  (JSON-RPC query view_account at a past block)"],
}


REPO_URL = "https://github.com/ivegor/near-real-usage"
SNAPSHOT = "2026-11-11"  # THESIS.md quotes the numbers as of this date; the page itself is rebuilt daily


def _repo_link(path: str) -> str:
    return f'<a href="{REPO_URL}/blob/main/{html.escape(path)}"><code>{html.escape(path)}</code></a>'


def json_safe(obj):
    """A copy with every NaN and infinity replaced by None, so that the text written from it is valid JSON."""
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_safe(v) for v in obj]
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def summary_json(summary: dict) -> str:
    """The summary as JSON text. A change from zero has no percentage; Python would write it as NaN, which is not
    JSON (a browser, Node or a strict parser refuses the whole file), so it is written as null."""
    return json.dumps(json_safe(summary), indent=2, default=str, allow_nan=False)


def measured_text(p: dict) -> str:
    """What a scored prediction was measured at, in the unit its statement uses."""
    v, metric = p.get("measured"), str(p.get("metric", ""))
    if v is None:
        return ""
    if metric.startswith("intents_volume"):
        return f"${v / 1e6:,.1f}M a day"
    if metric.startswith("buyback_month"):
        return f"${v / 1e6:,.2f}M"
    if metric.startswith("buyback_coverage"):
        return f"{v * 100:.0f}% of net new supply"
    if metric.startswith("core_self_paid_txs"):
        return f"{v / 1e6:,.2f}M a month"
    if metric.startswith("reward_minus_finance"):
        return f"{v * 100:+.1f} points of all transactions"
    return f"{v:,.0f}"


def split_sentence(text: str) -> tuple[str, str]:
    """The first sentence (shown as the card's one plain sentence) and the rest (folded under "More numbers")."""
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9$])", text.strip(), maxsplit=1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def query_block(c: Chart) -> str:
    """The query behind a chart, printed on the page: SQL text for BigQuery charts, the API requests otherwise."""
    path = ROOT / c.source if c.source else None
    if path and path.suffix == ".sql" and path.exists():
        return (f'<details><summary>The query behind this chart: {_repo_link(c.source)}</summary>'
                f'<pre>{html.escape(path.read_text(encoding="utf-8"))}</pre></details>')
    requests = REQUESTS.get(c.slug, [])
    if not requests and not c.source:
        return ""
    lines = "\n".join(f"GET {u}" if u.startswith("http") and " " not in u else u for u in requests)
    code = f" Computed by {_repo_link(c.source)}." if c.source else ""
    return f'<details><summary>The requests behind this chart</summary><pre>{html.escape(lines)}</pre>{code}</details>'


def render(charts: list[Chart], summary: dict, out: Path) -> Path:
    cards = []
    for c in charts:
        lead, rest = split_sentence(c.sentence)
        more = f'<details><summary>More numbers</summary><p>{html.escape(rest)}</p></details>' if rest else ""
        cards.append(f"""
<section class="card">
  <h2>{html.escape(c.title)}</h2>
  <p class="lead">{html.escape(lead)}</p>
  <a href="{c.slug}.png" title="Open the chart at full size"><img src="{c.slug}.png" alt="{html.escape(c.title)}"></a>
  {more}
  <p class="method"><b>Method:</b> {html.escape(c.method)}</p>
  {query_block(c)}
</section>""")
    pred = summary.get("predictions")
    pred_card = ""
    if pred:
        def row(p: dict) -> str:
            measured = "" if p["measured"] is None else f" ({html.escape(measured_text(p))})"
            cells = [str(p["id"]), str(p["check_on"]), str(p["statement"])]
            return ("<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in cells)
                    + f"<td><b>{html.escape(p['status'])}</b>{measured}</td></tr>")

        trs = "".join(row(p) for p in pred["items"])
        pred_card = (f'<section class="card"><h2>Predictions</h2><p class="lead">Written on 2026-11-13, scored by the build as the '
                     f'data reaches each check date (data through {html.escape(pred["data_through"])}). Details: {_repo_link("PREDICTIONS.md")}.</p>'
                     f'<table><tr><th>Id</th><th>Check on</th><th>Prediction</th><th>Status</th></tr>{trs}</table></section>')
    src = "".join(f'<li><code>{html.escape(k)}</code>: <a href="{html.escape(v)}">{html.escape(v)}</a></li>'
                  for k, v in {**SOURCES, **value.URLS}.items())
    # the keyless chain endpoints behind the block sample and the wallet balances; read by hand-run commands, not by the build
    src += ("<li><code>fastnear</code> (no key, paced requests): block archive <code>" + html.escape(census.BLOCK_URL)
            + "</code>, archival RPC node <code>" + html.escape(census.RPC_URL) + "</code>, transaction index <code>"
            + html.escape(census.TX_URL) + "</code>; results in <code>data/raw/census_*</code> and "
            "<code>data/raw/revenue_wallets.json</code></li>")
    page = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NEAR Real Usage: evidence dashboard</title>
<style>
body{{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;color:#1f2328;max-width:900px;margin:0 auto;padding:24px}}
h1{{font-size:24px;margin:0 0 4px}} .sub{{color:#57606a;margin:0 0 24px}}
.card{{border:1px solid #e6e8eb;border-radius:10px;padding:16px 18px;margin:0 0 18px}}
.card h2{{font-size:17px;margin:0 0 6px}} .lead{{margin:0 0 10px}}
img{{width:100%;height:auto}} .method{{color:#57606a;font-size:13px;margin:8px 0 0}}
code{{background:#f6f8fa;padding:1px 4px;border-radius:4px}} a,code{{overflow-wrap:anywhere}}
details{{margin:8px 0 0;font-size:13px;color:#57606a}} summary{{cursor:pointer}}
pre{{background:#f6f8fa;border-radius:6px;padding:10px 12px;overflow-x:auto;font-size:12px;line-height:1.4;color:#1f2328}}
table{{border-collapse:collapse;font-size:13px;width:100%}} td,th{{border-top:1px solid #e6e8eb;padding:5px 8px;text-align:left;vertical-align:top}}
</style></head><body>
<h1>NEAR Real Usage</h1>
<p class="sub">Daily data {summary['first_date']} → {summary['last_date']} ({summary['days']} days); account census through
{html.escape(summary.get('population', {}).get('query_end', 'n/a'))}. Rebuilt daily by <code>python -m thesis build</code>.
The argument: {_repo_link('THESIS.md')} (its numbers are a snapshot as of {SNAPSHOT}; the daily figures on this page move on).
Code and data: <a href="{REPO_URL}">{REPO_URL.split('//')[1]}</a>.</p>
{''.join(cards)}
{pred_card}
<section class="card"><h2>Sources</h2><ul>{src}
<li><code>bigquery</code>: NEAR public dataset <code>bigquery-public-data.crypto_near_mainnet_us</code>, queries: {", ".join(_repo_link(f"sql/{q.name}") for q in sorted((ROOT / "sql").glob("*.sql")))}; results in <code>data/bq/</code></li></ul>
<p class="method">Raw API responses are committed in <code>data/raw/</code>; every number on this page is in
<a href="summary.json"><code>summary.json</code></a>, written by the same build as the page.</p></section>
</body></html>"""
    out.mkdir(parents=True, exist_ok=True)
    p = out / "index.html"
    p.write_text(page, encoding="utf-8")  # the page has arrows and minus signs: not every default encoding has them
    (out / "summary.json").write_text(summary_json(summary), encoding="utf-8")
    return p
