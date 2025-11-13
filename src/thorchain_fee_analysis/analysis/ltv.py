"""
Lifetime Value (LTV) analysis for Phase 3.

This module provides functions to:
- Compute cumulative LTV by acquisition cohort
- Apply discount rates
- Generate bootstrap confidence intervals
- Perform sensitivity analysis over horizons and discount rates
"""

import numpy as np
import pandas as pd


def compute_ltv_by_cohort(
    cohort_df: pd.DataFrame, user_df: pd.DataFrame, horizon: int = 12, discount_rate: float = 0.0
) -> pd.DataFrame:
    """
    Compute cumulative LTV by acquisition fee tier (vectorized).

    LTV = sum of discounted fees per user over horizon H.

    Args:
        cohort_df: Cohort table with first_seen_period_id and first_seen_fee_bps
        user_df: User-period detail with fees_usd
        horizon: Number of weeks to calculate LTV over
        discount_rate: Annual discount rate (e.g., 0.05 for 5%)

    Returns:
        DataFrame with columns:
        - acquisition_fee_bps
        - horizon
        - discount_rate
        - user_count (users in cohort)
        - total_ltv (sum of all user LTVs)
        - ltv_mean (average LTV per user)
        - ltv_median, ltv_p25, ltv_p75
    """
    # Weekly discount factor
    weekly_discount = (1 + discount_rate) ** (1 / 52)

    # Merge cohort info with user activity
    user_with_cohort = user_df.merge(
        cohort_df[["user_address", "first_seen_period_id", "first_seen_fee_bps"]],
        on="user_address",
        how="inner",
    )

    # Filter to horizon window
    user_with_cohort["k"] = user_with_cohort["period_id"] - user_with_cohort["first_seen_period_id"]
    user_with_cohort = user_with_cohort[
        (user_with_cohort["k"] >= 0) & (user_with_cohort["k"] < horizon)
    ]

    # Calculate discounted fees (vectorized)
    user_with_cohort["discount_factor"] = weekly_discount ** (-user_with_cohort["k"])
    user_with_cohort["discounted_fees"] = (
        user_with_cohort["fees_usd"] * user_with_cohort["discount_factor"]
    )

    # Aggregate LTV per user
    user_ltv = (
        user_with_cohort.groupby(["user_address", "first_seen_fee_bps"])
        .agg({"discounted_fees": "sum"})
        .reset_index()
    )
    user_ltv.columns = ["user_address", "first_seen_fee_bps", "ltv"]

    # Aggregate by fee tier
    ltv_by_fee = (
        user_ltv.groupby("first_seen_fee_bps")["ltv"]
        .agg(
            [
                ("user_count", "count"),
                ("total_ltv", "sum"),
                ("ltv_mean", "mean"),
                ("ltv_median", "median"),
                ("ltv_p25", lambda x: np.percentile(x, 25)),
                ("ltv_p75", lambda x: np.percentile(x, 75)),
            ]
        )
        .reset_index()
    )

    ltv_by_fee.columns = [
        "acquisition_fee_bps",
        "user_count",
        "total_ltv",
        "ltv_mean",
        "ltv_median",
        "ltv_p25",
        "ltv_p75",
    ]

    # Add metadata
    ltv_by_fee["horizon"] = horizon
    ltv_by_fee["discount_rate"] = discount_rate

    return ltv_by_fee


