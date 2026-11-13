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


def prose(name):  # a file as one line of text, so that re-wrapping a paragraph cannot hide a number from the tests
    return " ".join((ROOT / name).read_text().split())


def test_thesis_quotes_the_committed_summary():
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text())
    text = prose("THESIS.md")
    p, c, d = s["population"], s["clients"], s["population"]["one_day"]
    seg = p["segments"]
    core, near = seg["core"], seg["near"]
    three = core["three_month_mean"]
    latest, prior = c["months"][c["latest_month"]], c["months"][c["prior_month"]]
    intents = s["month_yoy"]["intents_volume_usd"]
    fees = s["yoy_90d"]["fees_usd"]
    n_out = sum(len(v["outside_band"]) for v in s["lead_vs_price"].values())
    all_accounts, pay, sm = seg["all"]["accounts"], s["sponsors"]["month"], s["segments"]["metrics"]
    hot, hot_regular, independent = (sm[k] for k in ("app_namespace_self_paying_accounts", "app_namespace_regular_self_paying_accounts",
                                                      "independent_accounts"))
    hot_regular_change = f"{pct(hot_regular['pct_change'])}; {pct(hot_regular['three_month_mean']['pct_change'])}"
    # the one-off burst inside the self-paid series, and the reference level of prediction B2 with and without it
    burst, windows, monthly = p["core_direct_txs_from_dormant_implicit"], p["core_direct_txs_change_by_window"], p["core_direct_txs_monthly"]
    calm, base = burst["change_by_window_without_them"], s["predictions"]["baselines"]
    assert (burst["peak"]["month"], base["core_self_paid_txs_plateau_top_month"],
            base["core_self_paid_txs_plateau_top_without_dormant_implicit_month"]) == ("2026-02", "2026-02", "2026-06")
    # the payer table keeps the .sweat service accounts that the census leaves out
    sweat_then, sweat_now = (int(independent[k] - pay["independent_accounts"][k]) for k in ("prior", "latest"))
    main, pools = c["exchange_contracts_latest"][:2]
    assert (main["contract"], pools["contract"]) == ("v2.ref-finance.near", "dclv2.ref-labs.near")
    ember = c["ember"]
    # a reward game inside the "independent" accounts: its players paid their own fees a year ago and are relayed now
    game, bound = c["reward_game"], s["segments"]["regular_accounts_reward_game_bound"]
    direct, calls = game["direct"]["prior"], game["sample_calls"]
    assert game["direct"]["latest"] is None and calls["recent"]["relayed"] == calls["recent"]["calls"]
    counted, without = pct(bound["pct_change_as_counted"]), pct(bound["pct_change_if_all_of_them_were_regular"])
    # every transaction in three parts, and the finance group on the keyless 90-day sample
    parts, view = c["three_parts"], c["sample_view"]["groups"]["finance"]
    other, tail = parts["other_top_40_without_ember"], parts["outside_top_40_without_kaiching"]
    sample_change = f"{pct(view['pct_change'])} (95% interval {pct(view['pct_change_ci95'][0])} to {pct(view['pct_change_ci95'][1])})"
    # the step month and the price, and the monthly totals of the two sources
    step, totals = s["predictions"]["step"], p["totals_check"]
    price, short = step["price_usd"], {m: abs(v["share"]) * 100 for m, v in totals["differ"].items()}
    assert (step["month"], price["peak_since"]["date"], list(short)) == ("2026-09", "2026-10-12", ["2024-11", "2024-12", "2025-03"])
    quoted = [
        f"up to {bound['game_players_prior']:,} of last year's accounts were players of one wallet's reward game",
        f"up to {direct['accounts']:,} of them were players of Meteor's reward game",
        f"more than the whole fall of {bound['fall']:,.0f}", f"read as {bound['fall']:,.0f} users leaving",
        f"between the counted {counted} and {without} with all of the players taken out",
        f"between the counted {counted} and {without} with every player taken out",
        f"{direct['accounts']:,} accounts called the reward game", f"{direct['transactions_per_account']:.0f} times each on average",
        f"(fewer than {game['smallest_of_the_40_latest']:,} direct transactions against {direct['transactions']:,})",
        f"all {calls['recent']['calls']} calls to it in the keyless sample",
        f"{calls['prior']['calls'] - calls['prior']['relayed']} of {calls['prior']['calls']} were direct a year earlier",
        f"went {pay['sponsored_by_meteor']['prior']:,.0f} → {pay['sponsored_by_meteor']['latest']:,.0f}",
        f"({bound['share_of_prior_regular_at_most'] * 100:.0f}% of last year's {sm['regular_accounts']['prior']:,.0f})",
        f"with {direct['accounts']:,} accounts in October 2025",
        f"({c['reward_apps_share_incl_kaiching_namespace_prior'] * 100:.0f}% a year ago counted the same way)",
        f"the game Ember ({M(ember['prior'])} → {M(ember['latest'])} transactions); the other contracts are "
        f"{M(other['prior'])} → {M(other['latest'])} ({pct(other['pct_change'])})",
        f"{M(c['kaiching_txs_outside_its_contracts_prior'])} of them were sent by KaiChing's own accounts and "
        f"{M(c['kaiching_txs_outside_its_contracts'])} now are the one-off above; the rest is "
        f"{M(tail['prior'])} → {M(tail['latest'])} ({pct(tail['pct_change'])})",
        f"the reward side {M(parts['reward_side']['prior'])} → {M(parts['reward_side']['latest'])} ({pct(parts['reward_side']['pct_change'])}), "
        f"the financial group {M(parts['finance']['prior'])} → {M(parts['finance']['latest'])} ({pct(parts['finance']['pct_change'])}), "
        f"and everything else {M(parts['rest']['prior'])} → {M(parts['rest']['latest'])} ({pct(parts['rest']['pct_change'])})",
        f"the reward side fell {abs(parts['reward_side']['pct_change']):.0f}% and the rest of the chain stayed level "
        f"({pct(parts['rest']['pct_change'])})",
        f"the same group is {sample_change}",
        f"{pct(view['pct_change'])} between the two 90-day windows of the keyless sample (95% interval",
        f"(NEAR went from ${price['first_day']:.2f} to ${price['last_day']:.2f} during September)",
        f"NEAR went from ${price['first_day']:.2f} to ${price['last_day']:.2f} during September 2026, peaked at "
        f"${price['peak_since']['value']:.2f} on 12 October and was ${price['latest']['value']:.2f} on the snapshot date",
        f"Intents volume (${step['intents_volume_usd_a_day']['before'] / 1e6:.1f}M → ${step['intents_volume_usd_a_day']['month'] / 1e6:.1f}M a day)",
        f"(${step['buyback_usd']['before'] / 1e6:.2f}M → ${step['buyback_usd']['month'] / 1e6:.2f}M a month)",
        f"({M(step['core_self_paid_txs']['before'])} → {M(step['core_self_paid_txs']['month'])})",
        f"regular self-paying accounts ({step['regular_self_paying_accounts']['before']:,.0f} → {step['regular_self_paying_accounts']['month']:,.0f})",
        f"differ by at most {totals['agree']['largest_difference_txs']:,} transactions ({totals['agree']['largest_difference_share'] * 100:.3f}%) "
        f"in {totals['agree']['months']} of the {totals['months']} months",
        f"by {short['2024-11']:.1f}% in November 2024, {short['2024-12']:.1f}% in December 2024 and {short['2025-03']:.1f}% in March 2025",
        f"{c['kaiching_txs_outside_its_contracts']:,.0f} transactions to contracts outside the top 40; "
        f"{p['kaiching_one_off']['single_tx_accounts']:,} accounts sent exactly one",
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
        f"({all_accounts['prior']:,.0f} → {all_accounts['latest']:,.0f})",
        f"{pay['self_paying_accounts']['prior']:,.0f} → {pay['self_paying_accounts']['latest']:,.0f}",
        f"{p['kaiching_one_off']['single_tx_accounts']:,} old KaiChing accounts paid for one transaction each",
        f"HOT users who pay their own fees {hot['prior']:,.0f} → {hot['latest']:,.0f}",
        f"({independent['prior']:,.0f} → {independent['latest']:,.0f})",
        f"{hot_regular['prior']:,.0f} → {hot_regular['latest']:,.0f} ({hot_regular_change})",
        f"| {hot_regular['prior']:,.0f} | {hot_regular['latest']:,.0f} | {hot_regular_change} |",
        f"the regular ones among them {abs(hot_regular['pct_change']):.0f}%",
        f"({pct(calm['9'])} and {pct(calm['11'])} without a one-off burst in February 2026",
        f"{M(burst['peak']['txs'])} of that month's {M(monthly['2026-02'])}",
        f"self-paid core transactions ({burst['peak']['share_of_month'] * 100:.0f}%)",
        f"sent {burst['peak']['month_before_txs']:,} the month before",
        f"never more than {burst['largest_share_in_any_other_month'] * 100:.1f}% of a month",
        f"{pct(calm['9'])} instead of {pct(windows['9'])}", f"{pct(calm['11'])} instead of {pct(windows['11'])}",
        f"month was {M(base['core_self_paid_txs_plateau_top'])} (February 2026)", f"up to {M(monthly['2024-12'])} in December 2024",
        f"the top of the range is {M(base['core_self_paid_txs_plateau_top_without_dormant_implicit'])} (June 2026)",
        f"({sweat_then} in October 2025, {sweat_now} in October",
        f"at most {sweat_then} of its {sm['heavy_accounts']['prior']:,.0f} heavy accounts a year ago",
        f"{sweat_now} of the {sm['heavy_accounts']['latest']:,.0f} now",
        f"the table has {M(sm['independent_self_paid_txs']['prior'])} where the census has {M(core['direct_txs']['prior'])}",
        f"{main['share_of_app_txs'] * 100:.0f}% of these transactions go to the main contract from {main['accounts']:,} accounts",
        f"{pools['accounts']:,} accounts used the concentrated-liquidity contract, for {pools['transactions']:,} transactions",
        f"relayers ({c['reward_apps_share']['prior'] * 100:.0f}% a year ago), or {c['reward_apps_share_incl_kaiching_namespace'] * 100:.0f}% counting",
        f"it sponsored {pay['sponsored_by_ember']['prior']:,.0f} users a year ago "
        f"({ember['prior_share'] * 100:.1f}% of transactions, {ember['latest_share'] * 100:.1f}% now)",
        f"share is {ember['reward_apps_share_with_ember']['latest'] * 100:.1f}% ({ember['reward_apps_share_with_ember']['prior'] * 100:.1f}% a year ago)",
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


def test_readme_key_findings_quote_the_same_summary():
    """The README repeats the headline figures; they are checked against the same frozen summary as THESIS.md."""
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text())
    text = prose("README.md")
    p, c, sm, v = s["population"], s["clients"], s["segments"]["metrics"], s["value_capture"]
    accounts, core = p["segments"]["all"]["accounts"], p["segments"]["core"]
    bound, price = s["segments"]["regular_accounts_reward_game_bound"], s["predictions"]["step"]["price_usd"]
    latest = c["months"][c["latest_month"]]
    intents = s["month_yoy"]["intents_volume_usd"]
    n_out = sum(len(x["outside_band"]) for x in s["lead_vs_price"].values())
    quoted = [
        f"fell **{abs(accounts['pct_change']):.0f}%** ({accounts['prior'] / 1e6:.1f}M → {M(accounts['latest'])} a month)",
        f"{M(sm['sponsored_accounts']['prior'])} a year ago, {M(sm['sponsored_accounts']['latest'])} now",
        f"**{sm['heavy_accounts']['latest']:,.0f} heavy accounts (1,000 or more transactions a month) send "
        f"{s['segments']['heavy_share_of_independent_self_paid_txs']['latest'] * 100:.0f}% of the self-paid transactions**",
        f"number {sm['regular_accounts']['latest']:,.0f} against {sm['regular_accounts']['prior']:,.0f} a year earlier",
        f"up to {bound['game_players_prior']:,} of last year's",
        f"are up {core['direct_txs']['pct_change']:.0f}%** October to October",
        f"({pct(p['core_direct_txs_change_by_window']['11'])} on eleven-month means)",
        f"from ${price['first_day']:.2f} to ${price['last_day']:.2f}",
        f"fell {abs(core['relayed_txs']['pct_change']):.0f}%",
        f"are up **{c['finance_txs']['pct_change']:.0f}%**; what is neither that group nor the reward apps is level "
        f"({pct(c['three_parts']['rest']['pct_change'])})",
        f"**{latest['accounts_for_half_of_txs']} accounts send half of all transactions.**",
        f"still send {c['reward_apps_share']['latest'] * 100:.0f}%",
        f"or {c['reward_apps_share_incl_kaiching_namespace'] * 100:.0f}% counting",
        f"**${intents['prior'] / 1e6:.0f}M → ${intents['recent'] / 1e6:.0f}M a day**",
        f"{n_out} of {17 * len(s['lead_vs_price'])} weekly lead-lag tests",
        f"**${v['buyback_usd_annualized'] / 1e6:.1f}M a year** and cover **{v['buyback_coverage_of_new_supply'] * 100:.0f}%**",
    ]
    missing = [q for q in quoted if q not in text]
    assert not missing, f"README.md does not quote these summary values: {missing}"
