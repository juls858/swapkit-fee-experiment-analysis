"""Tests for revenue decomposition module."""

import pandas as pd
import pytest

from thorchain_fee_analysis.analysis.revenue_decomposition import (
    DecompositionResult,
    analyze_revenue_decomposition,
    create_waterfall_data,
    decompose_revenue_change,
    summarize_decomposition,
)


@pytest.fixture
def sample_period_data():
    """Create sample period data for decomposition testing."""
    prev_period = {
        "period_id": 1,
        "period_start_date": "2025-08-15",
        "final_fee_bps": 10.0,
        "volume_usd": 1000000.0,
        "fees_usd": 1000.0,
        "swaps_count": 1000,
        "avg_swap_size_usd": 1000.0,
    }

    current_period = {
        "period_id": 2,
        "period_start_date": "2025-08-22",
        "final_fee_bps": 25.0,
        "volume_usd": 800000.0,
        "fees_usd": 2000.0,
        "swaps_count": 900,
        "avg_swap_size_usd": 889.0,
    }

    return prev_period, current_period


@pytest.fixture
def sample_decomposition_data():
    """Create sample DataFrame for decomposition analysis."""
    data = {
        "period_id": [1, 2, 3, 4],
        "period_start_date": pd.date_range("2025-08-15", periods=4, freq="7D"),
        "final_fee_bps": [10.0, 25.0, 10.0, 15.0],
        "volume_usd": [1000000, 800000, 950000, 900000],
        "fees_usd": [1000, 2000, 950, 1350],
        "swaps_count": [1000, 900, 950, 900],
        "avg_swap_size_usd": [1000, 889, 1000, 1000],
    }
    return pd.DataFrame(data)


def test_decompose_revenue_change(sample_period_data):
    """Test basic revenue decomposition."""
    prev_period, current_period = sample_period_data

    result = decompose_revenue_change(current_period, prev_period)

    # Check result type
    assert isinstance(result, DecompositionResult)

    # Check basic fields
    assert result.period_id == 2
    assert result.total_revenue_change == 1000.0  # 2000 - 1000

    # Check that components sum to total (approximately)
    components_sum = (
        result.fee_rate_effect + result.volume_effect + result.mix_effect + result.external_effect
    )
    assert abs(components_sum - result.total_revenue_change) < 0.01

    # Check percentages sum to 100 (approximately)
    pct_sum = result.fee_rate_pct + result.volume_pct + result.mix_pct + result.external_pct
    assert abs(pct_sum - 100.0) < 0.1


def test_decompose_revenue_change_fee_effect(sample_period_data):
    """Test fee rate effect calculation."""
    prev_period, current_period = sample_period_data

    result = decompose_revenue_change(current_period, prev_period)

    # Fee rate effect = (new_fee - old_fee) * old_volume
    # = (0.0025 - 0.0010) * 1000000 = 1500
    expected_fee_effect = (0.0025 - 0.0010) * 1000000
    assert abs(result.fee_rate_effect - expected_fee_effect) < 1.0


def test_decompose_revenue_change_volume_effect(sample_period_data):
    """Test volume effect calculation."""
    prev_period, current_period = sample_period_data

    result = decompose_revenue_change(current_period, prev_period)

    # Volume effect = old_fee * (new_volume - old_volume)
    # = 0.0010 * (800000 - 1000000) = -200
    expected_volume_effect = 0.0010 * (800000 - 1000000)
    assert abs(result.volume_effect - expected_volume_effect) < 1.0


def test_decompose_revenue_change_zero_change():
    """Test decomposition with no revenue change."""
    prev_period = {
        "period_id": 1,
        "period_start_date": "2025-08-15",
        "final_fee_bps": 10.0,
        "volume_usd": 1000000.0,
        "fees_usd": 1000.0,
        "swaps_count": 1000,
        "avg_swap_size_usd": 1000.0,
    }

    current_period = {
        "period_id": 2,
        "period_start_date": "2025-08-22",
        "final_fee_bps": 10.0,
        "volume_usd": 1000000.0,
        "fees_usd": 1000.0,
        "swaps_count": 1000,
        "avg_swap_size_usd": 1000.0,
    }

    result = decompose_revenue_change(current_period, prev_period)

    assert result.total_revenue_change == 0.0
    # All percentages should be 0 when there's no change
    assert result.fee_rate_pct == 0.0
    assert result.volume_pct == 0.0


