-- ============================================================================
-- Phase 1: Weekly Summary using Final Fee Periods
-- ============================================================================
-- Purpose: Recompute weekly/period summary metrics using V_FEE_PERIODS_FINAL
-- Inputs: V_SWAPS_EXPERIMENT_WINDOW, V_FEE_PERIODS_FINAL
-- Output: "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL AS
WITH swaps_with_period AS (
    SELECT
        s.*,
        p.period_id,
        p.period_start_date,
        p.period_end_date,
        p.fee_bps AS final_fee_bps,
        p.source  AS period_source,
        MIN(s.swap_date) OVER (PARTITION BY s.from_address) AS first_swap_date_in_window,
        (s.swap_date = MIN(s.swap_date) OVER (PARTITION BY s.from_address)) AS is_new_in_window
    FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW s
    LEFT JOIN "9R".FEE_EXPERIMENT.V_FEE_PERIODS_FINAL p
        ON s.swap_date BETWEEN p.period_start_date AND p.period_end_date
)
SELECT
    period_id,
    period_start_date,
    period_end_date,
    DATEDIFF(day, period_start_date::DATE, period_end_date::DATE) + 1 AS days_in_period,
    final_fee_bps,
    period_source,
    COUNT(*) AS swaps_count,
    SUM(gross_volume_usd) AS volume_usd,
    SUM(total_fee_usd) AS fees_usd,
    COUNT(DISTINCT from_address) AS unique_swappers,
    AVG(gross_volume_usd) AS avg_swap_size_usd,
    MEDIAN(gross_volume_usd) AS median_swap_size_usd,
    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY gross_volume_usd) AS p75_swap_size_usd,
    PERCENTILE_CONT(0.90) WITHIN GROUP (ORDER BY gross_volume_usd) AS p90_swap_size_usd,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY gross_volume_usd) AS p99_swap_size_usd,
    COUNT(DISTINCT IFF(is_new_in_window, from_address, NULL)) AS new_swappers,
    (COUNT(DISTINCT from_address) - COUNT(DISTINCT IFF(is_new_in_window, from_address, NULL))) AS returning_swappers,
    CASE WHEN SUM(gross_volume_usd) > 0 THEN SUM(total_fee_usd) / SUM(gross_volume_usd) * 10000 ELSE NULL END AS realized_fee_bps,
    CASE WHEN COUNT(*) > 0 THEN SUM(total_fee_usd) / COUNT(*) ELSE NULL END AS revenue_per_swap_usd,
    CASE WHEN COUNT(DISTINCT from_address) > 0 THEN SUM(total_fee_usd) / COUNT(DISTINCT from_address) ELSE NULL END AS revenue_per_user_usd
FROM swaps_with_period
GROUP BY 1,2,3,4,5,6
ORDER BY period_start_date;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL IS
    'Weekly summary computed using the final fee periods (manual preferred).';

-- Sanity check
SELECT COUNT(*) AS periods FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL;
