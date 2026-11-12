"""CLI: `python -m thesis build [--offline]` rebuilds every chart from raw data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import census, charts, clients, dashboard, metrics, population, sources

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"


def build(offline: bool) -> None:
    daily = sources.load_daily(offline=offline)
    daily.to_csv(ROOT / "data" / "daily.csv")
    summary = metrics.summarize(daily)
    cs = census.load()
    if cs:
        summary["signer_census"] = census.summarize(*cs)
    pop = population.load()
    if pop is not None:
        summary["population"] = population.summarize(pop)
        day = population.one_day(daily)
        if day:
            summary["population"]["one_day"] = day
    top = clients.load()
    if top:
        summary["clients"] = clients.summarize(top)
    built = charts.build_all(daily, summary, DOCS)
    page = dashboard.render(built, summary, DOCS)
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nDashboard: {page}")
    for c in built:
        print(f"- {c.title}: {c.sentence}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="thesis")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="fetch data, compute metrics, render charts + dashboard")
    b.add_argument("--offline", action="store_true", help="use cached data/raw/*.json")
    c = sub.add_parser("census", help="sample blocks from the chain and measure account ages (network, ~1.5 h, resumable)")
    c.add_argument("--seed", type=int, default=census.SEED, help="another seed draws an independent sample")
    pn = sub.add_parser("panel", help="the same census for every month (network, hours, resumable)")
    pn.add_argument("--first-month", default="2025-07")
    pn.add_argument("--seed", type=int, default=census.SEED)
    sub.add_parser("firstseen", help="look up the first transaction of every sampled account (network, resumable)")
    ba = sub.add_parser("bq-age", help="unpack a BigQuery result of sql/account_age.sql into data/bq/account_age.csv")
    ba.add_argument("result_csv", help="the result saved from the BigQuery console as CSV (columns m, cells)")
    args = ap.parse_args()
    if args.cmd == "bq-age":
        df = population.unpack(Path(args.result_csv))
        print(f"{len(df)} rows, months {df['month'].min()} .. {df['month'].max()} -> {population.CSV}")
        return
    if args.cmd == "firstseen":
        census.fetch_first_seen()
        return
    if args.cmd == "panel":
        last_date = str(sources.load_daily(offline=True).index.max().date())
        census.fetch_panel(args.first_month, last_date, seed=args.seed)
        return
    if args.cmd == "build":
        build(args.offline)
    elif args.cmd == "census":
        last_date = str(sources.load_daily(offline=True).index.max().date())
        census.fetch(last_date, seed=args.seed)
        print(json.dumps(census.summarize(*census.load()), indent=2))


if __name__ == "__main__":
    main()
