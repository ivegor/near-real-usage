"""CLI: `python -m thesis build [--offline]` rebuilds every chart from raw data."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import census, charts, clients, dashboard, metrics, payers, population, predictions, segments, sources, value, wallets

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
# THESIS.md quotes this copy of the summary. `build` never writes it, so a rebuild on newer data cannot make the
# text and its test disagree; refresh it on purpose with `python -m thesis snapshot` when the text is rewritten.
SNAPSHOT = ROOT / "data" / "snapshot" / "thesis_summary.json"


def build(offline: bool, require_fresh: bool = False) -> None:
    daily = sources.load_daily(offline=offline)
    stale = [] if offline else list(sources.NOT_REFRESHED)  # sources read from their saved copies because a download failed
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
        totals = population.totals_check(pop, daily)  # BigQuery month by month against the aggregator
        if totals:
            summary["population"]["totals_check"] = totals
        fall = population.largest_daily_fall(pop, daily)  # the step other analyses see in the daily series, named
        if fall:
            summary["population"]["largest_daily_fall"] = fall
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
            kaiching = summary["population"]["segments"]["kaiching"]["txs"]
            clients.add_namespace_view(summary["clients"], kaiching["latest"])
            clients.add_three_parts(summary["clients"], kaiching["prior"])
        if cs:  # the same groups and the reward game on the keyless sample
            summary["clients"]["reward_game"]["sample_calls"] = census.calls_to(cs[0], clients.GAME_CONTRACT)
            # how many of those calls are reward claims, and how many of the claims arrive as a batch run by the app
            summary["clients"]["reward_game"]["sample_claims"] = census.batched_calls(
                cs[0], clients.GAME_RELAYER.split(":", 1)[1], clients.GAME_CLAIM)
            # the one-off of October 2026: what the old KaiChing user accounts in the sample actually sent
            summary["clients"]["kaiching_accounts_sample"] = census.self_deletions(cs[0], ".users.kaiching")
            ended = census.load_outcomes()  # how the sampled transactions to NEAR Intents ended, by sender
            if ended is not None and len(ended):
                summary["clients"]["intents_outcomes"] = census.outcomes(ended)
            view = clients.sample_view(cs[0], cs[2].get("windows", {}), daily, seed=cs[2].get("seed", census.SEED))
            if view:
                summary["clients"]["sample_view"] = view
        if seg is not None:
            segments.add_reward_game_bound(summary["segments"], summary["clients"]["reward_game"])
    if not offline:
        try:
            value.fetch()  # keep the fee and buyback series current; fall back to the saved copies on an outage
        except RuntimeError as e:
            print(f"[value] {e}; using the saved copies")
            stale += list(value.URLS)
    if require_fresh and stale:
        # The scheduled build starts from the committed copies every day. Falling back to them would publish a page
        # that is days or months old; failing here leaves the page of the last good run in place instead.
        raise SystemExit(f"not refreshed: {', '.join(stale)}. With --require-fresh nothing is built from saved copies.")
    fees = value.load()
    pred = predictions.evaluate(daily, fees, census=pop, seg=seg, top=top)
    if pred:
        pred["baselines"] = predictions.baselines(daily, fees, pop, seg)
        pred["step"] = predictions.step(daily, fees, pop, seg)  # what moved in the step month, the price included
        summary["predictions"] = pred
    if fees is not None:
        v = value.summarize(daily, fees)
        if v:
            summary["value_capture"] = v
            held = wallets.load()  # the same revenue measured from the wallets' balances on the chain
            w = wallets.summarize(held, daily, fees) if held else None
            if w:
                summary["value_capture"]["wallets"] = w
    if cs and pop is not None:
        summary["cross_check"] = population.cross_check(summary["signer_census"], pop, summary.get("clients"))
    built = charts.build_all(daily, summary, DOCS)
    page = dashboard.render(built, summary, DOCS)
    print(dashboard.summary_json(summary))
    print(f"\nDashboard: {page}")
    for c in built:
        print(f"- {c.title}: {c.sentence}")


def main() -> None:
    ap = argparse.ArgumentParser(prog="thesis")
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="fetch data, compute metrics, render charts + dashboard")
    b.add_argument("--offline", action="store_true", help="use cached data/raw/*.json")
    b.add_argument("--require-fresh", action="store_true",
                   help="fail instead of falling back to a saved copy when a source cannot be downloaded")
    c = sub.add_parser("census", help="sample blocks from the chain and measure account ages (network, ~1.5 h, resumable)")
    c.add_argument("--seed", type=int, default=census.SEED, help="another seed draws an independent sample")
    ba = sub.add_parser("bq-age", help="unpack a BigQuery result of sql/account_age.sql into data/bq/account_age.csv")
    ba.add_argument("result_csv", help="the result saved from the BigQuery console as CSV (columns m, cells)")
    bf = sub.add_parser("bq-freq", help="unpack a BigQuery result of sql/payer_frequency.sql into data/bq/payer_frequency.csv")
    bf.add_argument("result_csv", help="the result saved from the BigQuery console as CSV (columns m, cells)")
    sub.add_parser("snapshot", help="freeze docs/summary.json as the copy THESIS.md is checked against")
    sub.add_parser("video", help="render demo/near-real-usage.mp4 from the build outputs (needs ffmpeg)")
    sub.add_parser("fetch-value", help="download the NEAR Intents fee and buyback series from DefiLlama into data/raw/")
    sub.add_parser("wallets", help="read the balances of NEAR's three revenue wallets from an archival RPC node (network, ~2 min)")
    sub.add_parser("outcomes", help="ask a transaction index how the sampled transactions to NEAR Intents ended (network, ~5 min)")
    args = ap.parse_args()
    if args.cmd == "snapshot":
        SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
        SNAPSHOT.write_text((DOCS / "summary.json").read_text(encoding="utf-8"), encoding="utf-8")
        print(SNAPSHOT)
        return
    if args.cmd == "video":
        from . import video
        print(video.build())
        return
    if args.cmd == "fetch-value":
        value.fetch()
        return
    if args.cmd == "wallets":
        wallets.fetch(str(sources.load_daily(offline=True).index.max().date()))
        print(wallets.PATH)
        return
    if args.cmd == "outcomes":
        census.fetch_outcomes(clients.INTENTS_CONTRACT)
        print(json.dumps(census.outcomes(census.load_outcomes()), indent=2))
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
        build(args.offline, require_fresh=args.require_fresh)
    elif args.cmd == "census":
        last_date = str(sources.load_daily(offline=True).index.max().date())
        census.fetch(last_date, seed=args.seed)
        print(json.dumps(census.summarize(*census.load()), indent=2))


if __name__ == "__main__":
    main()
