"""THESIS.md is a snapshot: the numbers it quotes must be the ones in data/snapshot/thesis_summary.json.

That file is a frozen copy of the summary (`python -m thesis snapshot`). The build rewrites docs/summary.json
every day; it never touches the snapshot, so this test keeps passing after a rebuild on newer data.
"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def M(v):  # 9751032 -> "9.75M"
    return f"{v / 1e6:.2f}M"


def month(m):  # "2024-12" -> "December 2024"
    return datetime.strptime(m, "%Y-%m").strftime("%B %Y")


def pct(v):  # -65.8 -> "−66%"
    return f"{'+' if v > 0 else '−'}{abs(v):.0f}%"


def prose(name):  # a file as one line of text, so that re-wrapping a paragraph cannot hide a number from the tests
    if name == "THESIS.md":  # the argument and its appendix, which holds the detail under the same headings
        return " ".join(" ".join((ROOT / f).read_text(encoding="utf-8").split()) for f in ("THESIS.md", "APPENDIX.md"))
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
    # the players are taken out of both years by one rule: the direct callers, and the accounts that act through the
    # relayer and pay for something of their own. How many are in both groups the tables do not say: two high ends
    clean, hold, apart = bound["without_the_game"], "if_one_group_holds_the_other", "if_no_account_is_in_both"
    now_p, then_p = clean["players"]["latest"], clean["players"]["prior"]
    still, low = clean["players_still_self_paying_latest_at_most"], pct(clean["pct_change_low"])
    high, most = clean["pct_change_high"], clean["pct_change_with_the_most_out_of_both_months"]
    assert high[hold] == bound["pct_change_if_all_of_them_were_regular"]
    assert clean["pct_change_low"] < bound["pct_change_as_counted"] < high[hold] < high[apart] and most[hold] < most[apart]
    for k, players in (("latest", now_p), ("prior", then_p)):
        assert players["paying_through_the_relayer"] == game["relayed"][k]["accounts"] - pay["sponsored_by_meteor"][k]
    assert still == now_p["paying_through_the_relayer"] and now_p["direct_callers"] is None
    assert now_p["direct_txs_at_most"] == game["smallest_of_the_40_latest"]
    assert clean["players_prior_at_most"] == {hold: direct["accounts"], apart: direct["accounts"] + then_p["paying_through_the_relayer"]}
    # the relayer was already submitting calls to the game a year ago: the one relayed call in last year's sample, a claim
    assert calls["prior"]["relayed"] == game["sample_claims"]["prior"]["calls"] == 1
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
    # the unfinished month as a rate per day, the months of the range that were above the year before, and the two
    # things inside the self-paid series that are not independent use
    pace, above = p["partial_month"]["core_direct_txs"], core_step["range_months_above_a_year_earlier"]
    last_full, year_ago = pace["latest_complete_month"], pace["same_month_a_year_earlier"]
    assert (p["partial_month"]["month"], last_full["month"], year_ago["month"], list(above)) == ("2026-11", "2026-10", "2025-11", ["2026-05", "2026-06"])
    vs_september = (pace["per_day"] / pace["per_day_by_month"]["2026-09"] - 1) * 100
    over_b2 = (pace["whole_month_at_that_rate"] / base["core_self_paid_txs_plateau_top"] - 1) * 100
    vs_last_november = (monthly["2026-10"] / monthly["2025-11"] - 1) * 100
    thousand = lambda v: f"{v / 1e3:.0f} thousand"
    # the coverage over windows of other lengths, the one-off inside the unfinished month, and the term counted in both years
    cov = [x["coverage"] * 100 for x in s["value_capture"]["windows"]["by_length"].values()]
    cov_lo, cov_hi = min(cov), max(cov)
    spike_day = datetime.strptime(p["partial_month"]["signer_spike"]["date"], "%Y-%m-%d").strftime("%-d %B")
    assert spike_day == "10 November"
    term = clean["relayer_term_only"]
    halves = s["autumn"]["half_months"]
    below_peak_mean = (halves["2026-11-01..2026-11-11"]["price_usd"] / price["peak_since"]["value"] - 1) * 100
    # every half-month from the step's on is above the top of the range before
    assert all(v["intents_volume_usd"] > iv_step["range_top"] for k, v in halves.items() if k >= "2026-08-16")
    adj, side, failing = s["segments"]["self_paid_txs_adjustments"], c["reward_side_direct_calls"], c["failing_senders"]
    assert list(failing["sampled"]) == ["escrow.ai.near"] and failing["transactions_prior"] == {"escrow.ai.near": None}
    assert side["prior"]["transactions"] == game_txs["game_direct_txs_prior"]      # a year ago the game was all of it
    fast, ember_calls = (side["latest"]["by_contract"][k] for k in ("fast-auth.near", "embr.playember_reserve.near"))
    side_range = adj["pct_change_without_reward_side_direct_txs_range"]
    side_lo, side_hi = adj["pct_change_without_reward_side_direct_txs_both_ends"]
    both_lo, both_hi = adj["pct_change_without_both_both_ends"]
    failed_txs, finance_change = failing["transactions_latest_all"], c["finance_txs"]["pct_change"]
    # the unfinished month for the reward apps' namespaces too, not only where self-paid transactions slow down
    rates = p["partial_month"]["txs_per_day"]
    hot_tg, chain, share = rates["tg"], rates["all"], rates["reward_namespaces_share_of_txs"]
    assert (rates["month"], rates["latest_complete_month"], rates["days"]) == ("2026-11", "2026-10", pace["days"])
    relayed_rise = hot_tg["relayed"]["partial"] - hot_tg["relayed"]["latest_complete"]
    assert relayed_rise / (hot_tg["partial"] - hot_tg["latest_complete"]) > 0.5                    # "most of the rise through its relayer"
    assert 1.9 < hot_tg["partial"] / hot_tg["latest_complete"] < 2                                 # "almost twice"
    assert abs(chain["pct_change"]) < 2                                                            # "the chain as a whole did not move"
    assert c["kaiching_txs_outside_its_contracts"] / seg["kaiching"]["txs"]["latest"] > 0.5       # "mostly the one-off deletion"
    assert 200 <= sm["heavy_accounts"]["latest"] < 1000                                            # "a few hundred heavy accounts"
    # every series of the census starts a month after the table: the first month has no month before it
    assert (p["table_first_month"], p["first_month"], min(monthly), quota["first_month"]) == ("2024-11", "2024-12", "2024-12", "2024-12")
    assert set(p["core_direct_txs_top3_months"]) == {"2026-09", "2026-10", "2024-12"}
    # deletions counted by the aggregator in the months where the census finds one-transaction accounts
    deleted = p["deleted_accounts"]["months"]
    feb, mar, apr, oct_gone = (deleted[m] for m in ("2026-02", "2026-03", "2026-04", "2026-10"))
    feb_days, oct_days = feb["burst_days"], oct_gone["burst_days"]
    assert (feb_days["first"], feb_days["last"], oct_days["first"], oct_days["last"]) == ("2026-02-03", "2026-02-18", "2026-10-02", "2026-10-08")
    assert mar["burst_days"] is None and apr["burst_days"] is None                                 # "were not deletions"
    for row in (mar, apr):                                       # under a hundredth of the accounts that sent one transaction
        assert row["deleted_accounts"] < 0.01 * sum(row["census_one_transaction_accounts"].values())
    assert feb["census_one_transaction_accounts"] == {"implicit_one_transaction_burst": bursts["2026-02"]["accounts"]}
    assert oct_gone["census_one_transaction_accounts"] == {"kaiching_one_off": p["kaiching_one_off"]["single_tx_accounts"]}
    # "agrees with the burst in size": within a tenth of each other, on the days of the burst
    for row in (feb, oct_gone):
        assert 0.9 < row["burst_days"]["deleted_accounts"] / sum(row["census_one_transaction_accounts"].values()) < 1.1
    quoted = [
        # the long-term case in short names what stayed; November is quoted for the reward apps' namespaces as well
        f"which still send {c['reward_apps_share']['latest'] * 100:.0f}% of transactions (in October, close to their lowest month), and a "
        f"small amount of self-paid, financial "
        f"activity carried by a few hundred heavy accounts",
        f"In its first {rates['days']} days HOT's namespace (`.tg`) sent {thousand(hot_tg['partial'])} transactions a day against "
        f"{thousand(hot_tg['latest_complete'])} in October ({pct(hot_tg['pct_change'])}), most of the rise through its relayer "
        f"({thousand(hot_tg['relayed']['partial'])} a day against {thousand(hot_tg['relayed']['latest_complete'])})",
        f"({thousand(chain['partial'])} a day against {thousand(chain['latest_complete'])})",
        f"went from {share['latest_complete'] * 100:.0f}% of all transactions in October ({c['kaiching_share_by_namespace'] * 100:.1f} "
        f"points of it KaiChing's namespace, mostly the one-off deletion of its accounts) to {share['partial'] * 100:.0f}%",
        f"self-paid transactions outside the reward apps ran {abs(last_full['pct_change']):.0f}% below October's rate",
        "its transactions run at almost twice October's daily rate",
        # the long-term case in short, and the wording of the nine months before the step
        f"The revenue it earns covers {cov_lo:.0f}% to {cov_hi:.0f}% of the new NEAR issued, depending on the window",
        "What pays its own way averaged below the year before until autumn 2026",
        f"below the year before in {core_step['range_months_below_a_year_earlier']} of the {step['reference_range']['months']} months and "
        f"above it in May ({pct(above['2026-05'])}) and June ({pct(above['2026-06'])})",
        # November so far, as a rate per day
        f"In the first {pace['days']} days of November it runs at {thousand(pace['per_day'])} a day: {abs(last_full['pct_change']):.0f}% below "
        f"October's rate and {abs(year_ago['pct_change']):.0f}% below November 2025's",
        f"November 2025 was {M(monthly['2025-11'])}, and October 2026 is {pct(vs_last_november)} on it",
        f"the first {pace['days']} days of November 2026: {thousand(pace['per_day'])} a day, against {thousand(last_full['per_day'])} in October "
        f"({pct(last_full['pct_change'])}) and {thousand(year_ago['per_day'])} in November 2025 ({pct(year_ago['pct_change'])})",
        f"in its first {pace['days']} days the series ran at {thousand(pace['per_day'])} a day, {abs(last_full['pct_change']):.0f}% below October's "
        f"rate, {abs(vs_september):.0f}% below September's and {abs(year_ago['pct_change']):.0f}% below November 2025's. At that rate the month "
        f"would total {M(pace['whole_month_at_that_rate'])}, {over_b2:.0f}% above the {M(base['core_self_paid_txs_plateau_top'])} that "
        f"prediction B2 needs",
        f"The first {pace['days']} days of that quarter are in the census already, at a rate of "
        f"{M(pace['whole_month_at_that_rate'])} a month, or {M(pace['without_dormant_implicit']['whole_month_at_that_rate'])} without the "
        f"one-off of {spike_day} (B2 checks November to January)",
        # what is inside the self-paid series and the financial group without being independent use
        f"without them the October change is {pct(adj['pct_change_without_both'])} if every caller of the reward-side contracts "
        f"is outside the reward namespaces, and between {pct(both_lo)} and {pct(both_hi)} as far as the tables can say",
        f"Without the transactions of one account whose sampled calls all failed, {pct(failing['finance_pct_change_without_them'])}",
        f"This year's holds {side['latest']['transactions']:,} direct calls to reward-side contracts",
        f"and the {failed_txs:,} transactions of `escrow.ai.near`, whose sampled calls all failed. With the reward-side calls out of both "
        f"years the change is {pct(adj['pct_change_without_reward_side_direct_txs'])} if all their callers are outside the reward "
        f"namespaces ({pct(side_range[0])} to {pct(side_range[1])} allowing for such contracts outside the 40 largest)",
        f"so the change lies between {pct(side_lo)} and {pct(side_hi)}. With that account out as well, "
        f"{pct(adj['pct_change_without_both'])} on the same assumption, and between {pct(both_lo)} and {pct(both_hi)} without it",
        f"the change lies between {pct(side_range[0])} and {pct(side_range[1])} if every caller is outside the reward namespaces",
        f"the change lies between {pct(side_lo)} (none of last year's calls in the series, all of this year's) and {pct(side_hi)} "
        f"(the other way round); with `escrow.ai.near` out as well, between {pct(both_lo)} and {pct(both_hi)}",
        f"The count holds the {failed_txs:,} transactions of `escrow.ai.near`, whose sampled calls to Intents all failed: without them the "
        f"group is {pct(failing['finance_pct_change_without_them'])}, and Intents itself {pct(failing['target_pct_change_without_them'])} "
        f"instead of {pct(c['apps']['NEAR Intents']['pct_change'])}",
        f"without its {failed_txs:,} transactions the count is down {abs(failing['target_pct_change_without_them']):.0f}%",
        f"the financial group is then up {failing['finance_pct_change_without_them']:.0f}%, not {finance_change:.0f}%, and self-paid "
        f"transactions outside the reward namespaces {adj['pct_change_without_failing_senders']:.0f}%, not {adj['pct_change_as_counted']:.0f}%",
        f"That account sent {failed_txs:,} transactions in October, about a quarter of what NEAR Intents",
        f"that is {side['prior']['transactions']:,} calls a year ago (the game) and {side['latest']['transactions']:,} now: "
        f"{fast['transactions']:,} to `fast-auth.near`, whose main caller is Sweat's relayer, and {ember_calls['transactions']:,} to Ember's "
        f"contract from {ember_calls['accounts']} accounts",
        f"With the failing calls of `escrow.ai.near` taken out as well, the financial group is "
        f"{pct(failing['finance_pct_change_without_them_and_with_the_exchange_bot_targets'])}",
        f"{quota['median_month_to_the_nearest_thousand']:,.0f} transactions a day, to within a thousandth, in "
        f"{len(quota['months_within_a_thousandth_of_it'])} of its {quota['months_with_relayed_transactions']} months in the census, "
        f"{month(quota['first_month'])} to {month(quota['last_month'])} ({quota['in_the_month']['2025-10']:,} in October 2025, which has "
        f"31 days; {quota['in_the_month']['2025-11']:,} in November, which has 30)",
        # which months the series hold, and why the table's first month is not one of them
        f"two of the three highest of the {len(monthly)} months from {month(min(monthly))} to {month(max(monthly))}",
        f"The table begins with {month(p['table_first_month'])}, which has no month before it",
        f"the counts of months above (KaiChing's {quota['months_with_relayed_transactions']}, the self-paid series' {len(monthly)}) "
        f"start in {month(p['first_month'])}",
        # the aggregator's count of deleted accounts next to the census's one-transaction accounts: a second source
        f"NearBlocks counted {feb['deleted_accounts']:,} deleted accounts in February, {feb_days['deleted_accounts']:,} of them on the "
        f"{feb_days['days']} days from 3 to 18 February, against {feb['per_day_month_before']:.0f} a day in January",
        f"NearBlocks counted {mar['deleted_accounts']:,} and {apr['deleted_accounts']:,} deleted accounts in those months",
        f"NearBlocks counted {oct_gone['deleted_accounts']:,} deleted accounts in October, {oct_days['deleted_accounts']:,} of them from 2 "
        f"to 8 October",
        f"of its {oct_['accounts']:,} in October 2025 all but {oct_['accounts'] - oct_['also_active_the_month_before']} had also been active "
        f"in September, and so had all but {sep_['accounts'] - sep_['also_active_the_month_before']} of {sep_['accounts']:,} the month before",
        f"{claims['calls']} of the {calls['recent']['calls']} relayed calls to Meteor's game are reward claims, {claims['in_batches']} of them in "
        f"batches of up to {claims['largest_batch']} in one block",
        f"November 2025 already averaged ${iv_step['month_before_range']['value'] / 1e6:.1f}M (October 2026 is {pct(vs_spike)} on it)",
        f"({(1 - back['prior'] / core['returning_accounts']['prior']) * 100:.0f}% of the returning ones a year ago)",
        f"({sweat_by_month['2026-07']:,.0f} → {sweat_by_month['2026-10']:,.0f} sponsored accounts)",
        f"are {back['latest']:,.0f} against {back['prior']:,.0f} ({pct(back['pct_change'])}; {pct(back3['pct_change'])})",
        f"fully sponsors {met['latest']:,.0f} accounts outside the app namespaces against {met['prior']:,.0f} a year ago",
        f"The {met['latest'] - met['prior']:,.0f} more accounts it fully sponsors are {(met['latest'] - met['prior']) / bound['fall'] * 100:.0f}% of "
        f"the fall of {bound['fall']:,.0f}",
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
        f"every half-month has averaged above the range of the nine months before (${iv_step['range_low'] / 1e6:.1f}M to "
        f"${iv_step['range_top'] / 1e6:.1f}M a day), also the first {so_far['days']} days of November (${so_far['recent'] / 1e6:.1f}M), when "
        f"the price averaged {abs(below_peak_mean):.0f}% below its October peak ({abs(below_peak):.0f}% on 11 November)",
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
        f"But up to {bound['game_players_prior']:,} of last year's were players of Meteor's reward game paying their own fees",
        f"up to {direct['accounts']:,} of them were players of Meteor's reward game",
        f"read as {bound['fall']:,.0f} users leaving",
        f"Both years' counts can also hold players who act through that relayer and pay for a transaction of their own, because "
        f"a relayed call counts towards the frequency class: up to {still:,} accounts now and {then_p['paying_through_the_relayer']:,} "
        f"a year ago, when the relayer was already submitting calls to the game",
        f"Taking out only those, the players counted in both years, the change lies between {pct(term['pct_change_low'])} and "
        f"{pct(term['pct_change_high'])} ({pct(term['pct_change_with_both_out'])} with the most out of both years). The direct callers are "
        f"counted a year ago only: with them out of last year as well the high end is {without} or more ({pct(high[apart])} if none of "
        f"those {then_p['paying_through_the_relayer']:,} also called the game directly, which the tables do not say), and the low end is "
        f"{low} or lower, because who calls the game directly now the tables do not say. As counted it is {counted}",
        f"Of the {now_p['relayer_accounts']:,} accounts that act through Meteor's relayer now, it pays everything for "
        f"{now_p['fully_sponsored']:,}, so up to {still:,} still pay for something themselves and can be inside this year's "
        f"{sm['regular_accounts']['latest']:,.0f}",
        f"({calls['prior']['relayed']} of the {calls['prior']['calls']} calls to it in last year's keyless sample, a reward claim)",
        f"and of its {then_p['relayer_accounts']:,} accounts it paid everything for {then_p['fully_sponsored']:,}, so up to "
        f"{then_p['paying_through_the_relayer']:,} such accounts can be inside last year's {sm['regular_accounts']['prior']:,.0f} as well",
        f"last year's class can hold up to {direct['accounts']:,} players if all of them did and up to "
        f"{clean['players_prior_at_most'][apart]:,} ({clean['share_of_prior_regular_at_most'][apart] * 100:.0f}% of it) if none did",
        f"accounts lies between {pct(term['pct_change_low'])} (none of last year's accounts were such players, all {still:,} are in this "
        f"year's class) and {pct(term['pct_change_high'])} (all {then_p['paying_through_the_relayer']:,} were in last year's class, none are "
        f"in this year's), and is {pct(term['pct_change_with_both_out'])} with both taken out",
        f"they make the high end: {without} with {direct['accounts']:,} players taken out of last year, {pct(high[apart])} with "
        f"{clean['players_prior_at_most'][apart]:,}, and between {pct(most[hold])} and {pct(most[apart])} with this year's {still:,} taken "
        f"out as well",
        f"who still calls the game directly the tables do not say (at most {game['smallest_of_the_40_latest']:,} transactions, too few "
        f"for the 40 largest), so this year's class can hold more players than {still:,}, although none of the {calls['recent']['calls']} "
        f"calls to the game in the sample of autumn 2026 was direct. As counted the change is {counted}",
        f"{direct['accounts']:,} accounts called the reward game", f"{direct['transactions_per_account']:.0f} times each on average",
        f"(at most {game['smallest_of_the_40_latest']:,} direct transactions against {direct['transactions']:,})",
        f"all {calls['recent']['calls']} calls to it in the keyless sample",
        f"{calls['prior']['calls'] - calls['prior']['relayed']} of {calls['prior']['calls']} were direct a year earlier",
        f"went {pay['sponsored_by_meteor']['prior']:,.0f} → {pay['sponsored_by_meteor']['latest']:,.0f}",
        f"({bound['share_of_prior_regular_at_most'] * 100:.0f}% of last year's {sm['regular_accounts']['prior']:,.0f})",
        f"called directly by {direct['accounts']:,} accounts in October 2025",
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
        f"{p['core_txs_per_account_at_prior_mix']:.1f} at last year's mix of account types, so "
        f"{pct((p['core_txs_per_account_at_prior_mix'] / core['txs_per_account']['prior'] - 1) * 100)} is left",
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
        f"**The buybacks equal {s['value_capture']['buyback_coverage_of_new_supply'] * 100:.0f}% of the dilution.**",
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
    # the level is KaiChing; the one day is more than KaiChing, and the census names a candidate for the rest
    level = fall["median_day"]
    new = fall["new_accounts"]
    burst = {b["month"]: b for b in p["implicit_one_transaction_bursts"]["bursts"]}[of["month"]]
    assert fall["fall_txs"] == fall["txns"]["before"] - fall["txns"]["after"] == of["txs"] + fall["other_accounts_in_the_fall_at_least"]
    assert burst["relayed_tx_share"] > 0.9 and fall["kaiching"]["month_after"]["month"] == "2026-05"
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
        f"The growth of the 90 days is {cover} of the {w['net_new_supply_near'] / 1e6:.2f}M NEAR of net new supply",
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
        f"the median day of March carried {M(level['month_before'])} transactions and the median day of May {M(level['month_after'])}, "
        f"a fall of {M(level['fall'])} a day, of which KaiChing's rate is {level['kaiching_share_of_it'] * 100:.0f}%",
        f"It lost {M(fall['fall_txs'])} transactions, and KaiChing's accounts can be at most "
        f"{fall['kaiching_share_of_the_fall_at_most'] * 100:.0f}% of that (everything they sent in April), so at least "
        f"{M(fall['other_accounts_in_the_fall_at_least'])} was sent by other accounts that stopped on the same day",
        f"{burst['accounts'] / 1e6:.1f} million of them in April, one transaction each",
        # new accounts stepped down on the same day, by the aggregator's count and by KaiChing's accounts in the census
        f"Its count of new accounts stepped down on the same day, from {new['before']:,} to {new['after']:,} "
        f"({new['per_day_month_before']:,.0f} a day on average in March, {new['per_day_month_of']:,.0f} in April), and in the census "
        f"the KaiChing accounts seen for the first time went from {M(before['first_seen_accounts'])} in March to "
        f"{of['first_seen_accounts']:,} in April",
        # many lags tested at once
        "none of the 85 stands after Holm's correction",
        f"the smallest p-value is {holm['smallest_p']:.3f}; the first step of the correction asks for {holm['threshold_for_the_smallest_p']:.4f}",
        # how the sampled transactions to NEAR Intents ended
        f"{out['transactions']} transactions in {out['blocks']} blocks",
        f"all {bot['transactions']} sent by `escrow.ai.near` in the sample of autumn 2026 failed",
        f"against {own['failed']} failed of the {own['transactions']} that `intents.near` signed itself and none of the "
        f"{out['other_senders']['transactions']} from other accounts",
        f"(all {bot['transactions']} in the keyless sample failed, over 90 days)",
    ]
    missing = [q for q in quoted if q not in text]
    assert not missing, f"THESIS.md does not quote these summary values: {missing}"
    in_readme = [
        f"grew by {w['change_near_all_wallets']:,.0f} NEAR over the same 90 days, {cover} of the new supply ({cover_tail} over the last 30)",
        "none stands after Holm's correction",
    ]
    missing = [q for q in in_readme if q not in readme]
    assert not missing, f"README.md does not quote these summary values: {missing}"


def test_thesis_quotes_the_take_the_issuance_cut_and_the_relayed_users():
    """Where the revenue step came from, the approved cut in issuance, and the aggregator's own count of relayed users."""
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))
    text, readme = prose("THESIS.md"), prose("README.md")
    v, day, fall = s["value_capture"], s["population"]["one_day"], s["population"]["largest_daily_fall"]
    take, cut, v3 = v["take"], v["issuance_cut"], day["nearblocks_v3"]
    before, after, month, last = take["before"], take["after"], take["take_bps_by_month"], take["last_30_days_vs_the_30_before"]
    # the second source agrees with the BigQuery count of the same day to within a handful of accounts
    assert abs(v3["relayed_users"] - day["relayed_users"]) < 10 and abs(v3["relayed_txns"] - day["relayed_transactions"]) < 10
    assert v3["relayers"] == day["relayers"]
    assert (take["step_day"], after["through"], last["through"]) == (s["autumn"]["intents_step"]["day"], v["window"][1], v["window"][1])
    assert abs(take["revenue_ratio"] - take["volume_ratio"] * take["take_ratio"]) < 1e-9
    summer = [month[m] for m in ("2026-05", "2026-06", "2026-07", "2026-08")]
    down = [abs(last[k]) for k in ("volume_pct_change", "gross_fees_pct_change", "revenue_usd_pct_change")]
    assert all(last[k] < 0 for k in last if k.endswith("pct_change")) and 19.5 < min(down) and max(down) < 26   # "a fifth to a quarter"
    assert not cut["in_force_yet"] and cut["read_at_utc"].startswith("2026-11-14") and cut["id"] == "HSP-029"
    assert (cut["max_issuance_in_force"], cut["target_max_issuance"], cut["ramp_months"]) == (0.025, 0.016, 24)
    cover, need = f"{v['buyback_coverage_of_new_supply'] * 100:.0f}%", f"{v['growth_needed_to_cover_new_supply']:.1f} times"
    cover_cut, need_cut = f"{cut['coverage_at_target'] * 100:.0f}%", f"{cut['growth_needed_at_target']:.1f}"
    ratios = f"{take['volume_ratio']:.1f} times more volume and a {take['take_ratio']:.1f} times higher take"
    quoted = [
        f"{v3['relayed_users']:,} accounts acted for by {v3['relayers']} relayers in {v3['relayed_txns']:,} relayed transactions",
        f"{fall['relayed_users']['before']:,} on the first day and {fall['relayed_users']['after']:,} on the second",
        f"carried ${before['volume_usd_per_day'] / 1e6:.1f}M a day and NEAR kept {before['take_bps']:.2f} basis points of it",
        f"from the step to {after['through']} it carried ${after['volume_usd_per_day'] / 1e6:.1f}M a day and NEAR kept {after['take_bps']:.2f}",
        f"Volume grew {take['volume_ratio']:.1f} times and the take {take['take_ratio']:.1f} times, which together is the "
        f"{take['revenue_ratio']:.1f} times in revenue",
        f"the take was {min(summer):.1f} to {max(summer):.1f} basis points from May to August, {month['2026-09']:.1f} in September "
        f"and {month['2026-10']:.1f} in October",
        f"({month['2026-08']:.1f} basis points in August, {month['2026-10']:.1f} in October)",
        f"less tested than its {after['days']} days suggest",
        f"volume is {abs(last['volume_pct_change']):.0f}% below the 30 days before, gross fees {abs(last['gross_fees_pct_change']):.0f}%, "
        f"and captured revenue {abs(last['revenue_usd_pct_change']):.0f}% in USD and {abs(last['revenue_near_pct_change']):.0f}% in NEAR",
        f"from {cut['max_issuance_in_force'] * 100:.1f}% to {cut['target_max_issuance'] * 100:.1f}% a year on a {cut['ramp_months']}-month ramp",
        f"still gives a maximum of {cut['max_issuance_in_force'] * 100:.1f}%",
        f"the {cover} becomes {cover_cut} at the end of the ramp and the {need} becomes {need_cut}",
        f"is {ratios}",
        f"the {cover} would be {cover_cut} and the {need} {need_cut}",
        f"keeps {after['take_bps']:.2f} basis points of Intents volume against {before['take_bps']:.2f} before",
    ]
    missing = [q for q in quoted if q not in text]
    assert not missing, f"THESIS.md does not quote these summary values: {missing}"
    in_readme = [
        f"is {ratios} ({before['take_bps']:.2f} → {after['take_bps']:.2f} basis points of volume)",
        f"over the last 30 days volume is down {abs(last['volume_pct_change']):.0f}% and captured revenue {abs(last['revenue_usd_pct_change']):.0f}%",
        f"({cut['target_max_issuance'] * 100:.1f}% a year, not yet in force) the {cover} would be {cover_cut}",
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
    pace = p["partial_month"]["core_direct_txs"]
    assert (pace["latest_complete_month"]["month"], pace["same_month_a_year_earlier"]["month"]) == ("2026-10", "2025-11")
    quota = p["kaiching_relayed_txs_per_day"]
    rates = p["partial_month"]["txs_per_day"]
    cov = [x["coverage"] * 100 for x in v["windows"]["by_length"].values()]
    twelve = p["core_direct_txs_change_12_months_with_the_tables_first_month"]["pct_change"]
    assert pct(twelve) == pct(p["core_direct_txs_change_by_window"]["11"])                         # "the same on twelve"
    quoted = [
        f"which still send {c['reward_apps_share']['latest'] * 100:.0f}% of transactions (in October, close to their lowest month), and a "
        f"small amount of self-paid, financial "
        f"activity carried by a few hundred heavy accounts",
        f"in its first {rates['days']} days HOT's namespace sent {rates['tg']['partial'] / 1e3:.0f} thousand transactions a day against "
        f"{rates['tg']['latest_complete'] / 1e3:.0f} thousand in October",
        f"{quota['median_month_to_the_nearest_thousand']:,.0f} transactions a day, to within a thousandth in "
        f"{len(quota['months_within_a_thousandth_of_it'])} of its {quota['months_with_relayed_transactions']} months from "
        f"{month(quota['first_month'])} to {month(quota['last_month'])} (every series of the census leaves out its first month, "
        f"{month(p['table_first_month'])}, which has no month before it)",
        f"they averaged {abs(core_step['range_pct_change']):.0f}% below the year before (below it in "
        f"{core_step['range_months_below_a_year_earlier']} of the {step['reference_range']['months']} months)",
        f"in the first {pace['days']} days of November they run {abs(pace['latest_complete_month']['pct_change']):.0f}% below October's "
        f"daily rate and {abs(pace['same_month_a_year_earlier']['pct_change']):.0f}% below November 2025's",
        f"the October change is {pct(s['segments']['self_paid_txs_adjustments']['pct_change_without_both'])} if every caller "
        f"of the reward-side contracts is outside the reward namespaces, and between "
        f"{pct(s['segments']['self_paid_txs_adjustments']['pct_change_without_both_both_ends'][0])} and "
        f"{pct(s['segments']['self_paid_txs_adjustments']['pct_change_without_both_both_ends'][1])} as far as the tables can say",
        f"The revenue it earns covers {min(cov):.0f}% to {max(cov):.0f}% of the new NEAR issued, depending on the window",
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
        f"({pct(p['core_direct_txs_change_by_window']['11'])} on eleven-month means, the same on twelve)",
        f"from ${price['first_day']:.2f} to ${price['last_day']:.2f}",
        f"fell {abs(core['relayed_txs']['pct_change']):.0f}%",
        f"are up **{c['finance_txs']['pct_change']:.0f}%** ({pct(c['failing_senders']['finance_pct_change_without_them'])} without that "
        f"account); what is neither that group nor the reward apps is level ({pct(c['three_parts']['rest']['pct_change'])})",
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


def test_the_texts_quote_the_readings_by_window_half_month_and_family():
    """The figures that put a headline in context: other windows, half-months, account families, the months around one.

    Each of them answers a question a single figure leaves open (is this window typical, is this month typical, which
    part of the series moved, when exactly). They are numbers like any other: they come from the frozen summary.
    """
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))
    text, readme, notes = prose("THESIS.md"), prose("README.md"), prose("PREDICTIONS.md")
    p, c, sg, v, a = s["population"], s["clients"], s["segments"], s["value_capture"], s["autumn"]
    w, pm, fall = v["windows"], p["partial_month"], p["largest_daily_fall"]
    thousand = lambda x: f"{x / 1e3:.0f} thousand"
    k = lambda x: f"{x / 1e3:.0f}"
    day = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%-d %B")
    share = lambda x: f"{x * 100:.0f}%"

    # the two events of the autumn, dated by rule
    step, above = a["intents_step"], a["above_reference_top"]
    words = {5: "five"}
    up, twice = step["price_usd"]["highest_in_the_week_from_it"], step["price_usd"]["first_day_at_twice_it"]
    assert twice["days_after"] // 7 == 4                                                       # "a month before it doubled"
    # counted without deleted accounts in every half-month, transactions are above the reference in one half-month only
    assert above["txns_less_deleted"] == ["2026-09-16..2026-09-30"]
    assert (step["day"], step["weekly_mean_above_it_since"]) == ("2026-08-19", "2026-08-21")
    burst = above["fees_near"]
    assert burst == above["gas_tgas"] == ["2026-09-16..2026-09-30", "2026-10-01..2026-10-15"]
    assert above["intents_volume_usd"] == above["buyback_usd"] == [h for h in a["half_months"] if h >= "2026-08-16"]
    first, last = day(burst[0][:10]), day(burst[-1][-10:])
    halves = a["half_months"]
    sep2, oct1, oct2 = (halves[h] for h in ("2026-09-16..2026-09-30", "2026-10-01..2026-10-15", "2026-10-16..2026-10-31"))
    top = a["reference"]["top"]
    sample = a["sample_halves"]
    keys = list(sample)
    assert keys == ["2026-08-14..2026-08-31", "2026-09-01..2026-09-15", "2026-09-16..2026-09-30", "2026-10-01..2026-10-15",
                    "2026-10-16..2026-10-31", "2026-11-01..2026-11-11"]
    sp = [sample[h]["self_paid_outside_namespaces"]["per_day"] for h in keys]
    ex = [sample[h]["exchange"] for h in keys]
    assert all(0.99 < x["ratio"] < 1.01 for x in a["sample_halves_vs_census"].values())          # "to within 1%"
    # the sample by month and cut at the step month
    view = c["sample_view"]
    aug_now, aug_then = view["by_month"]["recent"]["2026-08"]["finance"], view["by_month"]["prior"]["2025-08"]["finance"]
    nov_then = view["by_month"]["prior"]["2025-11"]["finance"]
    split = view["split"]["recent"]
    rec, pri = view["groups"]["finance"]["recent"], view["groups"]["finance"]["prior"]
    fin = c["finance_txs"]
    oct_now, oct_then = fin["latest"] / 31, fin["prior"] / 31
    # families of the self-paid series over the nine months before the step
    fam = s["predictions"]["step"]["core_self_paid_txs"]["range_by_family"]
    rng_txs = s["predictions"]["step"]["core_self_paid_txs"]["range_change_txs"]
    assert rng_txs == sum(f["range_change_txs"] for f in fam.values()) and fam["near"]["range_change_txs"] > 0
    calm = pm["core_direct_txs"]["without_dormant_implicit"]
    spike = pm["signer_spike"]
    ns, nsw = p["reward_namespaces_share_of_txs_by_month"], p["reward_namespaces_share_of_txs_windows"]
    spring = [ns[m] for m in ("2026-04", "2026-05", "2026-06", "2026-07", "2026-08")]
    assert min(spring) == ns["2026-08"] and max(spring) == ns["2026-04"]
    sm, al, one_off = sg["metrics"]["sponsored_accounts"], p["segments"]["all"]["accounts"], p["kaiching_one_off"]["single_tx_accounts"]
    whole = (sm["prior"] - sm["latest"]) / (al["prior"] - al["latest"]) * 100
    whole_clean = (sm["prior"] - sm["latest"]) / (al["prior"] - al["latest"] + one_off) * 100
    # the regular class dated, the game's accounts, the heavy accounts month by month
    reg, regfall, every = sg["regular_by_month"], sg["regular_fall_by_month"], sg["regular_accounts_largest_monthly_fall"]["every_bucket"]
    game_acc = sg["regular_accounts_reward_game_bound"]["game_accounts"]
    per_acc, direct = s["sponsors"]["txs_per_sponsored_account"]["meteor"], c["reward_game"]["direct"]["prior"]
    heavy = sg["heavy_by_month"]
    spring_heavy = [heavy[m] for m in ("2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09")]
    heavy_aug, heavy_oct = heavy["2026-08"]["self_paid_txs"], heavy["2025-10"]["self_paid_txs"]
    callers = {r["contract"]: r for r in c["finance_contract_callers"]}
    many = [r for r in c["finance_contract_callers"] if r["callers"]["prior"] > 1000]
    assert [r["contract"] for r in many if r["callers_pct_change"] > 0] == ["v2.ref-finance.near"]
    wrap, usdc, usdt, rhea, ref = (callers[x] for x in ("wrap.near", "17208628f84f5d6ad33f0da3bbbeb27ffcb398eac501a31bd6ad2011e36133a1",
                                                       "usdt.tether-token.near", "token.rhealab.near", "v2.ref-finance.near"))
    # value: windows, months, the buybacks in NEAR, the wallets against all revenue
    roll, by_len, by_m = w["rolling_90d"], w["by_length"], w["by_month"]
    bb = w["buybacks_per_day_before_and_from_the_step"]
    ever = v["wallets"]["defillama_revenue_near_all_time"]
    # the day KaiChing stopped, by the column that tracks relayed users, and the run before it
    ac, run = fall["active_contracts"], fall["run_before_the_fall"]
    burst_apr = {b["month"]: b for b in p["implicit_one_transaction_bursts"]["bursts"]}
    tg = p["reward_namespace_txs_per_day_by_month"]["tg"]
    hot = s["sponsors"]["hot_relayers_by_month"]["0here.tg"]
    tg_now = pm["reward_namespaces"]["tg"]
    old = p["old_tx_share_by_payer"]
    fees = fall["fees_near"]
    fees_lost = s["yoy_90d"]["fees_near"]["prior"] - s["yoy_90d"]["fees_near"]["recent"]
    act = {o["lag_weeks"]: o["corr"] for o in s["lead_vs_price"]["active_accounts"]["outside_band"]}
    gone = p["deleted_accounts"]["months"]
    named = p["named_one_transaction_bursts"]
    nb = list(named["months"])
    dec, cell = gone["2025-12"]["burst_days"], gone["2025-12"]["census_cell_that_left"]
    without = p["core_direct_txs_without_bursts_monthly"]
    nine = [str(x) for x in __import__("pandas").period_range("2025-12", "2026-08", freq="M")]
    earlier = [f"{int(x[:4]) - 1}{x[4:]}" for x in nine]
    nine_both = (sum(without["without_both"][x] for x in nine) / sum(without["without_both"][x] for x in earlier) - 1) * 100
    calm9 = p["core_direct_txs_from_dormant_implicit"]["change_by_window_without_them"]
    both9 = named["change_by_window_without_them_and_the_dormant_implicit"]
    rng_calm = s["predictions"]["step"]["core_self_paid_txs"]["range_pct_change_without_dormant_implicit"]
    bots = c["exchange_bot_targets_with_the_oracle_by_name"]
    oracle = next(x for x in c["other_top_40"]["latest"] if x["contract"] == "aggregate-oracle.near")
    adj = sg["self_paid_txs_adjustments"]["reward_side_direct_txs_outside_the_40_at_most"]
    twelve = p["core_direct_txs_change_12_months_with_the_tables_first_month"]["pct_change"]
    feb, octo = gone["2026-02"]["burst_days"], gone["2026-10"]["burst_days"]
    th = w["threshold_price"]
    quoted = [
        f"stepped up on {day(step['day'])} and have held, while the load on the chain itself (its fees and gas) ran high for the four "
        f"weeks of the price rally, from {first} to {last}",
        f"(100.6% of the net fall as counted, 99.2% with the one-off deletion taken out)".replace("100.6", f"{whole:.1f}").replace("99.2", f"{whole_clean:.1f}"),
        f"named `.near` accounts sent {fam['near']['range_pct_change']:.0f}% more than a year earlier, implicit accounts "
        f"{abs(fam['implicit']['range_pct_change']):.0f}% less (those under a year old "
        f"{abs(fam['implicit']['by_age_and_activity']['under_a_year']['pct_change']):.0f}% less) and other accounts "
        f"{abs(fam['other']['range_pct_change']):.0f}% less",
        f"it runs at {thousand(calm['per_day'])} a day, {abs(calm['latest_complete_month']['pct_change']):.0f}% below October's rate",
        f"{thousand(aug_now['per_day'])} transactions a day against {thousand(aug_then['per_day'])}",
        # claim 6, 7, 8, 10
        f"the whole fall of {abs(rng_txs) / 1e6:.2f}M transactions over those nine months is implicit accounts "
        f"(−{abs(fam['implicit']['range_change_txs']) / 1e6:.2f}M, {pct(fam['implicit']['range_pct_change'])}; "
        f"{pct(fam['implicit']['range_pct_change_without_dormant_implicit'])} without the February burst) and other accounts "
        f"(−{abs(fam['other']['range_change_txs']) / 1e6:.2f}M, {pct(fam['other']['range_pct_change'])}); named `.near` accounts sent "
        f"{fam['near']['range_change_txs'] / 1e6:.2f}M more ({pct(fam['near']['range_pct_change'])})",
        f"of the one-off of {day(spike['date'])} taken out of every month compared, as from February, {thousand(calm['per_day'])} against "
        f"{thousand(calm['latest_complete_month']['per_day'])} ({pct(calm['latest_complete_month']['pct_change'])}) and "
        f"{thousand(calm['same_month_a_year_earlier']['per_day'])} in November 2025 ({pct(calm['same_month_a_year_earlier']['pct_change'])})",
        f"it runs at {thousand(calm['per_day'])} a day, {abs(calm['latest_complete_month']['pct_change']):.0f}% below October's rate and "
        f"{abs(calm['same_month_a_year_earlier']['pct_change']):.0f}% below November 2025's",
        f"({thousand(rec['transactions_per_30_days'] / 30)} a day against {thousand(oct_now)} by October's full count), while last "
        f"year's window sits below October 2025 ({k(pri['transactions_per_30_days'] / 30)} against {thousand(oct_then)})",
        f"from {thousand(aug_then['per_day'])} a day in its days of August to {thousand(nov_then['per_day'])} in its days of November",
        f"{thousand(aug_now['per_day'])} a day (95% interval {k(aug_now['per_day_ci95'][0])} to {thousand(aug_now['per_day_ci95'][1])}), "
        f"above the {thousand(aug_then['per_day'])} ({k(aug_then['per_day_ci95'][0])} to {thousand(aug_then['per_day_ci95'][1])})",
        f"went from {k(split['before']['exchange_and_tokens']['per_day'])} to {thousand(split['from']['exchange_and_tokens']['per_day'])} a "
        f"day ({pct(view['split']['recent']['pct_change']['exchange_and_tokens'])}) and Intents and the bridges from "
        f"{k(split['before']['intents_and_bridges']['per_day'])} to {thousand(split['from']['intents_and_bridges']['per_day'])} "
        f"({pct(view['split']['recent']['pct_change']['intents_and_bridges'])})",
        f"${step['volume']['day_before'] / 1e6:.0f}M on 18 August, ${step['volume']['day'] / 1e6:.0f}M on the 19th, at a price of "
        f"${step['price_usd']['day']:.2f} that rose {up['pct_change']:.0f}% to ${up['value']:.2f} by {day(up['date'])} and first stood at "
        f"twice the step day's price on {day(twice['date'])}; the weekly mean has stayed above the top of the range before "
        f"(${step['line'] / 1e6:.1f}M) since {day(step['weekly_mean_above_it_since'])}, its lowest since being "
        f"${step['lowest_weekly_mean_since'] / 1e6:.1f}M",
        f"on a day it was ${step['price_usd']['day']:.2f} ({up['pct_change']:.0f}% higher {words[up['days_after']]} days later, at ${up['value']:.2f})",
        f"On the day of the step the price fell {abs(step['price_usd']['day_before']['pct_change_to_the_day']):.0f}%, to its lowest since "
        f"{day(step['price_usd']['lowest_since'])}; it rose from the next day ({up['pct_change']:.0f}% higher on {day(up['date'])} than on "
        f"the 19th) and first stood at twice the step day's level on {day(twice['date'])}",
        f"{min(by_len[x]['coverage'] for x in by_len) * 100:.0f}% to {max(by_len[x]['coverage'] for x in by_len) * 100:.0f}% over other "
        f"windows, and {roll['median'] * 100:.0f}% in the median 90-day window",
        # who pays: the payer dated, the game's accounts, the heavy accounts
        f"fell from {reg['2025-10']['self_paid_txs'] / 1e6:.2f}M in October 2025 to {reg['2025-12']['self_paid_txs'] / 1e6:.2f}M in December "
        f"while its accounts went from {reg['2025-10']['accounts']:,} to {reg['2025-12']['accounts']:,}",
        f"from {thousand(reg['2025-11']['relayed_txs'])} in November to {thousand(reg['2025-12']['relayed_txs'])} in December: by January "
        f"{share(regfall['2026-01']['share_of_the_self_paid_txs_fall'])} of the fall in self-paid transactions to the August low had "
        f"happened, and {share(regfall['2026-01']['share_of_the_accounts_fall'])} of the fall in accounts",
        f"self-paying accounts with 2 to 9 transactions fell {abs(every['self 2-9']['pct_change']):.0f}% and sponsored accounts with 10 to "
        f"99 transactions {abs(every['sponsored 10-99']['pct_change']):.0f}%",
        f"which leaves at least {game_acc['prior']['only_direct_at_least']:,} and puts the game at {game_acc['prior']['at_least']:,} to "
        f"{game_acc['prior']['at_most']:,} accounts in all. If nobody calls it directly now, that is a fall of "
        f"{abs(game_acc['pct_change_if_nobody_calls_it_directly_now'][1]):.0f}% to {abs(game_acc['pct_change_if_nobody_calls_it_directly_now'][0]):.0f}%",
        f"made {per_acc['2025-10']:.0f} transactions each a year ago and {per_acc['2026-10']:.0f} now, about as many as the direct "
        f"players made then ({direct['transactions_per_account']:.1f})",
        f"there were {min(h['accounts'] for h in spring_heavy)} to {max(h['accounts'] for h in spring_heavy)} heavy accounts, and they sent "
        f"{min(h['share'] for h in spring_heavy) * 100:.0f}% to {max(h['share'] for h in spring_heavy) * 100:.0f}% of the self-paid "
        f"transactions every month; in August 2026 they sent {M(heavy_aug)}, {abs(heavy_aug / heavy_oct - 1) * 100:.0f}% fewer than in "
        f"October 2025",
        # the customers: the month in context, the callers
        f"the reward apps sent {share(ns['2026-10'])} of October's transactions against {share(ns['2026-09'])} in September, "
        f"{share(min(spring))[:-1]}% to {share(max(spring))} in each month from April to August and {share(ns['2026-11'])} in the first "
        f"11 days of November ({share(nsw['3'])} over the last three months, {share(nsw['6'])} over six)",
        f"except the exchange's main contract ({ref['callers']['prior']:,} → {ref['callers']['latest']:,}): `wrap.near` "
        f"{wrap['callers']['prior']:,} → {wrap['callers']['latest']:,} ({pct(wrap['callers_pct_change'])}) while its transactions rose "
        f"{wrap['transactions_pct_change']:.0f}%, USDC {usdc['callers']['prior']:,} → {usdc['callers']['latest']:,} "
        f"({pct(usdc['callers_pct_change'])}) while they rose {usdc['transactions_pct_change']:.0f}%, USDT {usdt['callers']['prior']:,} → "
        f"{usdt['callers']['latest']:,} ({pct(usdt['callers_pct_change'])}) and `token.rhealab.near` {rhea['callers']['prior']:,} → "
        f"{rhea['callers']['latest']:,} ({pct(rhea['callers_pct_change'])})",
        # value capture by window, month and unit
        f"Of the {roll['windows']} windows of 90 days since the buybacks began, it is the {roll['rank_of_the_latest']}th highest; the "
        f"median window covers {roll['median'] * 100:.1f}%, and the windows that end before the step of {day(bb['step_day'])} cover "
        f"{roll['ending_before_the_step']['min'] * 100:.1f}% to {roll['ending_before_the_step']['max'] * 100:.1f}%",
        f"(7 days {by_len['7']['coverage'] * 100:.1f}%, 30 days {by_len['30']['coverage'] * 100:.1f}%, 60 days "
        f"{by_len['60']['coverage'] * 100:.1f}%, 180 days {by_len['180']['coverage'] * 100:.1f}%, the whole programme "
        f"{by_len['programme']['coverage'] * 100:.1f}%), and calendar months {by_m['2026-08']['coverage'] * 100:.1f}% (August), "
        f"{by_m['2026-09']['coverage'] * 100:.1f}% (September), {by_m['2026-10']['coverage'] * 100:.1f}% (October) and "
        f"{by_m['2026-11']['coverage'] * 100:.1f}% (the first 11 days of November)",
        f"{by_len['90']['captured_share'] * 100:.0f}% over these 90 days, {by_len['30']['captured_share'] * 100:.0f}% over the last 30, "
        f"{by_len['programme']['captured_share'] * 100:.0f}% over the whole programme and "
        f"{w['reference_months']['captured_share'] * 100:.0f}% over March to August",
        f"the pace of the whole programme is ${by_len['programme']['buyback_usd_annualized'] / 1e6:.1f}M",
        f"In USD they went from ${bb['usd'][0]:,.0f} a day before 19 August to ${bb['usd'][1]:,.0f} a day since "
        f"({bb['usd_ratio']:.1f} times); in NEAR, from {bb['near'][0]:,.0f} to {bb['near'][1]:,.0f} NEAR a day ({bb['near_ratio']:.1f} "
        f"times), and over the last 30 days they ran at {bb['last_30_days_near']:,.0f} NEAR a day, about the level of August "
        f"({by_m['2026-08']['buyback_near_per_day']:,.0f})",
        f"the {v['wallets']['held_near_at_end_all_wallets'] / 1e6:.2f}M NEAR they hold at the end is {ever['held_at_end_over_it']:.2f} of "
        f"all the captured revenue the series has counted since {ever['from']} ({ever['near'] / 1e6:.2f}M NEAR at each day's price)",
        # the day KaiChing stopped
        f"on {ac['one_day']['date']} it is {ac['one_day']['value']:,} against {ac['one_day']['relayed_users']:,} users behind relayers",
        f"It fell by {ac['fall']:,} from 1 to 2 April, against {ac['kaiching_relayed_txs_in_the_month_of']:,} transactions that "
        f"KaiChing's relayer submitted in the whole of April. That match suggests the relayer's last day was 1 April",
        f"KaiChing sent at least those {ac['kaiching_relayed_txs_in_the_month_of']:,} on 1 April and at most the other "
        f"{fall['kaiching']['month_of']['txs'] - fall['kaiching']['month_of']['relayed_txs']:,} of its April transactions on 2 April, so it is at least "
        f"{fall['kaiching_share_of_the_fall_at_least_if_relayer_ended_the_day_before'] * 100:.0f}% of the one-day fall, and at most "
        f"{fall['kaiching_share_of_the_fall_at_most'] * 100:.0f}% in any case",
        f"KaiChing can be at most {fall['kaiching_share_of_the_fall_at_most'] * 100:.0f}% of that one-day fall (everything it sent in "
        f"April); the census is monthly, so how much it was is not measured. If its relayer sent all of April's relayed "
        f"transactions on 1 April, as a column of the daily data suggests, it is at least "
        f"{fall['kaiching_share_of_the_fall_at_least_if_relayer_ended_the_day_before'] * 100:.0f}%",
        f"on every day from {day(run['first'])} to {day(run['last'])}, {M(run['transactions_above_it_in_the_month_before'])} above the "
        f"median of the days before in March alone, against {burst_apr['2026-03']['accounts'] / 1e6:.1f} million accounts of the burst in "
        f"March, while `active_contracts` stayed within the range of the days before ({run['active_contracts_range_before'][0] / 1e6:.2f}M "
        f"to {run['active_contracts_range_before'][1] / 1e6:.2f}M) until 1 April",
        # evidence against: the halves, November, HOT, the largest accounts, old accounts, fees, lags
        f"ran at {thousand(sp[1])} a day in the first half of September, {thousand(sp[2])} in the second, {thousand(sp[3])} in the first "
        f"half of October and {thousand(sp[4])} in the second",
        f"on {day(spike['date'])} NearBlocks counted {spike['signers']:,} signers against {spike['median_other_day']:,.0f} on the median "
        f"day of the others, and the census has {calm['dormant_implicit_single_tx_accounts']['2026-11']:,} dormant implicit accounts with "
        f"one transaction in those 11 days against {calm['dormant_implicit_single_tx_accounts']['2026-10']:,} in all of October",
        f"the series runs at {thousand(calm['per_day'])} a day, {abs(calm['latest_complete_month']['pct_change']):.0f}% below October's "
        f"rate and {abs(calm['same_month_a_year_earlier']['pct_change']):.0f}% below November 2025's, and the month would total "
        f"{M(calm['whole_month_at_that_rate'])}, "
        f"{(calm['whole_month_at_that_rate'] / s['predictions']['baselines']['core_self_paid_txs_plateau_top'] - 1) * 100:.1f}% above the threshold",
        f"volume stepped up on {day(step['day'])}, at a price of ${step['price_usd']['day']:.2f}, and has held "
        f"({step['days_of_the_month_from_it']} of August's days, {share(step['share_of_the_month_volume_from_it'])} of its volume and "
        f"{share(step['share_of_the_month_buybacks_from_it'])} of its buybacks, are after the step)",
        f"to 15 October and in no other: {sep2['fees_near']:,.0f} and {oct1['fees_near']:,.0f} NEAR of fees a day against "
        f"{top['fees_near']:,.0f}",
        f"{thousand(sep2['txns_less_deleted'])} a day against a top of {thousand(top['txns_less_deleted'])}, and "
        f"{thousand(oct1['txns_less_deleted'])} in the first half of October, when the deletion of old KaiChing accounts lifted the "
        f"count as reported to {thousand(oct1['txns'])}",
        f"back at {thousand(oct2['txns_less_deleted'])} transactions and {oct2['fees_near']:,.0f} NEAR of fees a day, when the price was "
        f"still ${oct2['price_usd']:.2f} on average",
        f"the exchange rose earlier, from 1 September: {thousand(ex[0]['per_day'])} transactions a day (95% interval "
        f"{k(ex[0]['per_day_ci95'][0])} to {thousand(ex[0]['per_day_ci95'][1])}) from 14 to 31 August, "
        f"{thousand(ex[1]['per_day'])} in the first half of September, {thousand(ex[2]['per_day'])} and "
        f"{thousand(ex[3]['per_day'])} in the next two half-months, {thousand(ex[4]['per_day'])} (95% interval "
        f"{k(ex[4]['per_day_ci95'][0])} to {thousand(ex[4]['per_day_ci95'][1])}) in the second half of October and "
        f"{thousand(ex[5]['per_day'])} in November",
        f"its namespace sent {thousand(tg['2026-07'])} transactions a day in July, {thousand(tg['2026-08'])} in August, "
        f"{thousand(tg['2026-09'])} in September and {thousand(tg['2026-10'])} in October",
        f"paid everything for {hot['2026-08']['accounts']:,} accounts in August, {hot['2026-09']['accounts']:,} in September and "
        f"{hot['2026-10']['accounts']:,} in October",
        f"Old accounts sent {share(old['prior']['relayed'])} of the sponsored core transactions a year ago and send "
        f"{share(old['latest']['relayed'])} now, against {share(old['prior']['self_paid'])} and {share(old['latest']['self_paid'])} of the "
        f"self-paid ones, and sponsored transactions shrank from {share(old['prior']['relayed_part_of_core_txs'])} of the core to "
        f"{share(old['latest']['relayed_part_of_core_txs'])}",
        f"({share(old['prior']['self_paid'])} → {share(old['latest']['self_paid'])}; {share(old['three_months_prior']['self_paid'])} → "
        f"{share(old['three_months_latest']['self_paid'])} over three months); at last year's mix of the two, October 2026 would give "
        f"{share(old['latest_at_prior_mix'])}",
        f"{fees['before']:,.0f} NEAR of fees on 1 April, {fees['after']:,.0f} on 2 April, and {fees['median_day']['month_before']:,.0f} NEAR "
        f"on the median day of March against {fees['median_day']['month_after']:,.0f} on the median day of May, "
        f"{fees['median_day']['fall']:,.0f} of the {fees_lost:,.0f} NEAR a day the 90-day figure lost",
        f"active accounts r = {act[0]:.2f} at lag 0 and {act[-5]:.2f} at −5 weeks (price first)",
        f"{tg_now['accounts']:,}, more than in all of October", f"with {tg_now['txs_per_account']:.1f} transactions each and "
        f"{share(tg_now['older_than_1y_account_share'])} of them older than a year",
        # limits: what the 40 largest cannot show, the first month, the bursts the filter does not catch, the oracle
        f"up to {adj['prior']:,} more a year ago (two such contracts) and {adj['latest']:,} now (one)",
        f"twelve months against the twelve before, which need it, give {pct(twelve).replace('−5%', f'−{abs(twelve):.1f}%')}",
        f"they rose by {feb['signers_per_deleted_account']:.2f} for each deleted account (correlation {feb['correlation_of_signers_with_deletions']} "
        f"from 3 to 18 February; {octo['signers_per_deleted_account']:.2f} and {octo['correlation_of_signers_with_deletions']} for the "
        f"deletions of old KaiChing accounts",
        f"{named['months'][nb[0]]:,}, {named['months'][nb[1]]:,} and {named['months'][nb[2]]:,} existing `.near` accounts not active the "
        f"month before sent one transaction in March, April and May 2025, against {named['median_month']:,.0f} in the median month",
        f"NearBlocks counted {gone[nb[0]]['deleted_accounts']:,}, {gone[nb[1]]['deleted_accounts']:,} and {gone[nb[2]]['deleted_accounts']:,} "
        f"deletions in those months",
        f"move the nine-month window from {pct(calm9['9'])} to {pct(both9['9'])}, the eleven-month one from {pct(calm9['11'])} to "
        f"{pct(both9['11'])}, and the nine months before the step from {pct(rng_calm)} to {pct(nine_both)}",
        f"NearBlocks counted {dec['deleted_accounts']:,} deletions on {words[dec['days']]} days from 17 to 22 December",
        f"{cell['month']['accounts']:,} in December, {cell['month']['single_tx_accounts']:,} of them with one transaction, and "
        f"{cell['month_after']['accounts']:,} in January",
        f"(387,762 in October 2025)",
        f"a second group: {burst_apr['2026-04']['first_seen_the_month_before_single_tx_accounts']:,} implicit accounts first seen in March",
        f"`aggregate-oracle.near` ({oracle['transactions']:,} transactions from {oracle['accounts']} accounts;",
        f"all three make it {pct(bots['exchange_pct_change_with_them'])}, the financial group {pct(bots['finance_pct_change_with_them'])}, "
        f"everything else {pct(c['three_parts']['rest_without_exchange_bot_targets_and_the_oracle_by_name']['pct_change'])}, and the "
        f"financial group without `escrow.ai.near` {pct(c['failing_senders']['finance_pct_change_without_them_and_with_the_oracle_by_name'])}",
    ]
    assert (dec["first"], dec["last"], dec["days"], cell["family"], cell["age"]) == ("2025-12-17", "2025-12-22", 5, "implicit", "lt2y")
    assert s["sponsors"]["month"]["sponsored_by_ember"]["prior"] == 387762
    assert (burst_apr["2026-04"]["first_seen_the_month_before_relayed_tx_share"] > 0.5 and bots["latest"] == oracle["transactions"])
    missing = [q for q in quoted if q not in text]
    assert not missing, f"THESIS.md does not quote these summary values: {missing}"
    in_readme = [
        f"({whole_clean:.1f}% of the fall with a one-off deletion of old accounts taken out)",
        f"named `.near` accounts {pct(fam['near']['range_pct_change'])}",
        f"({abs(calm['latest_complete_month']['pct_change']):.0f}% and {abs(calm['same_month_a_year_earlier']['pct_change']):.0f}% below "
        f"without a one-off of dormant accounts on {day(spike['date'])})",
        f"({thousand(aug_now['per_day'])} transactions a day against {thousand(aug_then['per_day'])})",
        f"(by namespace {share(ns['2026-10'])} in October against {share(min(spring))[:-1]}% to {share(max(spring))} a month from April to August)",
        f"It stepped up on {day(step['day'])}, as the price began to move and a month before it doubled",
        f"the sixth-best of {roll['windows']} such windows since they began ({min(by_len[x]['coverage'] for x in by_len) * 100:.0f}% to "
        f"{max(by_len[x]['coverage'] for x in by_len) * 100:.0f}% over other windows; ${by_len['programme']['buyback_usd_annualized'] / 1e6:.1f}M "
        f"a year at the pace of the whole programme). In NEAR their step was {bb['near_ratio']:.1f} times, in USD {bb['usd_ratio']:.1f} times",
        f"stepped up on {day(step['day'])} and have held, while the load on the chain (its fees and gas) ran high only for the four weeks "
        f"of the price rally, from {first} to {last}",
    ]
    assert roll["rank_of_the_latest"] == 6                                                            # "the sixth-best"
    missing = [q for q in in_readme if q not in readme]
    assert not missing, f"README.md does not quote these summary values: {missing}"
    in_notes = [
        f"therefore holds {step['days_of_the_month_from_it']} days of the step: {share(step['share_of_the_month_volume_from_it'])} of its "
        f"Intents volume and {share(step['share_of_the_month_buybacks_from_it'])} of its buybacks came after {day(step['day'])}",
        f"({th['near_per_day']:,.0f} NEAR a day), December's buybacks exceed ${th['threshold_usd'] / 1e6:.2f}M at any mean price above "
        f"${th['mean_price_that_meets_it']:.2f}, and the price was ${th['price_on_the_step_day']:.2f} on the day of the step",
        f"with the same filter, {thousand(calm['per_day'])} a day and {M(calm['whole_month_at_that_rate'])} a month, "
        f"{(calm['whole_month_at_that_rate'] / s['predictions']['baselines']['core_self_paid_txs_plateau_top'] - 1) * 100:.1f}% above the threshold",
        f"({share(ns['2026-10'])} of transactions by namespace, against {share(min(spring))[:-1]}% to {share(max(spring))} a month from "
        f"April to August)",
    ]
    assert th["month"] == "2026-12"
    missing = [q for q in in_notes if q not in notes]
    assert not missing, f"PREDICTIONS.md does not quote these summary values: {missing}"


