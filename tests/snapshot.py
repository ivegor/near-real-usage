"""The committed query results as they stood when the snapshot behind THESIS.md was taken.

The account queries are run again later (predictions B1 to B4 need January 2027), and their results then hold more
months. A test that checks a fact of the snapshot's months reads the tables through this module, which cuts them at
the months of the frozen summary, so that a later month in a file cannot change what the test is about.
"""
import json
from pathlib import Path

from thesis import clients, population, segments

ROOT = Path(__file__).resolve().parent.parent
SUMMARY = json.loads((ROOT / "data" / "snapshot" / "thesis_summary.json").read_text(encoding="utf-8"))
SCAN_END = SUMMARY["population"]["query_end"]                  # the day the census scan stopped
LAST_MONTH, YEAR_BEFORE = SUMMARY["clients"]["latest_month"], SUMMARY["clients"]["prior_month"]


def census():
    """The account census up to the snapshot's last complete month (a later scan completes the month after it)."""
    df = population.load()
    return df[df["month"] <= SUMMARY["population"]["latest_month"]]


def frequency():
    df = segments.load()
    return df[df["month"] <= SUMMARY["segments"]["latest_month"]]


def top():
    """The two months of largest accounts and contracts that the snapshot compares."""
    data = clients.load()
    return {m: data[m] for m in (LAST_MONTH, YEAR_BEFORE)}
