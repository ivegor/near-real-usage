-- Revised relay detection: the saved results predate this correction and have not been re-queried.
-- Scan costs below describe the original queries; obtain a new dry-run estimate before running this version.
-- Who pays for a transaction, and how often the account acts: the product view of NEAR's accounts.
--
-- For every month and every account that acted (for a relayed transaction: the user, not the relayer):
--   payer      self       the account paid the fee of at least one of its transactions that month
--              sponsored  every transaction of the account was submitted and paid for by a relayer (an app)
--   frequency  transactions that month, in powers of ten: 1, 2-9, 10-99, 100-999, 1,000-9,999, 10,000+
--   namespace  kaiching / tg: accounts created by two reward apps inside their own namespaces; rest: all others
--
-- Output: one row per month; `cells` is ';'-separated namespace|payer|frequency|accounts|transactions|self-paid.
-- Cost: 91.28 GB (dry run, 2026-11-13). `python -m thesis bq-freq` unpacks the result into data/bq/payer_frequency.csv.
-- Move this date on a later run; it is saved with the result so partial months cannot become monthly comparisons.
DECLARE query_end DATE DEFAULT '2026-10-31';
WITH transaction_flags AS (
  -- One row per transaction, including Delegate after another action. Do not filter to action zero.
  SELECT block_date, transaction_hash, signer_account_id, receiver_account_id,
    MAX(CASE WHEN action_kind = 'DELEGATE_ACTION' THEN 1 ELSE 0 END) AS relayed
  FROM `bigquery-public-data.crypto_near_mainnet_us.transaction_actions`
  WHERE block_date BETWEEN '2025-08-01' AND query_end
  GROUP BY block_date, transaction_hash, signer_account_id, receiver_account_id
),
am AS (
  SELECT
    DATE_TRUNC(block_date, MONTH) AS m,
    IF(relayed = 1, receiver_account_id, signer_account_id) AS a,
    COUNT(*) AS txs,
    COUNTIF(relayed = 0) AS self_txs
  FROM transaction_flags
  GROUP BY 1, 2
),
g AS (
  SELECT
    m,
    CASE WHEN ENDS_WITH(a, '.kaiching') THEN 'kaiching' WHEN ENDS_WITH(a, '.tg') THEN 'tg' ELSE 'rest' END AS ns,
    IF(self_txs > 0, 'self', 'sponsored') AS payer,
    CASE WHEN txs = 1 THEN 'n1' WHEN txs < 10 THEN 'n2_9' WHEN txs < 100 THEN 'n10_99'
         WHEN txs < 1000 THEN 'n100_999' WHEN txs < 10000 THEN 'n1k_9k' ELSE 'n10k' END AS freq,
    COUNT(*) AS accounts, SUM(txs) AS txs, SUM(self_txs) AS self_txs
  FROM am
  GROUP BY 1, 2, 3, 4
)
SELECT FORMAT_DATE('%Y-%m', m) AS m, CAST(query_end AS STRING) AS query_end,
  STRING_AGG(FORMAT('%s|%s|%s|%d|%d|%d', ns, payer, freq, accounts, txs, self_txs), ';' ORDER BY ns, payer, freq) AS cells
FROM g
GROUP BY m
ORDER BY m
