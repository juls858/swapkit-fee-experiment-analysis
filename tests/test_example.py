"""Example test file demonstrating testing patterns."""

import pandas as pd
import pytest


def test_sample_data_fixture(sample_weekly_data):
    """Test that sample data fixture is properly structured."""
    df = pd.DataFrame(sample_weekly_data)

    # Check structure
    assert len(df) == 2
    assert "period_id" in df.columns
    assert "final_fee_bps" in df.columns
    assert "volume_usd" in df.columns

    # Check data types
    assert df["final_fee_bps"].dtype in [float, "float64"]
    assert df["volume_usd"].dtype in [float, "float64"]
    assert df["swaps_count"].dtype in [int, "int64"]


def test_basic_calculations(sample_weekly_data):
    """Test basic revenue calculations on sample data."""
    df = pd.DataFrame(sample_weekly_data)

    # Calculate revenue per swap
    df["revenue_per_swap"] = df["fees_usd"] / df["swaps_count"]

    # Verify calculations
    assert df["revenue_per_swap"].iloc[0] == 10.0  # 1000 / 100
    assert df["revenue_per_swap"].iloc[1] == 15.0  # 1800 / 120


@pytest.mark.parametrize(
    "fee_bps,volume,expected_revenue",
    [
        (10, 1000000, 1000),  # 10 bps = 0.1%
        (15, 1000000, 1500),  # 15 bps = 0.15%
        (20, 2000000, 4000),  # 20 bps = 0.2%
    ],
)
def test_fee_calculation(fee_bps, volume, expected_revenue):
    """Test fee calculation from basis points."""
    calculated_revenue = volume * (fee_bps / 10000)
    assert calculated_revenue == expected_revenue
