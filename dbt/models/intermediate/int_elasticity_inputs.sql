{{
  config(
    materialized='view',
    tags=['intermediate', 'elasticity']
  )
}}

/*
  Elasticity analysis inputs with lagged features and period-over-period changes

  Source: fct_weekly_summary_final

  This model:
  - Adds lagged metrics (previous period values)
  - Calculates percentage changes for volume, fees, fee_bps
  - Computes mix metrics (avg swap size changes, user composition)
  - Prepares features for elasticity regression

  Grain: One row per fee period (excluding first period which has no lag)
*/

WITH base AS (
    SELECT
        period_id,
        period_start_date,
        period_end_date,
        days_in_period,
        final_fee_bps,
        period_source,
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
        revenue_per_user_usd
    FROM {{ ref('fct_weekly_summary_final') }}
),

lagged AS (
    SELECT
        *,
        -- Lag all key metrics by 1 period
        LAG(final_fee_bps) OVER (ORDER BY period_start_date) AS prev_fee_bps,
        LAG(volume_usd) OVER (ORDER BY period_start_date) AS prev_volume_usd,
        LAG(fees_usd) OVER (ORDER BY period_start_date) AS prev_fees_usd,
        LAG(swaps_count) OVER (ORDER BY period_start_date) AS prev_swaps_count,
        LAG(unique_swappers) OVER (ORDER BY period_start_date) AS prev_unique_swappers,
        LAG(avg_swap_size_usd) OVER (ORDER BY period_start_date) AS prev_avg_swap_size_usd,
        LAG(revenue_per_swap_usd) OVER (ORDER BY period_start_date) AS prev_revenue_per_swap_usd,
        LAG(revenue_per_user_usd) OVER (ORDER BY period_start_date) AS prev_revenue_per_user_usd,
        LAG(realized_fee_bps) OVER (ORDER BY period_start_date) AS prev_realized_fee_bps,
        LAG(new_swappers) OVER (ORDER BY period_start_date) AS prev_new_swappers,
        LAG(returning_swappers) OVER (ORDER BY period_start_date) AS prev_returning_swappers
    FROM base
)

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

    -- Absolute changes
    final_fee_bps - prev_fee_bps AS delta_fee_bps,
    volume_usd - prev_volume_usd AS delta_volume_usd,
    fees_usd - prev_fees_usd AS delta_fees_usd,
    swaps_count - prev_swaps_count AS delta_swaps_count,
    unique_swappers - prev_unique_swappers AS delta_unique_swappers,

    -- Mix metrics (for decomposition)
    CASE
        WHEN unique_swappers > 0
        THEN CAST(new_swappers AS FLOAT) / unique_swappers
        ELSE NULL
    END AS new_user_ratio,

    CASE
        WHEN unique_swappers > 0
        THEN CAST(returning_swappers AS FLOAT) / unique_swappers
        ELSE NULL
    END AS returning_user_ratio,

    CASE
        WHEN prev_unique_swappers IS NOT NULL AND prev_unique_swappers > 0
        THEN (CAST(new_swappers AS FLOAT) / unique_swappers) -
             (CAST(prev_new_swappers AS FLOAT) / prev_unique_swappers)
        ELSE NULL
    END AS delta_new_user_ratio,

    -- Time trend (for regression controls)
    ROW_NUMBER() OVER (ORDER BY period_start_date) AS time_trend,

    -- Day of week for period start (for controls)
    DAYOFWEEK(period_start_date) AS period_start_dow

FROM lagged
WHERE prev_fee_bps IS NOT NULL  -- Exclude first period with no lag
ORDER BY period_start_date
