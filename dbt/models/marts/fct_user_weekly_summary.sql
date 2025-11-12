{{
  config(
    materialized='view',
    tags=['marts', 'fact', 'user']
  )
}}

/*
  User-level summary by fee period

  Sources:
  - stg_swaps_experiment_window
  - int_fee_periods_final

  Grain: One row per user per fee period

  Provides user-specific behavior metrics for analyzing
  how different user segments respond to fee changes.
*/

WITH swaps_with_period AS (
    SELECT
        s.*,
        p.period_id,
        p.period_start_date,
        p.period_end_date,
        p.fee_bps AS final_fee_bps,
        MIN(s.swap_date) OVER (PARTITION BY s.from_address) AS first_swap_date_in_window
    FROM {{ ref('stg_swaps_experiment_window') }} s
    LEFT JOIN {{ ref('int_fee_periods_final') }} p
        ON s.swap_date BETWEEN p.period_start_date AND p.period_end_date
),

user_period_agg AS (
    SELECT
        period_id,
        period_start_date,
        period_end_date,
        final_fee_bps,
        from_address AS user_address,
        MIN(first_swap_date_in_window) AS first_swap_date_in_window,
        COUNT(*) AS swaps_count,
        SUM(gross_volume_usd) AS volume_usd,
        SUM(total_fee_usd) AS fees_usd,
        AVG(gross_volume_usd) AS avg_swap_size_usd,
        COUNT(DISTINCT pool_name) AS distinct_pools_used,
        COUNT(DISTINCT swap_date) AS active_days
    FROM swaps_with_period
    WHERE period_id IS NOT NULL
    GROUP BY 1, 2, 3, 4, 5
)

SELECT
    period_id,
    period_start_date,
    period_end_date,
    final_fee_bps,
    user_address,
    swaps_count,
    volume_usd,
    fees_usd,
    avg_swap_size_usd,
    distinct_pools_used,
    active_days,

    -- User classification
    CASE
        WHEN first_swap_date_in_window >= period_start_date
            AND first_swap_date_in_window <= period_end_date
        THEN 'New'
        ELSE 'Returning'
    END AS user_cohort,

    -- User engagement level
    CASE
        WHEN swaps_count >= 10 THEN 'Power User'
        WHEN swaps_count >= 5 THEN 'Regular'
        WHEN swaps_count >= 2 THEN 'Occasional'
        ELSE 'One-time'
    END AS engagement_level

FROM user_period_agg
ORDER BY period_start_date, volume_usd DESC
