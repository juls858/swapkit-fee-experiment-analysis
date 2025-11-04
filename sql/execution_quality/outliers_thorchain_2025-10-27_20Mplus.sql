-- Extract THORCHAIN routes with extreme eq_bps in 20M+ USD size bucket
-- Week start: 2025-10-27 (Monday-based week)
-- Output columns: quote_id, created_at, providers, sell_asset, sell_amount, buy_asset,
--                  expected_buy_amount, total_slippage_bps, eq_bps, order_usd

WITH base AS (
  SELECT
    quote_id,
    created_at,
    providers,
    sell_asset,
    CAST(sell_amount AS FLOAT64) AS sell_amount,
    buy_asset,
    CAST(expected_buy_amount AS FLOAT64) AS expected_buy_amount,
    CAST(total_slippage_bps AS FLOAT64) AS total_slippage_bps,
    meta.affiliate AS affiliate
  FROM `swapkit-shared-analytics.api_data.quotes`
  WHERE created_at >= TIMESTAMP('2025-10-20')
    AND created_at <  TIMESTAMP('2025-11-03')
    AND status_code = 200
    AND providers LIKE '%THORCHAIN%'
), enriched AS (
  SELECT
    quote_id,
    DATE_TRUNC(DATE(created_at), WEEK(MONDAY)) AS week_start,
    created_at,
    providers,
    sell_asset,
    buy_asset,
    sell_amount,
    expected_buy_amount,
    CASE
      WHEN REGEXP_CONTAINS(buy_asset, r'(USDT|USDC|DAI|USDD|\\bUSD\\b)') THEN expected_buy_amount
      WHEN REGEXP_CONTAINS(sell_asset, r'(USDT|USDC|DAI|USDD|\\bUSD\\b)') THEN sell_amount
      ELSE NULL
    END AS order_usd,
    -total_slippage_bps AS eq_bps,
    total_slippage_bps,
    affiliate
  FROM base
)
SELECT
  quote_id,
  created_at,
  providers,
  sell_asset,
  sell_amount,
  buy_asset,
  expected_buy_amount,
  total_slippage_bps,
  eq_bps,
  order_usd,
  affiliate
FROM enriched
WHERE week_start = DATE '2025-10-27'
  AND order_usd >= 2e7
ORDER BY eq_bps DESC, created_at
;
