"""Charts. Each chart = one PNG + one plain sentence generated from the numbers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.ticker import FuncFormatter, LogLocator, NullFormatter  # noqa: E402

from . import metrics  # noqa: E402

INK, ACCENT, MUTED, GRID = "#1f2328", "#00a27a", "#8c959f", "#e6e8eb"


@dataclass
class Chart:
    slug: str
    title: str
    sentence: str
    method: str


def _style(ax, title: str):
    ax.set_title(title, loc="left", fontsize=11, color=INK)
    ax.grid(True, color=GRID, linewidth=0.8)
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
    charts.append(Chart(
        "accounts", "New vs returning accounts",
        f"Over the last 90 days returning accounts averaged {yoy['returning_accounts']['recent']:,.0f}/day "
        f"({_pct(yoy['returning_accounts']['pct_change'])} vs a year earlier), new accounts "
        f"{yoy['new_accounts']['recent']:,.0f}/day ({_pct(yoy['new_accounts']['pct_change'])}). "
        f"By medians returning accounts changed {_pct(yoy['returning_accounts'].get('median_pct_change'))}.",
        "returning_accounts = active_accounts - new_accounts (NearBlocks daily charts), 30-day rolling mean. "
        "This is a lower bound: new accounts that did not transact on their first day are subtracted anyway. "
        f"New accounts exceeded active accounts (returning clipped to 0) on {bad.get('recent', 0)} of the last 90 days, "
        f"{bad.get('prior', 0)} of the 90 days a year earlier and {bad.get('all_history', 0)} days in all history "
        "(mostly mid-2022, shown as a gap).",
    ))

    # 2. Usage vs price
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(r.index, _pos(r["returning_accounts"]), color=ACCENT, label="returning accounts, 30d avg (left)")
    ax.set_yscale("log")
    ax.set_ylim(bottom=1_000)
    ax2 = ax.twinx()
    ax2.plot(d.index, _pos(d["price_usd"]), color=INK, linewidth=0.9, label="NEAR price, USD (right)")
    ax2.set_yscale("log")
    ax2.tick_params(colors=MUTED, labelsize=8)
    _plain(ax)
    _plain(ax2, dense=True)
    _style(ax, "Returning accounts vs NEAR price (log scales)")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    _legend_below(ax, h1 + h2, l1 + l2)
    _save(fig, out, "usage_vs_price")
    charts.append(Chart(
        "usage_vs_price", "Usage vs price",
        f"Price changed {_pct(yoy['price_usd']['pct_change'])} year-on-year (90-day averages) while returning "
        f"accounts changed {_pct(yoy['returning_accounts']['pct_change'])}.",
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
        f"({_pct(yoy['tx_per_active']['pct_change'])} YoY); a rising value with flat accounts points to automated activity.",
        "txns / active_accounts (NearBlocks), 30-day rolling mean.",
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
        "txn_fee_usd / active_accounts (NearBlocks), 30-day rolling mean; NEAR terms = the same divided by the daily price.",
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
        charts.append(Chart(
            "intents", "NEAR Intents volume",
            f"Intents volume averaged ${yi.get('recent', float('nan')):,.0f}/day over the last 90 days "
            f"({_pct(yi.get('pct_change', float('nan')))} YoY).",
            "DefiLlama dexs/near-intents totalDataChart, 7-day rolling mean.",
        ))

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
            _style(ax, name.replace("_", " "))
            ax.set_xlabel("weeks metric leads price →", fontsize=7, color=MUTED)
        _save(fig, out, "lead_lag")
        parts = []
        for name, b in leads.items():
            outside = ", ".join(f"{o['lag_weeks']:+d} wk r={o['corr']:+.2f}" for o in b.get("outside_band", []))
            parts.append(f"{name.replace('_', ' ').replace(' usd', '')}: {outside or 'nothing outside the noise band'}")
        n_out = sum(len(b.get("outside_band", [])) for b in leads.values())
        n_tests = 17 * len(leads)
        charts.append(Chart(
            "lead_lag", "Does usage lead price?",
            f"Weekly-change correlation with price, lags outside the noise band ({n_out} of {n_tests} tested; "
            f"about {0.05 * n_tests:.0f} expected by chance): " + "; ".join(parts) + ".",
            "corr(Δlog metric_t, Δlog price_{t+k}), k in weeks, positive k = metric moves first (green bars); "
            "dotted lines = ±2/√n noise band.",
        ))
    return charts
