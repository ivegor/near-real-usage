"""Pure metric functions. No I/O here, so everything is unit-testable."""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def add_derived(daily: pd.DataFrame) -> pd.DataFrame:
    """Usage-quality metrics derived from the raw daily series."""
    d = daily.copy()
    d["price_usd"] = d["price_usd"].where(np.isfinite(d["price_usd"]) & (d["price_usd"] > 0))
    d["returning_accounts"] = (d["active_accounts"] - d["new_accounts"]).clip(lower=0)
    d["returning_share"] = d["returning_accounts"] / d["active_accounts"]
    d["tx_per_active"] = d["txns"] / d["active_accounts"]
    d["fees_per_active_usd"] = d["fees_usd"] / d["active_accounts"]
    # Fees in NEAR. Fees in USD are fees in NEAR times the price, so they move with the price by construction.
    d["fees_near"] = d["fees_usd"] / d["price_usd"].where(d["price_usd"] > 0)
    # Same fees in NEAR terms: removes the mechanical effect of the token price on USD fees.
    d["fees_per_active_near"] = d["fees_usd"] / d["price_usd"].where(d["price_usd"] > 0) / d["active_accounts"]
    if "intents_volume_usd" in d:
        d["intents_per_active_usd"] = d["intents_volume_usd"] / d["active_accounts"]
    return d.replace([np.inf, -np.inf], np.nan)


def rolling(d: pd.DataFrame, window: int = 30) -> pd.DataFrame:
    return d.asfreq("D").rolling(window, min_periods=window).mean()


def calendar_window(series: pd.Series, start, end) -> pd.Series:
    """One observation per expected day; absent and non-finite values remain missing."""
    return series.reindex(pd.date_range(start, end, freq="D")).replace([np.inf, -np.inf], np.nan)


def complete_mean(series: pd.Series) -> float:
    return float(series.mean()) if len(series) and series.notna().all() else float("nan")


def finite_ratio(numerator: float, denominator: float) -> float:
    """An undefined ratio is unknown; observed zero numerators remain zero."""
    if not np.isfinite(numerator) or not np.isfinite(denominator) or denominator == 0:
        return float("nan")
    result = numerator / denominator
    return float(result) if np.isfinite(result) else float("nan")


def calendar_months(series: pd.Series, first, last, stat: str = "mean") -> pd.Series:
    """Monthly means or sums, unavailable unless every calendar day is finite (zero is valid)."""
    first, last = pd.Period(first, "M"), pd.Period(last, "M")
    days = calendar_window(series, first.start_time, last.end_time.normalize())
    grouped = days.resample("ME")
    result = getattr(grouped, stat)()
    result = result.where(grouped.count() == result.index.days_in_month)
    result.index = result.index.to_period("M")
    return result


def period_change(series: pd.Series, days: int = 90, lookback_days: int = 365) -> dict:
    """Mean over the last `days` vs the same window `lookback_days` earlier.

    Medians of the same two windows are reported too, as a check that a few extreme days
    do not drive the change.
    """
    s = series.replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return {"recent": np.nan, "prior": np.nan, "pct_change": np.nan, "median_pct_change": np.nan}
    end = s.index.max()
    recent = calendar_window(s, end - pd.Timedelta(days=days - 1), end)
    p_end = end - pd.Timedelta(days=lookback_days)
    prior = calendar_window(s, p_end - pd.Timedelta(days=days - 1), p_end)
    r, p = complete_mean(recent), complete_mean(prior)
    pct = (r / p - 1) * 100 if prior.size and pd.notna(p) and p != 0 else np.nan
    rm = recent.median() if recent.notna().all() else np.nan
    pm = prior.median() if prior.notna().all() else np.nan
    mpct = (rm / pm - 1) * 100 if prior.size and pd.notna(pm) and pm != 0 else np.nan
    return {
        "recent": float(r),
        "prior": float(p) if pd.notna(p) else np.nan,
        "pct_change": float(pct) if pd.notna(pct) else np.nan,
        "median_pct_change": float(mpct) if pd.notna(mpct) else np.nan,
        "from": str(recent.index.min().date()), "through": str(end.date()),
        "prior_from": str(prior.index.min().date()), "prior_through": str(p_end.date()),
        "expected_days": days, "recent_days": int(recent.count()), "prior_days": int(prior.count()),
    }


