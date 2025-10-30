-- ============================================================================
-- Phase 1: Stage Swaps for Experiment Window
-- ============================================================================
-- Purpose: Create normalized view of swaps during experiment period
-- Source: THORCHAIN.DEFI.FACT_SWAPS
-- Output: "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW
-- ============================================================================

CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW AS
WITH base_swaps AS (
    SELECT
        -- Identifiers
        BLOCK_TIMESTAMP AS block_timestamp,
        FACT_SWAPS_ID AS tx_id,

        -- Swap details
        FROM_ASSET,
        FROM_AMOUNT,
        FROM_AMOUNT_USD,
        TO_ASSET,
        TO_AMOUNT,
        TO_AMOUNT_USD,

        -- Pool info
        POOL_NAME,

        -- Fee information (use liquidity fee USD for base fee detection)
        LIQ_FEE_RUNE_USD AS liquidity_fee_usd,
        0::FLOAT AS outbound_fee_usd,
        0::FLOAT AS affiliate_fee_usd,

        -- User info
        FROM_ADDRESS,
        NATIVE_TO_ADDRESS AS to_address,
        AFFILIATE_ADDRESS AS affiliate_address,

        -- Swap metadata
        SWAP_SLIP_BP AS swap_slip_bp,
        STREAMING_COUNT AS streaming_swap_count,
        STREAMING_QUANTITY AS streaming_swap_quantity,

        -- Derived fields
        GREATEST(FROM_AMOUNT_USD, TO_AMOUNT_USD) AS gross_volume_usd
    FROM THORCHAIN.DEFI.FACT_SWAPS
    WHERE
        -- Experiment window: Aug 15, 2025 to Oct 31, 2025
        BLOCK_TIMESTAMP >= '2025-08-15 00:00:00'
        AND BLOCK_TIMESTAMP < '2025-11-01 00:00:00'
        -- Exclude zero-volume swaps
        AND GREATEST(FROM_AMOUNT_USD, TO_AMOUNT_USD) > 0
)
SELECT
    *,
    -- Total fee (USD) for detection = liquidity fee USD only
    liquidity_fee_usd + outbound_fee_usd + affiliate_fee_usd AS total_fee_usd,

    -- Calculate effective fee in basis points (capped at 500 bps)
    LEAST(
        CASE
            WHEN gross_volume_usd > 0
            THEN ((liquidity_fee_usd + outbound_fee_usd + affiliate_fee_usd) / gross_volume_usd) * 10000
            ELSE NULL
        END,
        500
    ) AS effective_fee_bps,

    -- Date dimensions
    DATE_TRUNC('day', block_timestamp) AS swap_date,
    DATE_TRUNC('hour', block_timestamp) AS swap_hour,
    DAYOFWEEK(block_timestamp) AS day_of_week,
    HOUR(block_timestamp) AS hour_of_day,

    -- Swap size buckets
    CASE
        WHEN gross_volume_usd < 100 THEN 'Micro (<$100)'
        WHEN gross_volume_usd < 1000 THEN 'Small ($100-$1K)'
        WHEN gross_volume_usd < 10000 THEN 'Medium ($1K-$10K)'
        WHEN gross_volume_usd < 100000 THEN 'Large ($10K-$100K)'
        ELSE 'Whale (>$100K)'
    END AS swap_size_bucket,

    -- Pool type classification
    CASE
        WHEN POOL_NAME ILIKE '%BTC%' THEN 'BTC Pool'
        WHEN POOL_NAME ILIKE '%ETH%' THEN 'ETH Pool'
        WHEN POOL_NAME ILIKE '%USDC%' OR POOL_NAME ILIKE '%USDT%' THEN 'Stablecoin Pool'
        ELSE 'Other Pool'
    END AS pool_type,

    -- Streaming swap flag
    COALESCE(streaming_swap_count, 0) > 0 AS is_streaming_swap

FROM base_swaps
WHERE effective_fee_bps IS NOT NULL
    AND effective_fee_bps >= 0;

-- Add comment
COMMENT ON VIEW "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW IS
    'Normalized swaps for fee experiment window (2025-08-15 to 2025-10-31); effective_fee_bps based on liquidity fee USD.';

-- Quick validation query
SELECT
    MIN(block_timestamp) AS first_swap,
    MAX(block_timestamp) AS last_swap,
    COUNT(*) AS total_swaps,
    SUM(gross_volume_usd) AS total_volume_usd,
    SUM(liquidity_fee_usd) AS total_liquidity_fees_usd,
    AVG(effective_fee_bps) AS avg_effective_bps
FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW;
