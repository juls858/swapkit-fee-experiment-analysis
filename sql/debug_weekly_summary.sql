-- Debug query to see what data is actually in the weekly summary
SELECT
    period_id,
    period_start_date,
    period_end_date,
    days_in_period,
    final_fee_bps,
    swaps_count,
    volume_usd,
    fees_usd
FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL
ORDER BY period_start_date;
