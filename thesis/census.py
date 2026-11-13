"""Signer census: who signs NEAR transactions, measured from the chain itself.

The account counts in THESIS.md come from one source, BigQuery. This module is the independent check on
them: it measures the same chain a second way, with no API key and no Google account:

1. Draw random block heights (fixed seed) inside two 90-day windows: the latest one and the same
   window a year earlier.
2. Download those blocks from the FastNEAR block archive and list every transaction in them.
   For a meta transaction (a relayer signs for a user) the user is taken from the delegate action,
   so relayers do not hide the people behind them.
3. For every distinct account in the sample ask an archival RPC node whether the account already
   existed 30 days and 365 days before the window started (`view_account` at that block height).

Output: the share of transactions (and of sampled accounts) that comes from accounts older than
30 / 365 days, with a block-bootstrap 95% interval, plus what those transactions call.

`python -m thesis census` does the network part and writes data/raw/census_*. The public endpoints are
rate-limited without a key, so it takes about 1.5 hours; it caches every response and resumes if interrupted.
`python -m thesis build` only reads those files, so the build stays fast and works offline.
"""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import requests

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"
BLOCK_URL = "https://mainnet.neardata.xyz/v0/block/{height}"
RPC_URL = "https://archival-rpc.mainnet.fastnear.com"

SEED = 20261112
WINDOW_DAYS = 90
# Blocks carried about 6x more transactions a year ago, so fewer blocks give a similar sample size.
BLOCKS_PER_WINDOW = {"prior": 120, "recent": 330}
MAX_TX_PER_WINDOW = 1200  # transactions whose accounts get an age check (random subset of the sampled ones)
AGE_DAYS = (30, 365)
# Seconds between requests per host. Without an API key both hosts answer HTTP 429 after short bursts and then
# keep refusing for minutes, so the pace is slow on purpose and slows down further after every refusal.
MIN_INTERVAL = {BLOCK_URL.split("/v0")[0]: 7.0, RPC_URL: 2.5}
COOL_DOWN = 240  # seconds to wait after an HTTP 429
BOUND_TOLERANCE_NS = 5 * 60 * 10**9  # window edges are located to within 5 minutes

SAMPLE_FILE, EXIST_FILE, META_FILE = "census_sample.csv", "census_existence.csv", "census_meta.json"
CACHE_DIR = RAW_DIR.parent / "census_cache"  # resumable downloads, not committed
CLASSES = ["365d+", "30-365d", "new"]

_session = requests.Session()
_session.headers["User-Agent"] = "near-real-usage-thesis"
_locks = {host: threading.Lock() for host in MIN_INTERVAL}
_last_call = {host: 0.0 for host in MIN_INTERVAL}


# ---------------------------------------------------------------- network

def _get_json(url: str, **kw):
    """Paced request, one at a time per host. A 429 means: wait, slow down, try again."""
    host = next(h for h in MIN_INTERVAL if url.startswith(h))
    method = kw.pop("method", "GET")
    last: Exception | None = None
    for _ in range(60):
        with _locks[host]:
            wait = _last_call[host] + MIN_INTERVAL[host] - time.time()
            if wait > 0:
                time.sleep(wait)
            try:
                r = _session.request(method, url, timeout=90, **kw)
                status = r.status_code
            except requests.RequestException as e:
                last, status = e, 0
            if status == 429:
                MIN_INTERVAL[host] = min(20.0, MIN_INTERVAL[host] * 1.25)
                print(f"[census] {host} answered 429: waiting {COOL_DOWN}s, pace now {MIN_INTERVAL[host]:.1f}s", flush=True)
                time.sleep(COOL_DOWN)
            _last_call[host] = time.time()
        if status == 200:
            return r.json()
        if status not in (0, 429, 500, 502, 503, 504):
            try:
                return r.json()  # JSON-RPC errors can come with a 4xx status
            except ValueError:
                pass
        last = last if status == 0 else RuntimeError(f"HTTP {status}")
        if status != 429:
            time.sleep(5)
    raise RuntimeError(f"Failed to fetch {url}: {last}")


def _rpc(method: str, params: dict) -> dict:
    return _get_json(RPC_URL, method="POST", json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})


def _block_header(height: int) -> tuple[int, int] | None:
    """(height, timestamp_ns) of the first existing block at or after `height` (heights can be skipped)."""
    for h in range(height, height + 50):
        res = _rpc("block", {"block_id": h})
        if "result" in res:
            hd = res["result"]["header"]
            return int(hd["height"]), int(hd["timestamp"])
    return None