def weekly_log_diff(series: pd.Series, *, positive_only: bool = False) -> pd.Series:
    """Week-on-week log-change of the weekly mean, Monday to Sunday, over complete weeks only.

    A week counts only when all seven of its days have a value. The last week of a snapshot is usually unfinished (the
    data of 2026-11-11 end on a Wednesday, three days into the week), and a mean of three days is not the same
    observation as a mean of seven; the first week of a series is often partial too. A week left out leaves a gap: the
    changes into and out of it are not computed, rather than one change spanning two weeks. For prices, positive_only
    excludes non-positive or non-finite daily quotes before counting days: zero before trading began is not a price.
    Activity may legitimately be zero on a day, so that restriction is not applied to activity series.
    """
    if positive_only:
        series = series.where(np.isfinite(series) & (series > 0))
    s = series.dropna()
    w = s.resample("W-SUN").mean().where(s.resample("W-SUN").count() == 7)
    w = w.where(w > 0)
    return np.log(w).diff().dropna()


def bartlett_factor(x: pd.Series, y: pd.Series, lags: int = 8) -> float:
    """How much the variance of a correlation between two autocorrelated series exceeds 1/n (Bartlett's formula).

    Under no true relation, var(r) ≈ (1/n) · (1 + 2 Σ_k ρx(k) ρy(k)), with ρ the autocorrelations of each series. Above 1
    the noise band is wider than 2/√n, below 1 narrower. The sum is cut at `lags` weeks, the longest lag tested.
    """
    # Both autocorrelations describe the observations used by this lag's correlation. Missing calendar weeks must
    # remain gaps: two adjacent surviving observations need not be one week apart.
    pair = pd.concat([x, y], axis=1, keys=["x", "y"]).dropna()
    if isinstance(pair.index, pd.DatetimeIndex) and len(pair):
        pair = pair.asfreq("W-SUN")
    x, y = pair["x"], pair["y"]
    total = 1.0
    for k in range(1, lags + 1):
        a, b = x.autocorr(k), y.autocorr(k)
        if pd.notna(a) and pd.notna(b):
            total += 2 * a * b
    return max(total, 1e-9)


# Significant digits kept for the lag statistics. A correlation over a few hundred weekly changes comes out a few units
# in the 14th digit apart on different processors (arm64 and x86-64 sum in another order), and erfc and atanh in
# another C library can differ in the last digit too. Rounded to 12 digits, the same data gives the same summary.json
# on every machine; no figure the text quotes has more than four.
DIGITS = 12


def _sig(v: float) -> float:
    """v rounded to DIGITS significant digits, so that the summary does not depend on the processor that built it."""
    return float(f"{v:.{DIGITS}g}") if pd.notna(v) and math.isfinite(v) else v


def _lag_pair(dx: pd.Series, dp: pd.Series, k: int) -> pd.DataFrame:
    """Match changes k calendar weeks apart, even when an incomplete week has been removed."""
    return pd.concat([dx, dp.shift(freq=pd.Timedelta(weeks=-k))], axis=1,
                     keys=["x", "p"], sort=True).dropna()


def lead_lag(x: pd.Series, price: pd.Series, max_lag: int = 8) -> pd.DataFrame:
    """Correlation of weekly log-changes of x with price shifted by k weeks.

    k > 0  -> corr(x_t, price_{t+k}): x LEADS price by k weeks.
    k < 0  -> price leads x.
    `band` is the approximate 95% noise band 2/sqrt(n) for a zero true correlation.
    """
    dx, dp = weekly_log_diff(x), weekly_log_diff(price, positive_only=True)
    rows = []
    for k in range(-max_lag, max_lag + 1):
        pair = _lag_pair(dx, dp, k)
        n = len(pair)
        corr = pair["x"].corr(pair["p"]) if n > 5 else np.nan
        rows.append({"lag_weeks": k, "corr": _sig(corr), "n": n, "band": 2 / np.sqrt(n) if n else np.nan,
                     "p": _sig(_p_value(corr, n))})
    return pd.DataFrame(rows)


def _p_value(corr: float, n: float) -> float:
    """Two-sided p-value of a correlation under a zero true correlation, by Fisher's z (normal approximation).
    `n` may be an effective number of weeks (bartlett_scan), not a whole number."""
    if n <= 3 or not math.isfinite(corr):
        return float("nan")
    if abs(corr) > 1 and not math.isclose(abs(corr), 1, rel_tol=0, abs_tol=1e-14):
        return float("nan")
    if abs(corr) >= 1:
        return 0.0  # Fisher's z tends to infinity at either perfect correlation
    return float(math.erfc(abs(math.atanh(corr)) * math.sqrt(n - 3) / math.sqrt(2)))


def holm(p_values: list[float], alpha: float = 0.05) -> dict:
    """Holm's step-down correction for testing many lags at once: how many tests still stand at level alpha.

    The noise band flags about one test in twenty by chance. Holm's rule asks more of the smallest p-value the more
    tests there are (alpha / m for the first, alpha / (m - 1) for the next, ...) and stops at the first that fails.
    """
    ps = sorted(p for p in p_values if not pd.isna(p))
    m = len(ps)
    passed = 0
    for i, p in enumerate(ps):
        if p > alpha / (m - i):
            break
        passed += 1
    return {"tests": m, "alpha": alpha, "significant": passed, "smallest_p": ps[0] if ps else float("nan"),
            "threshold_for_the_smallest_p": alpha / m if m else float("nan")}


