-- Revised relay detection: the saved results predate this correction and have not been re-queried.
-- Scan costs below describe the original queries; obtain a new dry-run estimate before running this version.
-- Who is behind NEAR's transactions, month by month: account family, account age, and whether the
-- account was also active in the previous month. Full population, not a sample.
--
-- "actor"  = the account that acted. For a meta transaction (any action = DELEGATE_ACTION) the
--            signer is a relayer and the transaction's receiver is the user, so the receiver is the actor.
-- "f"      = the first day the account appears in ANY transaction, as signer or receiver, since genesis.
-- "age"    = f relative to the first day of the month: m0 (first seen during the month), lt30, lt1y,
--            lt2y, ge2y.
-- "ret"    = r if the same actor was also active in the previous calendar month, else n.
--
-- Output: one row per month; `cells` is a ';'-separated list of
--   family|age|ret|accounts|transactions|relayed_transactions|accounts_with_exactly_one_transaction
-- (packed this way so the result is 25 short rows). `python -m thesis bq-age` unpacks it.
--
-- Cost: 482.64 GB scanned (dry run, 2026-11-12). Run once; it fits the 1 TB/month free tier.
-- The `accounts` table in this dataset is NOT used: a query on it scans 1.03 TB.
WITH fs AS (
  SELECT a, MIN(d) AS f
  FROM (
    SELECT signer_account_id AS a, block_date AS d
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date <= '2026-11-11'
    UNION ALL
    SELECT receiver_account_id, block_date
    FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
    WHERE block_date <= '2026-11-11'
  )
  GROUP BY a
),
transaction_flags AS (
  -- One row per transaction, including Delegate after another action. Do not filter to action zero.
  SELECT block_date, transaction_hash, signer_account_id, receiver_account_id,
    MAX(CASE WHEN action_kind = 'DELEGATE_ACTION' THEN 1 ELSE 0 END) AS relayed
  FROM `bigquery-public-data.crypto_near_mainnet_us.transaction_actions`
  WHERE block_date BETWEEN '2024-11-01' AND '2026-11-11'
  GROUP BY block_date, transaction_hash, signer_account_id, receiver_account_id
),
act0 AS (
  SELECT
    DATE_TRUNC(block_date, MONTH) AS m,
    IF(relayed = 1, receiver_account_id, signer_account_id) AS a,
    COUNT(*) AS txs,
    COUNTIF(relayed = 1) AS rtx
  FROM transaction_flags
  GROUP BY 1, 2
),
act AS (
  SELECT m, a, txs, rtx, LAG(m) OVER (PARTITION BY a ORDER BY m) AS pm
  FROM act0
),
j AS (
  SELECT
    m,
    CASE
      WHEN ENDS_WITH(act.a, '.kaiching') THEN 'kaiching'
      WHEN ENDS_WITH(act.a, '.tg') THEN 'tg'
      WHEN ENDS_WITH(act.a, '.sweat') THEN 'sweat'
      WHEN LENGTH(act.a) = 64 AND STRPOS(act.a, '.') = 0 THEN 'implicit'
      WHEN ENDS_WITH(act.a, '.near') THEN 'near'
      ELSE 'other'
    END AS fam,
    CASE
      WHEN f IS NULL THEN 'unknown'
      WHEN f >= m THEN 'm0'
      WHEN DATE_DIFF(m, f, DAY) < 30 THEN 'lt30'
      WHEN DATE_DIFF(m, f, DAY) < 365 THEN 'lt1y'
      WHEN DATE_DIFF(m, f, DAY) < 730 THEN 'lt2y'
      ELSE 'ge2y'
    END AS age,
    IF(pm = DATE_SUB(m, INTERVAL 1 MONTH), 'r', 'n') AS ret,
    COUNT(*) AS accounts,
    SUM(txs) AS txs,
    SUM(rtx) AS rtx,
    COUNTIF(txs = 1) AS single
  FROM act
  LEFT JOIN fs ON act.a = fs.a
  GROUP BY 1, 2, 3, 4
)
SELECT
  m,
  STRING_AGG(FORMAT('%s|%s|%s|%d|%d|%d|%d', fam, age, ret, accounts, txs, rtx, single), ';' ORDER BY fam, age, ret) AS cells
FROM j
GROUP BY m
ORDER BY m