def test_the_texts_quote_the_eighth_review_readings():
    """Means against medians, a family cut by age, a unit changed from USD to NEAR, a step dated to the day, a one-off
    named by its own shape: each number below answers a reading that a single mean, month or unit had left open."""
    s = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))
    text, readme, notes = prose("THESIS.md"), prose("README.md"), prose("PREDICTIONS.md")
    p, a, v, c = s["population"], s["autumn"], s["value_capture"]["windows"], s["clients"]
    st = s["predictions"]["step"]["core_self_paid_txs"]
    thousand = lambda x: f"{x / 1e3:.0f} thousand"
    day = lambda d: datetime.strptime(d, "%Y-%m-%d").strftime("%-d %B")
    halves, med, ref = a["half_months"], a["half_months_median"], a["reference"]
    oct2, nov = "2026-10-16..2026-10-31", "2026-11-01..2026-11-11"
    # 1. HOT by month and by day
    tg, tg_rel = p["reward_namespace_txs_per_day_by_month"]["tg"], p["reward_namespace_relayed_txs_per_day_by_month"]["tg"]
    hot, rel = s["sponsors"]["sponsored_by_month"]["hot"], s["sponsors"]["hot_relayers_by_month"]
    assert min(tg_rel, key=tg_rel.get) == "2026-09" and len(tg_rel) == 24
    assert "2026-09" not in rel["0-relay.hot.tg"] and rel["0here.tg"]["2026-09"]["accounts"] == hot["2026-09"]
    pm = p["partial_month"]["daily"]
    ru = a["one_day_moves_relayed"]["relayed_users"]
    ac = a["one_day_moves"]["active_contracts"]["2026-11"]["rise"]
    assert ru["2026-11"]["rise"]["date"] == ac["date"] == "2026-11-09" and ru["2026-08"]["fall"]["date"] == "2026-08-21"
    days = sorted(pm["txns"])
    before = [pm["txns"][d] for d in days if d < ac["date"]]
    after = [pm["txns"][d] for d in days if d >= ac["date"]]
    sig = {d: x for d, x in pm["active_accounts"].items() if d not in ("2026-11-01", "2026-11-02", "2026-11-10")}
    # 2. implicit accounts by age, named accounts by age
    imp, near = st["range_by_family"]["implicit"]["by_age_and_activity"], st["range_by_family"]["near"]["by_age_and_activity"]
    # 3. buybacks in NEAR by mean and by median, and by calendar month
    bn, top_day = ref["top"]["buyback_near"], ref["top_half_largest_day"]["buyback_near"]
    by_m = v["by_month"]
    assert ref["top_half"]["buyback_near"] == "2026-06-01..2026-06-15"
    assert oct2 not in a["above_reference_top"]["buyback_near"] and oct2 in a["above_reference_top_by_median"]["buyback_near"]
    assert a["above_reference_top"]["fees_near"] == a["above_reference_top_by_median"]["fees_near"]
    spring = [by_m[m]["coverage"] for m in ("2026-04", "2026-05", "2026-06", "2026-07")]
    # 4. the price after the step
    pr = a["intents_step"]["price_usd"]
    # 5. the one-off of 10 November
    sweep = c["one_block_transfers_sample"]
    assert sweep["prior"] == [] and len(sweep["recent"]) == 1
    b = sweep["recent"][0]
    assert b["senders"] == b["implicit_senders"] == b["senders_older_than_a_year"] == 8 and len(b["receiver"]) == 64
    # 6. the base of May and June
    base, price = st["base_of_the_months_above"], st["price_usd_by_month"]
    assert [base[m]["rank_lowest_first_among_base_months"] for m in ("2026-05", "2026-06")] == [2, 1]
    assert [h for h, x in ref["top_half"].items() if x != "2026-06-01..2026-06-15" and h in a["above_reference_top"]] == ["new_contracts"]
    # 7. native transfers in NEAR; 9. new contracts
    tv = [halves[h]["transfer_volume_near"] / 1e6 for h in halves if h >= "2026-08-01"]
    assert a["above_reference_top"]["transfer_volume_near"] == ["2026-09-16..2026-09-30", "2026-10-01..2026-10-15"]
    nc = [halves[h]["new_contracts"] for h in halves if "2026-07-01" <= h < "2026-09-01"]
    late = [halves[h]["new_contracts"] for h in ("2026-09-16..2026-09-30", "2026-10-01..2026-10-15", oct2)]
    # 8. December's deletions in the self-paid series
    dl = st["deletions_in_the_range"]
    dec = dl["months"]["2025-12"]
    gone = p["deleted_accounts"]["months"]
    assert dl["taken_out"] == ["2025-12"] and dl["payer_table_first_month"] == "2025-08"
    assert {"2024-12", "2025-01"} <= set(dl["base_months_with_deletions"])
    quoted = [
        f"through relayers {tg_rel['2026-07'] / 1e3:.0f}, {tg_rel['2026-08'] / 1e3:.0f}, {tg_rel['2026-09'] / 1e3:.0f} and "
        f"{tg_rel['2026-10'] / 1e3:.0f} thousand ({thousand(tg_rel['2026-11'])} in November); September is the lowest of the "
        f"{len(tg_rel)} months of that series",
        f"The accounts HOT paid everything for went {hot['2026-07']:,.0f}, {hot['2026-08']:,.0f}, {hot['2026-09']:,.0f} and "
        f"{hot['2026-10']:,.0f} from July to October",
        f"`0-relay.hot.tg`, paid everything for {rel['0-relay.hot.tg']['2026-08']['accounts']:,} of them in August",
        f"went from {ru['2026-11']['rise']['day_before']:,.0f} on 8 November to {ru['2026-11']['rise']['day']:,.0f} on the 9th, the "
        f"largest one-day rise of the month",
        f"averaged {sum(before) / len(before) / 1e3:.0f} thousand a day from 1 to 8 November and "
        f"{sum(after) / len(after) / 1e3:.0f} thousand from 9 to 11",
        f"`active_contracts` moved the same day, from {ac['day_before']:,.0f} to {ac['day']:,.0f}",
        f"from {pm['active_accounts']['2026-11-01']:,} and {pm['active_accounts']['2026-11-02']:,} on 1 and 2 November to between "
        f"{min(sig.values()):,} and {max(sig.values()):,} on the other days but the 10th",
        f"from {ru['2026-08']['fall']['day_before']:,.0f} on 20 August to {ru['2026-08']['fall']['day']:,.0f} on the 21st, the largest "
        f"one-day fall of August",
        f"they sent {imp['under_a_year']['a_year_earlier'] / 1e6:.2f}M self-paid transactions a year earlier and "
        f"{imp['under_a_year']['range'] / 1e6:.2f}M now ({pct(imp['under_a_year']['pct_change'])})",
        f"sent {imp['older_active_the_month_before']['a_year_earlier'] / 1e6:.2f}M → {imp['older_active_the_month_before']['range'] / 1e6:.2f}M "
        f"({pct(imp['older_active_the_month_before']['pct_change'])}) and older ones that had not sent "
        f"{imp['older_not_active_the_month_before']['change'] / 1e6:.2f}M more",
        f"named `.near` accounts under a year old sent {abs(near['age_lt1y']['change']) / 1e6:.2f}M fewer and those one to two years "
        f"old {near['age_lt2y']['change'] / 1e6:.2f}M more",
        f"their mean from 16 to 31 October ({halves[oct2]['buyback_near']:,.0f} NEAR a day) and from 1 to 11 November "
        f"({halves[nov]['buyback_near']:,.0f}) is below the top before the step ({bn:,.0f}), while their median day is above the top "
        f"of the median days ({ref['top_median']['buyback_near']:,.0f}) by {(med[oct2]['buyback_near'] / ref['top_median']['buyback_near'] - 1) * 100:.0f}% "
        f"and {(med[nov]['buyback_near'] / ref['top_median']['buyback_near'] - 1) * 100:.0f}%",
        f"rests on one day, {day(top_day['date'])} 2026, with {top_day['value']:,.0f} NEAR, {top_day['share_of_the_half'] * 100:.0f}% of its "
        f"half-month; March's mean ({by_m['2026-03']['buyback_near_per_day']:,.0f} NEAR a day) rests on "
        f"{day(by_m['2026-03']['largest_day_near']['date'])} in the same way ({by_m['2026-03']['largest_day_near']['value']:,.0f} NEAR, "
        f"{by_m['2026-03']['largest_day_near']['share_of_the_month'] * 100:.0f}% of the month), and its median day is "
        f"{by_m['2026-03']['buyback_near_per_day_median']:,.0f}",
        f"March was {by_m['2026-03']['coverage'] * 100:.1f}% as well, April to July {min(spring) * 100:.1f}% to {max(spring) * 100:.1f}%",
        f"fees a day against {ref['top']['fees_near']:,.0f}. By the median day as well ({med['2026-09-16..2026-09-30']['fees_near']:,.0f} and "
        f"{med['2026-10-01..2026-10-15']['fees_near']:,.0f} NEAR against a top of {ref['top_median']['fees_near']:,.0f})",
        f"but {(halves[nov]['price_usd'] / pr['day'] - 1) * 100:.0f}% above its price on the day of the step "
        f"(${halves[nov]['price_usd']:.2f} against ${pr['day']:.2f}). After the step the price never fell below "
        f"${pr['lowest_after_it']['value']:.2f} ({day(pr['lowest_after_it']['date'])})",
        f"NearBlocks counted {pm['deleted_accounts']['2026-11-10']}. The keyless sample has one block of that day in which eight "
        f"implicit accounts older than a year each sent a plain transfer to the same implicit account (block {b['height']}, at "
        f"{b['time_utc'][-5:]} UTC; one of the {b['blocks_sampled_that_day']} blocks sampled that day",
        f"February was deletions ({gone['2026-02']['deleted_accounts'] / 1e6:.2f} million by NearBlocks)",
        f"which are set against the two lowest months of the base ({base['2026-05']['base'] / 1e6:.2f}M in May 2025 and "
        f"{base['2026-06']['base'] / 1e6:.2f}M in June 2025) and came with the price's previous rise, from "
        f"${price['2026-04']:.2f} a day on average in April 2026 to ${price['2026-06']:.2f} in June",
        f"(${halves['2026-06-01..2026-06-15']['price_usd']:.2f} a day on average in it)",
        f"{tv[0]:.1f}M NEAR a day in the first half of August, then {tv[1]:.1f}M, {tv[2]:.1f}M, {tv[3]:.1f}M and {tv[4]:.1f}M to 15 "
        f"October, and {tv[5]:.1f}M and {tv[6]:.1f}M since, above their earlier top ({ref['top']['transfer_volume_near'] / 1e6:.1f}M)",
        f"{min(nc):.1f} to {max(nc):.1f} a day by half-months in July and August 2026, {min(late):.0f} to {max(late):.0f} from 16 "
        f"September to 31 October and {halves[nov]['new_contracts']:.1f} in the first 11 days of November",
        f"the payer table has {dec['accounts']:,} self-paying accounts outside the app namespaces with one transaction in December "
        f"2025, {dec['above_the_median_month']:,} above its median month ({dec['median_month']:,.0f}), "
        f"{dec['share_of_the_month'] * 100:.1f}% of that month's self-paid transactions",
        f"the nine months before the step are −{abs(dl['range_pct_change_without_them']):.1f}% instead of "
        f"−{abs(st['range_pct_change']):.1f}%",
        f"NearBlocks counted {gone['2024-12']['deleted_accounts']:,} in December 2024 and {gone['2025-01']['deleted_accounts']:,} in "
        f"January 2025",
    ]
    missing = [q for q in quoted if q not in text]
    assert not missing, f"THESIS.md does not quote these summary values: {missing}"
    assert dl["range_pct_change_without_them"] < st["range_pct_change"] < 0       # taken out of the range only: a larger fall
    assert halves[nov]["new_contracts"] == max(x["new_contracts"] for x in halves.values())   # "the highest half-month since 16 April"
    in_readme = ["What held is the volume and the buybacks in USD; the buybacks in NEAR have held by the median day and not by the mean"]
    assert oct2 in a["above_reference_top"]["buyback_usd"]
    missing = [q for q in in_readme if q not in readme]
    assert not missing, f"README.md does not quote these: {missing}"
    in_notes = [f"(NearBlocks counted {pm['deleted_accounts']['2026-11-10']} that day)"]
    missing = [q for q in in_notes if q not in notes]
    assert not missing, f"PREDICTIONS.md does not quote these summary values: {missing}"
