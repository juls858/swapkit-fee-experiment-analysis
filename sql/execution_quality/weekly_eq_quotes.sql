-- Weekly EQ (bps) from SwapKit quotes only, grouped by provider and USD size buckets
-- Output columns: week_start, provider_group, size_bucket, routes, improvement_rate, avg_eq_bps, median_eq_bps, usd_volume
WITH base AS (
  SELECT
    created_at,
    providers,
    sell_asset,
    CAST(sell_amount AS FLOAT64) AS sell_amount,
    buy_asset,
    CAST(expected_buy_amount AS FLOAT64) AS expected_buy_amount,
    CAST(total_slippage_bps AS FLOAT64) AS total_slippage_bps
  FROM `swapkit-shared-analytics.api_data.quotes`
  WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
    AND status_code = 200
    AND (
      providers LIKE '%THORCHAIN%'
      OR providers LIKE '%CHAINFLIP%'
      OR providers LIKE '%NEAR%'
    )
), enriched AS (
  SELECT
    DATE_TRUNC(DATE(created_at), WEEK(MONDAY)) AS week_start,
    CASE
      WHEN providers LIKE '%THORCHAIN%' THEN 'THORCHAIN'
      WHEN providers LIKE '%CHAINFLIP%' THEN 'CHAINFLIP'
      WHEN providers LIKE '%NEAR%' THEN 'NEAR'
      ELSE 'OTHER'
    END AS provider_group,
    -- USD order size heuristic using stables on either side
    CASE
      WHEN REGEXP_CONTAINS(buy_asset, r'(USDT|USDC|DAI|USDD|\\bUSD\\b)') THEN expected_buy_amount
      WHEN REGEXP_CONTAINS(sell_asset, r'(USDT|USDC|DAI|USDD|\\bUSD\\b)') THEN sell_amount
      ELSE NULL
    END AS order_usd,
    -- Expected EQ (bps): invert slippage sign so improvement > 0
    -total_slippage_bps AS eq_bps
  FROM base
), bucketed AS (
  SELECT
    week_start,
    provider_group,
    CASE
      WHEN order_usd IS NULL THEN NULL
      WHEN order_usd < 1e3 THEN '[0,1k)'
      WHEN order_usd < 1e4 THEN '[1k,10k)'
      WHEN order_usd < 5e4 THEN '[10k,50k)'
      WHEN order_usd < 2.5e5 THEN '[50k,250k)'
      WHEN order_usd < 2e7 THEN '[250k,20M)'
      ELSE '20M+'
    END AS size_bucket,
    eq_bps,
    order_usd
  FROM enriched
)
SELECT
  week_start,
  provider_group,
  size_bucket,
  COUNT(*) AS routes,
  SAFE_DIVIDE(SUM(CASE WHEN eq_bps > 0 THEN 1 ELSE 0 END), COUNT(*)) AS improvement_rate,
  AVG(eq_bps) AS avg_eq_bps,
  APPROX_QUANTILES(eq_bps, 101)[OFFSET(50)] AS median_eq_bps,
  SUM(order_usd) AS usd_volume
FROM bucketed
WHERE size_bucket IS NOT NULL
GROUP BY week_start, provider_group, size_bucket
ORDER BY week_start DESC, provider_group, size_bucket;
