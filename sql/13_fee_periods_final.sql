-- ============================================================================
-- Phase 1: Final Fee Periods (Manual-only)
-- ============================================================================
-- Purpose: Publish final fee periods based solely on provided block heights.
-- Inputs: V_FEE_PERIODS_MANUAL
-- Output: "9R".FEE_EXPERIMENT.V_FEE_PERIODS_FINAL
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_FEE_PERIODS_FINAL AS
SELECT
    ROW_NUMBER() OVER (ORDER BY period_start_date) AS period_id,
    period_start_date,
    period_end_date,
    DATEDIFF(day, period_start_date::DATE, period_end_date::DATE) + 1 AS days_in_period,
    intended_fee_bps::FLOAT AS fee_bps,
    'manual' AS source
FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL
ORDER BY period_start_date;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_FEE_PERIODS_FINAL IS
    'Final fee periods derived from manual block-height windows (manual-only).';

-- Coverage check
SELECT
    MIN(period_start_date) AS first_period_start,
    MAX(period_end_date) AS last_period_end,
    SUM(days_in_period) AS total_days
FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_FINAL;
