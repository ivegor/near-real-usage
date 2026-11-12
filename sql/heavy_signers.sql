-- Monthly share of transactions coming from "heavy" signers:
-- accounts that signed >= @heavy transactions on at least one day (bot-like behaviour proxy).
WITH per_day AS (
  SELECT block_date, signer_account_id, COUNT(*) AS n
  FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
  WHERE block_date BETWEEN @start_date AND @end_date
  GROUP BY 1, 2
),
heavy_accounts AS (
  SELECT DISTINCT DATE_TRUNC(block_date, MONTH) AS month, signer_account_id
  FROM per_day
  WHERE n >= @heavy
)
SELECT
  DATE_TRUNC(p.block_date, MONTH) AS month,
  COUNT(DISTINCT p.signer_account_id) AS signers,
  COUNT(DISTINCT h.signer_account_id) AS heavy_signers,
  SUM(p.n) AS txns,
  SUM(IF(h.signer_account_id IS NOT NULL, p.n, 0)) AS heavy_txns
FROM per_day p
LEFT JOIN heavy_accounts h
  ON h.signer_account_id = p.signer_account_id
 AND h.month = DATE_TRUNC(p.block_date, MONTH)
GROUP BY 1
ORDER BY 1
