"""Tests for elasticity analysis module."""

import numpy as np
import pandas as pd
import pytest

from thorchain_fee_analysis.analysis.elasticity import (
    ElasticityResult,
    analyze_elasticity,
    bootstrap_elasticity_ci,
    calculate_elasticity_ols,
    calculate_optimal_fee,
    calculate_simple_elasticity,
)


@pytest.fixture
def sample_elasticity_data():
    """Create sample elasticity data for testing."""
    data = {
        "period_id": [2, 3, 4, 5, 6],
        "period_start_date": pd.date_range("2025-08-22", periods=5, freq="7D"),
        "final_fee_bps": [10.0, 25.0, 10.0, 15.0, 20.0],
        "prev_fee_bps": [10.0, 10.0, 25.0, 10.0, 15.0],
        "volume_usd": [1000000, 800000, 950000, 900000, 850000],
        "prev_volume_usd": [1000000, 1000000, 800000, 950000, 900000],
        "fees_usd": [1000, 2000, 950, 1350, 1700],
        "prev_fees_usd": [1000, 1000, 2000, 950, 1350],
        "pct_change_fee_bps": [0.0, 150.0, -60.0, 50.0, 33.33],
        "pct_change_volume": [0.0, -20.0, 18.75, -5.26, -5.56],
        "pct_change_fees": [0.0, 100.0, -52.5, 42.11, 25.93],
        "time_trend": [1, 2, 3, 4, 5],
    }
    return pd.DataFrame(data)


def test_calculate_simple_elasticity(sample_elasticity_data):
    """Test simple elasticity calculation."""
    ped, rev_elasticity = calculate_simple_elasticity(sample_elasticity_data)

    # PED should be negative (volume decreases with fee increases)
    assert ped < 0, "Price elasticity should be negative"

    # Should return valid numbers
    assert not np.isnan(ped)
    assert not np.isnan(rev_elasticity)


def test_calculate_simple_elasticity_empty():
    """Test elasticity calculation with empty data."""
    df = pd.DataFrame({"pct_change_fee_bps": [], "pct_change_volume": [], "pct_change_fees": []})

    with pytest.raises(ValueError, match="No valid observations"):
        calculate_simple_elasticity(df)


def test_calculate_simple_elasticity_zero_fee_change():
    """Test elasticity calculation with zero fee changes."""
    df = pd.DataFrame(
        {
            "pct_change_fee_bps": [0.0, 0.0, 0.0],
            "pct_change_volume": [1.0, 2.0, 3.0],
            "pct_change_fees": [1.0, 2.0, 3.0],
        }
    )

    with pytest.raises(ValueError, match="Mean fee change is zero"):
        calculate_simple_elasticity(df)


def test_calculate_elasticity_ols(sample_elasticity_data):
    """Test OLS elasticity calculation."""
    result = calculate_elasticity_ols(sample_elasticity_data)

    # Check result structure
    assert "price_elasticity_demand" in result
    assert "revenue_elasticity" in result
    assert "r_squared" in result
    assert "n_observations" in result

    # Check values are valid
    assert not np.isnan(result["price_elasticity_demand"])
    assert not np.isnan(result["revenue_elasticity"])
    assert 0 <= result["r_squared"] <= 1
    assert result["n_observations"] > 0


def test_calculate_elasticity_ols_with_controls(sample_elasticity_data):
    """Test OLS with control variables."""
    result = calculate_elasticity_ols(
        sample_elasticity_data,
        control_cols=["time_trend"],
    )

    assert result["n_observations"] > 0
    assert len(result["coefficients"]) == 2  # Fee + time_trend


def test_calculate_elasticity_ols_insufficient_data():
    """Test OLS with insufficient observations."""
    df = pd.DataFrame(
        {
            "pct_change_fee_bps": [10.0],
            "pct_change_volume": [-5.0],
            "pct_change_fees": [4.5],
        }
    )

    with pytest.raises(ValueError, match="Insufficient observations"):
        calculate_elasticity_ols(df)


def test_bootstrap_elasticity_ci(sample_elasticity_data):
    """Test bootstrap confidence interval calculation."""
    result = bootstrap_elasticity_ci(
        sample_elasticity_data,
        n_bootstrap=100,  # Fewer samples for faster test
        random_seed=42,
    )

    # Check result structure
    assert "price_elasticity_demand" in result
    assert "ped_ci_lower" in result
    assert "ped_ci_upper" in result
    assert "revenue_elasticity" in result
    assert "revenue_elasticity_ci_lower" in result
    assert "revenue_elasticity_ci_upper" in result

    # CI bounds should be ordered correctly
    assert result["ped_ci_lower"] < result["ped_ci_upper"]
    assert result["revenue_elasticity_ci_lower"] < result["revenue_elasticity_ci_upper"]

    # Point estimate should be within CI
    assert result["ped_ci_lower"] <= result["price_elasticity_demand"] <= result["ped_ci_upper"]


