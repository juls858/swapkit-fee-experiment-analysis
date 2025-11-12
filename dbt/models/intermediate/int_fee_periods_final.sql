{{
  config(
    materialized='view',
    tags=['intermediate', 'periods']
  )
}}

/*
  Final fee periods for experiment analysis

  Source: stg_fee_periods_manual

  This model:
  - Publishes final fee periods based solely on manual block heights
  - Normalizes column names for consistency
  - Adds period_id as sequential identifier
*/

SELECT
    ROW_NUMBER() OVER (ORDER BY period_start_date) AS period_id,
    period_start_date,
    period_end_date,
    DATEDIFF(day, period_start_date::DATE, period_end_date::DATE) + 1 AS days_in_period,
    intended_fee_bps::FLOAT AS fee_bps,
    source
FROM {{ ref('stg_fee_periods_manual') }}
ORDER BY period_start_date
