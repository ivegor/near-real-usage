"""CLI: `python -m thesis build [--offline]` rebuilds every chart from raw data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import census, charts, clients, dashboard, metrics, payers, population, predictions, segments, sources, value

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
# THESIS.md quotes this copy of the summary. `build` never writes it, so a rebuild on newer data cannot make the
# text and its test disagree; refresh it on purpose with `python -m thesis snapshot` when the text is rewritten.
SNAPSHOT = ROOT / "data" / "snapshot" / "thesis_summary.json"


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
    seg = segments.load()
    if seg is not None:
        summary["segments"] = segments.summarize(seg)
    pay = payers.load()
    if pay is not None:
        summary["sponsors"] = payers.summarize(pay)  # sponsored accounts named by the app whose relayer paid
    top = clients.load()
    if top:
        summary["clients"] = clients.summarize(top)
        if pop is not None:
            clients.add_namespace_view(summary["clients"], summary["population"]["segments"]["kaiching"]["txs"]["latest"])
    if not offline:
        try:
            value.fetch()  # keep the fee and buyback series current; fall back to the saved copies on an outage
        except RuntimeError as e:
            print(f"[value] {e}; using the saved copies")
    fees = value.load()
    pred = predictions.evaluate(daily, fees)
    if pred:
        pred["baselines"] = predictions.baselines(daily, fees, pop, seg)
        summary["predictions"] = pred
    if fees is not None:
        v = value.summarize(daily, fees)
        if v:
            summary["value_capture"] = v
    if cs and pop is not None:
        summary["cross_check"] = population.cross_check(summary["signer_census"], pop, summary.get("clients"))
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
    ba = sub.add_parser("bq-age", help="unpack a BigQuery result of sql/account_age.sql into data/bq/account_age.csv")
    ba.add_argument("result_csv", help="the result saved from the BigQuery console as CSV (columns m, cells)")
    bf = sub.add_parser("bq-freq", help="unpack a BigQuery result of sql/payer_frequency.sql into data/bq/payer_frequency.csv")
    bf.add_argument("result_csv", help="the result saved from the BigQuery console as CSV (columns m, cells)")
    sub.add_parser("snapshot", help="freeze docs/summary.json as the copy THESIS.md is checked against")
    sub.add_parser("video", help="render demo/near-real-usage.mp4 from the build outputs (needs ffmpeg)")
    sub.add_parser("fetch-value", help="download the NEAR Intents fee and buyback series from DefiLlama into data/raw/")
    args = ap.parse_args()
    if args.cmd == "snapshot":
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text((DOCS / "summary.json").read_text())
        print(SNAPSHOT)
        return
    if args.cmd == "video":
        from . import video
        print(video.build())
        return
    if args.cmd == "fetch-value":
        value.fetch()
        return
    if args.cmd == "bq-age":
        df = population.unpack(Path(args.result_csv))
        print(f"{len(df)} rows, months {df['month'].min()} .. {df['month'].max()} -> {population.CSV}")
        return
    if args.cmd == "bq-freq":
        df = segments.unpack(Path(args.result_csv))
        print(f"{len(df)} rows, months {df['month'].min()} .. {df['month'].max()} -> {segments.CSV}")
        return
    if args.cmd == "build":
        build(args.offline)
    elif args.cmd == "census":
        last_date = str(sources.load_daily(offline=True).index.max().date())
        census.fetch(last_date, seed=args.seed)
        print(json.dumps(census.summarize(*census.load()), indent=2))


if __name__ == "__main__":
    main()
