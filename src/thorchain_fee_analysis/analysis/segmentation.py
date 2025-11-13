"""
Trade-size segmentation and elasticity analysis for Phase 3.

This module provides functions to:
- Assign users to trade-size segments
- Compute segment-level metrics by period
- Estimate elasticity by segment
"""

import numpy as np
import pandas as pd
import statsmodels.api as sm

# Default segment thresholds (USD)
DEFAULT_THRESHOLDS = {
    "micro": (0, 100),
    "small": (100, 1_000),
    "medium": (1_000, 10_000),
    "large": (10_000, 100_000),
    "whale": (100_000, float("inf")),
}


def assign_trade_size_segment(
    user_df: pd.DataFrame, thresholds: dict[str, tuple[float, float]] = None
) -> pd.DataFrame:
    """
    Assign trade-size segment to each user-period observation.

    Args:
        user_df: User-period detail DataFrame with volume_usd column
        thresholds: Dict of segment_name -> (min_usd, max_usd)
                   If None, uses DEFAULT_THRESHOLDS

    Returns:
        user_df with added 'segment' column
    """
    if thresholds is None:
        thresholds = DEFAULT_THRESHOLDS

    df = user_df.copy()

    def classify_segment(volume):
        for segment_name, (min_val, max_val) in thresholds.items():
            if min_val <= volume < max_val:
                return segment_name
        return "whale"  # Fallback for very large values

    df["segment"] = df["volume_usd"].apply(classify_segment)

    return df


