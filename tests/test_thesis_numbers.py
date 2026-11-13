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
    return " ".join((ROOT / name).read_text(encoding="utf-8").split())


def test_thesis_quotes_the_committed_summary():
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))
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
    # the same game in the transaction series, the largest fall of regular accounts in one month, what a month's 40
    # largest contracts do not show, the three bursts of single-transaction accounts, and the sample sizes of the lag test
    game_txs, fall = s["segments"]["self_paid_txs_reward_game_bound"], s["segments"]["regular_accounts_largest_monthly_fall"]
    assert (fall["month_before"], fall["month"]) == ("2026-01", "2026-02") and 0.45 < fall["share_of_fall_from_prior_month_to_low"] < 0.5
    meteor, relayed = c["apps"]["Meteor wallet (Harvest Moon)"], game["relayed"]
    unseen, gap, (lo, hi) = c["groups_outside_the_40"]["finance"], c["reward_minus_finance_share"], c["finance_txs_change_range"]
    bursts = {b["month"]: b for b in p["implicit_one_transaction_bursts"]["bursts"]}
    assert list(bursts) == ["2026-02", "2026-03", "2026-04"] and bursts["2026-02"]["older_than_2y_share"] > 0.5
    assert bursts["2026-02"]["relayed_tx_share"] < 0.2 and min(bursts[m]["relayed_tx_share"] for m in ("2026-03", "2026-04")) > 0.9
    long_run = [v for k, v in s["lead_vs_price"].items() if k != "intents_volume_usd"]
    n_lo, n_hi = min(v["n_weeks_range"][0] for v in long_run), max(v["n_weeks_range"][1] for v in long_run)
    b_lo, b_hi = min(v["band_range"][0] for v in long_run), max(v["band_range"][1] for v in long_run)
    iv, quarter = s["lead_vs_price"]["intents_volume_usd"], s["qoq_90d"]
    # the nine months before the step and the month in progress: year-on-year figures whose base was a ramp-up are not enough
    iv_step, core_step, so_far = step["intents_volume_usd_a_day"], step["core_self_paid_txs"], s["month_to_date_yoy"]["intents_volume_usd"]
    assert step["reference_range"] == {"first": "2025-12", "last": "2026-08", "months": 9}
    assert iv_step["month_before_range"]["month"] == "2025-11" and (so_far["from"], so_far["days"]) == ("2026-11-01", 11)
    vs_spike = (intents["recent"] / iv_step["month_before_range"]["value"] - 1) * 100
    vs_range = (intents["recent"] / iv_step["range_mean"] - 1) * 100
    below_peak = (price["latest"]["value"] / price["peak_since"]["value"] - 1) * 100
    # what the old KaiChing accounts sent, what the residual rows hold, and the exchange's own bots
    gone, others, bots = c["kaiching_accounts_sample"]["recent"], c["other_top_40"], c["exchange_bot_targets"]
    assert gone["transactions"] == gone["delete_account"] and (gone["first_day"], gone["last_day"]) == ("2026-10-02", "2026-10-07")
    assert others["in_both_months"] == ["near"]
    was, now_ = [x["contract"] for x in others["prior"][:3]], others["latest"][:2]
    rest_alt = parts["rest_without_exchange_bot_targets"]
    # who the returning accounts outside the namespaces were, and how many accounts Meteor sponsors there
    back, back3 = pay["independent_returning_accounts"], s["sponsors"]["three_month_mean"]["independent_returning_accounts"]
    sweat_by_month, met = s["sponsors"]["sponsored_by_month"]["sweat"], pay["old_core_sponsored_by_meteor"]
    old3 = [three["old_txs"][k] / three["txs"][k] * 100 for k in ("latest", "prior")]
    # accounts that apps act for: a relayer with a daily quota, a game with the same accounts every month, claims in batches
    quota, ember_by_month, claims = p["kaiching_relayed_txs_per_day"], s["sponsors"]["ember_accounts_by_month"], game["sample_claims"]["recent"]
    assert quota["median_month_to_the_nearest_thousand"] == 2_000_000 and claims["shared_first_letters"] == ["ab", "co", "fu", "le", "ne"]
    oct_, sep_ = ember_by_month["2025-10"], ember_by_month["2025-09"]
    quoted = [
        f"{quota['median_month_to_the_nearest_thousand']:,.0f} transactions a day, to within a thousandth, in "
        f"{len(quota['months_within_a_thousandth_of_it'])} of its {quota['months_with_relayed_transactions']} months in the census "
        f"({quota['in_the_month']['2025-10']:,} in October 2025, which has 31 days; {quota['in_the_month']['2025-11']:,} in November, which has 30)",
        f"of its {oct_['accounts']:,} in October 2025 all but {oct_['accounts'] - oct_['also_active_the_month_before']} had also been active "
        f"in September, and so had all but {sep_['accounts'] - sep_['also_active_the_month_before']} of {sep_['accounts']:,} the month before",
        f"{claims['calls']} of the {calls['recent']['calls']} relayed calls to Meteor's game are reward claims, {claims['in_batches']} of them in "
        f"batches of up to {claims['largest_batch']} in one block",
        f"({pct(core_step['range_pct_change'])} from December to August)",
        f"against November 2025 (${iv_step['month_before_range']['value'] / 1e6:.0f}M) October is {pct(vs_spike)}",
        f"in between (${iv_step['range_mean'] / 1e6:.1f}M a day) it is {pct(vs_range)}",
        f"({(1 - back['prior'] / core['returning_accounts']['prior']) * 100:.0f}% of the returning ones a year ago)",
        f"({sweat_by_month['2026-07']:,.0f} → {sweat_by_month['2026-10']:,.0f} sponsored accounts)",
        f"are {back['latest']:,.0f} against {back['prior']:,.0f} ({pct(back['pct_change'])}; {pct(back3['pct_change'])})",
        f"fully sponsors {met['latest']:,.0f} accounts outside the app namespaces against {met['prior']:,.0f} a year ago",
        f"Up to {met['latest']:,.0f} of the players can therefore have moved",
        f"({met['prior']:,.0f} → {met['latest']:,.0f} outside the app namespaces)",
        f"they averaged {M(core_step['range_mean'])} against {M(core_step['range_mean_a_year_earlier'])} a year earlier "
        f"({pct(core_step['range_pct_change'])}; {pct(core_step['range_pct_change_without_dormant_implicit'])} without the February burst), "
        f"below the year before in {core_step['range_months_below_a_year_earlier']} of the {step['reference_range']['months']} months",
        f"November 2025 already averaged ${iv_step['month_before_range']['value'] / 1e6:.1f}M (October 2026 is {pct(vs_spike)} on it)",
        f"the first {so_far['days']} days of November 2026 average ${so_far['recent'] / 1e6:.1f}M against "
        f"${so_far['prior'] / 1e6:.1f}M a year earlier ({pct(so_far['pct_change'])})",
        f"volume averaged ${iv_step['range_mean'] / 1e6:.1f}M; against that level October 2026 is {pct(vs_range)}",
        f"the largest were `{was[0]}`, `{was[1]}` and `{was[2]}`; now they are `{now_[0]['contract']}`, with "
        f"{now_[0]['transactions']:,} transactions from {now_[0]['accounts']} accounts, and `{now_[1]['contract']}`",
        f"above the ${iv_step['range_low'] / 1e6:.1f}M to ${iv_step['range_top'] / 1e6:.1f}M range of the nine months before, "
        f"also in the first {so_far['days']} days of November (${so_far['recent'] / 1e6:.1f}M)",
        f"the price was {abs(below_peak):.0f}% below its October peak",
        f"({old3[0]:.0f}% against {old3[1]:.0f}% over three months)",
        f"({pct(intents['pct_change'])} for October, about {pct(so_far['pct_change'])} for November so far)",
        f"${iv_step['range_mean'] / 1e6:.1f}M a day from December 2025 to August 2026",
        f"{bots['prior']:,} transactions); filed with the exchange they make it {pct(bots['exchange_pct_change_with_them'])} instead of "
        f"{pct(c['apps']['Ref Finance / Rhea (DEX, lending)']['pct_change'])}, the financial group "
        f"{pct(bots['finance_pct_change_with_them'])} instead of {pct(c['finance_txs']['pct_change'])} and everything else "
        f"{pct(rest_alt['pct_change'])} instead of {pct(parts['rest']['pct_change'])}",
        f"whose {game_txs['game_direct_txs_prior']:,} direct calls were self-paid: without them the October change is at most "
        f"{pct(game_txs['pct_change_if_all_of_them_were_independent'])}",
        f"from {fall['before']:,} in January 2026 to {fall['after']:,} in February",
        f"Meteor's transactions as a whole are down {abs(meteor['pct_change']):.0f}% ({meteor['prior']:,} → {meteor['latest']:,}), "
        f"and {relayed['latest']['accounts']:,} accounts act through its relayer against {relayed['prior']['accounts']:,} a year earlier",
        f"up to {c['intents']['latest']['top2_share'] * 100:.0f}% of them signed by two accounts",
        f"{unseen['prior']['contracts']} contracts of the financial group a year ago (no more than "
        f"{unseen['prior']['transactions_each_at_most']:,} transactions each) and {unseen['latest']['contracts']} now "
        f"(no more than {unseen['latest']['transactions_each_at_most']:,} each)",
        f"the {pct(c['finance_txs']['pct_change'])} lies between {pct(lo)} and {pct(hi)}",
        f"{gap['latest'] * 100:.1f} points of all transactions in October 2026, lies between "
        f"{gap['latest_range'][0] * 100:.1f} and {gap['latest_range'][1] * 100:.1f}",
        f"about {bursts['2026-02']['accounts'] / 1e6:.1f}, {bursts['2026-03']['accounts'] / 1e6:.1f} and "
        f"{bursts['2026-04']['accounts'] / 1e6:.1f} million accounts against about "
        f"{p['implicit_one_transaction_bursts']['median_month'] / 1e6:.1f} million in an ordinary month",
        f"(n = {n_lo}–{n_hi} weeks depending on the metric and the lag, noise band ≈ ±{b_lo:.2f}–{b_hi:.2f})",
        f"(n = {iv['n_weeks_range'][0]}–{iv['n_weeks_range'][1]} weeks, band ≈ ±{iv['band_range'][0]:.2f}–{iv['band_range'][1]:.2f})",
        f"are down {abs(fees['pct_change']):.0f}% in USD on the same 90 days a year earlier",
        f"and {abs(s['yoy_90d']['fees_near']['pct_change']):.0f}% in NEAR; on the 90 days just before them they are up "
        f"({pct(quarter['fees_usd']['pct_change'])} in USD, {pct(quarter['fees_near']['pct_change'])} in NEAR)",
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
        f"{c['kaiching_txs_outside_its_contracts']:,.0f} transactions that are not calls to any of the 40 largest contracts, and "
        f"{p['kaiching_one_off']['single_tx_accounts']:,} accounts sent exactly one",
        f"All {gone['transactions']} of them that fall in the keyless sample are `DeleteAccount` on the account itself",
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
        f"({independent['prior']:,.0f} → {independent['latest']:,.0f}; {pct(independent['three_month_mean']['pct_change'])} on three-month means)",
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
        f"it sponsored {pay['sponsored_by_ember']['prior']:,.0f} accounts a year ago "
        f"({ember['prior_share'] * 100:.1f}% of transactions, {ember['latest_share'] * 100:.1f}% now)",
        f"share is {ember['reward_apps_share_with_ember']['latest'] * 100:.1f}% ({ember['reward_apps_share_with_ember']['prior'] * 100:.1f}% a year ago)",
        f"send {p['sweat_share_of_all_txs'] * 100:.1f}% of all transactions",
        f"{p['partial_month']['accounts']['tg']:,}",
        f"({p['partial_month']['latest_complete_accounts']['tg']:,})",
        f"{d['transactions']:,} transactions", f"({d['relayed_transactions']:,})", f"{d['relayed_users']:,} users",
        f"{d['nearblocks']['active_accounts']:,} active accounts",
        f"{d['accounts_created']:,} accounts were created that day by {d['create_account_transactions']:,} transactions",
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


def test_thesis_quotes_the_checks_read_from_the_chain():
    """The wallet balances, the outcomes of sampled transactions, the named step and the correction for many tests."""
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))
    text, readme = prose("THESIS.md"), prose("README.md")
    w, c, p = s["value_capture"]["wallets"], s["clients"], s["population"]
    tail, buyback, front, one_click = w["last_days"], *w["wallets"]
    assert (w["wallets"][buyback], w["wallets"][front], w["wallets"][one_click]) == ("buyback wallet", "front-end fund", "1Click fund")
    # the wallet check covers the same 90 days as the DefiLlama figure it is set against
    assert w["window"] == s["value_capture"]["window"] and (w["days"], tail["days"]) == (90, 30)
    cover, cover_tail = f"{w['coverage_of_new_supply'] * 100:.1f}%", f"{tail['coverage_of_new_supply'] * 100:.1f}%"
    relayer, fall, holm = c["largest_relayer"], p["largest_daily_fall"], s["lead_vs_price_holm"]
    assert (relayer["prior"]["relayer"], relayer["latest"]["relayer"]) == ("hotwallet.kaiching", "sweat-relayer.near")
    assert relayer["prior"]["transactions"] == p["kaiching_relayed_txs_per_day"]["in_the_month"][c["prior_month"]]
    before, of = fall["kaiching"]["month_before"], fall["kaiching"]["month_of"]
    assert (fall["date"], before["month"], of["month"]) == ("2026-04-02", "2026-03", "2026-04")
    assert holm["tests"] == 17 * len(s["lead_vs_price"]) and holm["significant"] == 0
    out = c["intents_outcomes"]
    own, bot = out["senders"]["intents.near"], out["senders"]["escrow.ai.near"]
    assert bot["failed"] == bot["transactions"] and out["target"] == "intents.near" and out["window"] == "recent"
    assert out["other_senders"]["failed"] == 0
    actors = {a["actor"]: a["txs"] for a in c["top_actors_latest"]}
    assert 0.23 < actors["escrow.ai.near"] / c["intents"]["latest"]["transactions"] < 0.27  # "a quarter"
    quoted = [
        # value capture read from the balances
        f"held {w['change_near_all_wallets']:,.0f} NEAR more at the end",
        f"That is {w['balance_growth_over_defillama_revenue']:.2f} of the revenue DefiLlama reports",
        f"it is {cover} of the {w['net_new_supply_near'] / 1e6:.2f}M NEAR of net new supply",
        f"over the last 30 days it is {cover_tail}",
        f"Of the {w['held_near_at_end_all_wallets'] / 1e6:.2f}M NEAR the three wallets hold, {w['buyback_wallet_share_of_held'] * 100:.0f}% is in the buyback wallet",
        f"{w['held_near_at_end'][front] / 1e6:.2f}M NEAR, sits in the front-end fund",
        f"(−{abs(w['change_near'][one_click]):,.0f} NEAR) while the buyback wallet grew by {w['change_near'][buyback]:,.0f}",
        f"gives {w['buyback_wallet_coverage_of_new_supply'] * 100:.1f}% over the 90 days and {tail['buyback_wallet_coverage_of_new_supply'] * 100:.1f}% over the last 30",
        f"grew by {cover} of the new supply of the same 90 days, and by {cover_tail} over the last 30",
        # concentration by actor and by signer
        f"signed {relayer['prior']['share_of_all_transactions'] * 100:.0f}% of all transactions in October 2025, and the largest one now, "
        f"Sweat's, signs {relayer['latest']['share_of_all_transactions'] * 100:.0f}%",
        # the step in the daily series
        f"went from {fall['txns']['before']:,} on {fall['day_before']} to {fall['txns']['after']:,} on {fall['date']} ({pct(fall['pct_change'])}",
        f"({fall['active_accounts']['before']:,} → {fall['active_accounts']['after']:,})",
        f"KaiChing sent {M(before['txs'])} transactions in March 2026, {M(before['txs_per_day'])} a day, and {M(of['txs'])} in the whole of April",
        # many lags tested at once
        "none of the 85 stands after Holm's correction",
        f"the smallest p-value is {holm['smallest_p']:.3f}; the first step of the correction asks for {holm['threshold_for_the_smallest_p']:.4f}",
        # how the sampled transactions to NEAR Intents ended
        f"{out['transactions']} transactions in {out['blocks']} blocks",
        f"all {bot['transactions']} sent by `escrow.ai.near` in the sample of autumn 2026 failed",
        f"against {own['failed']} failed of the {own['transactions']} that `intents.near` signed itself and none of the "
        f"{out['other_senders']['transactions']} from other accounts",
        f"(all {bot['transactions']} in the keyless sample failed)",
    ]
    missing = [q for q in quoted if q not in text]
    assert not missing, f"THESIS.md does not quote these summary values: {missing}"
    in_readme = [
        f"grew by {w['change_near_all_wallets']:,.0f} NEAR over the same 90 days, {cover} of the new supply ({cover_tail} over the last 30)",
        "none stands after Holm's correction",
    ]
    missing = [q for q in in_readme if q not in readme]
    assert not missing, f"README.md does not quote these summary values: {missing}"


