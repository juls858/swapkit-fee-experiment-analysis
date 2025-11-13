-- ============================================================================
-- Phase 3: User-Period Detail (User-Level Granularity)
-- ============================================================================
-- Purpose: One row per user per period for cohort and segmentation analysis
-- Inputs: V_SWAPS_EXPERIMENT_WINDOW, V_FEE_PERIODS_MANUAL
-- Output: "9R".FEE_EXPERIMENT.V_USER_PERIOD_DETAIL
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_USER_PERIOD_DETAIL AS
WITH swaps_with_period AS (
    SELECT
        s.*,
        p.period_id,
        p.period_start_date,
        p.period_end_date,
        p.fee_bps AS final_fee_bps,
        MIN(s.swap_date) OVER (PARTITION BY s.from_address) AS first_swap_date_in_window
    FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW s
    LEFT JOIN "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL p
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
        MEDIAN(gross_volume_usd) AS median_swap_size_usd,
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
    median_swap_size_usd,
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
    END AS engagement_level,

    -- First seen date for cohort analysis
    first_swap_date_in_window

FROM user_period_agg
ORDER BY period_start_date, volume_usd DESC;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_USER_PERIOD_DETAIL IS
    'User-level metrics by fee period for cohort and segmentation analysis (one row per user per period).';

-- Quick validation
SELECT
    period_id,
    final_fee_bps,
    COUNT(DISTINCT user_address) AS unique_users,
    SUM(volume_usd) AS total_volume,
    SUM(fees_usd) AS total_fees
FROM "9R".FEE_EXPERIMENT.V_USER_PERIOD_DETAIL
GROUP BY 1, 2
ORDER BY 1;