def bootstrap_ltv_ci(
    cohort_df: pd.DataFrame,
    user_df: pd.DataFrame,
    fee_bps: float,
    horizon: int = 12,
    discount_rate: float = 0.0,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """
    Calculate bootstrap confidence interval for mean LTV.

    Args:
        cohort_df: Cohort table
        user_df: User-period detail
        fee_bps: Acquisition fee tier
        horizon: Weeks to calculate LTV over
        discount_rate: Annual discount rate
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level

    Returns:
        Tuple of (point_estimate, ci_low, ci_high)
    """
    # Get cohort users
    cohort_users = cohort_df[cohort_df["first_seen_fee_bps"] == fee_bps]

    if len(cohort_users) == 0:
        return (0.0, 0.0, 0.0)

    # Calculate LTV for each user (reuse logic from compute_ltv_by_cohort)
    weekly_discount = (1 + discount_rate) ** (1 / 52)
    user_ltvs = []

    for _, user_row in cohort_users.iterrows():
        user_address = user_row["user_address"]
        first_period = user_row["first_seen_period_id"]

        user_activity = user_df[
            (user_df["user_address"] == user_address)
            & (user_df["period_id"] >= first_period)
            & (user_df["period_id"] < first_period + horizon)
        ].copy()

        user_activity["k"] = user_activity["period_id"] - first_period
        user_activity["discount_factor"] = weekly_discount ** (-user_activity["k"])
        user_activity["discounted_fees"] = (
            user_activity["fees_usd"] * user_activity["discount_factor"]
        )

        ltv = user_activity["discounted_fees"].sum()
        user_ltvs.append(ltv)

    # Point estimate
    point_estimate = np.mean(user_ltvs)

    # Bootstrap resampling
    bootstrap_means = []
    for _ in range(n_bootstrap):
        sample = np.random.choice(user_ltvs, size=len(user_ltvs), replace=True)
        bootstrap_means.append(np.mean(sample))

    # Calculate confidence interval
    alpha = 1 - confidence
    ci_low = np.percentile(bootstrap_means, alpha / 2 * 100)
    ci_high = np.percentile(bootstrap_means, (1 - alpha / 2) * 100)

    return (point_estimate, ci_low, ci_high)


def compute_ltv_sensitivity(
    cohort_df: pd.DataFrame,
    user_df: pd.DataFrame,
    horizons: list[int] = None,
    discount_rates: list[float] = None,
) -> pd.DataFrame:
    """
    Compute LTV sensitivity over multiple horizons and discount rates.

    Args:
        cohort_df: Cohort table
        user_df: User-period detail
        horizons: List of horizon weeks (default: [8, 12])
        discount_rates: List of annual discount rates (default: [0.0, 0.05, 0.10])

    Returns:
        DataFrame with LTV for all combinations of fee tier, horizon, and discount rate
    """
    if horizons is None:
        horizons = [8, 12]

    if discount_rates is None:
        discount_rates = [0.0, 0.05, 0.10]

    all_ltv = []

    for horizon in horizons:
        for discount_rate in discount_rates:
            ltv_df = compute_ltv_by_cohort(cohort_df, user_df, horizon, discount_rate)
            all_ltv.append(ltv_df)

    return pd.concat(all_ltv, ignore_index=True)


def add_ltv_confidence_intervals(
    ltv_df: pd.DataFrame, cohort_df: pd.DataFrame, user_df: pd.DataFrame, n_bootstrap: int = 1000
) -> pd.DataFrame:
    """
    Add bootstrap confidence intervals to LTV DataFrame.

    Args:
        ltv_df: Output from compute_ltv_by_cohort() or compute_ltv_sensitivity()
        cohort_df: Cohort table
        user_df: User-period detail
        n_bootstrap: Number of bootstrap samples

    Returns:
        ltv_df with added columns: ci_low, ci_high
    """
    ci_data = []

    for _, row in ltv_df.iterrows():
        _, ci_low, ci_high = bootstrap_ltv_ci(
            cohort_df,
            user_df,
            row["acquisition_fee_bps"],
            row["horizon"],
            row["discount_rate"],
            n_bootstrap=n_bootstrap,
        )
        ci_data.append({"ci_low": ci_low, "ci_high": ci_high})

    ci_df = pd.DataFrame(ci_data)
    return pd.concat([ltv_df, ci_df], axis=1)


def compare_ltv_by_fee(
    ltv_df: pd.DataFrame, horizon: int = 12, discount_rate: float = 0.0
) -> pd.DataFrame:
    """
    Compare LTV across acquisition fee tiers for a specific horizon and discount rate.

    Args:
        ltv_df: LTV DataFrame
        horizon: Horizon to compare
        discount_rate: Discount rate to compare

    Returns:
        DataFrame with LTV comparison and relative differences
    """
    subset = ltv_df[
        (ltv_df["horizon"] == horizon) & (ltv_df["discount_rate"] == discount_rate)
    ].copy()

    if len(subset) == 0:
        return pd.DataFrame()

    # Calculate relative to baseline (lowest fee tier)
    baseline_ltv = subset["ltv_mean"].iloc[0]
    subset["ltv_vs_baseline"] = subset["ltv_mean"] - baseline_ltv
    subset["ltv_vs_baseline_pct"] = (subset["ltv_mean"] / baseline_ltv - 1) * 100

    return subset.sort_values("acquisition_fee_bps")