def test_thesis_names_the_snapshot_date():
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))
    assert f"Snapshot as of {s['last_date']}" in (ROOT / "THESIS.md").read_text(encoding="utf-8")


def test_readme_key_findings_quote_the_same_summary():
    """The README repeats the headline figures; they are checked against the same frozen summary as THESIS.md."""
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))
    text = prose("README.md")
    p, c, sm, v = s["population"], s["clients"], s["segments"]["metrics"], s["value_capture"]
    accounts, core = p["segments"]["all"]["accounts"], p["segments"]["core"]
    bound, price = s["segments"]["regular_accounts_reward_game_bound"], s["predictions"]["step"]["price_usd"]
    latest = c["months"][c["latest_month"]]
    intents = s["month_yoy"]["intents_volume_usd"]
    n_out = sum(len(x["outside_band"]) for x in s["lead_vs_price"].values())
    step = s["predictions"]["step"]
    iv_step, core_step = step["intents_volume_usd_a_day"], step["core_self_paid_txs"]
    vs_range = (intents["recent"] / iv_step["range_mean"] - 1) * 100
    assert abs(intents["recent"] / iv_step["month_before_range"]["value"] - 1) < 0.1          # "level with November 2025"
    quota = p["kaiching_relayed_txs_per_day"]
    quoted = [
        f"{quota['median_month_to_the_nearest_thousand']:,.0f} transactions a day, to within a thousandth in "
        f"{len(quota['months_within_a_thousandth_of_it'])} of its {quota['months_with_relayed_transactions']} months",
        f"they ran {abs(core_step['range_pct_change']):.0f}% below the year before",
        f"level with November 2025 (${iv_step['month_before_range']['value'] / 1e6:.0f}M) and {pct(vs_range)} on the nine months "
        f"in between (${iv_step['range_mean'] / 1e6:.1f}M)",
        f"{p['one_day']['accounts_created']:,} accounts created by {p['one_day']['account_creators']} creators",
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


def test_the_notes_for_coding_agents_are_the_same_under_both_names():
    """Claude Code reads CLAUDE.md and Codex reads AGENTS.md; both screen the project, so both get the same notes."""
    assert (ROOT / "AGENTS.md").read_bytes() == (ROOT / "CLAUDE.md").read_bytes()