def compute_segment_metrics(user_df: pd.DataFrame, weekly_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Compute segment-level metrics by period.

    Args:
        user_df: User-period detail with 'segment' column
        weekly_df: Optional weekly summary for total volume/fees

    Returns:
        DataFrame with columns:
        - period_id, period_start_date, final_fee_bps, segment
        - user_count, volume_usd, fees_usd
        - volume_share, fees_share (if weekly_df provided)
        - avg_fees_paid_usd, retention_rate
    """
    # Aggregate by period and segment
    segment_agg = (
        user_df.groupby(["period_id", "period_start_date", "final_fee_bps", "segment"])
        .agg(
            {
                "user_address": "nunique",
                "volume_usd": "sum",
                "fees_usd": "sum",
                "swaps_count": "sum",
            }
        )
        .reset_index()
    )

    segment_agg.columns = [
        "period_id",
        "period_start_date",
        "final_fee_bps",
        "segment",
        "user_count",
        "volume_usd",
        "fees_usd",
        "swaps_count",
    ]

    # Calculate avg fees paid per user in segment
    segment_agg["avg_fees_paid_usd"] = segment_agg["fees_usd"] / segment_agg["user_count"]

    # Calculate shares if weekly totals provided
    if weekly_df is not None:
        # Merge with weekly totals
        weekly_totals = weekly_df[["period_id", "volume_usd", "fees_usd"]].copy()
        weekly_totals.columns = ["period_id", "total_volume_usd", "total_fees_usd"]

        segment_agg = segment_agg.merge(weekly_totals, on="period_id", how="left")

        segment_agg["volume_share"] = segment_agg["volume_usd"] / segment_agg["total_volume_usd"]
        segment_agg["fees_share"] = segment_agg["fees_usd"] / segment_agg["total_fees_usd"]

    # Calculate retention (users active in next period)
    # For each period-segment, count how many users are also in next period
    retention_data = []

    for period_id in sorted(user_df["period_id"].unique())[:-1]:  # Exclude last period
        next_period_id = period_id + 1

        for segment in user_df["segment"].unique():
            current_users = set(
                user_df[(user_df["period_id"] == period_id) & (user_df["segment"] == segment)][
                    "user_address"
                ]
            )

            next_period_users = set(user_df[user_df["period_id"] == next_period_id]["user_address"])

            retained = len(current_users & next_period_users)
            retention_rate = retained / len(current_users) if len(current_users) > 0 else 0

            retention_data.append(
                {"period_id": period_id, "segment": segment, "retention_rate": retention_rate}
            )

    retention_df = pd.DataFrame(retention_data)

    # Merge retention back
    segment_agg = segment_agg.merge(retention_df, on=["period_id", "segment"], how="left")

    return segment_agg


def estimate_segment_elasticity(
    segment_df: pd.DataFrame, controls: pd.DataFrame = None
) -> pd.DataFrame:
    """
    Estimate price elasticity by segment using OLS regression.

    Models: log(volume) ~ fee_bps + controls

    Args:
        segment_df: Segment metrics with volume_usd and final_fee_bps
        controls: Optional DataFrame with control variables

    Returns:
        DataFrame with columns:
        - segment
        - elasticity (coefficient on fee_bps)
        - std_error, pvalue, ci_low, ci_high
        - r_squared
    """
    elasticity_results = []

    for segment in sorted(segment_df["segment"].unique()):
        seg_data = segment_df[segment_df["segment"] == segment].copy()

        # Skip if insufficient data
        if len(seg_data) < 3:
            elasticity_results.append(
                {
                    "segment": segment,
                    "elasticity": np.nan,
                    "std_error": np.nan,
                    "pvalue": np.nan,
                    "ci_low": np.nan,
                    "ci_high": np.nan,
                    "r_squared": np.nan,
                    "n_obs": len(seg_data),
                }
            )
            continue

        # Prepare regression data
        seg_data["log_volume"] = np.log(seg_data["volume_usd"] + 1)  # Add 1 to handle zeros

        # Independent variables
        x_vars = seg_data[["final_fee_bps"]].copy()

        # Add time trend
        x_vars["time_trend"] = range(len(x_vars))

        # Add controls if provided
        if controls is not None:
            x_vars = x_vars.merge(controls, left_on="period_id", right_index=True, how="left")

        # Add constant
        x_vars = sm.add_constant(x_vars)

        # Dependent variable
        y = seg_data["log_volume"]

        try:
            # Fit OLS model
            model = sm.OLS(y, x_vars).fit()

            # Extract fee_bps coefficient
            fee_coef = model.params["final_fee_bps"]
            fee_se = model.bse["final_fee_bps"]
            fee_pval = model.pvalues["final_fee_bps"]

            # 95% confidence interval
            conf_int = model.conf_int(alpha=0.05)
            ci_low = conf_int.loc["final_fee_bps", 0]
            ci_high = conf_int.loc["final_fee_bps", 1]

            elasticity_results.append(
                {
                    "segment": segment,
                    "elasticity": fee_coef,
                    "std_error": fee_se,
                    "pvalue": fee_pval,
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                    "r_squared": model.rsquared,
                    "n_obs": len(seg_data),
                }
            )
        except Exception as e:
            # Handle regression failures
            elasticity_results.append(
                {
                    "segment": segment,
                    "elasticity": np.nan,
                    "std_error": np.nan,
                    "pvalue": np.nan,
                    "ci_low": np.nan,
                    "ci_high": np.nan,
                    "r_squared": np.nan,
                    "n_obs": len(seg_data),
                    "error": str(e),
                }
            )

    return pd.DataFrame(elasticity_results)


def add_elasticity_to_metrics(
    segment_df: pd.DataFrame, elasticity_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Add elasticity estimates to segment metrics DataFrame.

    Args:
        segment_df: Segment metrics from compute_segment_metrics()
        elasticity_df: Elasticity estimates from estimate_segment_elasticity()

    Returns:
        segment_df with added elasticity column
    """
    return segment_df.merge(elasticity_df[["segment", "elasticity"]], on="segment", how="left")


def get_segment_summary(segment_df: pd.DataFrame) -> pd.DataFrame:
    """
    Get overall summary statistics by segment.

    Args:
        segment_df: Segment metrics DataFrame

    Returns:
        DataFrame with summary stats per segment
    """
    summary = (
        segment_df.groupby("segment")
        .agg(
            {
                "user_count": "sum",
                "volume_usd": "sum",
                "fees_usd": "sum",
                "volume_share": "mean",
                "fees_share": "mean",
                "avg_fees_paid_usd": "mean",
                "retention_rate": "mean",
            }
        )
        .reset_index()
    )

    # Calculate overall shares
    total_volume = summary["volume_usd"].sum()
    total_fees = summary["fees_usd"].sum()

    summary["overall_volume_share"] = summary["volume_usd"] / total_volume
    summary["overall_fees_share"] = summary["fees_usd"] / total_fees

    return summary
