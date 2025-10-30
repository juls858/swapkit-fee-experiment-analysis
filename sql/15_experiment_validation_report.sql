-- ============================================================================
-- Phase 1: Experiment Validation Report
-- ============================================================================
-- Purpose: Compare intended fee bps (from manual block heights) to realized
--          fee bps computed from swaps, per period. Flag deviations and
--          summarize by fee tier.
-- Inputs: V_FEE_PERIODS_MANUAL, V_WEEKLY_SUMMARY_FINAL
-- Output (queries): Period-level validation table and summary checks
-- ============================================================================

-- Period-level validation (manual periods only)
WITH manual AS (
    SELECT
        period_start_date,
        period_end_date,
        intended_fee_bps
    FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL
),
realized AS (
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
        realized_fee_bps
    FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL
    WHERE period_source = 'manual'
),
joined AS (
    SELECT
        r.period_id,
        r.period_start_date,
        r.period_end_date,
        r.days_in_period,
        m.intended_fee_bps,
        r.realized_fee_bps,
        ROUND(r.realized_fee_bps - m.intended_fee_bps, 2) AS delta_bps,
        r.swaps_count,
        r.volume_usd,
        r.fees_usd
    FROM realized r
    LEFT JOIN manual m
      ON r.period_start_date = m.period_start_date
     AND r.period_end_date   = m.period_end_date
)
SELECT
    period_id,
    period_start_date,
    period_end_date,
    days_in_period,
    intended_fee_bps,
    ROUND(realized_fee_bps, 2) AS realized_fee_bps,
    delta_bps,
    CASE WHEN ABS(delta_bps) <= 1 THEN 'PASS' ELSE 'FAIL' END AS within_1bp,
    swaps_count,
    volume_usd,
    fees_usd
FROM joined
ORDER BY period_start_date;

-- Summary by intended fee tier (manual windows)
WITH manual AS (
    SELECT period_start_date, period_end_date, intended_fee_bps
    FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL
),
realized AS (
    SELECT period_start_date, period_end_date, realized_fee_bps
    FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL
    WHERE period_source = 'manual'
),
joined AS (
    SELECT m.*, r.realized_fee_bps
    FROM manual m
    LEFT JOIN realized r
      ON r.period_start_date = m.period_start_date
     AND r.period_end_date   = m.period_end_date
)
SELECT
    intended_fee_bps,
    COUNT(*) AS periods,
    SUM(DATEDIFF(day, period_start_date::DATE, period_end_date::DATE) + 1) AS total_days,
    ROUND(AVG(realized_fee_bps), 2) AS avg_realized_bps,
    ROUND(AVG(realized_fee_bps - intended_fee_bps), 2) AS avg_delta_bps
FROM joined
GROUP BY intended_fee_bps
ORDER BY intended_fee_bps;

-- Overall pass/fail
WITH per AS (
    SELECT
        CASE WHEN ABS(realized_fee_bps - intended_fee_bps) <= 1 THEN 1 ELSE 0 END AS pass_flag
    FROM (
        SELECT m.intended_fee_bps, r.realized_fee_bps
        FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL m
        LEFT JOIN "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL r
          ON r.period_source = 'manual'
         AND r.period_start_date = m.period_start_date
         AND r.period_end_date   = m.period_end_date
    ) x
)
SELECT
    SUM(pass_flag) AS periods_passing,
    COUNT(*)       AS periods_total,
    CASE WHEN SUM(pass_flag) = COUNT(*) THEN 'PASS' ELSE 'REVIEW' END AS overall
FROM per;
