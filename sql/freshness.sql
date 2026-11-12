-- Latest day present in the NEAR public dataset. Scans only the block_date column of recent partitions.
SELECT MAX(block_date) AS max_date
FROM `bigquery-public-data.crypto_near_mainnet_us.transactions`
WHERE block_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 400 DAY)
