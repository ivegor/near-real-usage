"""Optional BigQuery cross-check on the NEAR public dataset.

Runs only when google-cloud-bigquery is installed and credentials are available
(`gcloud auth application-default login` or GOOGLE_APPLICATION_CREDENTIALS).
Every query has a hard cap on bytes billed, and a freshness check runs first:
the NEAR Lake source behind this dataset was deprecated in March 2026, so the
dataset may stop before today. Results go to data/bq_*.csv.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SQL = ROOT / "sql"
DATA = ROOT / "data"
MAX_BYTES = 80 * 1024**3  # 80 GB per query; BigQuery sandbox gives 1 TB/month free


def _client():
    try:
        from google.cloud import bigquery  # type: ignore
    except ImportError:
        return None, "google-cloud-bigquery not installed (pip install google-cloud-bigquery)"
    try:
        return bigquery.Client(), None
    except Exception as e:  # no credentials / project
        return None, f"BigQuery client unavailable: {e}"


def _run(client, name: str, params: dict | None = None) -> pd.DataFrame:
    from google.cloud import bigquery  # type: ignore

    qp = []
    for k, v in (params or {}).items():
        typ = "DATE" if k.endswith("_date") else "INT64"
        qp.append(bigquery.ScalarQueryParameter(k, typ, v))
    cfg = bigquery.QueryJobConfig(maximum_bytes_billed=MAX_BYTES, query_parameters=qp)
    sql = (SQL / f"{name}.sql").read_text()
    dry = client.query(sql, job_config=bigquery.QueryJobConfig(dry_run=True, query_parameters=qp))
    gb = dry.total_bytes_processed / 1024**3
    print(f"[bq] {name}: will scan {gb:.1f} GB")
    df = client.query(sql, job_config=cfg).to_dataframe()
    df.to_csv(DATA / f"bq_{name}.csv", index=False)
    return df


def run(start_date: str = "2025-01-01", heavy_threshold: int = 500) -> str:
    client, err = _client()
    if client is None:
        return f"Skipped: {err}."
    fresh = _run(client, "freshness")
    max_date = str(fresh["max_date"].iloc[0])
    params = {"start_date": start_date, "end_date": max_date, "heavy": heavy_threshold}
    heavy = _run(client, "heavy_signers", params)
    _run(client, "signer_cohorts", {"start_date": start_date, "end_date": max_date})
    last = heavy.sort_values("month").iloc[-1]
    share = last["heavy_txns"] / last["txns"] * 100 if last["txns"] else float("nan")
    return (
        f"Dataset latest block_date: {max_date}. In {str(last['month'])[:7]}, "
        f"{int(last['heavy_signers']):,} of {int(last['signers']):,} signers sent ≥{heavy_threshold} tx on some day "
        f"and produced {share:.0f}% of transactions. Cohort retention table: data/bq_signer_cohorts.csv."
    )
