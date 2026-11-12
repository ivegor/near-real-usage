-- Monthly cohort retention of transaction signers.
-- cohort = first month a signer appears inside the window, so the first month of the window
-- also contains older accounts and should be ignored when reading retention.
WITH monthly AS (
  SELECT DISTINCT DATE_TRUNC(block_date, MONTH) AS month, signer_account_id
  FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
  WHERE block_date BETWEEN @start_date AND @end_date
),
first_seen AS (
  SELECT signer_account_id, MIN(month) AS cohort
  FROM monthly
  GROUP BY 1
)
SELECT
  f.cohort,
  DATE_DIFF(m.month, f.cohort, MONTH) AS months_since_first,
  COUNT(*) AS active_signers
FROM monthly m
JOIN first_seen f USING (signer_account_id)
GROUP BY 1, 2
ORDER BY 1, 2
