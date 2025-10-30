-- ============================================================================
-- Phase 1: Period-Level Weekly Summary
-- ============================================================================
-- Purpose: Aggregate descriptive metrics by detected fee period
-- Inputs: "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW, V_FEE_PERIODS_VALIDATED
-- Output: "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY AS
WITH swaps_with_period AS (
    SELECT
        s.*,
        p.period_id,
        p.period_start_date,
        p.period_end_date,
        p.detected_fee_bps,
        p.intended_fee_bps,
        p.fee_alignment_status,
        p.confidence_score
    FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW s
    LEFT JOIN "9R".FEE_EXPERIMENT.V_FEE_PERIODS_VALIDATED p
        ON s.swap_date BETWEEN p.period_start_date AND p.period_end_date
),
period_aggregates AS (
    SELECT
        period_id,
        period_start_date,
        period_end_date,
        DATEDIFF(day, period_start_date, period_end_date) + 1 AS days_in_period,
        detected_fee_bps,
        intended_fee_bps,
        fee_alignment_status,
        ROUND(AVG(confidence_score), 3) AS avg_confidence,
        COUNT(*) AS swaps_count,
        SUM(gross_volume_usd) AS volume_usd,
        SUM(total_fee_usd) AS fees_usd,
        SUM(liquidity_fee_usd) AS liquidity_fees_usd,
        SUM(outbound_fee_usd) AS outbound_fees_usd,
        SUM(affiliate_fee_usd) AS affiliate_fees_usd,
        COUNT(DISTINCT from_address) AS unique_swappers,
        COUNT(DISTINCT pool_name) AS distinct_pools,
        AVG(gross_volume_usd) AS avg_swap_size_usd,
        MEDIAN(gross_volume_usd) AS median_swap_size_usd,
        APPROX_PERCENTILE(gross_volume_usd, 0.75) AS p75_swap_size_usd,
        APPROX_PERCENTILE(gross_volume_usd, 0.9) AS p90_swap_size_usd,
        APPROX_PERCENTILE(gross_volume_usd, 0.99) AS p99_swap_size_usd,
        SUM(CASE WHEN swap_size_bucket = 'Whale (>$100K)' THEN total_fee_usd ELSE 0 END) AS whale_fees_usd,
        SUM(CASE WHEN swap_size_bucket = 'Whale (>$100K)' THEN gross_volume_usd ELSE 0 END) AS whale_volume_usd
    FROM swaps_with_period
    GROUP BY 1,2,3,4,5,6,7
),
revenue_metrics AS (
    SELECT
        period_id,
        CASE WHEN swaps_count > 0 THEN fees_usd / swaps_count ELSE NULL END AS revenue_per_swap_usd,
        CASE WHEN unique_swappers > 0 THEN fees_usd / unique_swappers ELSE NULL END AS revenue_per_user_usd,
        CASE WHEN volume_usd > 0 THEN fees_usd / volume_usd * 10000 ELSE NULL END AS realized_fee_bps
    FROM period_aggregates
)
SELECT
    p.period_id,
    p.period_start_date,
    p.period_end_date,
    p.days_in_period,
    p.detected_fee_bps,
    p.intended_fee_bps,
    p.fee_alignment_status,
    p.avg_confidence,
    p.volume_usd,
    p.fees_usd,
    p.liquidity_fees_usd,
    p.outbound_fees_usd,
    p.affiliate_fees_usd,
    p.swaps_count,
    p.unique_swappers,
    p.distinct_pools,
    p.avg_swap_size_usd,
    p.median_swap_size_usd,
    p.p75_swap_size_usd,
    p.p90_swap_size_usd,
    p.p99_swap_size_usd,
    p.whale_volume_usd,
    p.whale_fees_usd,
    r.revenue_per_swap_usd,
    r.revenue_per_user_usd,
    r.realized_fee_bps
FROM period_aggregates p
LEFT JOIN revenue_metrics r USING (period_id)
ORDER BY p.period_start_date;

COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY IS
    'Descriptive metrics for each detected fee period/week including volume, fees, swap counts, and size distribution.';

-- Quick check
SELECT
    COUNT(*) AS period_rows,
    SUM(volume_usd) AS total_volume_usd,
    SUM(fees_usd) AS total_fees_usd
FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY;
