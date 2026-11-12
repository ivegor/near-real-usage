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

from . import clients, metrics, population, value  # noqa: E402

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
# the query or code behind each chart, linked from the dashboard
SOURCE_OF = {"population": "sql/account_age.sql", "clients": "sql/top_accounts.sql", "signer_census": "thesis/census.py",
             "lead_lag": "thesis/metrics.py", "accounts": "thesis/sources.py", "usage_vs_price": "thesis/sources.py",
             "tx_per_active": "thesis/sources.py", "fees_per_active": "thesis/sources.py", "intents": "thesis/sources.py"}
FAMILY_STYLE = {"kaiching": ("KaiChing reward app", MUTED, "--"), "tg": ("HOT wallet (.tg)", "#c9a227", "--"),
                "core": ("everyone else (core)", ACCENT, "-"), "near": ("named .near accounts", INK, "-")}
POP_AGE = {"ge2y": ("older than 2 years", ACCENT), "lt2y": ("1 to 2 years", "#9bd8c6"), "lt1y": ("30 days to 1 year", "#d9dde1"),
           "lt30": ("under 30 days", "#b9c0c7"), "m0": ("first seen that month", MUTED)}


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
    _style(ax, "Core accounts, millions (no reward apps)")
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
    return Chart(
        "population", "Every active account, counted (full chain, not a sample)",
        f"In {lm}, {M(al['accounts']['latest'])} accounts acted on NEAR against {M(al['accounts']['prior'])} in {pm} "
        f"({_pct(al['accounts']['pct_change'])}). {M(one['accounts'])} of them are old accounts of the reward app KaiChing "
        f"that sent one transaction each in a single sweep; the app itself had {M(k['accounts']['prior'])} accounts a year "
        f"earlier and stopped in spring 2026. Without KaiChing: {M(ex['accounts']['prior'])} to {M(ex['accounts']['latest'])} "
        f"({_pct(ex['accounts']['pct_change'])}). Outside the reward apps, core accounts went {M(c['accounts']['prior'])} to "
        f"{M(c['accounts']['latest'])} ({_pct(c['accounts']['pct_change'])}; {_pct(c3['accounts']['pct_change'])} on three-month "
        f"means) and those also active the month before {M(c['returning_accounts']['prior'])} to "
        f"{M(c['returning_accounts']['latest'])} ({_pct(c['returning_accounts']['pct_change'])}). Core transactions paid by the "
        f"sender grew {_pct(c['direct_txs']['pct_change'])} ({_pct(c3['direct_txs']['pct_change'])} on three-month means) "
        f"while those sponsored through relayers fell {_pct(c['relayed_txs']['pct_change'])}. Transactions per core account "
        f"rose from {c['txs_per_account']['prior']:.1f} to {c['txs_per_account']['latest']:.1f} a month, but with last year's "
        f"mix of account types it would be {ps['core_txs_per_account_at_prior_mix']:.1f}: low-activity accounts left, "
        f"the rest did not get busier. Named .near accounts: {_pct(n['accounts']['pct_change'])} "
        f"({_pct(n['three_month_mean']['accounts']['pct_change'])} on three-month means).",
        "sql/account_age.sql on the NEAR BigQuery public dataset (all transactions, 482.64 GB scanned, result in "
        "data/bq/account_age.csv). The actor of a relayed transaction is the user, not the relayer. Core = accounts outside "
        f"the kaiching, .tg and .sweat namespaces. The scan ends on {ps['query_end']}, so the last month shown is {lm}. "
        "In February and March 2026 millions of existing implicit accounts sent one transaction each; those two months "
        "are off the scale in the middle panel.",
    )


