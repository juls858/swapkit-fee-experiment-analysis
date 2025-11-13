"""
User retention and cohort analysis for Phase 3.

This module provides functions to:
- Build user cohort tables with first_seen tracking
- Calculate retention rates by acquisition fee tier
- Generate k-week retention flags
- Compute bootstrap confidence intervals for retention metrics
"""

import numpy as np
import pandas as pd
from scipy import stats


def build_cohort_table(user_df: pd.DataFrame) -> pd.DataFrame:
    """
    Build cohort table with first_seen period and k-week retention flags.

    Args:
        user_df: User-period detail DataFrame with columns:
            - user_address
            - period_id
            - period_start_date
            - final_fee_bps
            - volume_usd, fees_usd, swaps_count

    Returns:
        DataFrame with one row per user containing:
        - user_address
        - first_seen_period_id
        - first_seen_fee_bps
        - first_seen_date
        - retained_k1, retained_k2, ..., retained_k12 (boolean flags)
        - total_periods_active
        - total_volume_usd, total_fees_usd, total_swaps
    """
    # Find first seen period for each user
    first_seen = (
        user_df.groupby("user_address")
        .agg(
            {
                "period_id": "min",
                "period_start_date": "min",
                "final_fee_bps": "first",  # Fee tier when first seen
            }
        )
        .reset_index()
    )

    first_seen.columns = [
        "user_address",
        "first_seen_period_id",
        "first_seen_date",
        "first_seen_fee_bps",
    ]

    # Get all periods each user was active in
    user_periods = user_df[["user_address", "period_id"]].drop_duplicates()

    # Merge first_seen with all user activity
    cohorts = first_seen.merge(user_periods, on="user_address", how="left")

    # Calculate k-weeks since first seen
    cohorts["k_weeks"] = cohorts["period_id"] - cohorts["first_seen_period_id"]

    # Create retention flags for k=1 to 12
    retention_flags = {}
    for k in range(1, 13):
        flag_col = f"retained_k{k}"
        # User is retained at k if they have activity in period first_seen + k
        retained = cohorts[cohorts["k_weeks"] == k].groupby("user_address").size() > 0
        retention_flags[flag_col] = retained

    # Build final cohort table
    cohort_table = first_seen.copy()

    # Add retention flags
    for flag_col, retained_series in retention_flags.items():
        cohort_table[flag_col] = (
            cohort_table["user_address"].map(retained_series).fillna(False).astype(bool)
        )

    # Add summary metrics
    user_totals = (
        user_df.groupby("user_address")
        .agg({"period_id": "nunique", "volume_usd": "sum", "fees_usd": "sum", "swaps_count": "sum"})
        .reset_index()
    )

    user_totals.columns = [
        "user_address",
        "total_periods_active",
        "total_volume_usd",
        "total_fees_usd",
        "total_swaps",
    ]

    cohort_table = cohort_table.merge(user_totals, on="user_address", how="left")

    return cohort_table


def calculate_retention_by_fee(cohort_df: pd.DataFrame, max_k: int = 12) -> pd.DataFrame:
    """
    Calculate retention rates by acquisition fee tier.

    Args:
        cohort_df: Cohort table from build_cohort_table()
        max_k: Maximum k-weeks to calculate retention for

    Returns:
        DataFrame with columns:
        - acquisition_fee_bps
        - k (weeks since acquisition)
        - base_users (users acquired at this fee tier)
        - retained_users (users retained at k weeks)
        - retention_rate
    """
    retention_data = []

    for fee_bps in sorted(cohort_df["first_seen_fee_bps"].unique()):
        cohort = cohort_df[cohort_df["first_seen_fee_bps"] == fee_bps]
        base_users = len(cohort)

        for k in range(1, max_k + 1):
            flag_col = f"retained_k{k}"
            if flag_col in cohort.columns:
                retained = cohort[flag_col].sum()
                retention_rate = retained / base_users if base_users > 0 else 0

                retention_data.append(
                    {
                        "acquisition_fee_bps": fee_bps,
                        "k": k,
                        "base_users": base_users,
                        "retained_users": retained,
                        "retention_rate": retention_rate,
                    }
                )

    return pd.DataFrame(retention_data)


