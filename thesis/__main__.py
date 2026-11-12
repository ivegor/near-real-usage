"""CLI: `python -m thesis build [--offline] [--bq]` rebuilds every chart from raw data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import bq, charts, dashboard, metrics, sources

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def build(offline: bool, use_bq: bool) -> None:
    daily = sources.load_daily(offline=offline)
    daily.to_csv(ROOT / "data" / "daily.csv")
    summary = metrics.summarize(daily)
    bq_note = bq.run() if use_bq else None
    if bq_note:
        summary["bigquery"] = bq_note
    built = charts.build_all(daily, summary, DOCS)
    page = dashboard.render(built, summary, DOCS, bq_note)
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nDashboard: {page}")
    for c in built:
        print(f"- {c.title}: {c.sentence}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="thesis")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="fetch data, compute metrics, render charts + dashboard")
    b.add_argument("--offline", action="store_true", help="use cached data/raw/*.json")
    b.add_argument("--bq", action="store_true", help="also run the optional BigQuery cross-check")
    args = ap.parse_args()
    if args.cmd == "build":
        build(args.offline, args.bq)


if __name__ == "__main__":
    main()
