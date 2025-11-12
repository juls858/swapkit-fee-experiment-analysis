{{
  config(
    materialized='table',
    tags=['marts', 'fact', 'weekly']
  )
}}

/*
  Weekly/period summary metrics using final fee periods

  Sources:
  - stg_swaps_experiment_window
  - int_fee_periods_final

  This is the primary fact table for dashboard consumption.

  Grain: One row per fee period

  Metrics included:
  - Volume and swap counts
  - User metrics (new vs returning)
  - Swap size distributions
  - Revenue per swap and per user
  - Realized fee bps vs intended
*/

WITH swaps_with_period AS (
    SELECT
        s.*,
        p.period_id,
        p.period_start_date,
        p.period_end_date,
        p.fee_bps AS final_fee_bps,
        p.source AS period_source,
        MIN(s.swap_date) OVER (PARTITION BY s.from_address) AS first_swap_date_in_window,
        (s.swap_date = MIN(s.swap_date) OVER (PARTITION BY s.from_address)) AS is_new_in_window
    FROM {{ ref('stg_swaps_experiment_window') }} s
    LEFT JOIN {{ ref('int_fee_periods_final') }} p
        ON s.swap_date BETWEEN p.period_start_date AND p.period_end_date
)

SELECT
    period_id,
    period_start_date,
    period_end_date,
    DATEDIFF(day, period_start_date::DATE, period_end_date::DATE) + 1 AS days_in_period,
    final_fee_bps,
    period_source,

    -- Volume and swap metrics
    COUNT(*) AS swaps_count,
    SUM(gross_volume_usd) AS volume_usd,
    SUM(total_fee_usd) AS fees_usd,

    -- User metrics
    COUNT(DISTINCT from_address) AS unique_swappers,
    COUNT(DISTINCT IFF(is_new_in_window, from_address, NULL)) AS new_swappers,
    (COUNT(DISTINCT from_address) - COUNT(DISTINCT IFF(is_new_in_window, from_address, NULL))) AS returning_swappers,

    -- Swap size distributions
    AVG(gross_volume_usd) AS avg_swap_size_usd,
    MEDIAN(gross_volume_usd) AS median_swap_size_usd,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY gross_volume_usd) AS p75_swap_size_usd,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY gross_volume_usd) AS p90_swap_size_usd,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY gross_volume_usd) AS p99_swap_size_usd,

    -- Revenue metrics
    CASE
        WHEN SUM(gross_volume_usd) > 0
        THEN SUM(total_fee_usd) / SUM(gross_volume_usd) * 10000
        ELSE NULL
    END AS realized_fee_bps,
    CASE
        WHEN COUNT(*) > 0
        THEN SUM(total_fee_usd) / COUNT(*)
        ELSE NULL
    END AS revenue_per_swap_usd,
    CASE
        WHEN COUNT(DISTINCT from_address) > 0
        THEN SUM(total_fee_usd) / COUNT(DISTINCT from_address)
        ELSE NULL
    END AS revenue_per_user_usd

FROM swaps_with_period
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY period_start_date
