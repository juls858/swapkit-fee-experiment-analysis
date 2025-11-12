{{
  config(
    materialized='view',
    tags=['marts', 'fact', 'elasticity']
  )
}}

/*
  Elasticity analysis inputs - final mart for Phase 2 analysis

  Source: int_elasticity_inputs

  This model:
  - Exposes cleaned elasticity inputs for Python analysis
  - Filters to valid periods with complete data
  - Ready for consumption by elasticity.py and revenue_decomposition.py

  Grain: One row per fee period transition (excludes first period)
*/

SELECT
    period_id,
    period_start_date,
    period_end_date,
    days_in_period,
    final_fee_bps,
    period_source,

    -- Current period metrics
    swaps_count,
    volume_usd,
    fees_usd,
    unique_swappers,
    new_swappers,
    returning_swappers,
    avg_swap_size_usd,
    median_swap_size_usd,
    p75_swap_size_usd,
    p90_swap_size_usd,
    p99_swap_size_usd,
    realized_fee_bps,
    revenue_per_swap_usd,
    revenue_per_user_usd,

    -- Previous period metrics
    prev_fee_bps,
    prev_volume_usd,
    prev_fees_usd,
    prev_swaps_count,
    prev_unique_swappers,
    prev_avg_swap_size_usd,
    prev_revenue_per_swap_usd,
    prev_revenue_per_user_usd,
    prev_realized_fee_bps,
    prev_new_swappers,
    prev_returning_swappers,

    -- Percentage changes
    pct_change_fee_bps,
    pct_change_volume,
    pct_change_fees,
    pct_change_swaps,
    pct_change_users,
    pct_change_avg_swap_size,

    -- Absolute changes
    delta_fee_bps,
    delta_volume_usd,
    delta_fees_usd,
    delta_swaps_count,
    delta_unique_swappers,

    -- Mix metrics
    new_user_ratio,
    returning_user_ratio,
    delta_new_user_ratio,

    -- Controls
    time_trend,
    period_start_dow

FROM {{ ref('int_elasticity_inputs') }}
WHERE
    -- Ensure we have valid data for elasticity calculation
    pct_change_fee_bps IS NOT NULL
    AND pct_change_volume IS NOT NULL
    AND pct_change_fees IS NOT NULL
ORDER BY period_start_date