def best_lead(ll: pd.DataFrame) -> dict:
    ll = ll.dropna(subset=["corr"])
    if ll.empty:
        return {"lag_weeks": None, "corr": np.nan, "significant": False, "outside_band": []}
    row = ll.loc[ll["corr"].abs().idxmax()]
    outside = ll[ll["corr"].abs() > ll["band"]]
    return {
        "lag_weeks": int(row["lag_weeks"]),
        "corr": float(row["corr"]),
        "band": float(row["band"]),
        "n_weeks": int(row["n"]),
        # the sample shrinks by one week per week of lag: the smallest and largest n over the lags tested
        "n_weeks_range": [int(ll["n"].min()), int(ll["n"].max())],
        "band_range": [float(ll["band"].min()), float(ll["band"].max())],
        "significant": bool(abs(row["corr"]) > row["band"]),
        # every lag whose correlation is outside the noise band, not only the largest one
        "outside_band": [
            {"lag_weeks": int(k), "corr": round(float(c), 3)} for k, c in zip(outside["lag_weeks"], outside["corr"])
        ],
        "p_values": [float(v) for v in ll["p"]] if "p" in ll else [],
        "lags": [int(k) for k in ll["lag_weeks"]],
    }


def holm_leading_lags(leads: dict, alpha: float = 0.05) -> list[dict]:
    """Identify positive lags surviving Holm over the entire family, including negative and zero lags."""
    tests = sorted((p, name, lag) for name, v in leads.items()
                   for lag, p in zip(v.get("lags", []), v.get("p_values", [])) if np.isfinite(p))
    significant = []
    for i, (p, name, lag) in enumerate(tests):
        if p > alpha / (len(tests) - i):
            break
        if lag > 0:
            significant.append({"metric": name, "lag_weeks": lag, "p": p})
    return significant


def decoupling_table(d: pd.DataFrame, days: int = 90, lookback_days: int = 365) -> pd.DataFrame:
    cols = [
        "price_usd",
        "active_accounts",
        "new_accounts",
        "returning_accounts",
        "returning_share",
        "txns",
        "tx_per_active",
        "fees_usd",
        "fees_near",
        "fees_per_active_usd",
        "fees_per_active_near",
        "intents_volume_usd",
        "intents_per_active_usd",
    ]
    rows = []
    for c in cols:
        if c in d:
            rows.append({"metric": c, **period_change(d[c], days=days, lookback_days=lookback_days)})
    return pd.DataFrame(rows)


def checks(daily: pd.DataFrame, days: int = 90) -> dict:
    """Sanity checks on the `returning = active - new` identity.

    The identity assumes every new account is also counted as active on its first day. Days where
    new_accounts > active_accounts show it does not always hold; on such days `returning` is clipped
    to 0 and, more generally, `active - new` is a LOWER bound for returning accounts.
    """
    d = add_derived(daily)
    bad = daily["new_accounts"] > daily["active_accounts"]
    end = d.index.max()

    def window(lookback: int) -> pd.Series:
        e = end - pd.Timedelta(days=lookback)
        return (d.index > e - pd.Timedelta(days=days)) & (d.index <= e)

    return {
        "new_exceeds_active_days": {
            "recent": int(bad[window(0)].sum()),
            "prior": int(bad[window(365)].sum()),
            "all_history": int(bad.sum()),
        },
        "returning_accounts_two_years_earlier": float(d["returning_accounts"][window(730)].mean()),
    }


def month_change(series: pd.Series) -> dict:
    """Mean of the last complete calendar month vs the same month a year earlier (a fixed, dated comparison)."""
    s = series.replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return {"month": None, "recent": np.nan, "prior": np.nan, "pct_change": np.nan}
    end = s.index.max()
    month = end.to_period("M") if (end + pd.Timedelta(days=1)).day == 1 else end.to_period("M") - 1
    recent = calendar_window(s, month.start_time, month.end_time.normalize())
    prior_month = month - 12
    prior = calendar_window(s, prior_month.start_time, prior_month.end_time.normalize())
    r, p = complete_mean(recent), complete_mean(prior)
    pct = (r / p - 1) * 100 if pd.notna(p) and p else np.nan
    return {"month": str(month), "recent": float(r), "prior": float(p) if pd.notna(p) else np.nan,
            "pct_change": float(pct) if pd.notna(pct) else np.nan,
            "recent_days": int(recent.count()), "expected_days": len(recent),
            "prior_days": int(prior.count()), "prior_expected_days": len(prior)}