def test_analyze_revenue_decomposition(sample_decomposition_data):
    """Test full decomposition analysis."""
    results = analyze_revenue_decomposition(sample_decomposition_data)

    # Should have one result per transition (n-1)
    assert len(results) == 3

    # All results should be DecompositionResult instances
    for result in results:
        assert isinstance(result, DecompositionResult)

    # Period IDs should be sequential starting from 2
    assert results[0].period_id == 2
    assert results[1].period_id == 3
    assert results[2].period_id == 4


def test_analyze_revenue_decomposition_single_period():
    """Test decomposition with single period (no transitions)."""
    df = pd.DataFrame(
        {
            "period_id": [1],
            "period_start_date": ["2025-08-15"],
            "final_fee_bps": [10.0],
            "volume_usd": [1000000],
            "fees_usd": [1000],
            "swaps_count": [1000],
            "avg_swap_size_usd": [1000],
        }
    )

    results = analyze_revenue_decomposition(df)

    # No transitions with single period
    assert len(results) == 0


def test_create_waterfall_data(sample_decomposition_data):
    """Test waterfall data creation."""
    decomp_results = analyze_revenue_decomposition(sample_decomposition_data)
    waterfall_df = create_waterfall_data(decomp_results)

    # Check DataFrame structure
    assert isinstance(waterfall_df, pd.DataFrame)
    assert "component" in waterfall_df.columns
    assert "value" in waterfall_df.columns
    assert "cumulative" in waterfall_df.columns
    assert "is_total" in waterfall_df.columns

    # Should have 6 rows per period (start + 4 effects + end)
    expected_rows = len(decomp_results) * 6
    assert len(waterfall_df) == expected_rows

    # Check component names
    components = waterfall_df["component"].unique()
    expected_components = [
        "Previous Revenue",
        "Fee Rate Effect",
        "Volume Effect",
        "Mix Effect",
        "External Effect",
        "Current Revenue",
    ]
    for comp in expected_components:
        assert comp in components


def test_create_waterfall_data_empty():
    """Test waterfall data with empty results."""
    waterfall_df = create_waterfall_data([])

    assert isinstance(waterfall_df, pd.DataFrame)
    assert len(waterfall_df) == 0


def test_summarize_decomposition(sample_decomposition_data):
    """Test decomposition summary statistics."""
    decomp_results = analyze_revenue_decomposition(sample_decomposition_data)
    summary = summarize_decomposition(decomp_results)

    # Check summary structure
    assert "n_periods" in summary
    assert "total_revenue_change" in summary
    assert "total_fee_rate_effect" in summary
    assert "total_volume_effect" in summary
    assert "total_mix_effect" in summary
    assert "total_external_effect" in summary
    assert "overall_fee_rate_pct" in summary
    assert "overall_volume_pct" in summary

    # Check values
    assert summary["n_periods"] == len(decomp_results)

    # Total effects should sum to total change (approximately)
    total_effects = (
        summary["total_fee_rate_effect"]
        + summary["total_volume_effect"]
        + summary["total_mix_effect"]
        + summary["total_external_effect"]
    )
    assert abs(total_effects - summary["total_revenue_change"]) < 1.0

    # Overall percentages should sum to 100 (approximately)
    pct_sum = (
        summary["overall_fee_rate_pct"]
        + summary["overall_volume_pct"]
        + summary["overall_mix_pct"]
        + summary["overall_external_pct"]
    )
    assert abs(pct_sum - 100.0) < 0.1


def test_summarize_decomposition_empty():
    """Test summary with no results."""
    summary = summarize_decomposition([])

    assert summary == {}


def test_decomposition_with_polars():
    """Test decomposition with Polars DataFrame."""
    try:
        import polars as pl

        data = {
            "period_id": [1, 2, 3],
            "period_start_date": ["2025-08-15", "2025-08-22", "2025-08-29"],
            "final_fee_bps": [10.0, 25.0, 10.0],
            "volume_usd": [1000000, 800000, 950000],
            "fees_usd": [1000, 2000, 950],
            "swaps_count": [1000, 900, 950],
            "avg_swap_size_usd": [1000, 889, 1000],
        }
        df = pl.DataFrame(data)

        results = analyze_revenue_decomposition(df)

        assert len(results) == 2
        assert all(isinstance(r, DecompositionResult) for r in results)

    except ImportError:
        pytest.skip("Polars not installed")
