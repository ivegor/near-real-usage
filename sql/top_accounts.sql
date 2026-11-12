-- Who sends NEAR's transactions: the largest accounts, what they call, and how concentrated it is.
-- Two months: October 2026 and October 2025.
--
-- a (actor) = the user behind the transaction (for a relayed transaction: the account the relayer acted for).
-- v (via)   = the contract a direct transaction calls, or 'relayer:<account>' for a relayed one. The relayer
--             identifies the app that paid for the transaction; the contract a relayed transaction ends up
--             calling is inside its arguments and is not read here (that column costs ~3 GB per day).
--
-- Output, one row per month and section, packed as ';'-separated cells:
--   via     top 40: via|transactions|distinct actors
--   actors  top 40: actor|transactions|its most frequent via
--   conc    total transactions|all actors|actors with >= 1000 transactions|their transactions|
--           top 10|top 25|top 100 transactions|actors needed for 50%|for 80% (among the >= 1000 group;
--           equal to the group size when the group does not reach that share)
--
-- Cost: 13.53 GB (dry run, 2026-11-12). Result committed as data/bq/top_accounts_result.csv.
WITH pairs AS (
  SELECT
    DATE_TRUNC(block_date, MONTH) AS m,
    IF(action_kind = 'DELEGATE_ACTION', receiver_account_id, signer_account_id) AS a,
    IF(action_kind = 'DELEGATE_ACTION', CONCAT('relayer:', signer_account_id), receiver_account_id) AS v,
    COUNT(*) AS n
  FROM `bigquery-public-data.crypto_near_mainnet_us.transaction_actions`
  WHERE (block_date BETWEEN '2025-10-01' AND '2025-10-31' OR block_date BETWEEN '2026-10-01' AND '2026-10-31')
    AND index_in_transaction = 0
  GROUP BY 1, 2, 3
),
tv AS (SELECT m, v, SUM(n) AS n, COUNT(DISTINCT a) AS actors FROM pairs GROUP BY 1, 2),
ta AS (SELECT m, a, SUM(n) AS n, ARRAY_AGG(v ORDER BY n DESC LIMIT 1)[OFFSET(0)] AS v FROM pairs GROUP BY 1, 2),
tt AS (SELECT m, SUM(n) AS total, COUNT(*) AS all_actors FROM ta GROUP BY 1),
heavy AS (
  SELECT m, a, n, v, total, all_actors,
    ROW_NUMBER() OVER (PARTITION BY m ORDER BY n DESC) AS rk,
    SUM(n) OVER (PARTITION BY m ORDER BY n DESC ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum
  FROM ta JOIN tt USING (m)
  WHERE n >= 1000
),
tvr AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY m ORDER BY n DESC) AS rk FROM tv WHERE n >= 1000)
SELECT FORMAT_DATE('%Y-%m', m) AS m, 'via' AS sec,
  STRING_AGG(FORMAT('%s|%d|%d', v, n, actors), ';' ORDER BY n DESC) AS cells
FROM tvr WHERE rk <= 40 GROUP BY m
UNION ALL
SELECT FORMAT_DATE('%Y-%m', m), 'actors', STRING_AGG(FORMAT('%s|%d|%s', a, n, v), ';' ORDER BY n DESC)
FROM heavy WHERE rk <= 40 GROUP BY m
UNION ALL
SELECT FORMAT_DATE('%Y-%m', m), 'conc',
  FORMAT('%d|%d|%d|%d|%d|%d|%d|%d|%d', ANY_VALUE(total), ANY_VALUE(all_actors), COUNT(*), SUM(n),
    SUM(IF(rk <= 10, n, 0)), SUM(IF(rk <= 25, n, 0)), SUM(IF(rk <= 100, n, 0)),
    COUNTIF(cum - n < 0.5 * total), COUNTIF(cum - n < 0.8 * total))
FROM heavy GROUP BY m
ORDER BY 1, 2
