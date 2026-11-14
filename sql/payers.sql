-- Revised relay detection: the saved results predate this correction and have not been re-queried.
-- Scan costs below describe the original queries; obtain a new dry-run estimate before running this version.
-- Who pays for an account's transactions: the account itself, or an app's relayer?
-- Months: July-October 2025 and July-October 2026 (July is only there so that August has a "previous month").
--
-- a (actor)  = the user behind the transaction (for a relayed transaction: the account the relayer acted for).
-- payer      = 'self' if the account paid for at least one of its own transactions in the month; otherwise the app
--              whose relayer paid for all of them: sweat, kaiching, hot (.tg relayers), ember, meteor, or 'other'.
-- fam        = namespace of the account, as in account_age.sql.
-- ret        = r if the same account was also active in the previous calendar month, else n.
--
-- Output, one row per month and section, packed as ';'-separated cells:
--   payer     family|payer|ret|accounts|transactions|transactions paid by the account itself
--   relayers  the 12 relayers with the most sponsored-only accounts: relayer|accounts|transactions
--
-- Cost: 53.23 GB (dry run, 2026-11-13). Result committed as data/bq/payers_result.csv.
WITH transaction_flags AS (
  -- One row per transaction, including Delegate after another action. Do not filter to action zero.
  SELECT block_date, transaction_hash, signer_account_id, receiver_account_id,
    MAX(CASE WHEN action_kind = 'DELEGATE_ACTION' THEN 1 ELSE 0 END) AS relayed
  FROM `bigquery-public-data.crypto_near_mainnet_us.transaction_actions`
  WHERE (block_date BETWEEN '2025-07-01' AND '2025-10-31' OR block_date BETWEEN '2026-07-01' AND '2026-10-31')
  GROUP BY block_date, transaction_hash, signer_account_id, receiver_account_id
),
t AS (
  SELECT
    DATE_TRUNC(block_date, MONTH) AS m,
    IF(relayed = 1, receiver_account_id, signer_account_id) AS a,
    IF(relayed = 1, signer_account_id, NULL) AS r,
    COUNT(*) AS n
  FROM transaction_flags
  GROUP BY 1, 2, 3
),
acc AS (
  SELECT m, a, SUM(n) AS txs, SUM(IF(r IS NULL, n, 0)) AS direct,
    ARRAY_AGG(r IGNORE NULLS ORDER BY n DESC LIMIT 1) AS rr
  FROM t GROUP BY 1, 2
),
x AS (
  SELECT m, a, txs, direct, IF(ARRAY_LENGTH(rr) > 0, rr[OFFSET(0)], NULL) AS relayer,
    LAG(m) OVER (PARTITION BY a ORDER BY m) AS pm
  FROM acc
),
y AS (
  SELECT m,
    CASE
      WHEN ENDS_WITH(a, '.kaiching') THEN 'kaiching'
      WHEN ENDS_WITH(a, '.tg') THEN 'tg'
      WHEN ENDS_WITH(a, '.sweat') THEN 'sweat'
      WHEN LENGTH(a) = 64 AND STRPOS(a, '.') = 0 THEN 'implicit'
      WHEN ENDS_WITH(a, '.near') THEN 'near'
      ELSE 'other'
    END AS fam,
    CASE
      WHEN direct > 0 THEN 'self'
      WHEN relayer = 'sweat-relayer.near' THEN 'sweat'
      WHEN ENDS_WITH(relayer, '.kaiching') THEN 'kaiching'
      WHEN ENDS_WITH(relayer, '.tg') THEN 'hot'
      WHEN ENDS_WITH(relayer, 'playember_reserve.near') THEN 'ember'
      WHEN relayer = 'meteor-relayer.near' THEN 'meteor'
      ELSE 'other'
    END AS payer,
    IF(pm = DATE_SUB(m, INTERVAL 1 MONTH), 'r', 'n') AS ret,
    relayer, txs, direct
  FROM x
)
SELECT FORMAT_DATE('%Y-%m', m) AS m, 'payer' AS sec, STRING_AGG(c, ';') AS cells
FROM (
  SELECT m, FORMAT('%s|%s|%s|%d|%d|%d', fam, payer, ret, COUNT(*), SUM(txs), SUM(direct)) AS c
  FROM y GROUP BY m, fam, payer, ret
)
GROUP BY m
UNION ALL
SELECT FORMAT_DATE('%Y-%m', m), 'relayers', STRING_AGG(c, ';')
FROM (
  SELECT m, FORMAT('%s|%d|%d', relayer, COUNT(*), SUM(txs)) AS c,
    ROW_NUMBER() OVER (PARTITION BY m ORDER BY COUNT(*) DESC) AS rk
  FROM y WHERE payer != 'self' GROUP BY m, relayer
)
WHERE rk <= 12
GROUP BY m
ORDER BY 1, 2
