-- ============================================================================
-- Phase 1: Daily Fee BPS Aggregation
-- ============================================================================
-- Purpose: Aggregate swap metrics to daily level with effective fee calculations
-- Source View: "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW
-- Output: "9R".FEE_EXPERIMENT.V_DAILY_FEE_BPS
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_DAILY_FEE_BPS AS
WITH daily_base AS (
    SELECT
        swap_date,
        SUM(gross_volume_usd) AS volume_usd,
        SUM(total_fee_usd) AS total_fees_usd,
        SUM(liquidity_fee_usd) AS liquidity_fees_usd,
        SUM(outbound_fee_usd) AS outbound_fees_usd,
        SUM(affiliate_fee_usd) AS affiliate_fees_usd,
        COUNT(*) AS swaps_count,
        COUNT(DISTINCT from_address) AS unique_swappers,
        COUNT(DISTINCT pool_name) AS distinct_pools,
        COUNT(DISTINCT IFF(affiliate_address IS NOT NULL, affiliate_address, NULL)) AS unique_affiliates,
        MEDIAN(effective_fee_bps) AS median_effective_fee_bps,
        AVG(effective_fee_bps) AS avg_effective_fee_bps,
        SUM(effective_fee_bps * gross_volume_usd) / NULLIF(SUM(gross_volume_usd), 0) AS vw_effective_fee_bps
    FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW
    GROUP BY swap_date
),
rolling AS (
    SELECT
        *,
        AVG(vw_effective_fee_bps) OVER (
            ORDER BY swap_date
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS vw_fee_bps_roll3,
        AVG(median_effective_fee_bps) OVER (
            ORDER BY swap_date
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS median_fee_bps_roll3,
        SUM(volume_usd) OVER (
            ORDER BY swap_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS volume_usd_roll7,
        SUM(total_fees_usd) OVER (
            ORDER BY swap_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS fees_usd_roll7
    FROM daily_base
)
SELECT
    swap_date,
    volume_usd,
    total_fees_usd,
    liquidity_fees_usd,
    outbound_fees_usd,
    affiliate_fees_usd,
    swaps_count,
    unique_swappers,
    distinct_pools,
    unique_affiliates,
    avg_effective_fee_bps,
    median_effective_fee_bps,
    vw_effective_fee_bps,
    vw_fee_bps_roll3,
    median_fee_bps_roll3,
    volume_usd_roll7,
    fees_usd_roll7,
    CASE
        WHEN volume_usd > 0 THEN total_fees_usd / volume_usd * 10000
        ELSE NULL
    END AS realized_fee_bps
FROM rolling
ORDER BY swap_date;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_DAILY_FEE_BPS IS
    'Daily swap aggregates with effective fee calculations and rolling metrics for fee-change detection.';

SELECT
    MIN(swap_date) AS first_day,
    MAX(swap_date) AS last_day,
    COUNT(*) AS num_days,
    ROUND(AVG(vw_effective_fee_bps), 2) AS avg_bps
FROM "9R".FEE_EXPERIMENT.V_DAILY_FEE_BPS;
