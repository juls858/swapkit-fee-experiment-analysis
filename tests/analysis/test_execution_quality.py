"""
Unit tests for execution quality analysis module.
"""

import polars as pl
import pytest

from thorchain_fee_analysis.analysis.execution_quality import (
    compute_execution_quality,
    get_size_bucket,
    map_provider_to_service,
    parse_asset,
    qa_extraction,
    qa_metrics,
    qa_parsing,
)


class TestAssetParsing:
    """Test asset parsing functions."""

    def test_parse_native_asset(self):
        """Test parsing native assets (two parts)."""
        result = parse_asset("ETH.ETH")
        assert result == {"chain": "ETH", "symbol": "ETH", "contract": None}

        result = parse_asset("BTC.BTC")
        assert result == {"chain": "BTC", "symbol": "BTC", "contract": None}

    def test_parse_token_asset(self):
        """Test parsing token assets (three parts with contract)."""
        result = parse_asset("ETH.USDT-0xdAC17F958D2ee523a2206206994597C13D831ec7")
        assert result["chain"] == "ETH"
        assert result["symbol"] == "USDT"
        assert result["contract"] == "0xdAC17F958D2ee523a2206206994597C13D831ec7"

    def test_parse_invalid_asset(self):
        """Test handling invalid asset strings."""
        result = parse_asset("INVALID")
        assert result == {"chain": None, "symbol": None, "contract": None}

        result = parse_asset("")
        assert result == {"chain": None, "symbol": None, "contract": None}

        result = parse_asset(None)
        assert result == {"chain": None, "symbol": None, "contract": None}

    def test_parse_edge_cases(self):
        """Test edge cases in asset parsing."""
        # Multiple hyphens in contract
        result = parse_asset("ETH.TOKEN-0x123-456")
        assert result["chain"] == "ETH"
        assert result["symbol"] == "TOKEN"
        assert result["contract"] == "0x123-456"


class TestProviderMapping:
    """Test provider to service mapping."""

    def test_map_thorchain(self):
        """Test THORChain variants."""
        assert map_provider_to_service("THORCHAIN") == "THORCHAIN"
        assert map_provider_to_service("THORCHAIN_STREAMING") == "THORCHAIN"
        assert map_provider_to_service("UNISWAP_V3-THORCHAIN") == "THORCHAIN"

    def test_map_chainflip(self):
        """Test Chainflip variants."""
        assert map_provider_to_service("CHAINFLIP") == "CHAINFLIP"
        assert map_provider_to_service("CHAINFLIP_STREAMING") == "CHAINFLIP"

    def test_map_near(self):
        """Test NEAR Intents."""
        assert map_provider_to_service("NEAR") == "NEAR"

    def test_map_maya(self):
        """Test Maya Protocol."""
        assert map_provider_to_service("MAYACHAIN") == "MAYA"
        assert map_provider_to_service("MAYACHAIN_STREAMING") == "MAYA"

    def test_map_other(self):
        """Test DEX-only providers."""
        assert map_provider_to_service("UNISWAP_V3") == "OTHER"
        assert map_provider_to_service("ONEINCH") == "OTHER"
        assert map_provider_to_service("") == "OTHER"
        assert map_provider_to_service(None) == "OTHER"

    def test_precedence(self):
        """Test that cross-chain providers take precedence."""
        # THORCHAIN should win even if UNISWAP is first
        assert map_provider_to_service("UNISWAP_V3-THORCHAIN") == "THORCHAIN"


