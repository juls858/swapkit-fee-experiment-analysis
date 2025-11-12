{{
  config(
    materialized='view',
    tags=['marts', 'fact', 'pool']
  )
}}

/*
  Pool-level summary by fee period

  Sources:
  - stg_swaps_experiment_window
  - int_fee_periods_final

  Grain: One row per pool per fee period

  Provides pool-specific metrics for analyzing which pools
  are most sensitive to fee changes.
*/

WITH swaps_with_period AS (
    SELECT
        s.*,
        p.period_id,
        p.period_start_date,
        p.period_end_date,
        p.fee_bps AS final_fee_bps
    FROM {{ ref('stg_swaps_experiment_window') }} s
    LEFT JOIN {{ ref('int_fee_periods_final') }} p
        ON s.swap_date BETWEEN p.period_start_date AND p.period_end_date
)

SELECT
    period_id,
    period_start_date,
    period_end_date,
    final_fee_bps,
    pool_name,
    pool_type,

    -- Pool metrics
    COUNT(*) AS swaps_count,
    SUM(gross_volume_usd) AS volume_usd,
    SUM(total_fee_usd) AS fees_usd,
    COUNT(DISTINCT from_address) AS unique_swappers,
    AVG(gross_volume_usd) AS avg_swap_size_usd,

    -- Pool share of total period activity
    COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY period_id) AS pct_of_period_swaps,
    SUM(gross_volume_usd) / SUM(SUM(gross_volume_usd)) OVER (PARTITION BY period_id) AS pct_of_period_volume,
    SUM(total_fee_usd) / SUM(SUM(total_fee_usd)) OVER (PARTITION BY period_id) AS pct_of_period_fees

FROM swaps_with_period
WHERE period_id IS NOT NULL
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY period_start_date, volume_usd DESC
