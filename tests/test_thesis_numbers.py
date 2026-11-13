"""THESIS.md is a snapshot: the numbers it quotes must be the ones in data/snapshot/thesis_summary.json.

That file is a frozen copy of the summary (`python -m thesis snapshot`). The build rewrites docs/summary.json
every day; it never touches the snapshot, so this test keeps passing after a rebuild on newer data.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def M(v):  # 9751032 -> "9.75M"
    return f"{v / 1e6:.2f}M"


def pct(v):  # -65.8 -> "−66%"
    return f"{'+' if v > 0 else '−'}{abs(v):.0f}%"


def test_thesis_quotes_the_committed_summary():
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text())
    text = (ROOT / "THESIS.md").read_text()
    p, c, d = s["population"], s["clients"], s["population"]["one_day"]
    seg = p["segments"]
    core, near = seg["core"], seg["near"]
    three = core["three_month_mean"]
    latest, prior = c["months"][c["latest_month"]], c["months"][c["prior_month"]]
    intents = s["month_yoy"]["intents_volume_usd"]
    fees = s["yoy_90d"]["fees_usd"]
    n_out = sum(len(v["outside_band"]) for v in s["lead_vs_price"].values())
    quoted = [
        f"{core['accounts']['prior']:,.0f} → {core['accounts']['latest']:,.0f}",
        f"({pct(core['accounts']['pct_change'])}; {pct(three['accounts']['pct_change'])})",
        f"{core['returning_accounts']['prior']:,.0f} → {core['returning_accounts']['latest']:,.0f}",
        f"({pct(core['returning_accounts']['pct_change'])}; {pct(three['returning_accounts']['pct_change'])})",
        f"{M(core['direct_txs']['prior'])} → {M(core['direct_txs']['latest'])}",
        f"({pct(core['direct_txs']['pct_change'])}; {pct(three['direct_txs']['pct_change'])})",
        f"{M(core['relayed_txs']['prior'])} → {M(core['relayed_txs']['latest'])}",
        f"({pct(core['relayed_txs']['pct_change'])}; {pct(three['relayed_txs']['pct_change'])})",
        f"{core['txs_per_account']['prior']:.1f} → {core['txs_per_account']['latest']:.1f}",
        f"{p['core_txs_per_account_at_prior_mix']:.1f} at last year's mix",
        f"{near['multi_tx_accounts']['prior']:,.0f} to {near['multi_tx_accounts']['latest']:,.0f}",
        f"between {near['accounts_range_12m']['min']:,.0f} and {near['accounts_range_12m']['max']:,.0f}",
        f"{p['reward_apps_share_of_lost']['accounts'] * 100:.1f}% of the accounts lost",
        f"{p['reward_apps_share_of_lost']['txs'] * 100:.1f}% of the transactions lost",
        f"{p['kaiching_one_off']['accounts']:,} single-transaction accounts",
        f"send {p['sweat_share_of_all_txs'] * 100:.1f}% of all transactions",
        f"{p['partial_month']['accounts']['tg']:,}",
        f"({p['partial_month']['latest_complete_accounts']['tg']:,})",
        f"{d['transactions']:,} transactions", f"({d['relayed_transactions']:,})", f"{d['relayed_users']:,} users",
        f"{d['nearblocks']['active_accounts']:,} active accounts", f"{d['create_account_transactions']:,} accounts were created",
        f"{d['nearblocks']['new_accounts']:,} new accounts",
        f"{M(c['finance_txs']['prior'])} → {M(c['finance_txs']['latest'])} a month ({pct(c['finance_txs']['pct_change'])})",
        f"{latest['accounts_for_half_of_txs']} accounts send 50% of transactions",
        f"the top 10 send {latest['top10_share'] * 100:.0f}% ({prior['top10_share'] * 100:.0f}% a year earlier)",
        f"${intents['prior'] / 1e6:.1f}M → ${intents['recent'] / 1e6:.1f}M a day ({pct(intents['pct_change'])}",
        f"${fees['prior']:,.0f} → ${fees['recent']:,.0f} a day",
        f"{n_out} of {17 * len(s['lead_vs_price'])} lag tests",
        f"{s['sponsors']['month']['sponsored_by_sweat']['prior']:,.0f} → {s['sponsors']['month']['sponsored_by_sweat']['latest']:,.0f}",
        f"Ember {s['sponsors']['month']['sponsored_by_ember']['prior']:,.0f} → {s['sponsors']['month']['sponsored_by_ember']['latest']:,.0f}",
        f"{s['segments']['metrics']['regular_accounts']['prior']:,.0f} → {s['segments']['metrics']['regular_accounts']['latest']:,.0f}",
        f"{s['segments']['metrics']['heavy_accounts']['prior']:,.0f} → {s['segments']['metrics']['heavy_accounts']['latest']:,.0f}",
        f"{s['segments']['metrics']['sponsored_accounts']['prior']:,.0f} → {s['segments']['metrics']['sponsored_accounts']['latest']:,.0f}",
        f"low of {s['segments']['regular_accounts_low']['value']:,.0f} in August 2026",
        f"{pct(s['population']['core_direct_txs_change_by_window']['6'])} (six months), {pct(s['population']['core_direct_txs_change_by_window']['9'])} (nine)",
        f"{s['clients']['kaiching_txs_outside_its_contracts']:,.0f} transactions, one each",
        f"${s['value_capture']['buyback_usd_annualized'] / 1e6:.1f}M a year",
        f"**Buybacks cover {s['value_capture']['buyback_coverage_of_new_supply'] * 100:.0f}% of dilution.**",
        f"{s['value_capture']['growth_needed_to_cover_new_supply']:.1f} times the captured revenue",
        f"{sum(w['blocks_found'] for w in s['signer_census']['windows'].values())} random blocks",
        f"each of the {sum(w['accounts'] for w in s['signer_census']['windows'].values()):,} accounts",
    ]
    missing = [q for q in quoted if q not in text]
    assert not missing, f"THESIS.md does not quote these summary.json values: {missing}"


def test_thesis_names_the_snapshot_date():
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text())
    assert f"Snapshot as of {s['last_date']}" in (ROOT / "THESIS.md").read_text()
