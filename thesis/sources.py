"""The two daily series the build downloads: NearBlocks network charts and DefiLlama NEAR Intents volume.

Raw responses are cached in data/raw/ so a run is reproducible offline
(`python -m thesis build --offline`) and judges can diff the exact inputs.
The other sources are read elsewhere: the BigQuery results (thesis/population.py, segments.py, payers.py,
clients.py), the DefiLlama fee series (thesis/value.py) and the keyless block sample (thesis/census.py).
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
# NearBlocks switches /v1 off on 2026-11-22 (its replies carry `sunset: Sun, 22 Nov 2026`). The API that replaces it
# splits the charts by metric. It is read in two cases: when /v1/charts cannot be downloaded, to carry the daily table
# on past the last day of the saved /v1 copy (see continue_with_v3), and for its count of relayed users, which /v1
# never had (see relayed_daily). While /v1 answers, the daily table is built from /v1 alone, as it always was.
NEARBLOCKS_V3 = {
    "nearblocks_v3_blocks": "https://api.nearblocks.io/v3/block-stats",
    "nearblocks_v3_txns": "https://api.nearblocks.io/v3/txn-stats",
    "nearblocks_v3_addresses": "https://api.nearblocks.io/v3/address-stats",
    "nearblocks_v3_prices": "https://api.nearblocks.io/v3/price-stats",
}
V1_SUNSET = "2026-11-22"
# Seconds to wait for a connection, then for each part of the reply. A host that does not answer at all is given up on
# after the first, so the fall-back to the committed copies takes well under a minute per source instead of minutes;
# a slow but working reply still gets the second.
TIMEOUT = (10, 60)


def _fetch_json(url: str, retries: int = 3) -> dict:
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=TIMEOUT, headers={"User-Agent": "near-real-usage-thesis"})
            r.raise_for_status()
            return r.json()
        except Exception as e:  # network hiccups, rate limits
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"Failed to fetch {url}: {last_err}")


REQUIRED_KEY = {"nearblocks_charts": "charts", "defillama_intents": "totalDataChart", **{k: "data" for k in NEARBLOCKS_V3}}
NOT_REFRESHED: list[str] = []  # the sources the last fetch_all() could not download and read from their saved copies
CONTINUED_FROM_V3: list[bool] = []  # non-empty when the last fetch_all() carried the daily table on from the v3 API


def _check_shape(name: str, data: object, key: str | None = None) -> None:
    """Raise if a response does not carry the series we read from it (an API change, a rate-limit page, ...)."""
    key = key or REQUIRED_KEY.get(name)
    rows = data.get(key) if isinstance(data, dict) and key else None
    if key and (not isinstance(rows, list) or len(rows) < 30):
        raise RuntimeError(f"unexpected response for {name}: no usable '{key}' series")


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
            out[name] = json.loads(path.read_text(encoding="utf-8"))
        else:
            try:
                data = _fetch_json(url)
                _check_shape(name, data)  # never overwrite the committed copy with an error page or an empty reply
                path.write_text(json.dumps(data), encoding="utf-8")
            except RuntimeError as e:
                # An API outage must not break the build or a judge's reproduction: fall back to the committed copy.
                if not path.exists():
                    raise
                print(f"[sources] {name}: {e}; using the saved copy {path.name}")
                data = json.loads(path.read_text(encoding="utf-8"))
                stale.append(name)
            out[name] = data
    CONTINUED_FROM_V3.clear()
    if "nearblocks_charts" in stale:
        v3 = fetch_v3()
        if v3:
            # the daily table is fresh after all: the saved /v1 copy up to its last day, v3 from there on
            out.update(v3)
            stale.remove("nearblocks_charts")
            CONTINUED_FROM_V3.append(True)
            print("[sources] nearblocks_charts: continued from the v3 API after the last day of the saved copy")
    meta = {name: {"url": url, "file": f"data/raw/{name}.json"} for name, url in SOURCES.items()}
    if CONTINUED_FROM_V3:
        meta["nearblocks_charts"]["continued_from"] = NEARBLOCKS_V3
    if stale:
        meta["not_refreshed"] = stale
    if not offline:
        meta["fetched_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()
        (RAW_DIR / "_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    NOT_REFRESHED[:] = stale
    return out


def fetch_v3() -> dict[str, dict]:
    """Download the four v3 series (network). All four or nothing: {} when any of them fails or has the wrong shape."""
    replies = {}
    try:
        for name, url in NEARBLOCKS_V3.items():
            replies[name] = _fetch_json(url)
            _check_shape(name, replies[name])
    except RuntimeError as e:
        print(f"[sources] v3: {e}")
        return {}
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in replies.items():
        (RAW_DIR / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
    return replies


def _v3_frame(raw: dict) -> pd.DataFrame:
    df = pd.DataFrame(raw["data"])
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    df = df.drop_duplicates("date").set_index("date").sort_index()
    return df.apply(pd.to_numeric, errors="coerce")


def parse_nearblocks_v3(raw: dict[str, dict]) -> pd.DataFrame:
    """The columns of the daily table that v3 carries with the same meaning as /v1/charts.

    On the days from 2025-10-01 that the two committed copies share, total supply, gas used, transactions, price and
    market capitalisation are equal on every day and active contracts on nearly all (tests/test_metrics.py compares
    them). Fees and transfer volume come in NEAR and are valued at the day's price here; /v1 gave them in USD, and
    the two agree to within a tenth of a percent on most days.
    Left out on purpose: v3 has no new or deleted accounts, and its `active_accounts` is another quantity (signers
    plus the accounts relayers acted for), so those columns end with /v1.
    """
    blocks, txns, addresses, prices = (_v3_frame(raw[k]) for k in NEARBLOCKS_V3)
    out = pd.DataFrame({
        "total_supply_yocto": blocks["total_supply"], "gas_used": blocks["gas_used"],
        "txns": txns["txns"], "price_usd": prices["near_price"], "market_cap_usd": prices["market_cap"],
        "active_contracts": addresses["active_contracts"],
    })
    out["fees_usd"] = txns["txn_fee"] * out["price_usd"]
    out["transfer_volume_usd"] = txns["txn_volume"] * out["price_usd"]
    out.index.name = "date"
    return out


def continue_with_v3(daily: pd.DataFrame, v3: pd.DataFrame) -> pd.DataFrame:
    """The /v1 table as it is, then the v3 days after its last day. Columns v3 does not carry stay empty there."""
    later = v3[v3.index > daily.index.max()].dropna(subset=["txns"])
    if later.empty:
        return daily
    return pd.concat([daily, later.reindex(columns=daily.columns)])


def series_ended(daily: pd.DataFrame) -> dict:
    """Columns whose last value is earlier than the table's last day: {column: last day with a value}.

    After /v1 is switched off the table goes on from v3, which has no count of signers, of new or of deleted accounts.
    Those columns end; a mean over "the last 90 days" of one of them then covers fewer days, and the page says so.
    """
    last = daily.index.max()
    out = {}
    for col in daily.columns:
        if col == "intents_volume_usd":  # another source; it may trail by a day and is handled where it is used
            continue
        end = daily[col].last_valid_index()
        if end is not None and end < last:
            out[col] = str(end.date())
    return out


def relayed_daily() -> pd.DataFrame | None:
    """NearBlocks' own daily count of relayed transactions and of the accounts relayers acted for (v3, saved copies).

    /v1's "active accounts" counted signers only. The v3 API adds the other side: the accounts acted for, the relayers
    and the relayed transactions of each day. It is a second source for what the census counts from BigQuery.
    """
    paths = {k: RAW_DIR / f"{k}.json" for k in ("nearblocks_v3_txns", "nearblocks_v3_addresses")}
    if not all(p.exists() for p in paths.values()):
        return None
    txns, addresses = (_v3_frame(json.loads(p.read_text(encoding="utf-8"))) for p in paths.values())
    return pd.DataFrame({"relayed_txns": txns["meta_txns"], "relayed_users": addresses["meta_accounts"],
                         "relayers": addresses["meta_relayers"], "accounts_with_relayed_users": addresses["active_accounts"]})


NUMERIC_FIELDS = {
    "total_supply": "total_supply_yocto",
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
    "gas_used": "gas_used",
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
    s = pd.Series(  # a null is a day without a value, not a reason to stop the build
        {pd.Timestamp(int(ts), unit="s").normalize(): float(v) for ts, v in pts if v is not None},
        name="intents_volume_usd", dtype=float,
    )
    s.index.name = "date"
    return s.sort_index()


def load_daily(offline: bool = False) -> pd.DataFrame:
    raw = fetch_all(offline=offline)
    daily = parse_nearblocks(raw["nearblocks_charts"])
    if all(k in raw for k in NEARBLOCKS_V3):  # /v1/charts could not be downloaded and v3 could
        daily = continue_with_v3(daily, parse_nearblocks_v3(raw))
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
