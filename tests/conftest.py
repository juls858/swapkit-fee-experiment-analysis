"""Pytest configuration and shared fixtures."""

from unittest.mock import Mock

import pytest
from snowflake.snowpark import Session


@pytest.fixture
def mock_snowpark_session():
    """Create a mock Snowpark session for testing."""
    session = Mock(spec=Session)
    return session


@pytest.fixture
def sample_weekly_data():
    """Sample weekly summary data for testing."""
    return {
        "period_id": ["P1", "P2"],
        "period_start_date": ["2025-01-01", "2025-01-08"],
        "period_end_date": ["2025-01-07", "2025-01-14"],
        "final_fee_bps": [10.0, 15.0],
        "volume_usd": [1000000.0, 1200000.0],
        "fees_usd": [1000.0, 1800.0],
        "swaps_count": [100, 120],
        "unique_swappers": [50, 60],
    }
