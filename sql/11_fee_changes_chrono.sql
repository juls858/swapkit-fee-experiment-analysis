-- ============================================================================
-- Phase 1: Fee Changes Chronological View (Direct-from-swaps)
-- ============================================================================
-- Purpose: Derive fee change dates directly from swaps by computing daily
--          volume-weighted effective fee bps, rounding to nearest 5 bps, and
--          compressing consecutive days with the same rounded fee into runs.
-- Source: THORCHAIN.DEFI.FACT_SWAPS
-- Output: "9R".FEE_EXPERIMENT.V_FEE_CHANGES_CHRONO
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_FEE_CHANGES_CHRONO AS
WITH daily AS (
    SELECT
        DATE_TRUNC('day', BLOCK_TIMESTAMP) AS day_date,
        SUM(GREATEST(FROM_AMOUNT_USD, TO_AMOUNT_USD)) AS volume_usd,
        SUM(LIQ_FEE_RUNE_USD) AS fees_usd,
        CASE
            WHEN SUM(GREATEST(FROM_AMOUNT_USD, TO_AMOUNT_USD)) > 0
            THEN 10000 * SUM(LIQ_FEE_RUNE_USD) / SUM(GREATEST(FROM_AMOUNT_USD, TO_AMOUNT_USD))
            ELSE NULL
        END AS vw_effective_fee_bps
    FROM THORCHAIN.DEFI.FACT_SWAPS
    WHERE BLOCK_TIMESTAMP >= '2025-08-15 00:00:00'
      AND BLOCK_TIMESTAMP <  '2025-11-01 00:00:00'
      AND GREATEST(FROM_AMOUNT_USD, TO_AMOUNT_USD) > 0
    GROUP BY 1
),
normalized AS (
    SELECT
        day_date,
        vw_effective_fee_bps,
        ROUND(vw_effective_fee_bps / 5) * 5 AS bps_nearest5
    FROM daily
),
with_lag AS (
    SELECT
        day_date,
        vw_effective_fee_bps,
        bps_nearest5,
        LAG(bps_nearest5) OVER (ORDER BY day_date) AS prev_bps_nearest5
    FROM normalized
),
run_flags AS (
    SELECT
        day_date,
        vw_effective_fee_bps,
        bps_nearest5,
        CASE WHEN prev_bps_nearest5 = bps_nearest5 THEN 0 ELSE 1 END AS is_new_run
    FROM with_lag
),
runs AS (
    SELECT
        day_date,
        vw_effective_fee_bps,
        bps_nearest5,
        SUM(is_new_run) OVER (ORDER BY day_date) AS run_id
    FROM run_flags
),
run_summary AS (
    SELECT
        run_id,
        MIN(day_date) AS fee_start_date,
        MAX(day_date) AS fee_end_date,
        COUNT(*) AS days_in_period,
        ROUND(AVG(vw_effective_fee_bps), 2) AS detected_fee_bps,
        MIN(bps_nearest5) AS detected_fee_bps_nearest5
    FROM runs
    GROUP BY run_id
),
days_by_fee AS (
    SELECT
        detected_fee_bps_nearest5,
        SUM(days_in_period) AS total_days_for_fee
    FROM run_summary
    GROUP BY 1
)
SELECT
    rs.run_id AS period_id,
    rs.fee_start_date,
    rs.fee_end_date,
    rs.days_in_period,
    rs.detected_fee_bps,
    rs.detected_fee_bps_nearest5,
    dbf.total_days_for_fee
FROM run_summary rs
LEFT JOIN days_by_fee dbf USING (detected_fee_bps_nearest5)
ORDER BY rs.fee_start_date;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_FEE_CHANGES_CHRONO IS
    'Chronological fee changes derived directly from swaps: daily VW fee bps rounded to nearest 5 bps, consecutive days compressed into runs.';

-- Quick check
SELECT
    COUNT(*) AS num_runs,
    MIN(fee_start_date) AS first_start,
    MAX(fee_end_date) AS last_end
FROM "9R".FEE_EXPERIMENT.V_FEE_CHANGES_CHRONO;
