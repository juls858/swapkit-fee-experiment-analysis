{{
  config(
    materialized='view',
    tags=['staging', 'periods']
  )
}}

/*
  Manual fee periods from block heights

  Sources:
  - seeds/fee_periods_manual_blocks.csv (block heights and intended fees)
  - THORCHAIN.CORE.DIM_BLOCK (block height to timestamp mapping)

  This model:
  - Joins block heights with timestamps
  - Anchors experiment start at 5 bps
  - Creates period boundaries
  - Makes period end timestamps exclusive
*/

WITH params AS (
    SELECT
        '2025-08-15 00:00:00'::TIMESTAMP AS window_start_ts,
        '2025-11-01 00:00:00'::TIMESTAMP AS window_end_ts
),

manual_blocks AS (
    SELECT
        block_id,
        intended_fee_bps
    FROM {{ ref('fee_periods_manual_blocks') }}
),

heights_to_ts AS (
    SELECT
        mb.block_id,
        mb.intended_fee_bps,
        db.BLOCK_TIMESTAMP AS start_ts
    FROM manual_blocks mb
    LEFT JOIN {{ source('thorchain_core', 'DIM_BLOCK') }} db
        ON db.BLOCK_ID = mb.block_id
),

starts_union AS (
    -- Anchor start of window at 5 bps before first change
    SELECT
        NULL::NUMBER AS block_id,
        5 AS intended_fee_bps,
        p.window_start_ts AS start_ts
    FROM params p

    UNION ALL

    SELECT
        block_id,
        intended_fee_bps,
        start_ts
    FROM heights_to_ts
),

ordered AS (
    SELECT
        intended_fee_bps,
        start_ts,
        ROW_NUMBER() OVER (ORDER BY start_ts) AS rn
    FROM starts_union
    WHERE start_ts IS NOT NULL
),

bounded AS (
    SELECT
        rn AS period_id,
        start_ts AS period_start_ts,
        LEAD(start_ts) OVER (ORDER BY start_ts) AS next_start_ts,
        intended_fee_bps
    FROM ordered
),

clamped AS (
    SELECT
        b.period_id,
        GREATEST(b.period_start_ts, p.window_start_ts) AS period_start_ts,
        -- Make period end exclusive by subtracting 1 second from next period start
        CASE
            WHEN b.next_start_ts IS NOT NULL
            THEN DATEADD(second, -1, LEAST(b.next_start_ts, p.window_end_ts))
            ELSE DATEADD(second, -1, p.window_end_ts)
        END AS period_end_ts,
        b.intended_fee_bps
    FROM bounded b
    CROSS JOIN params p
)

SELECT
    period_id,
    period_start_ts AS period_start_date,
    period_end_ts AS period_end_date,
    DATEDIFF(day, period_start_ts::DATE, period_end_ts::DATE) + 1 AS days_in_period,
    intended_fee_bps,
    'manual' AS source
FROM clamped
WHERE period_end_ts > period_start_ts
ORDER BY period_start_date