def month_to_date_change(series: pd.Series) -> dict | None:
    """The days of the current, incomplete month against the same days a year earlier; None when the last month is complete.

    A calendar-month comparison waits for the month to end. When last year's base was rising month by month, the
    days already in hand say where the year-on-year figure is heading.
    """
    s = series.replace([np.inf, -np.inf], np.nan).dropna()
    if s.empty:
        return None
    end = s.index.max()
    if (end + pd.Timedelta(days=1)).day == 1:
        return None
    start = end.replace(day=1)
    now = calendar_window(s, start, end)
    then = calendar_window(s, start - pd.DateOffset(years=1), end - pd.DateOffset(years=1))
    if len(then) != len(now) or not now.notna().all() or not then.notna().all():
        return None
    r, p = float(now.mean()), float(then.mean())
    return {"from": str(start.date()), "through": str(end.date()), "days": int(len(now)), "recent": r, "prior": p,
            "pct_change": (r / p - 1) * 100 if p else float("nan")}


LEAD_METRICS = ["returning_accounts", "active_accounts", "intents_volume_usd", "fees_near", "txns"]


def summarize(daily: pd.DataFrame) -> dict:
    d = add_derived(daily)
    table = decoupling_table(d)
    leads = {}
    for c in LEAD_METRICS:
        if c in d and d[c].notna().sum() > 120:
            leads[c] = best_lead(lead_lag(d[c], d["price_usd"]))
    return {
        "first_date": str(d.index.min().date()),
        "last_date": str(d.index.max().date()),
        "days": int(len(d)),
        "yoy_90d": table.set_index("metric").to_dict(orient="index"),
        # last 90 days vs the 90 days just before them: is the YoY direction still the current direction?
        "qoq_90d": decoupling_table(d, lookback_days=90).set_index("metric").to_dict(orient="index"),
        "month_yoy": {c: month_change(d[c]) for c in ("price_usd", "txns", "active_accounts", "fees_usd", "fees_near",
                                                       "intents_volume_usd") if c in d},
        "month_to_date_yoy": {c: month_to_date_change(d[c]) for c in ("price_usd", "intents_volume_usd") if c in d},
        "lead_vs_price": leads,
        # all lags of all metrics as one family of tests
        "lead_vs_price_holm": holm([p for v in leads.values() for p in v.get("p_values", [])]),
        "lead_vs_price_holm_leads": holm_leading_lags(leads),
        # reported apart from the scan above: USD fees contain the price, so this correlation is mechanical
        "lead_fees_usd_mechanical": best_lead(lead_lag(d["fees_usd"], d["price_usd"])),
        # The band and the p-values treat the weeks as independent. Correlation of each series' weekly change with the
        # week before: where both series of a pair have it of the same sign, the true noise band is wider than 2/sqrt(n).
        "lead_vs_price_lag1_autocorrelation": {c: _sig(float(weekly_log_diff(d[c], positive_only=c == "price_usd")
                                                           .asfreq("W-SUN").autocorr(1)))
                                               for c in ["price_usd", *leads] if c in d},
        # The same scan with the band and the p-values widened (or narrowed) for the autocorrelation of both series.
        "lead_vs_price_bartlett": bartlett_scan(d, leads),
        "checks": checks(daily),
    }


def bartlett_scan(d: pd.DataFrame, leads: dict) -> dict:
    """The lead-lag scan with Bartlett's formula on the matched observations of each metric and lag.

    The band becomes 2·√(factor/n) and each p-value is taken with n/factor weeks. This is an approximation too (the
    autocorrelations are estimated from the same data), published next to the plain scan, not in place of it.
    """
    dp = weekly_log_diff(d["price_usd"], positive_only=True)
    per, ps, outside = {}, [], 0
    for c in leads:
        dx = weekly_log_diff(d[c])
        ll = lead_lag(d[c], d["price_usd"]).dropna(subset=["corr"])
        factors, out = {}, []
        for k, r, n in zip(ll["lag_weeks"], ll["corr"], ll["n"]):
            pair = _lag_pair(dx, dp, int(k))
            f = bartlett_factor(pair["x"], pair["p"])
            factors[str(k)] = _sig(f)
            if abs(r) > 2 * math.sqrt(f / n):
                out.append(int(k))
            ps.append(_p_value(r, n / f))
        per[c] = {"factor_by_lag": factors, "outside_band_lags": out}
        outside += len(out)
    return {"metrics": per, "outside_band": outside, "tests": len(ps),
            "holm": {k: (_sig(v) if isinstance(v, float) else v) for k, v in holm(ps).items()}}
