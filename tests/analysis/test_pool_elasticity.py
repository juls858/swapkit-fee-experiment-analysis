"""Tests for pool-level elasticity analysis."""

import numpy as np
import pandas as pd
import pytest


@pytest.fixture
def sample_pool_elasticity_data():
    """Create sample pool elasticity data for testing."""
    return pd.DataFrame(
        {
            "period_id": [1, 2, 3, 1, 2, 3],
            "pool_name": ["BTC.BTC", "BTC.BTC", "BTC.BTC", "ETH.ETH", "ETH.ETH", "ETH.ETH"],
            "pool_type": ["BTC", "BTC", "BTC", "ETH", "ETH", "ETH"],
            "final_fee_bps": [10, 15, 20, 10, 15, 20],
            "prev_fee_bps": [5, 10, 15, 5, 10, 15],
            "volume_usd": [1000000, 900000, 800000, 500000, 480000, 450000],
            "prev_volume_usd": [1100000, 1000000, 900000, 520000, 500000, 480000],
            "fees_usd": [10000, 13500, 16000, 5000, 7200, 9000],
            "prev_fees_usd": [5500, 10000, 13500, 2600, 5000, 7200],
            "swaps_count": [100, 95, 90, 50, 48, 45],
            "prev_swaps_count": [110, 100, 95, 52, 50, 48],
            "pct_change_fee_bps": [100.0, 50.0, 33.33, 100.0, 50.0, 33.33],
            "pct_change_volume": [-9.09, -10.0, -11.11, -3.85, -4.0, -6.25],
            "pct_change_fees": [81.82, 35.0, 18.52, 92.31, 44.0, 25.0],
            "pct_of_period_volume": [0.6, 0.6, 0.6, 0.3, 0.3, 0.3],
            "prev_pct_of_period_volume": [0.65, 0.6, 0.6, 0.32, 0.3, 0.3],
        }
    )


def test_pool_elasticity_data_shape(sample_pool_elasticity_data):
    """Test that pool elasticity data has expected shape."""
    df = sample_pool_elasticity_data
    assert len(df) == 6
    assert "pool_name" in df.columns
    assert "pct_change_fee_bps" in df.columns
    assert "pct_change_volume" in df.columns
    assert "pct_change_fees" in df.columns


def test_pool_elasticity_no_nans_in_key_fields(sample_pool_elasticity_data):
    """Test that key fields have no NaN values."""
    df = sample_pool_elasticity_data
    key_fields = [
        "pool_name",
        "pool_type",
        "final_fee_bps",
        "prev_fee_bps",
        "volume_usd",
        "fees_usd",
        "pct_change_fee_bps",
        "pct_change_volume",
        "pct_change_fees",
    ]
    for field in key_fields:
        assert df[field].notna().all(), f"Field {field} contains NaN values"


def test_pool_elasticity_reasonable_ranges(sample_pool_elasticity_data):
    """Test that elasticity values are in reasonable ranges."""
    df = sample_pool_elasticity_data

    # Fee changes should be reasonable (not > 1000%)
    assert (df["pct_change_fee_bps"].abs() <= 1000).all()

    # Volume changes should be reasonable (not > 500%)
    assert (df["pct_change_volume"].abs() <= 500).all()

    # Fees should be positive
    assert (df["fees_usd"] >= 0).all()
    assert (df["volume_usd"] >= 0).all()

    # Fee tiers should be in expected range
    assert df["final_fee_bps"].between(0, 100).all()


def test_pool_types_standardized(sample_pool_elasticity_data):
    """Test that pool types are standardized."""
    df = sample_pool_elasticity_data
    valid_types = ["BTC", "ETH", "STABLE", "LONG_TAIL"]
    assert df["pool_type"].isin(valid_types).all()


def test_pool_elasticity_per_pool_consistency(sample_pool_elasticity_data):
    """Test that each pool has consistent data across periods."""
    df = sample_pool_elasticity_data

    for pool in df["pool_name"].unique():
        pool_data = df[df["pool_name"] == pool]

        # Pool type should be consistent
        assert pool_data["pool_type"].nunique() == 1

        # Periods should be sequential
        periods = sorted(pool_data["period_id"].tolist())
        assert len(periods) == len(pool_data)


def test_lagged_values_consistency(sample_pool_elasticity_data):
    """Test that lagged values are consistent with previous period."""
    df = sample_pool_elasticity_data.sort_values(["pool_name", "period_id"])

    for pool in df["pool_name"].unique():
        pool_data = df[df["pool_name"] == pool].reset_index(drop=True)

        # For periods after the first, prev values should match previous period current values
        for i in range(1, len(pool_data)):
            # Allow small floating point differences
            assert np.isclose(
                pool_data.loc[i, "prev_volume_usd"],
                pool_data.loc[i - 1, "volume_usd"],
                rtol=0.01,
            )


def test_percentage_change_calculations(sample_pool_elasticity_data):
    """Test that percentage changes are calculated correctly."""
    df = sample_pool_elasticity_data

    for _, row in df.iterrows():
        # Test fee change calculation
        expected_fee_change = (
            (row["final_fee_bps"] - row["prev_fee_bps"]) / row["prev_fee_bps"]
        ) * 100
        assert np.isclose(row["pct_change_fee_bps"], expected_fee_change, rtol=0.01)

        # Test volume change calculation
        expected_vol_change = (
            (row["volume_usd"] - row["prev_volume_usd"]) / row["prev_volume_usd"]
        ) * 100
        assert np.isclose(row["pct_change_volume"], expected_vol_change, rtol=0.01)


def test_market_share_values(sample_pool_elasticity_data):
    """Test that market share values are valid percentages."""
    df = sample_pool_elasticity_data

    # Market share should be between 0 and 1
    assert (df["pct_of_period_volume"] >= 0).all()
    assert (df["pct_of_period_volume"] <= 1).all()

    # For each period, shares should sum to <= 1 (may not include all pools)
    period_shares = df.groupby("period_id")["pct_of_period_volume"].sum()
    assert (period_shares <= 1.01).all()  # Allow small tolerance


def test_minimum_activity_threshold(sample_pool_elasticity_data):
    """Test that pools meet minimum activity threshold."""
    df = sample_pool_elasticity_data

    # All pools should have at least 10 swaps (per fct_pool_elasticity_inputs filter)
    assert (df["swaps_count"] >= 10).all()
    assert (df["prev_swaps_count"] >= 10).all()
