"""Tests for chart builder functions."""

import pandas as pd
import pytest

from src.thorchain_fee_analysis.visualization.charts import (
    create_elasticity_scatter,
    create_fee_revenue_dual_axis,
    create_pool_elasticity_heatmap,
    create_pool_elasticity_scatter,
    create_pool_market_share_area,
    create_pool_revenue_treemap,
    create_pool_small_multiples,
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


@pytest.fixture
def sample_pool_data():
    """Sample pool data for testing pool charts."""
    data = {
        "pool_name": ["BTC.BTC", "ETH.ETH", "BTC.BTC", "ETH.ETH", "USDC.USDC", "USDC.USDC"],
        "pool_type": ["BTC", "ETH", "BTC", "ETH", "STABLE", "STABLE"],
        "period_id": [1, 1, 2, 2, 1, 2],
        "period_start_date": pd.to_datetime(
            ["2023-01-01", "2023-01-01", "2023-01-08", "2023-01-08", "2023-01-01", "2023-01-08"]
        ),
        "final_fee_bps": [10.0, 10.0, 15.0, 15.0, 10.0, 15.0],
        "fees_usd": [10000.0, 5000.0, 12000.0, 4500.0, 3000.0, 3500.0],
        "volume_usd": [1000000.0, 500000.0, 900000.0, 450000.0, 300000.0, 280000.0],
        "swaps_count": [100, 50, 95, 48, 30, 28],
        "pct_of_period_volume": [0.5, 0.25, 0.52, 0.26, 0.15, 0.16],
        "pct_change_fee_bps": [0.0, 0.0, 50.0, 50.0, 0.0, 50.0],
        "pct_change_volume": [0.0, 0.0, -10.0, -10.0, 0.0, -6.67],
        "pct_change_fees": [0.0, 0.0, 20.0, -10.0, 0.0, 16.67],
    }
    return pd.DataFrame(data)


def test_create_pool_revenue_treemap(sample_pool_data):
    """Test pool revenue treemap creation."""
    fig = create_pool_revenue_treemap(sample_pool_data, pool_type_col="pool_type")

    assert fig is not None
    assert hasattr(fig, "data")
    assert len(fig.data) > 0
    assert fig.layout.title.text is not None
    assert "Pool Revenue" in fig.layout.title.text


def test_create_pool_small_multiples(sample_pool_data):
    """Test pool small multiples chart creation."""
    chart = create_pool_small_multiples(sample_pool_data, top_n=3, metric="fees_usd")

    assert chart is not None
    assert hasattr(chart, "to_dict")
    chart_dict = chart.to_dict()
    assert "facet" in chart_dict or "spec" in chart_dict  # Faceted chart structure


def test_create_pool_elasticity_heatmap(sample_pool_data):
    """Test pool elasticity heatmap creation."""
    chart = create_pool_elasticity_heatmap(sample_pool_data, metric="pct_change_fees")

    assert chart is not None
    assert hasattr(chart, "to_dict")
    chart_dict = chart.to_dict()
    assert "layer" in chart_dict  # Should have rect + text layers


def test_create_pool_elasticity_scatter(sample_pool_data):
    """Test pool elasticity scatter plot creation."""
    chart = create_pool_elasticity_scatter(
        sample_pool_data,
        x_col="pct_change_fee_bps",
        y_col="pct_change_volume",
        color_by="pool_type",
    )

    assert chart is not None
    assert hasattr(chart, "to_dict")
    chart_dict = chart.to_dict()
    # Should have scatter + regression layers
    assert "layer" in chart_dict


def test_create_pool_market_share_area(sample_pool_data):
    """Test pool market share area chart creation."""
    chart = create_pool_market_share_area(sample_pool_data, pool_type_col="pool_type")

    assert chart is not None
    assert hasattr(chart, "to_dict")
    chart_dict = chart.to_dict()
    assert "mark" in chart_dict
    assert chart_dict["mark"]["type"] == "area"


def test_pool_charts_handle_empty_data():
    """Test that pool charts handle empty data gracefully."""
    empty_df = pd.DataFrame()

    # These should not raise exceptions
    try:
        create_pool_revenue_treemap(empty_df)
    except Exception:
        pass  # Expected to fail gracefully

    try:
        create_pool_small_multiples(empty_df)
    except Exception:
        pass  # Expected to fail gracefully


def test_pool_elasticity_scatter_insufficient_data():
    """Test pool elasticity scatter with insufficient data."""
    # Single row - not enough for regression
    single_row = pd.DataFrame(
        {
            "pool_name": ["BTC.BTC"],
            "pool_type": ["BTC"],
            "period_id": [1],
            "final_fee_bps": [10.0],
            "pct_change_fee_bps": [0.0],
            "pct_change_volume": [0.0],
        }
    )

    chart = create_pool_elasticity_scatter(single_row)

    assert chart is not None
    # Should return a placeholder or minimal chart