def _value_chart(d: pd.DataFrame, fees: pd.DataFrame, vc: dict, out: Path) -> Chart:
    """Buybacks funded by Intents revenue against the value of the NEAR created in the same month."""
    m = value.monthly(d, fees)
    x = np.arange(len(m))
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.bar(x - 0.27, m["new_supply_value"] / 1e6, width=0.27, color=MUTED, label="value of net new NEAR supply")
    ax.bar(x, m["fees"] / 1e6, width=0.27, color="#9bd8c6", label="Intents gross fees")
    ax.bar(x + 0.27, m["holders_revenue"] / 1e6, width=0.27, color=ACCENT, label="captured and used for buybacks")
    ax.set_xticks(x, [str(p) for p in m.index], fontsize=6.5)
    _style(ax, "USD millions per month")
    ax.legend(frameon=False, fontsize=8, loc="upper left")
    _save(fig, out, "value_capture")
    return Chart(
        "value_capture", "Does it reach the token?",
        f"Over the last 90 days NEAR Intents charged ${vc['intents_gross_fees_usd'] / 1e6:.1f}M in fees "
        f"({vc['intents_fees_vs_l1_fees']:.0f}x the network's own transaction fees) and NEAR captured "
        f"${vc['captured_revenue_usd'] / 1e6:.2f}M of it ({vc['captured_share_of_gross_fees'] * 100:.0f}%), all used to buy NEAR "
        f"on the market since {vc['buyback_start']}. That is ${vc['buyback_usd_annualized'] / 1e6:.1f}M a year against "
        f"${vc['new_supply_value_usd_annualized'] / 1e6:.0f}M a year of net new NEAR "
        f"({vc['net_new_supply_near_annualized'] / 1e6:.1f}M NEAR at ${vc['mean_price_usd']:.2f}): buybacks cover "
        f"{vc['buyback_coverage_of_new_supply'] * 100:.0f}% of dilution, and the market capitalisation is "
        f"{vc['market_cap_to_annual_buyback']:.0f} times the annual buyback.",
        "DefiLlama fee series for NEAR Intents (dailyFees, dailyRevenue, dailyHoldersRevenue); net new supply = change in "
        "NearBlocks' daily total supply (already net of burned fees) valued at the mean price of the period. Bought NEAR is "
        "held, not burned, so supply itself does not shrink.",
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
    return Chart(
        "clients", "Who sends the transactions",
        f"In {lm}, {L['accounts_for_half_of_txs']} accounts sent half of NEAR's {L['transactions'] / 1e6:.1f}M transactions "
        f"and the top 10 sent {L['top10_share'] * 100:.0f}% ({P['top10_share'] * 100:.0f}% in {pm}). Reward and wallet apps "
        f"(Sweat, HOT, Meteor, KaiChing) are {cl['reward_apps_share']['latest'] * 100:.0f}% of transactions, down from "
        f"{cl['reward_apps_share']['prior'] * 100:.0f}%; Sweat alone is {sw['latest_share'] * 100:.0f}%. Trading, Intents, token "
        f"transfers and bridges are {cl['finance_share']['latest'] * 100:.0f}% (was {cl['finance_share']['prior'] * 100:.0f}%); "
        f"transactions on the Ref/Rhea exchange changed {_pct(ref['pct_change'])}. intents.near received "
        f"{i['latest']['transactions'] / 1e6:.2f}M transactions ({i['prior']['transactions'] / 1e6:.2f}M a year earlier), "
        f"{i['latest']['top2_share'] * 100:.0f}% of them signed by two accounts.",
        "sql/top_accounts.sql on the NEAR BigQuery public dataset (13.53 GB), result in data/bq/top_accounts_result.csv. "
        "A direct transaction is assigned to the contract it calls, a relayed one to its relayer; contracts and relayers are "
        "grouped into apps by the table in thesis/clients.py. Intents users sign off-chain, so its on-chain signers are "
        "relayers, not users.",
    )


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
        core = summary["population"]["segments"]["core"]["returning_accounts"]
        proxy_title = "What the daily aggregates show, and why they mislead"
        proxy_note = (
            f" This proxy is wrong about the direction: counted directly on the full chain, core accounts active two months "
            f"running changed {_pct(core['pct_change'])} over the same year (see the first chart). The aggregator's "
            "\"active accounts\" are transaction signers, so users acting through relayers are missing, and its "
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
        charts.append(Chart(
            "intents", "NEAR Intents volume",
            f"In {mi.get('month')} Intents volume averaged ${mi.get('recent', float('nan')) / 1e6:,.1f}M a day against "
            f"${mi.get('prior', float('nan')) / 1e6:,.1f}M in the same month a year earlier ({_pct(mi.get('pct_change'))}); "
            f"the last 90 days averaged ${yi.get('recent', float('nan')) / 1e6:,.1f}M a day, {_pct(qi.get('pct_change'))} on the "
            f"90 days before and {_pct(yi.get('pct_change'))} on the same 90 days a year earlier.",
            "DefiLlama dexs/near-intents totalDataChart, 7-day rolling mean. The 90-day year-on-year figure shrinks every "
            "day as its base moves through the ramp-up of autumn 2025; the calendar-month comparison does not.",
        ))

    # 5a. Full-population account census from BigQuery (only when data/bq/account_age.csv exists)
    pop = population.load()
    if pop is not None and "population" in summary:
        charts.append(_population_chart(pop, summary, out))

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
            band = ll["band"].iloc[0]
            ax.axhline(band, color=INK, linestyle=":", linewidth=0.8)
            ax.axhline(-band, color=INK, linestyle=":", linewidth=0.8)
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
            f"about {0.05 * n_tests:.0f} expected by chance): " + "; ".join(parts) + ". Fees are tested in NEAR: in USD they "
            f"correlate with price in the same week (r={usd.get('corr', float('nan')):.2f}) only because USD fees are NEAR "
            "fees multiplied by the price.",
            "corr(Δlog metric_t, Δlog price_{t+k}), k in weeks, positive k = metric moves first (green bars); "
            "dotted lines = ±2/√n noise band.",
        ))
    lead = ["population", "clients", "value_capture"]  # the full-chain counts lead the dashboard
    charts.sort(key=lambda c: lead.index(c.slug) if c.slug in lead else len(lead))
    for c in charts:
        c.source = SOURCE_OF.get(c.slug, "")
    return charts
