-- Debug query to check period boundaries
SELECT
    period_id,
    period_start_date,
    period_end_date,
    DATEDIFF(second, period_start_date, period_end_date) as seconds_in_period,
    intended_fee_bps,
    -- Check for gaps or overlaps
    LAG(period_end_date) OVER (ORDER BY period_start_date) as prev_end,
    DATEDIFF(second,
        LAG(period_end_date) OVER (ORDER BY period_start_date),
        period_start_date
    ) as gap_seconds
FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL
ORDER BY period_start_date;
