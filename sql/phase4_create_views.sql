/*
  Phase 4 Pool Analysis - Create Views

  Run this script with a user that has CREATE VIEW permissions on:
  - 9R.FEE_EXPERIMENT schema
  - 9R.FEE_EXPERIMENT_MARTS schema (will be created if needed)

  Dependencies:
  - 9R.FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY must exist
*/

-- Create MARTS schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS "9R".FEE_EXPERIMENT_MARTS;

-- ============================================================================
-- Intermediate View: INT_POOL_ELASTICITY_INPUTS
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.INT_POOL_ELASTICITY_INPUTS AS
WITH base AS (
    SELECT
        period_id,
        period_start_date,
        period_end_date,
        final_fee_bps,
        pool_name,
        pool_type,
        swaps_count,
        volume_usd,
        fees_usd,
        unique_swappers,
        avg_swap_size_usd,
        pct_of_period_swaps,
        pct_of_period_volume,
        pct_of_period_fees
    FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
),

lagged AS (
    SELECT
        *,
        -- Lag all key metrics by 1 period, partitioned by pool_name
        LAG(final_fee_bps) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_fee_bps,
        LAG(volume_usd) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_volume_usd,
        LAG(fees_usd) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_fees_usd,
        LAG(swaps_count) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_swaps_count,
        LAG(unique_swappers) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_unique_swappers,
        LAG(avg_swap_size_usd) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_avg_swap_size_usd,
        LAG(pct_of_period_volume) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_pct_of_period_volume,
        LAG(pct_of_period_fees) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_pct_of_period_fees,
        LAG(pct_of_period_swaps) OVER (PARTITION BY pool_name ORDER BY period_start_date) AS prev_pct_of_period_swaps
    FROM base
)

SELECT
    period_id,
    period_start_date,
    period_end_date,
    final_fee_bps,
    pool_name,
    pool_type,

    -- Current period metrics
    swaps_count,
    volume_usd,
    fees_usd,
    unique_swappers,
    avg_swap_size_usd,
    pct_of_period_swaps,
    pct_of_period_volume,
    pct_of_period_fees,

    -- Previous period metrics
    prev_fee_bps,
    prev_volume_usd,
    prev_fees_usd,
    prev_swaps_count,
    prev_unique_swappers,
    prev_avg_swap_size_usd,
    prev_pct_of_period_volume,
    prev_pct_of_period_fees,
    prev_pct_of_period_swaps,

    -- Percentage changes (for elasticity calculation)
    CASE
        WHEN prev_fee_bps IS NOT NULL AND prev_fee_bps > 0
        THEN ((final_fee_bps - prev_fee_bps) / prev_fee_bps) * 100
        ELSE NULL
    END AS pct_change_fee_bps,

    CASE
        WHEN prev_volume_usd IS NOT NULL AND prev_volume_usd > 0
        THEN ((volume_usd - prev_volume_usd) / prev_volume_usd) * 100
        ELSE NULL
    END AS pct_change_volume,

    CASE
        WHEN prev_fees_usd IS NOT NULL AND prev_fees_usd > 0
        THEN ((fees_usd - prev_fees_usd) / prev_fees_usd) * 100
        ELSE NULL
    END AS pct_change_fees,

    CASE
        WHEN prev_swaps_count IS NOT NULL AND prev_swaps_count > 0
        THEN ((swaps_count - prev_swaps_count) / CAST(prev_swaps_count AS FLOAT)) * 100
        ELSE NULL
    END AS pct_change_swaps,

    CASE
        WHEN prev_unique_swappers IS NOT NULL AND prev_unique_swappers > 0
        THEN ((unique_swappers - prev_unique_swappers) / CAST(prev_unique_swappers AS FLOAT)) * 100
        ELSE NULL
    END AS pct_change_users,

    CASE
        WHEN prev_avg_swap_size_usd IS NOT NULL AND prev_avg_swap_size_usd > 0
        THEN ((avg_swap_size_usd - prev_avg_swap_size_usd) / prev_avg_swap_size_usd) * 100
        ELSE NULL
    END AS pct_change_avg_swap_size,

    CASE
        WHEN prev_pct_of_period_volume IS NOT NULL AND prev_pct_of_period_volume > 0
        THEN ((pct_of_period_volume - prev_pct_of_period_volume) / prev_pct_of_period_volume) * 100
        ELSE NULL
    END AS pct_change_market_share_volume,

    CASE
        WHEN prev_pct_of_period_fees IS NOT NULL AND prev_pct_of_period_fees > 0
        THEN ((pct_of_period_fees - prev_pct_of_period_fees) / prev_pct_of_period_fees) * 100
        ELSE NULL
    END AS pct_change_market_share_fees,

    -- Absolute changes
    final_fee_bps - prev_fee_bps AS delta_fee_bps,
    volume_usd - prev_volume_usd AS delta_volume_usd,
    fees_usd - prev_fees_usd AS delta_fees_usd,
    swaps_count - prev_swaps_count AS delta_swaps_count,
    unique_swappers - prev_unique_swappers AS delta_unique_swappers,
    pct_of_period_volume - prev_pct_of_period_volume AS delta_market_share_volume,
    pct_of_period_fees - prev_pct_of_period_fees AS delta_market_share_fees,

    -- Per-unit metrics
    CASE
        WHEN swaps_count > 0
        THEN fees_usd / swaps_count
        ELSE NULL
    END AS revenue_per_swap_usd,

    CASE
        WHEN unique_swappers > 0
        THEN fees_usd / unique_swappers
        ELSE NULL
    END AS revenue_per_user_usd,

    -- Time trend per pool (for regression controls)
    ROW_NUMBER() OVER (PARTITION BY pool_name ORDER BY period_start_date) AS time_trend_pool,

    -- Global time trend (for regression controls)
    ROW_NUMBER() OVER (ORDER BY period_start_date, pool_name) AS time_trend_global

