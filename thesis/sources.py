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
from collections.abc import Mapping

import pandas as pd
import numpy as np
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
# When the reply each source was read from was downloaded (ISO time, UTC), or None when that is not recorded. A saved
# copy keeps the time it was downloaded at, not the time of the build that fell back to it.
FETCHED_AT: dict[str, str | None] = {}


def _read_meta() -> dict:
    meta_path = RAW_DIR / "_meta.json"
    return json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}


def _saved_fetch_time(meta: dict, name: str) -> str | None:
    """When the saved copy of a source was downloaded, by the _meta.json of the build that saved it.

    Builds since 2026-11-14 record it for each source. Older files carry one time for the whole build, which holds for
    every source that build did refresh, and the v3 copies are only read when that build downloaded them.
    """
    own = (meta.get(name) or {}).get("fetched_at_utc")
    if own:
        return own
    if "fetched_at_utc" in meta and name not in meta.get("not_refreshed", []):
        return meta["fetched_at_utc"]
    return None


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
    last_run = _read_meta()
    FETCHED_AT.clear()
    for name, url in SOURCES.items():
        path = RAW_DIR / f"{name}.json"
        if offline:
            if not path.exists():
                raise FileNotFoundError(f"{path} missing; run without --offline first")
            out[name] = json.loads(path.read_text(encoding="utf-8"))
            FETCHED_AT[name] = _saved_fetch_time(last_run, name)
        else:
            try:
                data = _fetch_json(url)
                _check_shape(name, data)  # never overwrite the committed copy with an error page or an empty reply
                path.write_text(json.dumps(data), encoding="utf-8")
                FETCHED_AT[name] = pd.Timestamp.now(tz="UTC").isoformat()
            except RuntimeError as e:
                # An API outage must not break the build or a judge's reproduction: fall back to the committed copy.
                if not path.exists():
                    raise
                print(f"[sources] {name}: {e}; using the saved copy {path.name}")
                data = json.loads(path.read_text(encoding="utf-8"))
                stale.append(name)
                FETCHED_AT[name] = _saved_fetch_time(last_run, name)  # when that copy was downloaded, not now
            out[name] = data
    CONTINUED_FROM_V3.clear()
    if offline:
        # An offline build rebuilds what the last build with the network built, from the same saved replies. If that
        # build carried the daily table on from v3 (its _meta.json says so), the saved v3 copies are read too; without
        # them the table would end on the last day of the saved /v1 copy and the offline build would differ from it.
        if (last_run.get("nearblocks_charts") or {}).get("continued_from"):
            missing = [k for k in NEARBLOCKS_V3 if not (RAW_DIR / f"{k}.json").exists()]
            if missing:
                raise FileNotFoundError(f"_meta.json says the daily table went on from v3, but {missing} are missing")
            out.update({k: json.loads((RAW_DIR / f"{k}.json").read_text(encoding="utf-8")) for k in NEARBLOCKS_V3})
            FETCHED_AT.update({k: _saved_fetch_time(last_run, k) for k in NEARBLOCKS_V3})
            CONTINUED_FROM_V3.append(True)
    elif "nearblocks_charts" in stale:
        v3 = fetch_v3()
        if v3:
            # the daily table is fresh after all: the saved /v1 copy up to its last finished day, v3 from there on
            out.update(v3)
            FETCHED_AT.update({k: pd.Timestamp.now(tz="UTC").isoformat() for k in v3})
            stale.remove("nearblocks_charts")
            CONTINUED_FROM_V3.append(True)
            print("[sources] nearblocks_charts: continued from the v3 API after the last day of the saved copy")
    meta = {name: {"url": url, "file": f"data/raw/{name}.json", "fetched_at_utc": FETCHED_AT.get(name)}
            for name, url in SOURCES.items()}
    if CONTINUED_FROM_V3:
        meta["nearblocks_charts"]["continued_from"] = NEARBLOCKS_V3
        meta.update({k: {"url": url, "file": f"data/raw/{k}.json", "fetched_at_utc": FETCHED_AT.get(k)}
                     for k, url in NEARBLOCKS_V3.items()})
    if stale:
        meta["not_refreshed"] = stale
    if not offline:
        meta["built_at_utc"] = pd.Timestamp.now(tz="UTC").isoformat()  # the build; each source has its own time above
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
    out = df.apply(pd.to_numeric, errors="coerce")
    if "total_supply" in df:
        out.attrs["exact_supply"] = _exact_supply(df["total_supply"], out["total_supply"])
    return out


