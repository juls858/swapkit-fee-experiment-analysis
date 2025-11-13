{{
  config(
    materialized='view',
    tags=['intermediate', 'elasticity', 'pool']
  )
}}

/*
  Pool-level elasticity analysis inputs with lagged features and period-over-period changes

  Source: fct_pool_weekly_summary

  This model:
  - Adds lagged metrics (previous period values) per pool
  - Calculates percentage changes for volume, fees, fee_bps per pool
  - Computes mix metrics (avg swap size changes, user composition) per pool
  - Prepares features for pool-level elasticity regression

  Grain: One row per pool per fee period (excluding first period which has no lag for each pool)
*/

WITH base AS (
    SELECT
        period_id,
        period_start_date,
        period_end_date,
        final_fee_bps,
        pool_name,
        pool_type,
        swaps_count,
        volume_usd,
        fees_usd,
        unique_swappers,
        avg_swap_size_usd,
        pct_of_period_swaps,
        pct_of_period_volume,
        pct_of_period_fees
    FROM {{ ref('fct_pool_weekly_summary') }}
),

lagged AS (
    SELECT
        *,
        -- Lag all key metrics by 1 period PER POOL
        LAG(final_fee_bps) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_fee_bps,
        LAG(volume_usd) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_volume_usd,
        LAG(fees_usd) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_fees_usd,
        LAG(swaps_count) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_swaps_count,
        LAG(unique_swappers) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_unique_swappers,
        LAG(avg_swap_size_usd) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_avg_swap_size_usd,
        LAG(pct_of_period_volume) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_pct_of_period_volume,
        LAG(pct_of_period_fees) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_pct_of_period_fees,
        LAG(pct_of_period_swaps) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_pct_of_period_swaps
    FROM base
)

SELECT
    period_id,
    period_start_date,
    period_end_date,
    final_fee_bps,
    pool_name,
    pool_type,

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

    -- Percentage changes (for elasticity calculation)
    CASE
        WHEN prev_fee_bps IS NOT NULL AND prev_fee_bps > 0
        THEN ((final_fee_bps - prev_fee_bps) / prev_fee_bps) * 100
        ELSE NULL
    END AS pct_change_fee_bps,

    CASE
        WHEN prev_volume_usd IS NOT NULL AND prev_volume_usd > 0
        THEN ((volume_usd - prev_volume_usd) / prev_volume_usd) * 100
        ELSE NULL
    END AS pct_change_volume,

    CASE
        WHEN prev_fees_usd IS NOT NULL AND prev_fees_usd > 0
        THEN ((fees_usd - prev_fees_usd) / prev_fees_usd) * 100
        ELSE NULL
    END AS pct_change_fees,

    CASE
        WHEN prev_swaps_count IS NOT NULL AND prev_swaps_count > 0
        THEN ((swaps_count - prev_swaps_count) / CAST(prev_swaps_count AS FLOAT)) * 100
        ELSE NULL
    END AS pct_change_swaps,

    CASE
        WHEN prev_unique_swappers IS NOT NULL AND prev_unique_swappers > 0
        THEN ((unique_swappers - prev_unique_swappers) / CAST(prev_unique_swappers AS FLOAT)) * 100
        ELSE NULL
    END AS pct_change_users,

    CASE
        WHEN prev_avg_swap_size_usd IS NOT NULL AND prev_avg_swap_size_usd > 0
        THEN ((avg_swap_size_usd - prev_avg_swap_size_usd) / prev_avg_swap_size_usd) * 100
        ELSE NULL
    END AS pct_change_avg_swap_size,

    -- Market share changes
    CASE
        WHEN prev_pct_of_period_volume IS NOT NULL AND prev_pct_of_period_volume > 0
        THEN ((pct_of_period_volume - prev_pct_of_period_volume) / prev_pct_of_period_volume) * 100
        ELSE NULL
    END AS pct_change_market_share_volume,

    CASE
        WHEN prev_pct_of_period_fees IS NOT NULL AND prev_pct_of_period_fees > 0
        THEN ((pct_of_period_fees - prev_pct_of_period_fees) / prev_pct_of_period_fees) * 100
        ELSE NULL
    END AS pct_change_market_share_fees,

    -- Absolute changes
    final_fee_bps - prev_fee_bps AS delta_fee_bps,
    volume_usd - prev_volume_usd AS delta_volume_usd,
    fees_usd - prev_fees_usd AS delta_fees_usd,
    swaps_count - prev_swaps_count AS delta_swaps_count,
    unique_swappers - prev_unique_swappers AS delta_unique_swappers,
    pct_of_period_volume - prev_pct_of_period_volume AS delta_market_share_volume,
    pct_of_period_fees - prev_pct_of_period_fees AS delta_market_share_fees,

    -- Revenue per swap/user
    CASE
        WHEN swaps_count > 0
        THEN fees_usd / swaps_count
        ELSE NULL
    END AS revenue_per_swap_usd,

    CASE
        WHEN unique_swappers > 0
        THEN fees_usd / unique_swappers
        ELSE NULL
    END AS revenue_per_user_usd,

    -- Time trend (for regression controls) - per pool
    ROW_NUMBER() OVER (PARTITION BY pool_name ORDER BY period_start_date) AS time_trend_pool,

    -- Global time trend
    ROW_NUMBER() OVER (ORDER BY period_start_date, pool_name) AS time_trend_global

FROM lagged
WHERE prev_fee_bps IS NOT NULL  -- Exclude first period with no lag per pool
ORDER BY period_start_date, pool_name
