"""Raw data sources. Every number in this project comes from one of these URLs.

Raw responses are cached in data/raw/ so a run is reproducible offline
(`python -m thesis build --offline`) and judges can diff the exact inputs.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

NEARBLOCKS_CHARTS_URL = "https://api.nearblocks.io/v1/charts"
DEFILLAMA_INTENTS_URL = (
    "https://api.llama.fi/summary/dexs/near-intents"
    "?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true"
)

SOURCES = {
    "nearblocks_charts": NEARBLOCKS_CHARTS_URL,
    "defillama_intents": DEFILLAMA_INTENTS_URL,
}


def _fetch_json(url: str, retries: int = 3) -> dict:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=60, headers={"User-Agent": "near-real-usage-thesis"})
            r.raise_for_status()
            return r.json()
        except Exception as e:  # network hiccups, rate limits
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


def fetch_all(offline: bool = False) -> dict[str, dict]:
    """Return raw JSON for every source, downloading unless offline."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    out: dict[str, dict] = {}
    stale: list[str] = []
    for name, url in SOURCES.items():
        path = RAW_DIR / f"{name}.json"
        if offline:
            if not path.exists():
                raise FileNotFoundError(f"{path} missing; run without --offline first")
            out[name] = json.loads(path.read_text())
        else:
            try:
                data = _fetch_json(url)
                path.write_text(json.dumps(data))
            except RuntimeError as e:
                # An API outage must not break the build or a judge's reproduction: fall back to the committed copy.
                if not path.exists():
                    raise
                print(f"[sources] {name}: {e}; using the saved copy {path.name}")
                data = json.loads(path.read_text())
                stale.append(name)
            out[name] = data
    meta = {name: {"url": url, "file": f"data/raw/{name}.json"} for name, url in SOURCES.items()}
    if stale:
        meta["not_refreshed"] = stale
    if not offline:
        meta["fetched_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
        (RAW_DIR / "_meta.json").write_text(json.dumps(meta, indent=2))
    return out


NUMERIC_FIELDS = {
    "near_price": "price_usd",
    "market_cap": "market_cap_usd",
    "txns": "txns",
    "txn_volume_usd": "transfer_volume_usd",
    "txn_fee_usd": "fees_usd",
    "new_accounts": "new_accounts",
    "active_accounts": "active_accounts",
    "deleted_accounts": "deleted_accounts",
    "new_contracts": "new_contracts",
    "active_contracts": "active_contracts",
}


def parse_nearblocks(raw: dict) -> pd.DataFrame:
    rows = raw["charts"]
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None).dt.normalize()
    keep = {k: v for k, v in NUMERIC_FIELDS.items() if k in df.columns}
    df = df[["date", *keep]].rename(columns=keep)
    for col in keep.values():
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.drop_duplicates("date").set_index("date").sort_index()


def parse_defillama(raw: dict) -> pd.Series:
    pts = raw.get("totalDataChart") or []
    s = pd.Series(
        {pd.Timestamp(int(ts), unit="s").normalize(): float(v) for ts, v in pts},
        name="intents_volume_usd",
    )
    s.index.name = "date"
    return s.sort_index()


def load_daily(offline: bool = False) -> pd.DataFrame:
    raw = fetch_all(offline=offline)
    daily = parse_nearblocks(raw["nearblocks_charts"])
    intents = parse_defillama(raw["defillama_intents"])
    daily = daily.join(intents, how="left")
    # Drop today's partial day if present: only keep days strictly before the last row
    # when the last row looks incomplete (far fewer txns than the 7-day median).
    if len(daily) > 8:
        last = daily["txns"].iloc[-1]
        med = daily["txns"].iloc[-8:-1].median()
        if pd.notna(last) and pd.notna(med) and last < 0.5 * med:
            daily = daily.iloc[:-1]
    return daily