class TestSizeBucketing:
    """Test order size bucketing."""

    def test_bucket_ranges(self):
        """Test each bucket range."""
        assert get_size_bucket(500) == "[0,1k)"
        assert get_size_bucket(5000) == "[1k,10k)"
        assert get_size_bucket(25000) == "[10k,50k)"
        assert get_size_bucket(100000) == "[50k,250k)"
        assert get_size_bucket(500000) == "[250k,20M)"

    def test_bucket_boundaries(self):
        """Test exact bucket boundaries."""
        assert get_size_bucket(999.99) == "[0,1k)"
        assert get_size_bucket(1000) == "[1k,10k)"
        assert get_size_bucket(9999.99) == "[1k,10k)"
        assert get_size_bucket(10000) == "[10k,50k)"
        assert get_size_bucket(49999.99) == "[10k,50k)"
        assert get_size_bucket(50000) == "[50k,250k)"
        assert get_size_bucket(249999.99) == "[50k,250k)"
        assert get_size_bucket(250000) == "[250k,20M)"

    def test_bucket_edge_cases(self):
        """Test edge cases."""
        assert get_size_bucket(0) == "[0,1k)"
        assert get_size_bucket(-100) == "unknown"
        assert get_size_bucket(None) == "unknown"


class TestMetricsComputation:
    """Test execution quality metrics computation."""

    def test_compute_eq_improvement(self):
        """Test EQ calculation for price improvement."""
        # Create test data: realized > expected (price improvement)
        # Use pandas to avoid Polars segfault on Python 3.13
        import pandas as pd

        df_pd = pd.DataFrame(
            {
                "expected_buy_amount": [1.0],
                "realized_buy_amount": [1.01],  # 1% improvement
                "expected_buy_amount_max_slippage": [0.99],
            }
        )
        df = pl.from_pandas(df_pd)

        result = compute_execution_quality(df)

        # 1% improvement = 100 bps
        assert abs(result["eq_bps"][0] - 100.0) < 0.1
        assert result["is_improvement"][0]
        assert not result["is_breach"][0]
        assert abs(result["eq_pct"][0] - 1.0) < 0.01
        assert abs(result["slippage_bps"][0] - (-100.0)) < 0.1

    def test_compute_eq_slippage(self):
        """Test EQ calculation for negative slippage."""
        # Create test data: realized < expected (slippage)
        import pandas as pd

        df_pd = pd.DataFrame(
            {
                "expected_buy_amount": [1.0],
                "realized_buy_amount": [0.98],  # 2% slippage
                "expected_buy_amount_max_slippage": [0.97],
            }
        )
        df = pl.from_pandas(df_pd)

        result = compute_execution_quality(df)

        # 2% slippage = -200 bps
        assert abs(result["eq_bps"][0] - (-200.0)) < 0.1
        assert not result["is_improvement"][0]
        assert not result["is_breach"][0]  # Still above max slippage
        assert abs(result["eq_pct"][0] - (-2.0)) < 0.01

    def test_compute_eq_breach(self):
        """Test detection of max slippage breach."""
        # Create test data: realized < max_slippage (breach)
        import pandas as pd

        df_pd = pd.DataFrame(
            {
                "expected_buy_amount": [1.0],
                "realized_buy_amount": [0.96],  # 4% slippage
                "expected_buy_amount_max_slippage": [0.97],  # Max allowed was 3%
            }
        )
        df = pl.from_pandas(df_pd)

        result = compute_execution_quality(df)

        assert not result["is_improvement"][0]
        assert result["is_breach"][0]  # Breached max slippage

    def test_compute_eq_exact_match(self):
        """Test EQ calculation for exact match."""
        import pandas as pd

        df_pd = pd.DataFrame(
            {
                "expected_buy_amount": [1.0],
                "realized_buy_amount": [1.0],  # Exact match
                "expected_buy_amount_max_slippage": [0.97],
            }
        )
        df = pl.from_pandas(df_pd)

        result = compute_execution_quality(df)

        assert abs(result["eq_bps"][0]) < 0.1  # Should be ~0
        assert not result["is_improvement"][0]  # Not strictly better
        assert not result["is_breach"][0]