class ExactSupply(Mapping):
    """Immutable source provenance, shared by pandas copies instead of copying the entire history per slice."""
    def __init__(self, values):
        self._values = dict(values)

    def __getitem__(self, key):
        return self._values[key]

    def __iter__(self):
        return iter(self._values)

    def __len__(self):
        return len(self._values)

    def __deepcopy__(self, memo):
        return self


def _exact_supply(raw: pd.Series, parsed: pd.Series) -> ExactSupply:
    """Keep source decimals for threshold arithmetic without changing the numeric plotting table.

    The parsed value travels with each decimal so consumers can reject stale provenance after an in-memory edit.
    """
    return ExactSupply({str(day.date()): (str(raw.loc[day]), float(v)) for day, v in parsed.items() if pd.notna(v)})


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
    out.attrs = blocks.attrs.copy()
    return out


def continue_with_v3(daily: pd.DataFrame, v3: pd.DataFrame) -> pd.DataFrame:
    """The /v1 table as it is, then the v3 days after its last day. Columns v3 does not carry stay empty there."""
    later = v3[v3.index > daily.index.max()].dropna(subset=["txns"])
    if later.empty:
        return daily
    out = pd.concat([daily, later.reindex(columns=daily.columns)])
    out.attrs["exact_supply"] = ExactSupply({**daily.attrs.get("exact_supply", {}),
                                  **{str(d.date()): v3.attrs["exact_supply"][str(d.date())]
                                     for d in later.index if str(d.date()) in v3.attrs.get("exact_supply", {})}})
    return out


def series_ended(daily: pd.DataFrame) -> dict:
    """Columns whose last value is earlier than the table's last day: {column: last day with a value}.

    After /v1 is switched off the table goes on from v3, which has no count of signers, of new or of deleted accounts.
    Those columns end; their 90-day comparisons end earlier than the table, and the page says so.
    Invalid prices and non-finite observations do not extend a series' coverage either.
    """
    last = daily.index.max()
    out = {}
    for col in daily.columns:
        if col == "intents_volume_usd":  # another source; it may trail by a day and is handled where it is used
            continue
        valid = daily[col].where(np.isfinite(daily[col]))
        if col == "price_usd":
            valid = valid.where(valid > 0)
        end = valid.last_valid_index()
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
    df = df.drop_duplicates("date").set_index("date").sort_index()
    supply = df["total_supply_yocto"].copy() if "total_supply_yocto" in df else None
    for col in keep.values():
        df[col] = pd.to_numeric(df[col], errors="coerce")
    if supply is not None:
        df.attrs["exact_supply"] = _exact_supply(supply, df["total_supply_yocto"])
    return df


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
    # Each source is cut at the day its own reply was downloaded on, before the sources are put together: an unfinished
    # last day of the saved /v1 copy must not stand in for the finished day v3 carries for the same date.
    daily = drop_unfinished_days(parse_nearblocks(raw["nearblocks_charts"]), fetched_on("nearblocks_charts"))
    if all(k in raw for k in NEARBLOCKS_V3):  # /v1/charts could not be downloaded and v3 could
        v3_days = [fetched_on(k) for k in NEARBLOCKS_V3]
        v3_day = None if any(d is None for d in v3_days) else min(v3_days)
        daily = continue_with_v3(daily, drop_unfinished_days(parse_nearblocks_v3(raw), v3_day))
    intents = parse_defillama(raw["defillama_intents"])
    day = fetched_on("defillama_intents")
    out = daily.join(intents[intents.index < day] if day is not None else intents, how="left")
    out.attrs = daily.attrs.copy()
    return out


def fetched_on(name: str) -> pd.Timestamp | None:
    """The UTC day the reply a source was read from was downloaded on (by the last fetch_all), or None if not known."""
    at = FETCHED_AT.get(name)
    return pd.Timestamp(at).tz_convert("UTC").tz_localize(None).normalize() if at else None


def drop_unfinished_days(daily: pd.DataFrame, fetched: pd.Timestamp | None) -> pd.DataFrame:
    """Leave out the days that had not ended (UTC) when the replies were downloaded: their counts are partial.

    A day is unfinished because of its date, not because of its size: a day with far fewer transactions than the days
    before can be a real fall (2026-04-02 lost 72% of them), and a filter by size would drop it whenever it is the last
    day of a download. The daily APIs have so far returned finished days only, so this usually leaves the table as it is.
    """
    return daily if fetched is None else daily[daily.index < fetched]
