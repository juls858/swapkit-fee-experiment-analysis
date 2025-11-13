{{
  config(
    materialized='view',
    tags=['marts', 'fact', 'elasticity', 'pool']
  )
}}

/*
  Pool-level elasticity analysis inputs - final mart for Phase 4 analysis

  Source: int_pool_elasticity_inputs

  This model:
  - Exposes cleaned pool elasticity inputs for Python analysis
  - Filters to valid periods with complete data per pool
  - Ready for consumption by pool elasticity analysis and dashboard
  - Standardizes pool_type classification

  Grain: One row per pool per fee period transition (excludes first period per pool)
*/

SELECT
    period_id,
    period_start_date,
    period_end_date,
    final_fee_bps,
    pool_name,

    -- Standardize pool_type for consistency
    CASE
        WHEN pool_type = 'BTC Pool' THEN 'BTC'
        WHEN pool_type = 'ETH Pool' THEN 'ETH'
        WHEN pool_type = 'Stablecoin Pool' THEN 'STABLE'
        ELSE 'LONG_TAIL'
    END AS pool_type,

    -- Current period metrics
    swaps_count,
    volume_usd,
    fees_usd,
    unique_swappers,
    avg_swap_size_usd,
    pct_of_period_swaps,
    pct_of_period_volume,
    pct_of_period_fees,

    -- Previous period metrics
    prev_fee_bps,
    prev_volume_usd,
    prev_fees_usd,
    prev_swaps_count,
    prev_unique_swappers,
    prev_avg_swap_size_usd,
    prev_pct_of_period_volume,
    prev_pct_of_period_fees,
    prev_pct_of_period_swaps,

    -- Percentage changes
    pct_change_fee_bps,
    pct_change_volume,
    pct_change_fees,
    pct_change_swaps,
    pct_change_users,
    pct_change_avg_swap_size,
    pct_change_market_share_volume,
    pct_change_market_share_fees,

    -- Absolute changes
    delta_fee_bps,
    delta_volume_usd,
    delta_fees_usd,
    delta_swaps_count,
    delta_unique_swappers,
    delta_market_share_volume,
    delta_market_share_fees,

    -- Revenue metrics
    revenue_per_swap_usd,
    revenue_per_user_usd,

    -- Controls
    time_trend_pool,
    time_trend_global

FROM {{ ref('int_pool_elasticity_inputs') }}
WHERE
    -- Ensure we have valid data for elasticity calculation
    pct_change_fee_bps IS NOT NULL
    AND pct_change_volume IS NOT NULL
    AND pct_change_fees IS NOT NULL
    -- Filter out pools with very low activity (< 10 swaps in period)
    AND swaps_count >= 10
    AND prev_swaps_count >= 10
ORDER BY period_start_date, pool_name
