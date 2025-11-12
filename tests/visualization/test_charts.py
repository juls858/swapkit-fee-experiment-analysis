"""Tests for chart builder functions."""

import pandas as pd
import pytest

from src.thorchain_fee_analysis.visualization.charts import (
    create_elasticity_scatter,
    create_fee_revenue_dual_axis,
    create_volume_footprint_chart,
    create_waterfall_chart,
)


@pytest.fixture
def sample_elasticity_data():
    """Sample elasticity data for testing."""
    data = {
        "period_id": [1, 2, 3, 4, 5],
        "period_start_date": pd.to_datetime(
            ["2023-01-01", "2023-01-08", "2023-01-15", "2023-01-22", "2023-01-29"]
        ),
        "period_end_date": pd.to_datetime(
            ["2023-01-07", "2023-01-14", "2023-01-21", "2023-01-28", "2023-02-04"]
        ),
        "final_fee_bps": [10.0, 15.0, 12.0, 20.0, 10.0],
        "prev_fee_bps": [10.0, 10.0, 15.0, 12.0, 20.0],
        "volume_usd": [100000.0, 80000.0, 95000.0, 60000.0, 110000.0],
        "prev_volume_usd": [100000.0, 100000.0, 80000.0, 95000.0, 60000.0],
        "fees_usd": [1000.0, 1200.0, 1140.0, 1200.0, 1100.0],
        "prev_fees_usd": [1000.0, 1000.0, 1200.0, 1140.0, 1200.0],
        "pct_change_fee_bps": [0.0, 50.0, -20.0, 66.67, -50.0],
        "pct_change_volume": [0.0, -20.0, 18.75, -36.84, 83.33],
        "pct_change_fees": [0.0, 20.0, -5.0, 5.26, -8.33],
    }
    return pd.DataFrame(data)


def test_create_volume_footprint_chart(sample_elasticity_data):
    """Test volume footprint chart creation."""
    fig = create_volume_footprint_chart(sample_elasticity_data)

    assert fig is not None
    assert hasattr(fig, "data")
    assert len(fig.data) > 0
    assert fig.layout.title.text is not None
    assert "Volume" in fig.layout.yaxis.title.text


def test_create_fee_revenue_dual_axis(sample_elasticity_data):
    """Test dual-axis fee/revenue chart creation."""
    fig = create_fee_revenue_dual_axis(sample_elasticity_data)

    assert fig is not None
    assert hasattr(fig, "data")
    assert len(fig.data) >= 2  # Should have at least fee and revenue traces
    assert fig.layout.title.text is not None
    # Check for dual y-axes
    assert fig.layout.yaxis is not None
    assert fig.layout.yaxis2 is not None


def test_create_elasticity_scatter(sample_elasticity_data):
    """Test elasticity scatter plot creation."""
    chart = create_elasticity_scatter(
        sample_elasticity_data,
        "pct_change_fee_bps",
        "pct_change_volume",
        "Test Elasticity",
        "Fee Change (%)",
        "Volume Change (%)",
        -0.5,
    )

    assert chart is not None
    assert hasattr(chart, "to_dict")
    chart_dict = chart.to_dict()
    assert "layer" in chart_dict  # Should have scatter + regression layers
    assert len(chart_dict["layer"]) == 2


def test_create_waterfall_chart():
    """Test waterfall chart creation."""
    components = [
        {"component": "Starting", "value": 1000, "type": "total"},
        {"component": "Increase", "value": 200, "type": "positive"},
        {"component": "Decrease", "value": -100, "type": "negative"},
        {"component": "Ending", "value": 1100, "type": "total"},
    ]

    fig = create_waterfall_chart(components, "Test Waterfall")

    assert fig is not None
    assert hasattr(fig, "data")
    assert len(fig.data) > 0
    assert fig.layout.title.text == "Test Waterfall"
    assert "Revenue" in fig.layout.yaxis.title.text


def test_volume_footprint_handles_zero_delta(sample_elasticity_data):
    """Test that volume footprint handles zero delta gracefully."""
    # Create data with zero delta
    df = sample_elasticity_data.copy()
    df["prev_volume_usd"] = df["volume_usd"]  # Make all deltas zero

    fig = create_volume_footprint_chart(df)

    assert fig is not None
    assert len(fig.data) > 0


def test_elasticity_scatter_without_elasticity_value(sample_elasticity_data):
    """Test elasticity scatter without elasticity coefficient."""
    chart = create_elasticity_scatter(
        sample_elasticity_data, "pct_change_fee_bps", "pct_change_volume", "Test", "X", "Y", None
    )

    assert chart is not None
    chart_dict = chart.to_dict()
    assert "title" in chart_dict
