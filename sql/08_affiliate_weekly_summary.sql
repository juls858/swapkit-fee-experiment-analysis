-- ============================================================================
-- Phase 1: Affiliate Weekly Summary
-- ============================================================================
-- Purpose: Capture affiliate behavior by detected fee period
-- Inputs: V_SWAPS_EXPERIMENT_WINDOW, V_FEE_PERIODS_VALIDATED
-- Output: "9R".FEE_EXPERIMENT.V_AFFIL_WEEKLY_SUMMARY
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_AFFIL_WEEKLY_SUMMARY AS
WITH swaps_with_period AS (
    SELECT
        s.affiliate_address,
        s.gross_volume_usd,
        s.total_fee_usd,
        s.affiliate_fee_usd,
        p.period_id,
        p.period_start_date,
        p.period_end_date,
        p.detected_fee_bps,
        p.intended_fee_bps,
        p.fee_alignment_status
    FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW s
    LEFT JOIN "9R".FEE_EXPERIMENT.V_FEE_PERIODS_VALIDATED p
        ON s.swap_date BETWEEN p.period_start_date AND p.period_end_date
    WHERE s.affiliate_address IS NOT NULL
)
SELECT
    period_id,
    period_start_date,
    period_end_date,
    detected_fee_bps,
    intended_fee_bps,
    fee_alignment_status,
    affiliate_address,
    COUNT(*) AS swaps_count,
    SUM(gross_volume_usd) AS volume_usd,
    SUM(total_fee_usd) AS fees_usd,
    SUM(affiliate_fee_usd) AS affiliate_fees_usd
FROM swaps_with_period
GROUP BY 1,2,3,4,5,6,7
ORDER BY period_start_date, fees_usd DESC;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_AFFIL_WEEKLY_SUMMARY IS
    'Affiliate metrics by fee period including volume, fees, and affiliate earnings.';

-- Top affiliates per period
SELECT
    period_id,
    affiliate_address,
    volume_usd,
    affiliate_fees_usd
FROM "9R".FEE_EXPERIMENT.V_AFFIL_WEEKLY_SUMMARY
QUALIFY ROW_NUMBER() OVER (PARTITION BY period_id ORDER BY volume_usd DESC) <= 5;
