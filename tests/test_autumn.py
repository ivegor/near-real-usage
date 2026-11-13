"""The autumn by half-months: the rules that date the step of Intents volume and mark the half-months above the reference."""
import numpy as np
import pandas as pd

from thesis import autumn, value


def test_half_months_are_calendar_halves_cut_at_the_last_day():
    got = autumn.halves(pd.Timestamp("2026-08-16"), pd.Timestamp("2026-10-20"))
    assert [(a.strftime("%m-%d"), b.strftime("%m-%d")) for a, b in got] == [
        ("08-16", "08-31"), ("09-01", "09-15"), ("09-16", "09-30"), ("10-01", "10-15"), ("10-16", "10-20")]


def synthetic():
    """A year of days: volume at 50 with a step to 150 on 19 August, a burst of transactions from 16 September to 15 October."""
    idx = pd.date_range("2025-11-01", "2026-11-11", freq="D")
    vol = pd.Series(50e6, index=idx)
    vol[idx >= "2026-08-19"] = 150e6
    vol[idx == "2026-08-25"] = 60e6                       # one weak day after the step: the weekly mean holds above the line
    txns = pd.Series(700e3, index=idx)
    txns[(idx >= "2026-09-16") & (idx <= "2026-10-15")] = 900e3
    price = pd.Series(1.5, index=idx)
    price[idx >= "2026-09-01"] = 4.0
    daily = pd.DataFrame({"intents_volume_usd": vol, "txns": txns, "price_usd": price, "fees_usd": txns / 1000 * price,
                          "deleted_accounts": 0.0, "active_accounts": 1e5, "gas_used": txns * 1e7}, index=idx)
    fees = pd.DataFrame({"fees": vol / 1000, "revenue": vol / 4000, "holders_revenue": vol / 4000}, index=idx)
    return daily, fees


def test_the_step_day_and_the_burst_are_found_by_rule():
    daily, fees = synthetic()
    out = autumn.summarize(daily, fees, ("2025-12", "2026-08"), "2026-04-02", line=89.6e6)
    step = out["intents_step"]
    # the weekly mean crosses the line on the third day of the step (4 × 50 + 3 × 150 over 7 > 89.6), and the largest one-day rise is the step itself
    assert (step["day"], step["weekly_mean_above_it_since"], step["days_of_the_month_from_it"]) == ("2026-08-19", "2026-08-21", 13)
    assert abs(step["share_of_the_month_volume_from_it"] - (12 * 150 + 60) / (18 * 50 + 12 * 150 + 60)) < 1e-12
    # the reference stops before the half-month of the step; volume is above it from that half-month on, transactions only
    # in the two half-months of the burst
    assert out["reference"]["through"] == "2026-08-15" and out["reference"]["from"] == "2026-04-16"
    assert out["above_reference_top"]["intents_volume_usd"][0] == "2026-08-16..2026-08-31"
    assert out["above_reference_top"]["txns"] == ["2026-09-16..2026-09-30", "2026-10-01..2026-10-15"]
    assert out["above_reference_top"]["fees_near"] == ["2026-09-16..2026-09-30", "2026-10-01..2026-10-15"]


def test_no_step_while_the_weekly_mean_is_at_the_line_today():
    daily, fees = synthetic()
    daily.loc[daily.index[-7]:, "intents_volume_usd"] = 50e6
    assert autumn.intents_step(daily, fees, 89.6e6, "2025-12") is None


def test_buyback_windows_set_the_last_window_against_every_other():
    daily, fees = synthetic()
    daily["total_supply_yocto"] = (1e9 + 1e5 * np.arange(len(daily))) * 1e24
    daily["market_cap_usd"] = 1e9
    fees.loc[fees.index < "2026-02-23", "holders_revenue"] = 0.0          # the programme starts on 23 February
    w = value.windows(daily, fees, step_day="2026-08-19", threshold_month_usd=723262.0, threshold_month="2026-12")
    roll = w["rolling_90d"]
    assert w["programme_start"] == "2026-02-23" and roll["windows"] == len(pd.date_range("2026-05-23", "2026-11-11"))
    assert 1 <= roll["rank_of_the_latest"] <= roll["windows"] and roll["min"] <= roll["median"] <= roll["max"]
    bb = w["buybacks_per_day_before_and_from_the_step"]
    assert abs(bb["usd_ratio"] - 3.0) < 0.05           # 12.5k a day before, 37.5k after (one weak day aside)
    # in NEAR the step is smaller wherever the price rose with it
    assert bb["near_ratio"] < bb["usd_ratio"]
    th = w["threshold_price"]
    assert abs(th["mean_price_that_meets_it"] * th["near_per_day"] * 31 - 723262.0) < 1e-6
