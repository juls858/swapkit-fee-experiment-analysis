-- ============================================================================
-- Phase 1: Fee Change Point Detection
-- ============================================================================
-- Purpose: Derive fee-period boundaries from observed swap fees
-- Inputs: "9R".FEE_EXPERIMENT.V_DAILY_FEE_BPS
-- Output: "9R".FEE_EXPERIMENT.V_FEE_CHANGEPOINTS (one row per detected period)
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_FEE_CHANGEPOINTS AS
WITH daily AS (
    SELECT
        swap_date,
        vw_effective_fee_bps,
        median_fee_bps_roll3,
        vw_fee_bps_roll3,
        volume_usd,
        volume_usd_roll7,
        total_fees_usd,
        fees_usd_roll7,
        ROW_NUMBER() OVER (ORDER BY swap_date) AS day_seq
    FROM "9R".FEE_EXPERIMENT.V_DAILY_FEE_BPS
),
lagged AS (
    SELECT
        *,
        LAG(vw_fee_bps_roll3) OVER (ORDER BY swap_date) AS prev_vw_fee_bps_roll3,
        LAG(median_fee_bps_roll3) OVER (ORDER BY swap_date) AS prev_median_fee_bps_roll3,
        LAG(volume_usd_roll7) OVER (ORDER BY swap_date) AS prev_volume_usd_roll7
    FROM daily
),
flags AS (
    SELECT
        *,
        CASE
            WHEN prev_vw_fee_bps_roll3 IS NULL THEN 1  -- first day
            WHEN ABS(vw_fee_bps_roll3 - prev_vw_fee_bps_roll3) >= 1.5
                AND vw_fee_bps_roll3 IS NOT NULL
                AND prev_vw_fee_bps_roll3 IS NOT NULL
            THEN 1
            WHEN ABS(median_fee_bps_roll3 - prev_median_fee_bps_roll3) >= 1.5
                AND median_fee_bps_roll3 IS NOT NULL
                AND prev_median_fee_bps_roll3 IS NOT NULL
            THEN 1
            ELSE 0
        END AS change_flag
    FROM lagged
),
periodized AS (
    SELECT
        *,
        SUM(change_flag) OVER (
            ORDER BY swap_date
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS period_id
    FROM flags
),
period_summary AS (
    SELECT
        period_id,
        MIN(swap_date) AS period_start_date,
        MAX(swap_date) AS period_end_date,
        COUNT(*) AS days_in_period,
        MEDIAN(vw_effective_fee_bps) AS median_fee_bps,
        MEDIAN(vw_fee_bps_roll3) AS smoothed_fee_bps,
        SUM(volume_usd) AS volume_usd,
        SUM(total_fees_usd) AS fees_usd,
        AVG(volume_usd_roll7) AS avg_volume_usd_roll7,
        AVG(fees_usd_roll7) AS avg_fees_usd_roll7
    FROM periodized
    GROUP BY period_id
),
with_shifts AS (
    SELECT
        ps.*,
        LAG(smoothed_fee_bps) OVER (ORDER BY period_start_date) AS prev_fee_bps,
        LEAD(smoothed_fee_bps) OVER (ORDER BY period_start_date) AS next_fee_bps,
        LEAD(period_start_date) OVER (ORDER BY period_start_date) AS next_period_start
    FROM period_summary ps
),
scored AS (
    SELECT
        period_id,
        period_start_date,
        COALESCE(DATEADD(day, -1, next_period_start), period_end_date) AS period_end_date,
        days_in_period,
        ROUND(smoothed_fee_bps, 2) AS detected_fee_bps,
        ROUND(prev_fee_bps, 2) AS previous_fee_bps,
        ROUND(next_fee_bps, 2) AS next_fee_bps,
        ROUND(smoothed_fee_bps - prev_fee_bps, 2) AS delta_from_previous,
        volume_usd,
        fees_usd,
        avg_volume_usd_roll7,
        avg_fees_usd_roll7,
        CASE
            WHEN prev_fee_bps IS NULL THEN 'initial'
            WHEN smoothed_fee_bps > prev_fee_bps THEN 'increase'
            WHEN smoothed_fee_bps < prev_fee_bps THEN 'decrease'
            ELSE 'flat'
        END AS change_direction,
        LEAST(
            1.0,
            0.3
            + CASE WHEN days_in_period >= 5 THEN 0.2 ELSE 0.05 END
            + CASE WHEN ABS(smoothed_fee_bps - prev_fee_bps) >= 4 THEN 0.35
                   WHEN ABS(smoothed_fee_bps - prev_fee_bps) >= 2 THEN 0.25
                   ELSE 0.1 END
            + CASE WHEN COALESCE(volume_usd, 0) >= 500000 THEN 0.2 ELSE 0.1 END
        ) AS confidence_score
    FROM with_shifts
)
SELECT
    period_id,
    period_start_date,
    period_end_date,
    days_in_period,
    detected_fee_bps,
    previous_fee_bps,
    next_fee_bps,
    delta_from_previous,
    change_direction,
    volume_usd,
    fees_usd,
    avg_volume_usd_roll7,
    avg_fees_usd_roll7,
    confidence_score,
    'detected' AS source
FROM scored
ORDER BY period_start_date;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_FEE_CHANGEPOINTS IS
    'Detected fee periods derived from observed swap fees with change direction and confidence score.';

SELECT
    COUNT(*) AS periods,
    MIN(period_start_date) AS first_period_start,
    MAX(period_end_date) AS last_period_end,
    ROUND(AVG(detected_fee_bps), 2) AS avg_detected_bps
FROM "9R".FEE_EXPERIMENT.V_FEE_CHANGEPOINTS;
