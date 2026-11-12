"""THESIS.md is a snapshot: the numbers it quotes must be the ones in the committed docs/summary.json."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def M(v):  # 9751032 -> "9.75M"
    return f"{v / 1e6:.2f}M"


def pct(v):  # -65.8 -> "−66%"
    return f"{'+' if v > 0 else '−'}{abs(v):.0f}%"


def test_thesis_quotes_the_committed_summary():
    s = json.loads((ROOT / "docs" / "summary.json").read_text())
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
        f"${s['value_capture']['buyback_usd_annualized'] / 1e6:.1f}M a year",
        f"**Buybacks cover {s['value_capture']['buyback_coverage_of_new_supply'] * 100:.0f}% of dilution.**",
        f"{s['value_capture']['growth_needed_to_cover_new_supply']:.1f} times the captured revenue",
        f"{sum(w['blocks_found'] for w in s['signer_census']['windows'].values())} random blocks",
        f"each of the {sum(w['accounts'] for w in s['signer_census']['windows'].values()):,} accounts",
    ]
    missing = [q for q in quoted if q not in text]
    assert not missing, f"THESIS.md does not quote these summary.json values: {missing}"
