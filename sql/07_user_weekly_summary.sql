-- ============================================================================
-- Phase 1: User-Level Weekly Summary
-- ============================================================================
-- Purpose: Track new vs returning users by detected fee period
-- Inputs: V_SWAPS_EXPERIMENT_WINDOW, V_FEE_PERIODS_VALIDATED
-- Output: "9R".FEE_EXPERIMENT.V_USER_WEEKLY_SUMMARY
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_USER_WEEKLY_SUMMARY AS
WITH first_seen AS (
    SELECT
        from_address,
        MIN(block_timestamp) AS first_swap_ts
    FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW
    GROUP BY 1
),
swaps_with_period AS (
    SELECT
        s.from_address,
        s.gross_volume_usd,
        s.total_fee_usd,
        p.period_id,
        p.period_start_date,
        p.period_end_date,
        p.detected_fee_bps,
        p.intended_fee_bps,
        p.fee_alignment_status,
        CASE WHEN f.first_swap_ts BETWEEN p.period_start_date AND p.period_end_date THEN 1 ELSE 0 END AS is_new_user
    FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW s
    LEFT JOIN "9R".FEE_EXPERIMENT.V_FEE_PERIODS_VALIDATED p
        ON s.swap_date BETWEEN p.period_start_date AND p.period_end_date
    LEFT JOIN first_seen f
        ON s.from_address = f.from_address
)
SELECT
    period_id,
    period_start_date,
    period_end_date,
    detected_fee_bps,
    intended_fee_bps,
    fee_alignment_status,
    COUNT(DISTINCT CASE WHEN is_new_user = 1 THEN from_address END) AS new_swappers,
    COUNT(DISTINCT CASE WHEN is_new_user = 0 THEN from_address END) AS returning_swappers,
    COUNT(DISTINCT from_address) AS unique_swappers,
    SUM(CASE WHEN is_new_user = 1 THEN gross_volume_usd ELSE 0 END) AS new_user_volume_usd,
    SUM(CASE WHEN is_new_user = 0 THEN gross_volume_usd ELSE 0 END) AS returning_user_volume_usd,
    SUM(CASE WHEN is_new_user = 1 THEN total_fee_usd ELSE 0 END) AS new_user_fees_usd,
    SUM(CASE WHEN is_new_user = 0 THEN total_fee_usd ELSE 0 END) AS returning_user_fees_usd
FROM swaps_with_period
GROUP BY 1,2,3,4,5,6
ORDER BY period_start_date;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_USER_WEEKLY_SUMMARY IS
    'User acquisition and retention metrics by detected fee period (new vs returning swappers).';

-- Summary
SELECT
    SUM(new_user_volume_usd) AS total_new_user_volume,
    SUM(returning_user_volume_usd) AS total_returning_user_volume
FROM "9R".FEE_EXPERIMENT.V_USER_WEEKLY_SUMMARY;
