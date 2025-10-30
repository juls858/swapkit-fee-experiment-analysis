-- ============================================================================
-- Phase 1: Pool-Level Weekly Summary
-- ============================================================================
-- Purpose: Aggregate metrics per pool within each detected fee period
-- Inputs: "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW, V_FEE_PERIODS_VALIDATED
-- Output: "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY AS
WITH swaps_with_period AS (
    SELECT
        s.pool_name,
        s.pool_type,
        s.swap_size_bucket,
        s.gross_volume_usd,
        s.total_fee_usd,
        s.liquidity_fee_usd,
        s.outbound_fee_usd,
        s.affiliate_fee_usd,
        s.from_address,
        p.period_id,
        p.period_start_date,
        p.period_end_date,
        p.detected_fee_bps,
        p.intended_fee_bps,
        p.fee_alignment_status
    FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW s
    LEFT JOIN "9R".FEE_EXPERIMENT.V_FEE_PERIODS_VALIDATED p
        ON s.swap_date BETWEEN p.period_start_date AND p.period_end_date
)
SELECT
    period_id,
    period_start_date,
    period_end_date,
    detected_fee_bps,
    intended_fee_bps,
    fee_alignment_status,
    pool_name,
    pool_type,
    COUNT(*) AS swaps_count,
    SUM(gross_volume_usd) AS volume_usd,
    SUM(total_fee_usd) AS fees_usd,
    SUM(liquidity_fee_usd) AS liquidity_fees_usd,
    SUM(outbound_fee_usd) AS outbound_fees_usd,
    SUM(affiliate_fee_usd) AS affiliate_fees_usd,
    COUNT(DISTINCT from_address) AS unique_swappers,
    SUM(CASE WHEN swap_size_bucket = 'Whale (>$100K)' THEN total_fee_usd ELSE 0 END) AS whale_fees_usd,
    SUM(CASE WHEN swap_size_bucket = 'Whale (>$100K)' THEN gross_volume_usd ELSE 0 END) AS whale_volume_usd
FROM swaps_with_period
GROUP BY 1,2,3,4,5,6,7,8
ORDER BY period_start_date, fees_usd DESC;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY IS
    'Pool-level metrics for each detected fee period including volume, fees, and whale contributions.';

-- Check top pools per period
SELECT
    period_id,
    pool_name,
    volume_usd,
    fees_usd
FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
QUALIFY ROW_NUMBER() OVER (PARTITION BY period_id ORDER BY fees_usd DESC) <= 5;