def height_at(ts_ns: int, lo: tuple[int, int], hi: tuple[int, int]) -> int:
    """Height of a block within BOUND_TOLERANCE_NS of ts_ns, by interpolation between two known
    (height, timestamp) points. Block times are regular, so this takes a few requests, not dozens."""
    best = min((lo, hi), key=lambda p: abs(p[1] - ts_ns))
    for _ in range(25):
        if abs(best[1] - ts_ns) <= BOUND_TOLERANCE_NS or hi[0] - lo[0] <= 1:
            break
        guess = lo[0] + int((ts_ns - lo[1]) / max(hi[1] - lo[1], 1) * (hi[0] - lo[0]))
        guess = min(max(guess, lo[0] + 1), hi[0] - 1)
        got = _block_header(guess)
        if got is None:
            break
        lo, hi = (got, hi) if got[1] < ts_ns else (lo, got)
        best = min((best, got), key=lambda p: abs(p[1] - ts_ns))
    return best[0]


def parse_block(block: dict | None) -> list[dict]:
    """One row per transaction: who acted (user behind a relayer if any) and what was called."""
    if not block:
        return []
    hd = block["block"]["header"]
    rows = []
    for shard in block.get("shards", []):
        chunk = shard.get("chunk")
        if not chunk:
            continue
        for item in chunk.get("transactions", []):
            tx = item["transaction"]
            actor, target, actions, relayed = tx["signer_id"], tx["receiver_id"], tx.get("actions", []), False
            for a in actions:
                if isinstance(a, dict) and "Delegate" in a:
                    d = a["Delegate"]["delegate_action"]
                    actor, target, actions, relayed = d["sender_id"], d["receiver_id"], d.get("actions", []), True
                    break
            first = actions[0] if actions else "none"
            if isinstance(first, dict):
                kind = next(iter(first))
                body = first[kind]
                method = body.get("method_name", kind) if isinstance(body, dict) else kind
            else:
                method = str(first)
            rows.append({
                "height": int(hd["height"]), "ts": int(hd["timestamp"]), "actor": actor,
                "signer": tx["signer_id"], "target": target, "method": method, "relayed": relayed,
            })
    return rows


def _cached(name: str, compute):
    path = CACHE_DIR / name
    if path.exists():
        return json.loads(path.read_text())
    value = compute()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))
    return value


def _block_rows(height: int) -> dict:
    def get():
        block = _get_json(BLOCK_URL.format(height=height))
        return {"found": block is not None, "rows": parse_block(block)}
    return _cached(f"blocks/{height}.json", get)


def _exists(account: str, height: int) -> bool:
    def get():
        res = _rpc("query", {"request_type": "view_account", "account_id": account, "block_id": height})
        if "result" in res:
            return True
        cause = (res.get("error", {}).get("cause") or {}).get("name", "")
        if cause in ("UNKNOWN_ACCOUNT", "INVALID_ACCOUNT"):
            return False
        raise RuntimeError(f"view_account {account}@{height}: {json.dumps(res)[:200]}")
    return _cached(f"exists/{height}/{account}.json", get)


def fetch(last_date: str, seed: int = SEED, blocks: dict[str, int] | None = None) -> None:
    """Network part: sample blocks, check account ages, write data/raw/census_*. Safe to re-run: it resumes."""
    blocks = blocks or BLOCKS_PER_WINDOW
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    end = pd.Timestamp(last_date) + pd.Timedelta(days=1)  # end of the last full day, UTC

    def bounds() -> dict:
        hd = _rpc("block", {"finality": "final"})["result"]["header"]
        top = (int(hd["height"]), int(hd["timestamp"]))
        floor = _block_header(top[0] - 140_000_000)  # far enough back for every bound used below
        out = {}
        for label, shift in (("prior", 365), ("recent", 0)):
            w_end = end - pd.Timedelta(days=shift)
            w_start = w_end - pd.Timedelta(days=WINDOW_DAYS)
            out[label] = {
                "start": str(w_start.date()), "end": str((w_end - pd.Timedelta(days=1)).date()),
                "height_start": height_at(int(w_start.value), floor, top),
                "height_end": height_at(int(w_end.value), floor, top),
                "ref_heights": {f"{d}d_before_start": height_at(int((w_start - pd.Timedelta(days=d)).value), floor, top)
                                for d in AGE_DAYS},
            }
            print(f"[census] {label}: {out[label]}", flush=True)
        return out

    windows = _cached(f"bounds_{last_date}.json", bounds)
    plan = {label: sorted({int(h) for h in rng.integers(w["height_start"], w["height_end"], size=blocks[label])})
            for label, w in windows.items()}

    def download(label: str) -> pd.DataFrame:
        got = [_block_rows(h) for h in plan[label]]
        windows[label]["blocks_requested"] = len(plan[label])
        windows[label]["blocks_found"] = sum(1 for g in got if g["found"])
        df = pd.DataFrame([r for g in got for r in g["rows"]])
        df.insert(0, "window", label)
        return df

    samples, exist_rows = [], []
    with ThreadPoolExecutor(1) as pool:  # blocks download ahead while ages are checked on the other host
        futures = {label: pool.submit(download, label) for label in plan}
        for label, fut in futures.items():
            df = fut.result()
            windows[label]["transactions_sampled"] = len(df)
            if len(df) > MAX_TX_PER_WINDOW:
                df = df.iloc[np.sort(rng.choice(len(df), MAX_TX_PER_WINDOW, replace=False))]
            samples.append(df)
            actors = sorted(df["actor"].unique())
            refs = [windows[label]["ref_heights"][f"{d}d_before_start"] for d in AGE_DAYS]
            print(f"[census] {label}: {windows[label]['blocks_found']} blocks, {windows[label]['transactions_sampled']} "
                  f"transactions, keeping {len(df)}, {len(actors)} accounts to check", flush=True)
            for i, a in enumerate(actors):
                young = _exists(a, refs[0])
                # an account that did not exist 30 days before the window did not exist 365 days before it either
                old = _exists(a, refs[1]) if young else False
                exist_rows.append({"window": label, "actor": a, "existed_30d": young, "existed_365d": old})
                if i % 200 == 0:
                    print(f"[census] {label}: checked {i}/{len(actors)}", flush=True)
    meta = {"seed": seed, "window_days": WINDOW_DAYS, "max_tx_per_window": MAX_TX_PER_WINDOW,
            "sources": {"blocks": BLOCK_URL, "rpc": RPC_URL},
            "fetched_at_utc": pd.Timestamp.now(tz="UTC").isoformat(), "windows": windows}
    pd.concat(samples).to_csv(RAW_DIR / SAMPLE_FILE, index=False)
    pd.DataFrame(exist_rows).to_csv(RAW_DIR / EXIST_FILE, index=False)
    (RAW_DIR / META_FILE).write_text(json.dumps(meta, indent=2))


