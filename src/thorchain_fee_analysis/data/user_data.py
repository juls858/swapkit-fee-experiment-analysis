"""
User-level data loading and preparation for Phase 3 analysis.

This module builds user-period detail data from swap-level data when
database views are not available.
"""

import pandas as pd
from snowflake.snowpark import Session


def load_user_period_detail(session: Session) -> pd.DataFrame:
    """
    Load user-period detail data (one row per user per period).

    Builds user-level aggregations from swap data when V_USER_PERIOD_DETAIL
    view is not available.

    Args:
        session: Snowpark session

    Returns:
        DataFrame with columns:
        - period_id, period_start_date, period_end_date, final_fee_bps
        - user_address, swaps_count, volume_usd, fees_usd
        - avg_swap_size_usd, median_swap_size_usd
        - user_cohort ('New' or 'Returning')
        - engagement_level, first_swap_date_in_window
    """
    sql = """
    WITH swaps_with_period AS (
        SELECT
            s.*,
            p.period_id,
            p.period_start_date,
            p.period_end_date,
            p.intended_fee_bps AS final_fee_bps,
            MIN(s.swap_date) OVER (PARTITION BY s.from_address) AS first_swap_date_in_window
        FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW s
        LEFT JOIN "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL p
            ON s.swap_date BETWEEN p.period_start_date AND p.period_end_date
    ),

    user_period_agg AS (
        SELECT
            period_id,
            period_start_date,
            period_end_date,
            final_fee_bps,
            from_address AS user_address,
            MIN(first_swap_date_in_window) AS first_swap_date_in_window,
            COUNT(*) AS swaps_count,
            SUM(gross_volume_usd) AS volume_usd,
            SUM(total_fee_usd) AS fees_usd,
            AVG(gross_volume_usd) AS avg_swap_size_usd,
            MEDIAN(gross_volume_usd) AS median_swap_size_usd,
            COUNT(DISTINCT pool_name) AS distinct_pools_used,
            COUNT(DISTINCT swap_date) AS active_days
        FROM swaps_with_period
        WHERE period_id IS NOT NULL
        GROUP BY 1, 2, 3, 4, 5
    )

    SELECT
        period_id,
        period_start_date,
        period_end_date,
        final_fee_bps,
        user_address,
        swaps_count,
        volume_usd,
        fees_usd,
        avg_swap_size_usd,
        median_swap_size_usd,
        distinct_pools_used,
        active_days,

        -- User classification
        CASE
            WHEN first_swap_date_in_window >= period_start_date
                AND first_swap_date_in_window <= period_end_date
            THEN 'New'
            ELSE 'Returning'
        END AS user_cohort,

        -- User engagement level
        CASE
            WHEN swaps_count >= 10 THEN 'Power User'
            WHEN swaps_count >= 5 THEN 'Regular'
            WHEN swaps_count >= 2 THEN 'Occasional'
            ELSE 'One-time'
        END AS engagement_level,

        -- First seen date for cohort analysis
        first_swap_date_in_window

    FROM user_period_agg
    ORDER BY period_start_date, volume_usd DESC
    """

    df = session.sql(sql).to_pandas()
    df.columns = df.columns.str.lower()
    return df


def load_weekly_summary(session: Session) -> pd.DataFrame:
    """
    Load weekly summary data.

    Args:
        session: Snowpark session

    Returns:
        DataFrame with weekly aggregated metrics
    """
    sql = 'SELECT * FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL ORDER BY period_start_date'
    df = session.sql(sql).to_pandas()
    df.columns = df.columns.str.lower()
    return df
