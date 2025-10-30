-- ============================================================================
-- Phase 1: Prior-Year Comparison
-- ============================================================================
-- Purpose: Provide matched-window metrics for prior-year baseline
-- Inputs: V_SWAPS_EXPERIMENT_WINDOW (current year), THORCHAIN.DEFI.FACT_SWAPS for prior year
-- Output: "9R".FEE_EXPERIMENT.V_PRIOR_YEAR_COMPARISON
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_PRIOR_YEAR_COMPARISON AS
WITH current_periods AS (
    SELECT
        w.period_id,
        w.period_start_date,
        w.period_end_date,
        w.detected_fee_bps,
        w.intended_fee_bps,
        w.volume_usd,
        w.fees_usd,
        w.swaps_count,
        w.unique_swappers,
        w.avg_swap_size_usd,
        w.median_swap_size_usd,
        w.realized_fee_bps
    FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY w
),
prior_swaps AS (
    SELECT
        block_timestamp,
        GREATEST(FROM_AMOUNT_USD, TO_AMOUNT_USD) AS gross_volume_usd,
        LIQ_FEE_RUNE_USD AS liquidity_fee_usd,
        from_address
    FROM THORCHAIN.DEFI.FACT_SWAPS
    WHERE block_timestamp >= DATEADD(year, -1, '2025-08-15'::timestamp)
      AND block_timestamp < DATEADD(year, -1, '2025-11-01'::timestamp)
      AND GREATEST(FROM_AMOUNT_USD, TO_AMOUNT_USD) > 0
),
prior_periodized AS (
    SELECT
        c.period_id,
        c.period_start_date,
        c.period_end_date,
        p.block_timestamp,
        p.gross_volume_usd,
        p.liquidity_fee_usd,
        p.from_address
    FROM current_periods c
    LEFT JOIN prior_swaps p
        ON p.block_timestamp >= DATEADD(year, -1, c.period_start_date)
       AND p.block_timestamp < DATEADD(year, -1, DATEADD(day, 1, c.period_end_date))
),
prior_aggregates AS (
    SELECT
        period_id,
        MIN(block_timestamp) AS prior_period_start,
        MAX(block_timestamp) AS prior_period_end,
        SUM(gross_volume_usd) AS prior_volume_usd,
        SUM(liquidity_fee_usd) AS prior_fees_usd,
        COUNT(*) AS prior_swaps_count,
        COUNT(DISTINCT from_address) AS prior_unique_swappers,
        AVG(gross_volume_usd) AS prior_avg_swap_size_usd,
        MEDIAN(gross_volume_usd) AS prior_median_swap_size_usd,
        CASE WHEN SUM(gross_volume_usd) > 0 THEN SUM(liquidity_fee_usd) / SUM(gross_volume_usd) * 10000 ELSE NULL END AS prior_realized_fee_bps
    FROM prior_periodized
    GROUP BY 1
)
SELECT
    c.period_id,
    c.period_start_date,
    c.period_end_date,
    c.detected_fee_bps,
    c.intended_fee_bps,
    c.volume_usd,
    c.fees_usd,
    c.swaps_count,
    c.unique_swappers,
    c.avg_swap_size_usd,
    c.median_swap_size_usd,
    c.realized_fee_bps,
    p.prior_period_start,
    p.prior_period_end,
    p.prior_volume_usd,
    p.prior_fees_usd,
    p.prior_swaps_count,
    p.prior_unique_swappers,
    p.prior_avg_swap_size_usd,
    p.prior_median_swap_size_usd,
    p.prior_realized_fee_bps,
    CASE WHEN p.prior_volume_usd > 0 THEN (c.volume_usd - p.prior_volume_usd) / p.prior_volume_usd ELSE NULL END AS volume_change_pct,
    CASE WHEN p.prior_fees_usd > 0 THEN (c.fees_usd - p.prior_fees_usd) / p.prior_fees_usd ELSE NULL END AS fees_change_pct
FROM current_periods c
LEFT JOIN prior_aggregates p USING (period_id)
ORDER BY c.period_start_date;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_PRIOR_YEAR_COMPARISON IS
    'Comparison of experiment periods to prior-year matched windows for baseline benchmarking.';

SELECT
    COUNT(*) AS periods_compared,
    SUM(prior_volume_usd) AS prior_volume_total
FROM "9R".FEE_EXPERIMENT.V_PRIOR_YEAR_COMPARISON;