# ---------------------------------------------------------------- pure metrics

def load() -> tuple[pd.DataFrame, pd.DataFrame, dict] | None:
    paths = [RAW_DIR / f for f in (SAMPLE_FILE, EXIST_FILE, META_FILE)]
    if not all(p.exists() for p in paths):
        return None
    return pd.read_csv(paths[0]), pd.read_csv(paths[1]), json.loads(paths[2].read_text())


def classify(sample: pd.DataFrame, exist: pd.DataFrame) -> pd.DataFrame:
    """Attach an age class to every sampled transaction: 365d+, 30-365d or new."""
    df = sample.merge(exist, on=["window", "actor"], how="left")
    df["age"] = np.where(df["existed_365d"].fillna(False).astype(bool), "365d+",
                         np.where(df["existed_30d"].fillna(False).astype(bool), "30-365d", "new"))
    return df


def _block_bootstrap(per_block: pd.DataFrame, col: str, seed: int, n_boot: int = 2000) -> tuple[float, float]:
    """95% interval for sum(col)/sum(n), resampling whole blocks (transactions in a block are not independent)."""
    rng = np.random.default_rng(seed)
    num, den = per_block[col].to_numpy(float), per_block["n"].to_numpy(float)
    idx = rng.integers(0, len(den), size=(n_boot, len(den)))
    est = num[idx].sum(axis=1) / np.maximum(den[idx].sum(axis=1), 1)
    lo, hi = np.percentile(est, [2.5, 97.5])
    return float(lo), float(hi)


def summarize(sample: pd.DataFrame, exist: pd.DataFrame, meta: dict | None = None, seed: int = SEED) -> dict:
    df = classify(sample, exist)
    out: dict = {"seed": (meta or {}).get("seed", seed), "windows": {}}
    for label, w in df.groupby("window"):
        pb = w.assign(**{c: (w["age"] == c).astype(int) for c in CLASSES}).groupby("height")[CLASSES].sum()
        pb["n"] = w.groupby("height").size()
        n = len(w)
        tx_share = {c: float((w["age"] == c).mean()) for c in CLASSES}
        tx_ci = {c: _block_bootstrap(pb, c, seed) for c in CLASSES}
        acc = w.drop_duplicates("actor")
        by_actor = w["actor"].value_counts()
        targets = w["target"].value_counts(normalize=True).head(8)
        methods = (w["target"] + " :: " + w["method"]).value_counts(normalize=True).head(8)
        out["windows"][label] = {
            **((meta or {}).get("windows", {}).get(label, {})),
            "transactions": n,
            "blocks_with_transactions": int(len(pb)),
            "accounts": int(len(acc)),
            "tx_share_by_account_age": tx_share,
            "tx_share_ci95": {c: [round(lo, 4), round(hi, 4)] for c, (lo, hi) in tx_ci.items()},
            # distinct accounts in a transaction sample over-represent frequent senders; read with that in mind
            "account_share_by_age": {c: float((acc["age"] == c).mean()) for c in CLASSES},
            "relayed_tx_share": float(w["relayed"].mean()),
            "top10_accounts_tx_share": float(by_actor.head(10).sum() / n),
            "top_targets": {k: round(float(v), 4) for k, v in targets.items()},
            "top_calls": {k: round(float(v), 4) for k, v in methods.items()},
        }
    return out
