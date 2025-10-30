-- ============================================================================
-- Affiliate Exclusion Check
-- ============================================================================
-- Purpose: For manual fee periods, compare realized bps using:
--  (A) Liquidity fees only, and
--  (B) Liquidity + affiliate fees
-- to intended fee bps.
-- ============================================================================

WITH manual AS (
    SELECT period_start_date, period_end_date, intended_fee_bps
    FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL
),
swaps AS (
    SELECT
        DATE_TRUNC('day', s.BLOCK_TIMESTAMP) AS day_date,
        SUM(GREATEST(FROM_AMOUNT_USD, TO_AMOUNT_USD)) AS volume_usd,
        SUM(LIQ_FEE_RUNE_USD) AS liq_fee_usd
    FROM THORCHAIN.DEFI.FACT_SWAPS s
    WHERE s.BLOCK_TIMESTAMP >= '2025-08-15 00:00:00'
      AND s.BLOCK_TIMESTAMP <  '2025-11-01 00:00:00'
      AND GREATEST(FROM_AMOUNT_USD, TO_AMOUNT_USD) > 0
    GROUP BY 1
),
aff AS (
    SELECT
        DATE_TRUNC('day', a.BLOCK_TIMESTAMP) AS day_date,
        SUM(a.FEE_USD) AS affiliate_fee_usd
    FROM THORCHAIN.DEFI.FACT_AFFILIATE_FEE_EVENTS a
    WHERE a.BLOCK_TIMESTAMP >= '2025-08-15 00:00:00'
      AND a.BLOCK_TIMESTAMP <  '2025-11-01 00:00:00'
    GROUP BY 1
),
daily AS (
    SELECT
        s.day_date,
        s.volume_usd,
        s.liq_fee_usd,
        COALESCE(a.affiliate_fee_usd, 0) AS affiliate_fee_usd
    FROM swaps s
    LEFT JOIN aff a USING (day_date)
),
per_manual AS (
    SELECT
        m.period_start_date,
        m.period_end_date,
        m.intended_fee_bps,
        SUM(d.volume_usd) AS volume_usd,
        SUM(d.liq_fee_usd) AS liq_fee_usd,
        SUM(d.affiliate_fee_usd) AS affiliate_fee_usd
    FROM manual m
    LEFT JOIN daily d
      ON d.day_date >= m.period_start_date
     AND d.day_date <  DATEADD(day, 1, m.period_end_date)
    GROUP BY 1,2,3
)
SELECT
    period_start_date,
    period_end_date,
    intended_fee_bps,
    ROUND(10000 * liq_fee_usd / NULLIF(volume_usd,0), 2) AS realized_liq_bps,
    ROUND(10000 * (liq_fee_usd + affiliate_fee_usd) / NULLIF(volume_usd,0), 2) AS realized_liq_plus_aff_bps,
    ROUND(ROUND(10000 * liq_fee_usd / NULLIF(volume_usd,0), 2) - intended_fee_bps, 2) AS delta_liq_bps,
    ROUND(ROUND(10000 * (liq_fee_usd + affiliate_fee_usd) / NULLIF(volume_usd,0), 2) - intended_fee_bps, 2) AS delta_liq_plus_aff_bps,
    volume_usd,
    liq_fee_usd,
    affiliate_fee_usd
FROM per_manual
ORDER BY period_start_date;
