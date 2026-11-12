-- One day of NEAR transactions by the kind of their actions: who signs, and for whom.
-- Used to show what the aggregator metrics "active accounts" and "new accounts" do and do not count.
-- Cost: 0.6 GB. Result for 2025-10-01 is committed as data/bq/one_day_actions_2025-10-01.csv.
SELECT
  action_kind,
  index_in_transaction = 0 AS is_first,          -- TRUE: the first action of a transaction
  COUNT(*) AS n,
  COUNT(DISTINCT transaction_hash) AS txs,
  COUNT(DISTINCT signer_account_id) AS signers,
  COUNT(DISTINCT receiver_account_id) AS receivers
FROM `bigquery-public-data.crypto_near_mainnet_us.transaction_actions`
WHERE block_date = '2025-10-01'
GROUP BY 1, 2
ORDER BY n DESC
