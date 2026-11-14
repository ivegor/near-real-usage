"""Charts. Each chart = one PNG + one plain sentence generated from the numbers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter  # noqa: E402

from . import metrics, population, segments, value  # noqa: E402

INK, ACCENT, MUTED, GRID = "#1f2328", "#00a27a", "#8c959f", "#e6e8eb"


@dataclass
class Chart:
    slug: str
    title: str
    sentence: str
    method: str
    source: str = ""  # repo path of the query or code behind the chart, linked from the dashboard


def _style(ax, title: str):
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=MUTED, labelsize=8)


def _plain(ax, dense: bool = False):
    """Readable tick labels on log axes (no 10^x notation). dense=True also labels 2x and 5x."""
    if dense:
        ax.yaxis.set_major_locator(LogLocator(base=10, subs=(1.0, 2.0, 5.0)))
    fmt = FuncFormatter(lambda v, _: f"{v:,.0f}" if v >= 10 else f"{v:g}")
    ax.yaxis.set_major_formatter(fmt)
    ax.yaxis.set_minor_formatter(NullFormatter())


def _pos(s: pd.Series) -> pd.Series:
    """Hide zero / negative values so a log axis shows a gap instead of a vertical drop."""
    return s.where(s > 0)


def _legend_below(ax, handles=None, labels=None):
    args = (handles, labels) if handles else ()
    ax.legend(*args, frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.1), ncol=3)


def _pct(x: float) -> str:
    return "n/a" if x is None or not np.isfinite(x) else f"{x:+.0f}%"


def _save(fig, out: Path, slug: str):
    fig.tight_layout()
    fig.savefig(out / f"{slug}.png", dpi=140, bbox_inches="tight")
    plt.close(fig)


LEAD_LABELS = {"returning_accounts": "active - new (proxy)", "active_accounts": "active accounts",
               "intents_volume_usd": "intents volume", "fees_near": "fees (in NEAR)", "fees_usd": "fees (in USD)",
               "txns": "transactions"}
FAMILY_STYLE = {"kaiching": ("KaiChing reward app", MUTED, "--"), "tg": ("HOT wallet (.tg)", "#c9a227", "--"),
                "core": ("everyone else (core)", ACCENT, "-"), "near": ("named .near accounts", INK, "-")}


def _population_chart(pop: pd.DataFrame, summary: dict, out: Path) -> Chart:
    """Every account that acted in a month (BigQuery, full population): how many, how sticky, how old."""
    ps = summary["population"]
    months = population.complete_months(pop, ps["query_end"])
    x = pd.to_datetime(months)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.7))

    ax = axes[0]
    for name, (label, color, style) in FAMILY_STYLE.items():
        m = population.monthly(population.segment(pop, name)).reindex(months)["accounts"]
        ax.plot(x, _pos(m), color=color, linestyle=style, label=label)
    ax.set_yscale("log")
    ax.set_ylim(bottom=10_000)  # KaiChing falls to a handful of accounts after April 2026 and leaves the chart
    _plain(ax)
    _style(ax, "Accounts active in the month (log scale)")
    one_off = ps["kaiching_one_off"]["accounts"]
    if one_off > 10_000:  # the reappearance at the right edge is not a comeback: say what it is on the chart itself
        ax.annotate(f"one-off: {one_off / 1e3:.0f}K old KaiChing accounts,\none transaction each", xy=(x[-1], one_off),
                    xytext=(x[len(x) // 4], 17_000), textcoords="data", fontsize=6.5, color=MUTED, va="center",
                    arrowprops={"arrowstyle": "-", "color": MUTED, "linewidth": 0.6})
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)

    ax = axes[1]
    core = population.monthly(population.segment(pop, "core")).reindex(months)
    ax.plot(x, core["accounts"] / 1e6, color=MUTED, label="core accounts")
    ax.plot(x, core["returning_accounts"] / 1e6, color=ACCENT, label="also active the month before")
    ax.plot(x, core["old_accounts"] / 1e6, color=INK, linewidth=0.9, label="older than 1 year")
    ax.set_ylim(0, 3)  # Feb-Mar 2026: millions of existing accounts sent one transaction each and run off the scale
    _style(ax, "Core accounts, millions")  # a longer title runs into the next panel's
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)

    ax = axes[2]
    ax.plot(x, core["direct_txs"] / 1e6, color=ACCENT, label="paid by the sender")
    ax.plot(x, core["relayed_txs"] / 1e6, color=MUTED, label="sponsored through a relayer")
    ax.set_ylim(bottom=0)
    _style(ax, "Core transactions, millions a month")
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    for a in axes:
        a.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 7]))
        a.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        a.tick_params(axis="x", labelsize=7)
    _save(fig, out, "population")

    seg = ps["segments"]
    c, n, k, al = seg["core"], seg["near"], seg["kaiching"], seg["all"]
    lm, pm = ps["latest_month"], ps["prior_month"]

    def M(v: float) -> str:
        return f"{v / 1e6:.2f}M" if v >= 1e6 else f"{v / 1e3:.0f}K"

    c3, one, ex = c["three_month_mean"], ps["kaiching_one_off"], seg["all_ex_kaiching"]
    gone = ((summary.get("clients") or {}).get("kaiching_accounts_sample") or {}).get("recent") or {}
    # in the keyless block sample every transaction of these accounts is the deletion of the account itself
    one_off = ("that were deleted, one transaction each" if gone.get("transactions") and gone["transactions"] == gone.get("delete_account")
               else "that sent one transaction each in a single sweep")
    quota, quota_note = ps.get("kaiching_relayed_txs_per_day"), ""
    if quota and quota["months_within_a_thousandth_of_it"]:  # the same number of transactions every day is a job, not a crowd
        quota_note = (f" Its relayer submitted {quota['median_month_to_the_nearest_thousand']:,.0f} transactions a day, to within a "
                      f"thousandth, in {len(quota['months_within_a_thousandth_of_it'])} of its "
                      f"{quota['months_with_relayed_transactions']} months in the census ({quota['first_month']} to "
                      f"{quota['last_month']}), by its monthly totals: a job with a daily quota, as far as monthly totals can show.")
    check, checked = ps.get("totals_check"), ""
    if check:  # the same transactions counted by a second, independent source
        short = [abs(v["share"]) * 100 for v in check["differ"].values()]
        checked = (f" Checked against NearBlocks month by month: in {check['agree']['months']} of {check['months']} months the two "
                   f"transaction counts differ by at most {check['agree']['largest_difference_txs']:,} transactions")
        if short:
            checked += (f"; in the other {len(short)} ({', '.join(check['differ'])}) BigQuery is lower by "
                        f"{min(short):.1f}% to {max(short):.1f}%")
        checked += "."
    pace, so_far = (ps.get("partial_month") or {}).get("core_direct_txs"), ""
    if pace and "latest_complete_month" in pace:  # the days of the unfinished month the scan covers: where the series is heading
        was, year = pace["latest_complete_month"], pace.get("same_month_a_year_earlier")
        so_far = (f" In the first {pace['days']} days of {ps['partial_month']['month']} those self-paid transactions ran at "
                  f"{pace['per_day'] / 1e3:,.0f}K a day, against {was['per_day'] / 1e3:,.0f}K a day in {was['month']} "
                  f"({_pct(was['pct_change'])})"
                  + (f" and {year['per_day'] / 1e3:,.0f}K in {year['month']} ({_pct(year['pct_change'])})" if year else "") + ".")
    rates = (ps.get("partial_month") or {}).get("txs_per_day") or {}
    hot = rates.get("tg") or {}
    if hot.get("partial") and hot.get("latest_complete"):  # the same days for the largest reward namespace that is left
        share = rates["reward_namespaces_share_of_txs"]
        so_far += (f" In the same days HOT's namespace (.tg) sent {hot['partial'] / 1e3:,.0f}K transactions a day against "
                   f"{hot['latest_complete'] / 1e3:,.0f}K in {rates['latest_complete_month']} ({_pct(hot['pct_change'])}), and the "
                   f"reward apps' namespaces {share['partial'] * 100:.0f}% of all transactions against "
                   f"{share['latest_complete'] * 100:.0f}%.")
    return Chart(
        "population", "Every active account, counted (full chain, not a sample)",
        f"In {lm}, {M(al['accounts']['latest'])} accounts acted on NEAR against {M(al['accounts']['prior'])} in {pm} "
        f"({_pct(al['accounts']['pct_change'])}). {M(one['accounts'])} of them are old accounts of the reward app KaiChing "
        f"{one_off}; the app itself had {M(k['accounts']['prior'])} accounts a year "
        f"earlier and stopped in spring 2026.{quota_note} Without KaiChing: {M(ex['accounts']['prior'])} to {M(ex['accounts']['latest'])} "
        f"({_pct(ex['accounts']['pct_change'])}). Accounts outside the reward namespaces went {M(c['accounts']['prior'])} to "
        f"{M(c['accounts']['latest'])} ({_pct(c['accounts']['pct_change'])}; {_pct(c3['accounts']['pct_change'])} on three-month "
        f"means) and those also active the month before {M(c['returning_accounts']['prior'])} to "
        f"{M(c['returning_accounts']['latest'])} ({_pct(c['returning_accounts']['pct_change'])}); most of those accounts were "
        f"sponsored users of other apps, see the next chart. Their transactions paid by the "
        f"sender changed {_pct(c['direct_txs']['pct_change'])} ({_pct(c3['direct_txs']['pct_change'])} on three-month means) "
        f"while those sponsored through relayers changed {_pct(c['relayed_txs']['pct_change'])}.{so_far} Transactions per account in that group "
        f"rose from {c['txs_per_account']['prior']:.1f} to {c['txs_per_account']['latest']:.1f} a month, but with last year's "
        f"mix of account types it would be {ps['core_txs_per_account_at_prior_mix']:.1f} "
        f"({_pct((ps['core_txs_per_account_at_prior_mix'] / c['txs_per_account']['prior'] - 1) * 100)}): most of the rise is "
        f"low-activity accounts leaving. Named .near accounts: {_pct(n['accounts']['pct_change'])} "
        f"({_pct(n['three_month_mean']['accounts']['pct_change'])} on three-month means).",
        "sql/account_age.sql on the NEAR BigQuery public dataset (all transactions, 482.64 GB scanned, result in "
        "data/bq/account_age.csv). The actor of a relayed transaction is the user, not the relayer. Core = accounts outside "
        f"the kaiching, .tg and .sweat namespaces. The scan ends on {ps['query_end']}, so the last month shown is {lm}; the "
        f"table starts in {ps.get('table_first_month', ps['first_month'])}, which has no month before it to say which accounts "
        f"returned, so every series starts in {ps['first_month']}. "
        "In February and March 2026 millions of existing implicit accounts sent one transaction each; those two months "
        "are off the scale in the middle panel." + checked,
    )


def _value_chart(d: pd.DataFrame, fees: pd.DataFrame, vc: dict, out: Path) -> Chart:
    """Buybacks funded by Intents revenue against the value of the NEAR created in the same month."""
    m = value.monthly(d, fees)
    x = np.arange(len(m))
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.bar(x - 0.27, m["new_supply_value"] / 1e6, width=0.27, color=MUTED, label="value of net new NEAR supply")
    ax.bar(x, m["fees"] / 1e6, width=0.27, color="#9bd8c6", label="Intents gross fees")
    ax.bar(x + 0.27, m["holders_revenue"] / 1e6, width=0.27, color=ACCENT, label="captured, arriving at the revenue wallets (DefiLlama: buybacks)")
    ax.set_xticks(x, [str(p) for p in m.index], fontsize=6.5)
    _style(ax, "USD millions per month")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    _save(fig, out, "value_capture")
    return Chart(
        "value_capture", "Does it reach the token?",
        f"Over the 90 days to {vc['window'][1]} NEAR Intents charged ${vc['intents_gross_fees_usd'] / 1e6:.1f}M in fees "
        f"({vc['intents_fees_vs_l1_fees']:.0f}x the network's own transaction fees) and NEAR captured "
        f"${vc['captured_revenue_usd'] / 1e6:.2f}M of it ({vc['captured_share_of_gross_fees'] * 100:.0f}%), all of it, by DefiLlama's "
        f"description, used to buy NEAR on the market since {vc['buyback_start']}. That is ${vc['buyback_usd_annualized'] / 1e6:.1f}M a year against "
        f"${vc['new_supply_value_usd_annualized'] / 1e6:.0f}M a year of net new NEAR "
        f"({vc['net_new_supply_near_annualized'] / 1e6:.1f}M NEAR at ${vc['mean_price_usd']:.2f}): the buybacks equal "
        f"{vc['buyback_coverage_of_new_supply'] * 100:.0f}% of the net new supply (a ratio of flows, not a measured offset), and the market capitalisation is "
        f"{vc['market_cap_to_annual_buyback']:.0f} times the annual buyback.",
        "DefiLlama fee series for NEAR Intents (dailyFees, dailyRevenue, dailyHoldersRevenue); net new supply = change in "
        "NearBlocks' daily total supply (already net of burned fees) valued at the mean price of the period. The window ends "
        "on the last day both sources cover. The bought NEAR is not burned, so supply itself does not shrink. What is checked "
        "here is the NEAR arriving at the revenue wallets and staying there; the purchases on the market are not."
        + (f" The fee series ends {vc['days_behind_the_daily_series']} days before the daily data."
           if vc.get("days_behind_the_daily_series", 0) > 1 else ""),
    )


def _segments_chart(seg: pd.DataFrame, sg: dict, out: Path) -> Chart:
    """Accounts by who pays the fee and how often they act."""
    s = segments.series(seg)
    x = pd.to_datetime(s.index)
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
    ax = axes[0]
    for col, label, color, style in (
            ("sponsored_accounts", "an app pays for them (sponsored)", MUTED, "--"),
            ("app_namespace_self_paying_accounts", "HOT wallet users paying their own fees", "#c9a227", "--"),
            ("regular_accounts", "independent, regular (10 to 999 tx a month)", ACCENT, "-"),
            ("heavy_accounts", "independent, heavy (1,000+ tx a month)", INK, "-")):
        ax.plot(x, _pos(s[col]), color=color, linestyle=style, label=label)
    ax.set_yscale("log")
    _plain(ax)
    _style(ax, "Accounts active in the month, by who pays (log scale)")
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
    ax = axes[1]
    bottom = np.zeros(len(s))
    for col, label, color in (("heavy_self_paid_txs", "heavy accounts", INK), ("regular_self_paid_txs", "regular", ACCENT),
                              ("occasional_self_paid_txs", "occasional (under 10 a month)", "#9bd8c6")):
        ax.bar(x, s[col] / 1e6, bottom=bottom, width=20, color=color, label=label)
        bottom += (s[col] / 1e6).to_numpy()
    _style(ax, "Self-paid transactions of independent accounts, millions")
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    for a in axes:
        a.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
        a.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
        a.tick_params(axis="x", labelsize=7)
    _save(fig, out, "segments")
    m = sg["metrics"]

    def both(k: str) -> str:
        return f"{_pct(m[k]['pct_change'])} ({_pct(m[k]['three_month_mean']['pct_change'])} on three-month means)"

    game, game_note = sg.get("regular_accounts_reward_game_bound"), ""
    if game:  # part of that fall is one game changing who pays, not accounts leaving
        game_note = (f" That fall is not a clean count of users leaving: up to {game['game_players_prior']:,} of last year's accounts "
                     f"called the Meteor wallet's reward game themselves and paid the fees; its relayer submits the game's calls now.")
        clean = game.get("without_the_game")
        if clean:  # players are inside the self-paying count of both years, so one rule takes them out of both
            then, now = (clean["players"][k]["paying_through_the_relayer"] for k in ("prior", "latest"))
            high, both_years = clean["pct_change_high"], clean.get("relayer_term_only")
            game_note += (f" In either year an account that acts through that relayer and pays for a transaction of its own can "
                          f"be a player too: up to {then:,} a year ago and {now:,} now.")
            if both_years:  # the one term counted in both years, then what the direct callers of last year add
                game_note += (f" Without those, the players counted in both years, the change lies between "
                              f"{_pct(both_years['pct_change_low'])} and {_pct(both_years['pct_change_high'])}.")
            game_note += (f" The direct callers are counted a year ago only: with them out as well the high end is "
                          f"{_pct(high[segments.OVERLAP[0]])} or more ({_pct(high[segments.OVERLAP[1]])} if none of last year's "
                          f"{then:,} called the game directly), and the low end, {_pct(clean['pct_change_low'])}, is open below, "
                          f"because who calls the game directly now the tables do not say.")
        else:
            game_note += (f" With all of them taken out of last year's count the change would be "
                          f"{_pct(game['pct_change_if_all_of_them_were_regular'])}.")
    adj, adj_note = sg.get("self_paid_txs_adjustments"), ""
    if adj and "pct_change_without_both" in adj:  # what the tables show inside those transactions that is not independent use
        side = adj["reward_side_direct_txs"]
        adj_note = (f" Both months hold transactions that are not independent use: direct calls to reward-side contracts "
                    f"({side['prior'] / 1e6:.2f}M in {sg['prior_month']}, {side['latest'] / 1e6:.2f}M in {sg['latest_month']}) and, in "
                    f"{sg['latest_month']}, {adj['failing_sender_txs_latest'] / 1e6:.2f}M from an account whose sampled calls all "
                    f"failed. Without them the change is {_pct(adj['pct_change_without_both'])} if every caller of those contracts "
                    f"is outside the reward namespaces; how many are inside them the tables do not say, and the two ends are "
                    f"{_pct(adj['pct_change_without_both_both_ends'][0])} and {_pct(adj['pct_change_without_both_both_ends'][1])}.")
    return Chart(
        "segments", "Who pays, and how often",
        f"Accounts whose fees an app paid: {m['sponsored_accounts']['prior'] / 1e6:.1f}M in {sg['prior_month']}, "
        f"{m['sponsored_accounts']['latest'] / 1e6:.2f}M in {sg['latest_month']}. Accounts that pay for themselves and are not in a "
        f"reward app's namespace, acting 10 to 999 times a month: {m['regular_accounts']['prior']:,.0f} to "
        f"{m['regular_accounts']['latest']:,.0f}, {both('regular_accounts')}; their low was {sg['regular_accounts_low']['value']:,.0f} in "
        f"{sg['regular_accounts_low']['month']}.{game_note} Accounts sending 1,000 or more a month: {m['heavy_accounts']['prior']:,.0f} to "
        f"{m['heavy_accounts']['latest']:,.0f}, and they send {sg['heavy_share_of_independent_self_paid_txs']['latest'] * 100:.0f}% of "
        f"those self-paid transactions, which changed {both('independent_self_paid_txs')}.{adj_note}",
        "sql/payer_frequency.sql on the NEAR BigQuery public dataset (91.28 GB), result in data/bq/payer_frequency.csv. "
        "Sponsored = every transaction of the account that month was submitted by a relayer. Frequency classes are powers "
        "of ten of the monthly transaction count; 1,000 a month is more than 30 a day. Occasional accounts (under 10 a "
        "month) swing with one-off events and are not read as a trend.",
        source="sql/payer_frequency.sql",
    )


def _clients_chart(cl: dict, out: Path) -> Chart:
    """Which apps send the transactions, and how few accounts it takes."""
    lm, pm = cl["latest_month"], cl["prior_month"]
    apps = sorted(cl["apps"].items(), key=lambda kv: kv[1]["latest_share"])
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.9), gridspec_kw={"width_ratios": [1.7, 1]})
    ax = axes[0]
    names = [k for k, _ in apps]
    y = np.arange(len(names))
    ax.barh(y + 0.19, [v["latest_share"] * 100 for _, v in apps], height=0.38, color=ACCENT, label=lm)
    ax.barh(y - 0.19, [v["prior_share"] * 100 for _, v in apps], height=0.38, color=MUTED, label=pm)
    ax.set_yticks(y, names, fontsize=7.5)
    ax.set_xlabel("% of all transactions in the month", fontsize=7, color=MUTED)
    _style(ax, "Who the transactions belong to")
    ax.legend(frameon=False, fontsize=7, loc="center right")
    ax = axes[1]
    labels = ["top 10", "top 25", "top 100", "1,000+ tx"]
    keys = ["top10_share", "top25_share", "top100_share", "their_tx_share"]
    x = np.arange(len(labels))
    ax.bar(x - 0.19, [cl["months"][pm][k] * 100 for k in keys], width=0.38, color=MUTED, label=pm)
    ax.bar(x + 0.19, [cl["months"][lm][k] * 100 for k in keys], width=0.38, color=ACCENT, label=lm)
    ax.set_xticks(x, labels, fontsize=7.5)
    ax.set_ylim(0, 100)
    _style(ax, "Share of transactions sent by the largest accounts, %")
    ax.legend(frameon=False, fontsize=7, loc="upper left")
    _save(fig, out, "clients")
    a, L, P, i = cl["apps"], cl["months"][lm], cl["months"][pm], cl["intents"]
    ref, sw = a["Ref Finance / Rhea (DEX, lending)"], a["Sweat (move-to-earn app)"]
    parts, view, more = cl.get("three_parts"), (cl.get("sample_view") or {}).get("groups", {}).get("finance"), ""
    if parts:  # the two bottom bars hold Ember and KaiChing's own accounts; without them the rest of the chain did not shrink
        more += (f" Counted in three parts, with the game Ember and KaiChing's own accounts on the reward side: the reward side changed "
                 f"{_pct(parts['reward_side']['pct_change'])}, the finance group {_pct(parts['finance']['pct_change'])}, and everything "
                 f"else is {parts['rest']['latest'] / 1e6:.2f}M transactions against {parts['rest']['prior'] / 1e6:.2f}M "
                 f"({_pct(parts['rest']['pct_change'])}).")
    if view:  # two calendar months against two 90-day windows of the keyless sample
        lo, hi = view["pct_change_ci95"]
        more += (f" On the keyless 90-day block sample the finance group changed {_pct(view['pct_change'])} "
                 f"(95% interval {_pct(lo)} to {_pct(hi)}).")
    if cl.get("finance_txs_change_range"):  # the group's contracts that one month's 40 do not show
        lo, hi = cl["finance_txs_change_range"]
        more += (f" Allowing for the group's contracts that are not among a month's 40 largest, its change on the full "
                 f"count lies between {_pct(lo)} and {_pct(hi)}.")
    failing = cl.get("failing_senders")
    if failing:  # a count is not always use: one sender's sampled calls all failed, and its transactions are in the group
        sampled, who = sum(v["transactions"] for v in failing["sampled"].values()), " and ".join(failing["sampled"])
        more += (f" A count is not always use: all {sampled} sampled calls of {who} to {failing['target']} failed. Without the "
                 f"{failing['transactions_latest_all'] / 1e6:.2f}M transactions that {who} sent in {lm}, the finance group "
                 f"changed {_pct(failing['finance_pct_change_without_them'])}.")
    return Chart(
        "clients", "Who sends the transactions",
        f"In {lm}, {L['accounts_for_half_of_txs']} accounts sent half of NEAR's {L['transactions'] / 1e6:.1f}M transactions "
        f"and the top 10 sent {L['top10_share'] * 100:.0f}% ({P['top10_share'] * 100:.0f}% in {pm}). Reward and wallet apps "
        f"(Sweat, HOT, Meteor, KaiChing) are {cl['reward_apps_share']['latest'] * 100:.0f}% of transactions, down from "
        f"{cl['reward_apps_share']['prior'] * 100:.0f}%; Sweat alone is {sw['latest_share'] * 100:.0f}%. Trading, Intents, token "
        f"transfers and bridges are {cl['finance_share']['latest'] * 100:.0f}% (was {cl['finance_share']['prior'] * 100:.0f}%); "
        f"transactions on the Ref/Rhea exchange changed {_pct(ref['pct_change'])}. intents.near received "
        f"{i['latest']['transactions'] / 1e6:.2f}M transactions ({i['prior']['transactions'] / 1e6:.2f}M in {pm}), "
        f"up to {i['latest']['top2_share'] * 100:.0f}% of them signed by two accounts." + more,
        "sql/top_accounts.sql on the NEAR BigQuery public dataset (13.53 GB), result in data/bq/top_accounts_result.csv. "
        "A direct transaction is assigned to the contract it calls, a relayed one to its relayer; contracts and relayers are "
        "grouped into apps by the table in thesis/clients.py. A month counts only the contracts among its 40 largest; a "
        "group's other contracts are inside \"everything outside the top 40\" for that month. Intents users sign "
        "off-chain, so its on-chain signers are relayers, not users.",
    )


# The query or code behind each chart. The dashboard prints the SQL text of a query on the page and links the rest.
CHART_SOURCE = {
    "population": "sql/account_age.sql", "segments": "sql/payer_frequency.sql", "clients": "sql/top_accounts.sql",
    "value_capture": "thesis/value.py", "signer_census": "thesis/census.py", "accounts": "thesis/metrics.py",
    "usage_vs_price": "thesis/metrics.py", "tx_per_active": "thesis/metrics.py", "fees_per_active": "thesis/metrics.py",
    "intents": "thesis/sources.py", "lead_lag": "thesis/metrics.py",
}


def _holm_words(s: dict) -> str:
    h = s.get("lead_vs_price_holm") or {}
    n = h.get("significant")
    if n is None:
        return "no correction for multiple tests computed"
    return f"{'none' if n == 0 else n} of them {'stands' if n <= 1 else 'stand'} after Holm's correction for testing them together"


def _takeaway(slug: str, s: dict) -> str:
    """One plain sentence per chart, built from the same summary as the detailed caption. Empty if the data is absent."""
    try:
        if slug == "population":
            return f"NEAR lost {abs(s['population']['segments']['all']['accounts']['pct_change']):.0f}% of its active accounts in a year."
        if slug == "segments":
            sg = s["segments"]
            return (f"Almost all of the lost accounts were users an app was paying for; outside the reward apps, "
                    f"{sg['metrics']['heavy_accounts']['latest']:,.0f} heavy accounts send "
                    f"{sg['heavy_share_of_independent_self_paid_txs']['latest'] * 100:.0f}% of the transactions that senders pay for themselves.")
        if slug == "clients":
            c = s["clients"]
            return f"{c['months'][c['latest_month']]['accounts_for_half_of_txs']} accounts send half of all NEAR transactions."
        if slug == "value_capture":
            v = s["value_capture"]
            first = f"The revenue NEAR Intents captures for buybacks equals {v['buyback_coverage_of_new_supply'] * 100:.0f}% of the new NEAR issued."
            lengths = (v.get("windows") or {}).get("by_length")
            if lengths:  # one window is not the figure: the range over windows of other lengths ending on the same day
                cov = [x["coverage"] for x in lengths.values()]
                first = (f"The revenue NEAR Intents captures for buybacks equals {v['buyback_coverage_of_new_supply'] * 100:.0f}% of the new NEAR "
                         f"issued over the last 90 days, and {min(cov) * 100:.0f}% to {max(cov) * 100:.0f}% over windows from a "
                         f"week to the whole programme.")
            w = v.get("wallets")
            if not w:
                return first
            return (f"{first} Read from the chain, the three revenue wallets grew by {w['change_near_all_wallets'] / 1e6:.2f}M NEAR "
                    f"from {w['window'][0]} to {w['window'][1]}, {w['coverage_of_new_supply'] * 100:.1f}% of the new supply "
                    f"of those days ({w['last_days']['coverage_of_new_supply'] * 100:.1f}% over the last {w['last_days']['days']} of them)."
                    if "last_days" in w else first)
        if slug == "accounts":
            if "population" not in s:
                return "Returning accounts are estimated as active minus new accounts."
            return ("The usual proxy for returning accounts points the wrong way." if _proxy_points_the_other_way(s)
                    else "The usual proxy for returning accounts is not a count of them.")
        if slug == "usage_vs_price":
            y = s["yoy_90d"]
            return (f"Over a year the NEAR price changed {_pct(y['price_usd']['pct_change'])} and daily transactions "
                    f"{_pct(y['txns']['pct_change'])}.")
        if slug == "tx_per_active":
            return "Transactions per active account mostly show which apps are on the chain, not how people behave."
        if slug == "fees_per_active":
            return f"Total network fees changed {_pct(s['yoy_90d']['fees_usd']['pct_change'])} in a year."
        if slug == "intents":
            mi = s["month_yoy"]["intents_volume_usd"]
            st = (s.get("predictions") or {}).get("step") or {}
            v = st.get("intents_volume_usd_a_day") or {}
            if v.get("range_top"):  # a year-on-year figure depends on where last year's ramp-up was; the range does not
                where = "above" if mi["recent"] > v["range_top"] else "inside" if mi["recent"] >= v["range_low"] else "below"
                return (f"In {mi['month']} NEAR Intents volume averaged ${mi['recent'] / 1e6:,.0f}M a day, {where} the "
                        f"${v['range_low'] / 1e6:,.0f}M to ${v['range_top'] / 1e6:,.0f}M range it held from "
                        f"{st['reference_range']['first']} to {st['reference_range']['last']}.")
            return f"NEAR Intents volume changed {_pct(mi['pct_change'])} against the same month a year earlier."
        if slug == "signer_census":
            return "A sample of random blocks, taken without any API key, agrees with the full count."
        if slug == "lead_lag":
            from . import predictions
            # what was tested is a linear correlation of weekly changes at fixed lags: that finds no lead, it does not
            # rule out every kind of one
            return ("No usage metric leads price in these tests." if predictions.adjacent_positive_leads(s["lead_vs_price"]) == 0
                    else "Some usage metrics move before price; see the lags.")
    except (KeyError, TypeError):
        return ""
    return ""


def _proxy_points_the_other_way(s: dict) -> bool:
    """True while the aggregate proxy and the full-chain count of returning accounts changed in opposite directions.

    The proxy is a rolling 90-day comparison and the count is frozen with the census, so the sentence on the page
    is decided by the data of the day, not written once.
    """
    proxy = s["yoy_90d"]["returning_accounts"]["pct_change"]
    counted = s["population"]["segments"]["core"]["returning_accounts"]["pct_change"]
    if proxy is None or counted is None or not (np.isfinite(proxy) and np.isfinite(counted)):
        return False
    return (proxy > 0) != (counted > 0)


AGE_LABELS = {"365d+": "older than 1 year", "30-365d": "30 days to 1 year", "new": "newer than 30 days"}
AGE_COLORS = {"365d+": ACCENT, "30-365d": "#9bd8c6", "new": MUTED}


def _short(name: str, n: int = 26) -> str:
    return name if len(name) <= n else name[: n - 1] + "…"


def _census_chart(cs: dict, out: Path) -> Chart:
    """Who signs transactions: account age measured on sampled blocks, a year ago vs now."""
    w = cs["windows"]
    order = [("prior", f"{w['prior']['start']} to {w['prior']['end']}"), ("recent", f"{w['recent']['start']} to {w['recent']['end']}")]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), gridspec_kw={"width_ratios": [1.25, 1, 1]})
    ax = axes[0]
    rows = [(f"transactions\n{lab}", w[k]["tx_share_by_account_age"]) for k, lab in order]
    rows += [(f"sampled accounts\n{lab}", w[k]["account_share_by_age"]) for k, lab in order]
    for i, (lab, shares) in enumerate(rows):
        left = 0.0
        for c in ("365d+", "30-365d", "new"):
            v = shares[c] * 100
            ax.barh(i, v, left=left, color=AGE_COLORS[c], label=AGE_LABELS[c] if i == 0 else None)
            if v >= 7:
                ax.text(left + v / 2, i, f"{v:.0f}%", ha="center", va="center", fontsize=8, color=INK)
            left += v
    ax.set_yticks(range(len(rows)), [r[0] for r in rows], fontsize=7)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    _style(ax, "Age of the account behind each transaction")
    ax.grid(False)
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3)
    for ax, (k, lab) in zip(axes[1:], order):
        t = w[k]["top_targets"]
        names, vals = list(t)[:6][::-1], [v * 100 for v in list(t.values())[:6]][::-1]
        ax.barh([_short(n) for n in names], vals, color=ACCENT if k == "recent" else MUTED)
        _style(ax, f"Most-called contracts, {lab[:4]}" + (" (a year earlier)" if k == "prior" else " (now)"))
        ax.set_xlabel("% of sampled transactions", fontsize=7, color=MUTED)
        ax.tick_params(axis="y", labelsize=7)
    _save(fig, out, "signer_census")
    p, r = w["prior"], w["recent"]

    def share(win: dict, c: str) -> str:
        lo, hi = win["tx_share_ci95"][c]
        return f"{win['tx_share_by_account_age'][c] * 100:.0f}% (95% interval {lo * 100:.0f}-{hi * 100:.0f}%)"

    return Chart(
        "signer_census", "Who signs the transactions (measured on the chain)",
        f"Accounts older than one year sign {share(r, '365d+')} of transactions now, against {share(p, '365d+')} a year "
        f"earlier; accounts newer than 30 days sign {share(r, 'new')} now, against {share(p, 'new')}. "
        f"The ten busiest accounts send {r['top10_accounts_tx_share'] * 100:.0f}% of transactions now "
        f"({p['top10_accounts_tx_share'] * 100:.0f}% a year earlier).",
        f"Random block heights (seed {cs['seed']}) from the FastNEAR block archive: {r['blocks_found']} blocks / "
        f"{r['transactions']} transactions now, {p['blocks_found']} blocks / {p['transactions']} transactions a year earlier. "
        "For a relayed (meta) transaction the user is read from the delegate action. An account's age class comes from "
        "view_account on an archival RPC node at the block 30 and 365 days before the window starts. Intervals resample "
        "whole blocks. Sampled accounts over-represent frequent senders. Re-run: python -m thesis census [--seed N].",
    )


def build_all(daily: pd.DataFrame, summary: dict, out: Path) -> list[Chart]:
    out.mkdir(parents=True, exist_ok=True)
    d = metrics.add_derived(daily)
    r = metrics.rolling(d, 30)
    yoy = summary["yoy_90d"]
    bad = summary.get("checks", {}).get("new_exceeds_active_days", {})
    charts: list[Chart] = []

    # 1. Who is active: new vs returning
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(r.index, _pos(r["returning_accounts"]), color=ACCENT, label="returning (active - new)")
    ax.plot(r.index, _pos(r["new_accounts"]), color=MUTED, label="new accounts")
    ax.set_yscale("log")
    ax.set_ylim(bottom=1_000)
    _plain(ax)
    _style(ax, "Daily accounts, 30-day average (log scale)")
    _legend_below(ax)
    _save(fig, out, "accounts")
    proxy_title, proxy_note = "New vs returning accounts", ""
    if "population" in summary:
        core, ps = summary["population"]["segments"]["core"]["returning_accounts"], summary["population"]
        proxy_title = "What the daily aggregates show, and why they mislead"
        verdict = ("is wrong about the direction" if _proxy_points_the_other_way(summary) else "is not a count of returning accounts")
        proxy_note = (
            f" This proxy {verdict}: counted directly on the full chain, core accounts active two months "
            f"running changed {_pct(core['pct_change'])} from {ps['prior_month']} to {ps['latest_month']} (see the first chart). "
            "The aggregator's \"active accounts\" are transaction signers, so users acting through relayers are missing, and its "
            "\"new accounts\" include accounts created in bulk by a handful of creator accounts.")
    charts.append(Chart(
        "accounts", proxy_title,
        f"Over the last 90 days the proxy active - new averaged {yoy['returning_accounts']['recent']:,.0f}/day "
        f"({_pct(yoy['returning_accounts']['pct_change'])} vs a year earlier), new accounts "
        f"{yoy['new_accounts']['recent']:,.0f}/day ({_pct(yoy['new_accounts']['pct_change'])}). "
        f"By medians it changed {_pct(yoy['returning_accounts'].get('median_pct_change'))}." + proxy_note,
        "returning_accounts = active_accounts - new_accounts (NearBlocks daily charts), 30-day rolling mean. "
        "This is a lower bound: new accounts that did not transact on their first day are subtracted anyway. "
        f"New accounts exceeded active accounts (returning clipped to 0) on {bad.get('recent', 0)} of the last 90 days, "
        f"{bad.get('prior', 0)} of the 90 days a year earlier and {bad.get('all_history', 0)} days in all history "
        "(mostly mid-2022, shown as a gap).",
    ))

    # 2. Usage vs price
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(r.index, _pos(r["txns"]), color=ACCENT, label="transactions per day, 30d avg (left)")
    ax.set_yscale("log")
    ax.set_ylim(bottom=10_000)
    ax2 = ax.twinx()
    ax2.plot(d.index, _pos(d["price_usd"]), color=INK, linewidth=0.9, label="NEAR price, USD (right)")
    ax2.set_yscale("log")
    ax2.tick_params(colors=MUTED, labelsize=8)
    _plain(ax)
    _plain(ax2, dense=True)
    _style(ax, "Transactions vs NEAR price (log scales)")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    _legend_below(ax, h1 + h2, l1 + l2)
    _save(fig, out, "usage_vs_price")
    charts.append(Chart(
        "usage_vs_price", "Usage vs price",
        f"Price changed {_pct(yoy['price_usd']['pct_change'])} year-on-year (90-day averages) while daily "
        f"transactions changed {_pct(yoy['txns']['pct_change'])} and active accounts {_pct(yoy['active_accounts']['pct_change'])}.",
        "Same 90-day window compared with the window 365 days earlier.",
    ))

    # 3. Bot-intensity proxy
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(r.index, r["tx_per_active"], color=INK)
    _style(ax, "Transactions per active account, 30-day average")
    _save(fig, out, "tx_per_active")
    charts.append(Chart(
        "tx_per_active", "Transactions per active account",
        f"Each active account sent {yoy['tx_per_active']['recent']:.1f} transactions a day on average in the last 90 days "
        f"({_pct(yoy['tx_per_active']['pct_change'])} YoY). This aggregate moved with the reward apps: relayers that signed "
        "millions of transactions for other accounts count as single active accounts here, and most of them are gone.",
        "txns / active_accounts (NearBlocks), 30-day rolling mean. NearBlocks' active accounts are transaction signers; "
        "users acting through relayers are not counted, so this is not transactions per user (see the first chart).",
    ))

    # 4. Fees per active account
    fig, ax = plt.subplots(figsize=(8, 3.2))
    ax.plot(r.index, _pos(r["fees_per_active_usd"]), color=ACCENT, label="USD")
    ax.plot(r.index, _pos(r["fees_per_active_near"]), color=MUTED, label="NEAR")
    ax.set_yscale("log")
    ax.set_ylim(bottom=1e-3)
    _plain(ax, dense=True)
    _style(ax, "Fees paid per active account per day, 30-day average (log scale)")
    _legend_below(ax)
    _save(fig, out, "fees_per_active")
    fa, fn = yoy["fees_per_active_usd"], yoy["fees_per_active_near"]
    charts.append(Chart(
        "fees_per_active", "Fees per active account",
        f"An active account paid ${fa['recent']:.3f} a day in fees over the last 90 days "
        f"({_pct(fa['pct_change'])} YoY in USD, {_pct(fn['pct_change'])} in NEAR terms, "
        f"{_pct(fa.get('median_pct_change'))} by USD medians); total fees were "
        f"${yoy['fees_usd']['recent']:,.0f}/day ({_pct(yoy['fees_usd']['pct_change'])} YoY).",
        "txn_fee_usd / active_accounts (NearBlocks), 30-day rolling mean; NEAR terms = the same divided by the daily price. "
        "The denominator counts transaction signers only, so read the level with care; total fees do not depend on it.",
    ))

    # 5. Intents
    if "intents_volume_usd" in d and d["intents_volume_usd"].notna().any():
        iv = d["intents_volume_usd"].dropna()
        r7 = iv.rolling(7, min_periods=3).mean()
        fig, ax = plt.subplots(figsize=(8, 3.6))
        ax.plot(r7.index, r7, color=ACCENT, label="Intents volume, 7d avg (left)")
        ax.set_yscale("log")
        ax2 = ax.twinx()
        p = d["price_usd"].loc[iv.index.min():]
        ax2.plot(p.index, p, color=INK, linewidth=0.9, label="NEAR price, USD (right)")
        ax2.tick_params(colors=MUTED, labelsize=8)
        _plain(ax)
        _style(ax, "NEAR Intents daily volume (USD, log) vs price")
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax2.get_legend_handles_labels()
        _legend_below(ax, h1 + h2, l1 + l2)
        _save(fig, out, "intents")
        yi = yoy.get("intents_volume_usd", {})
        mi = summary.get("month_yoy", {}).get("intents_volume_usd", {})
        qi = summary.get("qoq_90d", {}).get("intents_volume_usd", {})
        st, rally = (summary.get("predictions") or {}).get("step") or {}, ""
        if st.get("intents_volume_usd_a_day"):  # the step up and the price rally are the same month: say so next to the chart
            v, pr = st["intents_volume_usd_a_day"], st["price_usd"]
            rally = (f" The step up in {st['month']} (${v['before'] / 1e6:,.1f}M to ${v['month'] / 1e6:,.1f}M a day) came in the "
                     f"month the NEAR price went from ${pr['first_day']:.2f} to ${pr['last_day']:.2f}.")
            if v.get("range_mean"):  # last year's base was still rising, so say what the level in between was
                was, rng = v["month_before_range"], st["reference_range"]
                rally += (f" A year earlier the base was still rising: {was['month']} already averaged ${was['value'] / 1e6:,.1f}M "
                          f"a day, and from {rng['first']} to {rng['last']} volume averaged ${v['range_mean'] / 1e6:,.1f}M.")
        step_day = (summary.get("autumn") or {}).get("intents_step")
        if step_day:  # by day the step came with the start of the price's move, before the price doubled
            pr = step_day["price_usd"]
            rally += (f" By day it came earlier: volume went from ${step_day['volume']['day_before'] / 1e6:,.0f}M to "
                      f"${step_day['volume']['day'] / 1e6:,.0f}M on {step_day['day']}, at a price of ${pr['day']:.2f}")
            up, twice = pr.get("highest_in_the_week_from_it"), pr.get("first_day_at_twice_it")
            if up:
                rally += f" that was {up['pct_change']:.0f}% higher {up['days_after']} days later"
            if twice:
                rally += f" and first stood at twice that on {twice['date']}"
            rally += (f"; its 7-day mean has stayed above ${step_day['line'] / 1e6:,.1f}M since "
                      f"{step_day['weekly_mean_above_it_since']}.")
        so_far = (summary.get("month_to_date_yoy") or {}).get("intents_volume_usd")
        if so_far:  # the days of the current month already in hand, against the same days a year earlier
            rally += (f" From {so_far['from']} to {so_far['through']} it averaged ${so_far['recent'] / 1e6:,.1f}M a day against "
                      f"${so_far['prior'] / 1e6:,.1f}M in the same days a year earlier ({_pct(so_far['pct_change'])}).")
        charts.append(Chart(
            "intents", "NEAR Intents volume",
            f"In {mi.get('month')} Intents volume averaged ${mi.get('recent', float('nan')) / 1e6:,.1f}M a day against "
            f"${mi.get('prior', float('nan')) / 1e6:,.1f}M in the same month a year earlier ({_pct(mi.get('pct_change'))}); "
            f"the last 90 days averaged ${yi.get('recent', float('nan')) / 1e6:,.1f}M a day, {_pct(qi.get('pct_change'))} on the "
            f"90 days before and {_pct(yi.get('pct_change'))} on the same 90 days a year earlier." + rally,
            "DefiLlama dexs/near-intents totalDataChart, 7-day rolling mean. Both year-on-year figures shrink as their "
            "base moves through the ramp-up of autumn 2025: the 90-day one every day, the calendar-month one at each "
            "month's end. The level the volume held between the two autumns does not move.",
        ))

    # 5a. Full-population account census from BigQuery (only when data/bq/account_age.csv exists)
    pop = population.load()
    if pop is not None and "population" in summary:
        charts.append(_population_chart(pop, summary, out))

    seg = segments.load()
    if seg is not None and "segments" in summary:
        charts.append(_segments_chart(seg, summary["segments"], out))
    if "clients" in summary:
        charts.append(_clients_chart(summary["clients"], out))

    fees = value.load()
    if fees is not None and "value_capture" in summary:
        charts.append(_value_chart(d, fees, summary["value_capture"], out))

    # 5b. Signer census (only when data/raw/census_* exists)
    cs = summary.get("signer_census")
    if cs and {"prior", "recent"} <= set(cs["windows"]):
        charts.append(_census_chart(cs, out))

    # 6. Lead-lag
    leads = summary["lead_vs_price"]
    if leads:
        names = list(leads)
        fig, axes = plt.subplots(1, len(names), figsize=(2.4 * len(names), 2.8), sharey=True)
        axes = np.atleast_1d(axes)
        for ax, name in zip(axes, names):
            ll = metrics.lead_lag(d[name], d["price_usd"])
            ax.bar(ll["lag_weeks"], ll["corr"], color=[ACCENT if k > 0 else MUTED for k in ll["lag_weeks"]])
            # the band of each lag, the one the text decides by: the sample loses a week per week of lag, so the band
            # is a little wider at the ends. It is carried to the edges of the panel, which keeps its limits.
            left, right = ax.get_xlim()
            xs = np.r_[left, ll["lag_weeks"].to_numpy(float), right]
            band = np.r_[ll["band"].iloc[0], ll["band"].to_numpy(float), ll["band"].iloc[-1]]
            for sign in (1, -1):
                ax.plot(xs, sign * band, color=INK, linestyle=":", linewidth=0.8)
            ax.set_xlim(left, right)
            _style(ax, LEAD_LABELS.get(name, name.replace("_", " ")))
            ax.set_xlabel("weeks metric leads price →", fontsize=7, color=MUTED)
        _save(fig, out, "lead_lag")
        parts = []
        for name, b in leads.items():
            outside = ", ".join(f"{o['lag_weeks']:+d} wk r={o['corr']:+.2f}" for o in b.get("outside_band", []))
            parts.append(f"{LEAD_LABELS.get(name, name.replace('_', ' '))}: {outside or 'nothing outside the noise band'}")
        n_out = sum(len(b.get("outside_band", [])) for b in leads.values())
        n_tests = 17 * len(leads)
        usd = summary.get("lead_fees_usd_mechanical", {})
        charts.append(Chart(
            "lead_lag", "Does usage lead price?",
            f"Weekly-change correlation with price, lags outside the noise band ({n_out} of {n_tests} tested; "
            f"about {0.05 * n_tests:.0f} expected by chance; {_holm_words(summary)}): " + "; ".join(parts) + ". Fees are tested in NEAR: in USD they "
            f"correlate with price in the same week (r={usd.get('corr', float('nan')):.2f}) mostly because USD fees are NEAR "
            "fees multiplied by the price.",
            "corr(Δlog metric_t, Δlog price_{t+k}), k in weeks, positive k = metric moves first (green bars); "
            "dotted lines = ±2/√n noise band of each lag.",
        ))
    for c in charts:  # the dashboard shows the first sentence on its own: make it the plain takeaway
        first = _takeaway(c.slug, summary)
        if first:
            c.sentence = f"{first} {c.sentence}"
        c.source = c.source or CHART_SOURCE.get(c.slug, "")
    lead = ["population", "segments", "clients", "value_capture"]  # the full-chain counts lead the dashboard
    charts.sort(key=lambda c: lead.index(c.slug) if c.slug in lead else len(lead))
    return charts
