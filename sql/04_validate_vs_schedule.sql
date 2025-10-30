-- ============================================================================
-- Phase 1: Validation Against Intended Fee Schedule
-- ============================================================================
-- Purpose: Compare detected fee periods to intended experiment schedule
-- Inputs: "9R".FEE_EXPERIMENT.V_FEE_CHANGEPOINTS
-- Output: "9R".FEE_EXPERIMENT.V_FEE_PERIODS_VALIDATED
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_FEE_PERIODS_VALIDATED AS
WITH intended_schedule AS (
    SELECT * FROM VALUES
        ('2025-08-22'::DATE, '2025-08-28'::DATE, 5),
        ('2025-08-29'::DATE, '2025-09-04'::DATE, 10),
        ('2025-09-05'::DATE, '2025-09-11'::DATE, 15),
        ('2025-09-12'::DATE, '2025-09-18'::DATE, 20),
        ('2025-09-19'::DATE, '2025-09-25'::DATE, 25),
        ('2025-09-26'::DATE, '2025-10-02'::DATE, 20),
        ('2025-10-03'::DATE, '2025-10-09'::DATE, 15),
        ('2025-10-10'::DATE, '2025-10-16'::DATE, 10),
        ('2025-10-17'::DATE, '2025-10-23'::DATE, 5)
        AS intended(start_date, end_date, intended_fee_bps)
),
intended_daily AS (
    SELECT
        intended_fee_bps,
        start_date,
        end_date,
        value AS day_offset,
        DATEADD(day, value, start_date) AS day_date
    FROM intended_schedule,
         LATERAL FLATTEN(
             INPUT => ARRAY_GENERATE_RANGE(
                 0,
                 DATEDIFF(day, start_date, end_date) + 1,
                 1
             )
         )
),
matched_daily AS (
    SELECT
        d.period_id,
        d.period_start_date,
        d.period_end_date,
        d.detected_fee_bps,
        d.confidence_score,
        d.volume_usd,
        d.fees_usd,
        d.change_direction,
        MAX(i.intended_fee_bps) AS intended_fee_bps,
        COUNT(*) AS overlap_days
    FROM "9R".FEE_EXPERIMENT.V_FEE_CHANGEPOINTS d
    LEFT JOIN intended_daily i
        ON i.day_date BETWEEN d.period_start_date AND d.period_end_date
    GROUP BY 1,2,3,4,5,6,7,8
),
matched_periods AS (
    SELECT
        period_id,
        period_start_date,
        period_end_date,
        detected_fee_bps,
        confidence_score,
        volume_usd,
        fees_usd,
        change_direction,
        intended_fee_bps,
        overlap_days,
        ROW_NUMBER() OVER (
            PARTITION BY period_id
            ORDER BY overlap_days DESC NULLS LAST
        ) AS overlap_rank
    FROM matched_daily
),
final AS (
    SELECT
        period_id,
        period_start_date,
        period_end_date,
        DATEDIFF(day, period_start_date, period_end_date) + 1 AS days_in_period,
        detected_fee_bps,
        intended_fee_bps,
        (detected_fee_bps - intended_fee_bps) AS delta_bps,
        volume_usd,
        fees_usd,
        change_direction,
        confidence_score,
        overlap_days,
        CASE
            WHEN intended_fee_bps IS NULL THEN 'no_intended_match'
            WHEN ABS(detected_fee_bps - intended_fee_bps) <= 1 THEN 'aligned'
            WHEN ABS(detected_fee_bps - intended_fee_bps) <= 3 THEN 'minor_deviation'
            ELSE 'major_deviation'
        END AS fee_alignment_status,
        CASE WHEN intended_fee_bps IS NULL THEN TRUE ELSE FALSE END AS is_missing_week,
        CASE WHEN overlap_days < days_in_period THEN TRUE ELSE FALSE END AS is_partial_overlap
    FROM matched_periods
    WHERE overlap_rank = 1
)
SELECT
    period_id,
    period_start_date,
    period_end_date,
    days_in_period,
    detected_fee_bps,
    intended_fee_bps,
    delta_bps,
    volume_usd,
    fees_usd,
    change_direction,
    confidence_score,
    overlap_days,
    fee_alignment_status,
    is_missing_week,
    is_partial_overlap
FROM final
ORDER BY period_start_date;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_FEE_PERIODS_VALIDATED IS
    'Validated fee periods comparing detected bps to intended schedule with anomaly flags.';

SELECT
    fee_alignment_status,
    COUNT(*) AS periods,
    ROUND(AVG(detected_fee_bps), 2) AS avg_detected_bps
FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_VALIDATED
GROUP BY 1;