class TestQAFunctions:
    """Test QA checking functions."""

    def test_qa_extraction(self):
        """Test extraction QA metrics."""
        import pandas as pd

        df_pd = pd.DataFrame({"col1": [1, 2, 3, None, 5], "col2": ["a", "b", None, "d", "e"]})
        df = pl.from_pandas(df_pd)

        qa = qa_extraction(df, "test_data")

        assert qa["dataset"] == "test_data"
        assert qa["total_rows"] == 5
        assert "timestamp" in qa
        assert "null_rates" in qa
        assert qa["null_rates"]["col1"]["null_count"] == 1
        assert abs(qa["null_rates"]["col1"]["null_rate_pct"] - 20.0) < 0.1
        assert qa["null_rates"]["col2"]["null_count"] == 1

    def test_qa_parsing(self):
        """Test parsing QA metrics."""
        import pandas as pd

        df_pd = pd.DataFrame(
            {
                "sell_chain": ["ETH", "BTC", None, "AVAX", "ETH"],
                "buy_chain": ["BTC", "ETH", "ETH", None, "AVAX"],
            }
        )
        df = pl.from_pandas(df_pd)

        qa = qa_parsing(df)

        assert qa["total_rows"] == 5
        assert qa["sell_asset_parsed"] == 4  # 1 null
        assert qa["sell_asset_coverage_pct"] == 80.0
        assert qa["buy_asset_parsed"] == 4  # 1 null
        assert qa["buy_asset_coverage_pct"] == 80.0

    def test_qa_metrics(self):
        """Test metrics QA checks."""
        # Create test data with some outliers
        import pandas as pd

        df_pd = pd.DataFrame(
            {
                "eq_bps": [-100, -50, 0, 50, 100, 6000, -6000],  # 2 outliers
                "is_improvement": [False, False, False, True, True, True, False],
                "is_breach": [False, False, False, False, False, False, True],
            }
        )
        df = pl.from_pandas(df_pd)

        qa = qa_metrics(df)

        assert qa["total_metrics"] == 7
        assert qa["outlier_count"] == 2  # Beyond ±5000 bps
        assert abs(qa["outlier_rate_pct"] - 28.57) < 0.1
        assert qa["eq_bps_stats"]["median"] == 0.0
        assert abs(qa["improvement_rate_pct"] - 42.86) < 0.1  # 3/7
        assert abs(qa["breach_rate_pct"] - 14.29) < 0.1  # 1/7


class TestQAThresholds:
    """Test QA threshold violations."""

    def test_null_rate_threshold(self):
        """Test null rate threshold detection."""
        # High null rate should be flagged
        import pandas as pd

        df_pd = pd.DataFrame(
            {
                "critical_field": [1, None, None, None, 5]  # 60% null
            }
        )
        df = pl.from_pandas(df_pd)

        qa = qa_extraction(df, "test")
        null_rate = qa["null_rates"]["critical_field"]["null_rate_pct"]

        # Check if it exceeds 1% threshold
        assert null_rate > 1.0  # Should trigger alert

    def test_parsing_coverage_threshold(self):
        """Test parsing coverage threshold."""
        # Low coverage should be flagged
        import pandas as pd

        df_pd = pd.DataFrame(
            {
                "sell_chain": [None, None, "ETH", None, None]  # 20% coverage
            }
        )
        df = pl.from_pandas(df_pd)

        qa = qa_parsing(df)

        # Check if below 99.5% threshold
        assert qa["sell_asset_coverage_pct"] < 99.5  # Should trigger alert

    def test_outlier_threshold(self):
        """Test outlier threshold."""
        # Many outliers should be flagged
        import pandas as pd

        outliers = [6000, 7000, -6000, -7000, -8000, 9000]
        normal = [10, 20, 30, 40, 50]

        df_pd = pd.DataFrame(
            {
                "eq_bps": outliers + normal,
                "is_improvement": [True] * len(outliers + normal),
                "is_breach": [False] * len(outliers + normal),
            }
        )
        df = pl.from_pandas(df_pd)

        qa = qa_metrics(df)

        # Check if exceeds 5% outlier threshold
        assert qa["outlier_rate_pct"] > 5.0  # Should trigger alert


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