FROM lagged
WHERE prev_fee_bps IS NOT NULL  -- Exclude first period per pool with no lag
ORDER BY period_start_date, pool_name;


-- ============================================================================
-- Mart View: FCT_POOL_ELASTICITY_INPUTS
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS AS
SELECT
    period_id,
    period_start_date,
    period_end_date,
    final_fee_bps,
    pool_name,

    -- Standardize pool type for analysis
    CASE
        WHEN pool_type = 'BTC Pool' THEN 'BTC'
        WHEN pool_type = 'ETH Pool' THEN 'ETH'
        WHEN pool_type = 'Stablecoin Pool' THEN 'STABLE'
        ELSE 'LONG_TAIL'
    END AS pool_type,

    -- Current period metrics
    swaps_count,
    volume_usd,
    fees_usd,
    unique_swappers,
    avg_swap_size_usd,
    pct_of_period_swaps,
    pct_of_period_volume,
    pct_of_period_fees,

    -- Previous period metrics
    prev_fee_bps,
    prev_volume_usd,
    prev_fees_usd,
    prev_swaps_count,
    prev_unique_swappers,
    prev_avg_swap_size_usd,
    prev_pct_of_period_volume,
    prev_pct_of_period_fees,
    prev_pct_of_period_swaps,

    -- Percentage changes
    pct_change_fee_bps,
    pct_change_volume,
    pct_change_fees,
    pct_change_swaps,
    pct_change_users,
    pct_change_avg_swap_size,
    pct_change_market_share_volume,
    pct_change_market_share_fees,

    -- Absolute changes
    delta_fee_bps,
    delta_volume_usd,
    delta_fees_usd,
    delta_swaps_count,
    delta_unique_swappers,
    delta_market_share_volume,
    delta_market_share_fees,

    -- Per-unit metrics
    revenue_per_swap_usd,
    revenue_per_user_usd,

    -- Controls
    time_trend_pool,
    time_trend_global

FROM "9R".FEE_EXPERIMENT.INT_POOL_ELASTICITY_INPUTS
WHERE
    -- Ensure we have valid data for elasticity calculation
    pct_change_fee_bps IS NOT NULL
    AND pct_change_volume IS NOT NULL
    AND pct_change_fees IS NOT NULL
    -- Filter low-activity pools (minimum 10 swaps in both periods)
    AND swaps_count >= 10
    AND prev_swaps_count >= 10
ORDER BY period_start_date, pool_name;


-- ============================================================================
-- Verification Queries
-- ============================================================================

-- Check row counts
SELECT
    'INT_POOL_ELASTICITY_INPUTS' AS view_name,
    COUNT(*) AS row_count
FROM "9R".FEE_EXPERIMENT.INT_POOL_ELASTICITY_INPUTS
UNION ALL
SELECT
    'FCT_POOL_ELASTICITY_INPUTS',
    COUNT(*)
FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS;

-- Check for duplicates (should return 0 rows)
SELECT 'INT_POOL_ELASTICITY_INPUTS - Duplicates' AS check_name, COUNT(*) AS issue_count
FROM (
    SELECT period_id, pool_name, COUNT(*) as cnt
    FROM "9R".FEE_EXPERIMENT.INT_POOL_ELASTICITY_INPUTS
    GROUP BY period_id, pool_name
    HAVING COUNT(*) > 1
)
UNION ALL
SELECT 'FCT_POOL_ELASTICITY_INPUTS - Duplicates', COUNT(*)
FROM (
    SELECT period_id, pool_name, COUNT(*) as cnt
    FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS
    GROUP BY period_id, pool_name
    HAVING COUNT(*) > 1
);

-- Sample data
SELECT
    period_id,
    period_start_date,
    pool_name,
    pool_type,
    final_fee_bps,
    pct_change_fee_bps,
    pct_change_volume,
    pct_change_fees
FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS
ORDER BY period_start_date, pool_name
LIMIT 10;

-- Summary by pool type
SELECT
    pool_type,
    COUNT(*) AS observations,
    COUNT(DISTINCT pool_name) AS unique_pools,
    AVG(pct_change_volume) AS avg_volume_change_pct,
    AVG(pct_change_fees) AS avg_revenue_change_pct
FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS
GROUP BY pool_type
ORDER BY pool_type;