def test_bootstrap_elasticity_ci_insufficient_data():
    """Test bootstrap with insufficient data."""
    df = pd.DataFrame(
        {
            "pct_change_fee_bps": [10.0],
            "pct_change_volume": [-5.0],
            "pct_change_fees": [4.5],
        }
    )

    with pytest.raises(ValueError, match="Insufficient observations"):
        bootstrap_elasticity_ci(df, n_bootstrap=100)


def test_calculate_optimal_fee_elastic():
    """Test optimal fee calculation with elastic demand."""
    # Elastic demand (|PED| > 1)
    optimal = calculate_optimal_fee(
        current_volume=1000000,
        current_fee_bps=10.0,
        price_elasticity=-2.0,  # Elastic
        min_fee_bps=1.0,
        max_fee_bps=50.0,
    )

    assert optimal is not None
    assert 1.0 <= optimal <= 50.0
    # For PED = -2, optimal = 10 * (-1 / -2) = 5
    assert abs(optimal - 5.0) < 0.1


def test_calculate_optimal_fee_inelastic():
    """Test optimal fee calculation with inelastic demand."""
    # Inelastic demand (|PED| < 1)
    optimal = calculate_optimal_fee(
        current_volume=1000000,
        current_fee_bps=10.0,
        price_elasticity=-0.5,  # Inelastic
        min_fee_bps=1.0,
        max_fee_bps=50.0,
    )

    # Should return max fee for inelastic demand
    assert optimal == 50.0


def test_calculate_optimal_fee_positive_elasticity():
    """Test optimal fee with positive elasticity (unusual case)."""
    optimal = calculate_optimal_fee(
        current_volume=1000000,
        current_fee_bps=10.0,
        price_elasticity=0.5,  # Positive (unusual)
        min_fee_bps=1.0,
        max_fee_bps=50.0,
    )

    # Should return max fee
    assert optimal == 50.0


def test_calculate_optimal_fee_constrained():
    """Test optimal fee respects min/max constraints."""
    # Would calculate very high optimal, but constrained to max
    optimal = calculate_optimal_fee(
        current_volume=1000000,
        current_fee_bps=10.0,
        price_elasticity=-5.0,  # Very elastic
        min_fee_bps=1.0,
        max_fee_bps=15.0,
    )

    # Optimal = 10 * (-1 / -5) = 2, which is within bounds
    assert 1.0 <= optimal <= 15.0


def test_analyze_elasticity(sample_elasticity_data):
    """Test comprehensive elasticity analysis."""
    result = analyze_elasticity(
        sample_elasticity_data,
        use_ols=True,
        control_cols=["time_trend"],
        n_bootstrap=100,  # Fewer for faster test
    )

    # Check result type
    assert isinstance(result, ElasticityResult)

    # Check all required fields are present
    assert result.price_elasticity_demand is not None
    assert result.revenue_elasticity is not None
    assert result.ped_ci_lower is not None
    assert result.ped_ci_upper is not None
    assert result.revenue_elasticity_ci_lower is not None
    assert result.revenue_elasticity_ci_upper is not None
    assert result.r_squared >= 0
    assert result.n_observations > 0

    # Check confidence intervals are ordered
    assert result.ped_ci_lower < result.ped_ci_upper
    assert result.revenue_elasticity_ci_lower < result.revenue_elasticity_ci_upper


def test_analyze_elasticity_no_ols(sample_elasticity_data):
    """Test elasticity analysis without OLS."""
    result = analyze_elasticity(
        sample_elasticity_data,
        use_ols=False,
        n_bootstrap=100,
    )

    assert isinstance(result, ElasticityResult)
    assert result.r_squared == 0.0  # No OLS, so no R-squared


def test_elasticity_with_polars():
    """Test elasticity calculation with Polars DataFrame."""
    try:
        import polars as pl

        # Create Polars DataFrame
        data = {
            "pct_change_fee_bps": [10.0, 20.0, -15.0, 5.0],
            "pct_change_volume": [-5.0, -10.0, 8.0, -2.5],
            "pct_change_fees": [4.5, 8.0, -7.8, 2.3],
        }
        df = pl.DataFrame(data)

        ped, rev_elast = calculate_simple_elasticity(df)

        assert not np.isnan(ped)
        assert not np.isnan(rev_elast)

    except ImportError:
        pytest.skip("Polars not installed")
