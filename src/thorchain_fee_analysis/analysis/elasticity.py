"""
Elasticity analysis for THORChain fee experiment.

Implements:
- Price Elasticity of Demand (PED)
- Revenue Elasticity
- OLS regression with controls
- Bootstrap confidence intervals
- Optimal fee calculation
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
import polars as pl


@dataclass
class ElasticityResult:
    """Container for elasticity analysis results."""

    # Point estimates
    price_elasticity_demand: float
    revenue_elasticity: float
    optimal_fee_bps: float | None

    # Confidence intervals (95%)
    ped_ci_lower: float
    ped_ci_upper: float
    revenue_elasticity_ci_lower: float
    revenue_elasticity_ci_upper: float
    optimal_fee_ci_lower: float | None
    optimal_fee_ci_upper: float | None

    # Regression details
    r_squared: float
    n_observations: int
    regression_coefficients: dict

    # Summary statistics
    mean_volume_change_pct: float
    mean_fee_change_pct: float
    mean_revenue_change_pct: float


def calculate_simple_elasticity(
    df: pd.DataFrame | pl.DataFrame,
    fee_col: str = "pct_change_fee_bps",
    volume_col: str = "pct_change_volume",
    revenue_col: str = "pct_change_fees",
) -> tuple[float, float]:
    """
    Calculate simple elasticity using average percentage changes.

    Price Elasticity of Demand (PED) = % change in volume / % change in fee
    Revenue Elasticity = % change in revenue / % change in fee

    Args:
        df: DataFrame with percentage change columns
        fee_col: Column name for fee percentage changes
        volume_col: Column name for volume percentage changes
        revenue_col: Column name for revenue percentage changes

    Returns:
        Tuple of (price_elasticity_demand, revenue_elasticity)
    """
    # Convert to pandas if polars
    if isinstance(df, pl.DataFrame):
        df = df.to_pandas()

    # Filter out rows with missing values
    valid_df = df[[fee_col, volume_col, revenue_col]].dropna()

    if len(valid_df) == 0:
        raise ValueError("No valid observations for elasticity calculation")

    # Calculate mean percentage changes
    mean_fee_change = valid_df[fee_col].mean()
    mean_volume_change = valid_df[volume_col].mean()
    mean_revenue_change = valid_df[revenue_col].mean()

    # Calculate elasticities
    if mean_fee_change == 0:
        raise ValueError("Mean fee change is zero, cannot calculate elasticity")

    ped = mean_volume_change / mean_fee_change
    revenue_elasticity = mean_revenue_change / mean_fee_change

    return ped, revenue_elasticity


def calculate_elasticity_ols(
    df: pd.DataFrame | pl.DataFrame,
    fee_col: str = "pct_change_fee_bps",
    volume_col: str = "pct_change_volume",
    revenue_col: str = "pct_change_fees",
    control_cols: list[str] | None = None,
) -> dict:
    """
    Calculate elasticity using OLS regression with optional controls.

    Model: log(Volume) ~ log(Fee) + controls

    Args:
        df: DataFrame with percentage change columns
        fee_col: Column name for fee percentage changes
        volume_col: Column name for volume percentage changes
        revenue_col: Column name for revenue percentage changes
        control_cols: Optional list of control variable column names

    Returns:
        Dictionary with regression results
    """
    # Convert to pandas if polars
    if isinstance(df, pl.DataFrame):
        df = df.to_pandas()

    # Prepare data
    valid_df = df[[fee_col, volume_col, revenue_col]].dropna()

    if control_cols:
        for col in control_cols:
            if col in df.columns:
                valid_df = valid_df.join(df[[col]], how="left")
        valid_df = valid_df.dropna()

    if len(valid_df) < 3:
        raise ValueError(f"Insufficient observations for regression: {len(valid_df)}")

    # Use numpy for simple OLS (avoiding sklearn dependency)
    # Model: volume_change = beta0 + beta1 * fee_change + controls
    X = valid_df[[fee_col]].values  # noqa: N806
    y = valid_df[volume_col].values

    if control_cols:
        for col in control_cols:
            if col in valid_df.columns:
                X = np.column_stack([X, valid_df[col].values])  # noqa: N806

    # Add intercept
    X = np.column_stack([np.ones(len(X)), X])  # noqa: N806

    # OLS: beta = (X'X)^-1 X'y
    try:
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
    except np.linalg.LinAlgError:
        raise ValueError("Singular matrix in OLS regression")

    # Calculate R-squared
    y_pred = X @ beta
    ss_res = np.sum((y - y_pred) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # Price elasticity is the coefficient on fee change
    ped = beta[1]

    # Revenue elasticity (for revenue model)
    X_rev = valid_df[[fee_col]].values  # noqa: N806
    y_rev = valid_df[revenue_col].values

    if control_cols:
        for col in control_cols:
            if col in valid_df.columns:
                X_rev = np.column_stack([X_rev, valid_df[col].values])  # noqa: N806

    X_rev = np.column_stack([np.ones(len(X_rev)), X_rev])  # noqa: N806
    beta_rev = np.linalg.lstsq(X_rev, y_rev, rcond=None)[0]
    revenue_elasticity = beta_rev[1]

    return {
        "price_elasticity_demand": ped,
        "revenue_elasticity": revenue_elasticity,
        "r_squared": r_squared,
        "n_observations": len(valid_df),
        "intercept": beta[0],
        "coefficients": beta[1:].tolist(),
    }


def bootstrap_elasticity_ci(
    df: pd.DataFrame | pl.DataFrame,
    fee_col: str = "pct_change_fee_bps",
    volume_col: str = "pct_change_volume",
    revenue_col: str = "pct_change_fees",
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
    random_seed: int = 42,
) -> dict:
    """
    Calculate bootstrap confidence intervals for elasticity estimates.

    Args:
        df: DataFrame with percentage change columns
        fee_col: Column name for fee percentage changes
        volume_col: Column name for volume percentage changes
        revenue_col: Column name for revenue percentage changes
        n_bootstrap: Number of bootstrap samples
        confidence_level: Confidence level (default 0.95 for 95% CI)
        random_seed: Random seed for reproducibility

    Returns:
        Dictionary with point estimates and confidence intervals
    """
    # Convert to pandas if polars
    if isinstance(df, pl.DataFrame):
        df = df.to_pandas()

    np.random.seed(random_seed)

    valid_df = df[[fee_col, volume_col, revenue_col]].dropna()
    n = len(valid_df)

    if n < 3:
        raise ValueError(f"Insufficient observations for bootstrap: {n}")

    ped_samples = []
    rev_elasticity_samples = []

    for _ in range(n_bootstrap):
        # Resample with replacement
        sample_idx = np.random.choice(n, size=n, replace=True)
        sample_df = valid_df.iloc[sample_idx]

        try:
            ped, rev_elast = calculate_simple_elasticity(
                sample_df, fee_col, volume_col, revenue_col
            )
            ped_samples.append(ped)
            rev_elasticity_samples.append(rev_elast)
        except (ValueError, ZeroDivisionError):
            continue

    if len(ped_samples) < 100:
        raise ValueError(f"Too few successful bootstrap samples: {len(ped_samples)}")

    # Calculate percentiles for confidence intervals
    alpha = 1 - confidence_level
    lower_percentile = (alpha / 2) * 100
    upper_percentile = (1 - alpha / 2) * 100

    ped_ci = np.percentile(ped_samples, [lower_percentile, upper_percentile])
    rev_ci = np.percentile(rev_elasticity_samples, [lower_percentile, upper_percentile])

    # Point estimates (mean of bootstrap samples)
    ped_mean = np.mean(ped_samples)
    rev_mean = np.mean(rev_elasticity_samples)

    return {
        "price_elasticity_demand": ped_mean,
        "ped_ci_lower": ped_ci[0],
        "ped_ci_upper": ped_ci[1],
        "revenue_elasticity": rev_mean,
        "revenue_elasticity_ci_lower": rev_ci[0],
        "revenue_elasticity_ci_upper": rev_ci[1],
        "n_bootstrap_samples": len(ped_samples),
    }


def calculate_optimal_fee(
    current_volume: float,
    current_fee_bps: float,
    price_elasticity: float,
    min_fee_bps: float = 1.0,
    max_fee_bps: float = 50.0,
) -> float | None:
    """
    Calculate revenue-optimal fee rate given elasticity.

    Revenue = Volume * Fee
    Volume = V0 * (Fee / Fee0)^elasticity

    Optimal fee maximizes Revenue = V0 * (Fee / Fee0)^elasticity * Fee

    Taking derivative and solving:
    Optimal Fee = Fee0 * (-1 / elasticity) if elasticity < 0

    Args:
        current_volume: Current period volume
        current_fee_bps: Current fee in basis points
        price_elasticity: Price elasticity of demand (should be negative)
        min_fee_bps: Minimum allowed fee
        max_fee_bps: Maximum allowed fee

    Returns:
        Optimal fee in basis points, or None if no valid optimum
    """
    if price_elasticity >= 0:
        # Positive elasticity means higher fees increase volume (unusual)
        # No interior optimum, return max fee
        return max_fee_bps

    if price_elasticity >= -1:
        # Inelastic demand (|elasticity| < 1)
        # Revenue increases with fee, return max fee
        return max_fee_bps

    # Elastic demand (|elasticity| > 1)
    # Optimal fee = current_fee * (-1 / elasticity)
    optimal_fee = current_fee_bps * (-1 / price_elasticity)

    # Constrain to valid range
    optimal_fee = max(min_fee_bps, min(max_fee_bps, optimal_fee))

    return optimal_fee


def analyze_elasticity(
    df: pd.DataFrame | pl.DataFrame,
    use_ols: bool = True,
    control_cols: list[str] | None = None,
    n_bootstrap: int = 1000,
    confidence_level: float = 0.95,
) -> ElasticityResult:
    """
    Comprehensive elasticity analysis with confidence intervals.

    Args:
        df: DataFrame with elasticity inputs (from fct_elasticity_inputs)
        use_ols: Whether to use OLS regression (vs simple average)
        control_cols: Optional control variables for OLS
        n_bootstrap: Number of bootstrap samples for CI
        confidence_level: Confidence level for intervals

    Returns:
        ElasticityResult with all analysis outputs
    """
    # Convert to pandas if polars
    if isinstance(df, pl.DataFrame):
        df = df.to_pandas()

    # Calculate point estimates
    if use_ols:
        ols_results = calculate_elasticity_ols(
            df,
            control_cols=control_cols,
        )
        ped = ols_results["price_elasticity_demand"]
        rev_elasticity = ols_results["revenue_elasticity"]
        r_squared = ols_results["r_squared"]
        n_obs = ols_results["n_observations"]
        coefficients = ols_results
    else:
        ped, rev_elasticity = calculate_simple_elasticity(df)
        r_squared = 0.0
        n_obs = len(df.dropna())
        coefficients = {}

    # Bootstrap confidence intervals
    boot_results = bootstrap_elasticity_ci(
        df,
        n_bootstrap=n_bootstrap,
        confidence_level=confidence_level,
    )

    # Calculate optimal fee
    # Use most recent period's data
    latest = df.iloc[-1]
    current_fee = latest["final_fee_bps"]
    current_volume = latest["volume_usd"]

    optimal_fee = calculate_optimal_fee(
        current_volume=current_volume,
        current_fee_bps=current_fee,
        price_elasticity=ped,
    )

    # Bootstrap optimal fee CI
    optimal_fee_samples = []
    for _ in range(100):  # Fewer samples for optimal fee
        sample_ped = np.random.normal(
            boot_results["price_elasticity_demand"],
            (boot_results["ped_ci_upper"] - boot_results["ped_ci_lower"]) / 4,
        )
        opt_fee = calculate_optimal_fee(current_volume, current_fee, sample_ped)
        if opt_fee is not None:
            optimal_fee_samples.append(opt_fee)

    if len(optimal_fee_samples) > 0:
        alpha = 1 - confidence_level
        optimal_fee_ci = np.percentile(
            optimal_fee_samples,
            [(alpha / 2) * 100, (1 - alpha / 2) * 100],
        )
        optimal_fee_ci_lower = optimal_fee_ci[0]
        optimal_fee_ci_upper = optimal_fee_ci[1]
    else:
        optimal_fee_ci_lower = None
        optimal_fee_ci_upper = None

    # Summary statistics
    mean_volume_change = df["pct_change_volume"].mean()
    mean_fee_change = df["pct_change_fee_bps"].mean()
    mean_revenue_change = df["pct_change_fees"].mean()

    return ElasticityResult(
        price_elasticity_demand=ped,
        revenue_elasticity=rev_elasticity,
        optimal_fee_bps=optimal_fee,
        ped_ci_lower=boot_results["ped_ci_lower"],
        ped_ci_upper=boot_results["ped_ci_upper"],
        revenue_elasticity_ci_lower=boot_results["revenue_elasticity_ci_lower"],
        revenue_elasticity_ci_upper=boot_results["revenue_elasticity_ci_upper"],
        optimal_fee_ci_lower=optimal_fee_ci_lower,
        optimal_fee_ci_upper=optimal_fee_ci_upper,
        r_squared=r_squared,
        n_observations=n_obs,
        regression_coefficients=coefficients,
        mean_volume_change_pct=mean_volume_change,
        mean_fee_change_pct=mean_fee_change,
        mean_revenue_change_pct=mean_revenue_change,
    )