def bootstrap_retention_ci(
    cohort_df: pd.DataFrame,
    fee_bps: float,
    k: int,
    n_bootstrap: int = 1000,
    confidence: float = 0.95,
) -> tuple[float, float, float]:
    """
    Calculate bootstrap confidence interval for retention rate.

    Args:
        cohort_df: Cohort table
        fee_bps: Acquisition fee tier
        k: Weeks since acquisition
        n_bootstrap: Number of bootstrap samples
        confidence: Confidence level (default 0.95 for 95% CI)

    Returns:
        Tuple of (point_estimate, ci_low, ci_high)
    """
    cohort = cohort_df[cohort_df["first_seen_fee_bps"] == fee_bps]
    flag_col = f"retained_k{k}"

    if flag_col not in cohort.columns or len(cohort) == 0:
        return (0.0, 0.0, 0.0)

    # Point estimate
    point_estimate = cohort[flag_col].mean()

    # Bootstrap resampling
    bootstrap_rates = []
    for _ in range(n_bootstrap):
        sample = cohort.sample(n=len(cohort), replace=True)
        bootstrap_rates.append(sample[flag_col].mean())

    # Calculate confidence interval
    alpha = 1 - confidence
    ci_low = np.percentile(bootstrap_rates, alpha / 2 * 100)
    ci_high = np.percentile(bootstrap_rates, (1 - alpha / 2) * 100)

    return (point_estimate, ci_low, ci_high)


def add_retention_confidence_intervals(
    retention_df: pd.DataFrame, cohort_df: pd.DataFrame, n_bootstrap: int = 1000
) -> pd.DataFrame:
    """
    Add bootstrap confidence intervals to retention DataFrame.

    Args:
        retention_df: Output from calculate_retention_by_fee()
        cohort_df: Cohort table
        n_bootstrap: Number of bootstrap samples

    Returns:
        retention_df with added columns: ci_low, ci_high
    """
    ci_data = []

    for _, row in retention_df.iterrows():
        _, ci_low, ci_high = bootstrap_retention_ci(
            cohort_df, row["acquisition_fee_bps"], row["k"], n_bootstrap=n_bootstrap
        )
        ci_data.append({"ci_low": ci_low, "ci_high": ci_high})

    ci_df = pd.DataFrame(ci_data)
    return pd.concat([retention_df, ci_df], axis=1)


def calculate_acquisition_by_period(user_df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate new user acquisition by period.

    Args:
        user_df: User-period detail DataFrame

    Returns:
        DataFrame with columns:
        - period_id
        - period_start_date
        - final_fee_bps
        - new_users (count of users first seen in this period)
        - returning_users (count of users active but not first seen)
    """
    # Identify first seen period for each user
    first_seen = user_df.groupby("user_address")["period_id"].min().reset_index()
    first_seen.columns = ["user_address", "first_seen_period_id"]

    # Merge back to user_df
    user_with_first = user_df.merge(first_seen, on="user_address", how="left")
    user_with_first["is_new"] = (
        user_with_first["period_id"] == user_with_first["first_seen_period_id"]
    )

    # Aggregate by period
    acquisition = (
        user_with_first.groupby(["period_id", "period_start_date", "final_fee_bps"])
        .agg({"user_address": "nunique", "is_new": lambda x: x.sum()})
        .reset_index()
    )

    acquisition.columns = [
        "period_id",
        "period_start_date",
        "final_fee_bps",
        "total_users",
        "new_users",
    ]
    acquisition["returning_users"] = acquisition["total_users"] - acquisition["new_users"]

    return acquisition[
        ["period_id", "period_start_date", "final_fee_bps", "new_users", "returning_users"]
    ]


def fit_retention_model(retention_df: pd.DataFrame, controls: pd.DataFrame = None) -> dict:
    """
    Fit logistic regression model for retention.

    Models retention ~ fee_bps + controls (if provided).

    Args:
        retention_df: Retention data with acquisition_fee_bps and retention_rate
        controls: Optional DataFrame with control variables (BTC price, time trend, etc.)

    Returns:
        Dictionary with model results:
        - coefficients: Dict of variable -> coefficient
        - marginal_effects: Dict of variable -> marginal effect
        - pvalues: Dict of variable -> p-value
        - summary: Model summary string
    """
    # Prepare data for regression
    # For now, simple model without controls
    # TODO: Add control variables when available

    # Group by fee tier and calculate average retention
    agg = (
        retention_df.groupby("acquisition_fee_bps")
        .agg({"retention_rate": "mean", "base_users": "first"})
        .reset_index()
    )

    if len(agg) < 2:
        return {
            "coefficients": {},
            "marginal_effects": {},
            "pvalues": {},
            "summary": "Insufficient data for regression",
        }

    # Simple linear regression: retention ~ fee_bps
    x_values = agg["acquisition_fee_bps"].values
    y = agg["retention_rate"].values
    # weights = agg["base_users"].values  # Available for WLS if needed

    # Linear regression
    slope, intercept, r_value, p_value, std_err = stats.linregress(x_values, y)

    return {
        "coefficients": {"intercept": intercept, "fee_bps": slope},
        "marginal_effects": {
            "fee_bps_per_5bps": slope * 5  # Effect of +5 bps increase
        },
        "pvalues": {"fee_bps": p_value},
        "r_squared": r_value**2,
        "summary": f"Retention = {intercept:.4f} + {slope:.6f} * fee_bps (R²={r_value**2:.3f}, p={p_value:.4f})",
    }
