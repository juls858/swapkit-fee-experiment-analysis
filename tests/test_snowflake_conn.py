"""Tests for Snowflake connection utilities."""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest

from thorchain_fee_analysis.data.snowflake_conn import (
    get_session_info,
    get_snowpark_session,
    test_connection,
)


class TestGetSnowparkSession:
    """Tests for get_snowpark_session function."""

    @patch("thorchain_fee_analysis.data.snowflake_conn.Path")
    @patch("thorchain_fee_analysis.data.snowflake_conn.Session")
    def test_connection_with_env_vars(self, mock_session_class, mock_path):
        """Test connection using environment variables."""
        # Mock Path.exists() to return False (no connections.toml file)
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.exists.return_value = False

        # Set up environment variables
        env_vars = {
            "SNOWFLAKE_ACCOUNT": "test_account",
            "SNOWFLAKE_USER": "test_user",
            "SNOWFLAKE_PASSWORD": "test_password",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            # Mock the session builder chain
            mock_builder = MagicMock()
            mock_session_class.builder = mock_builder
            mock_builder.configs.return_value = mock_builder
            mock_builder.create.return_value = Mock()

            # Call function
            session = get_snowpark_session(use_streamlit_secrets=False)

            # Verify session was created
            assert session is not None
            mock_builder.configs.assert_called_once()
            mock_builder.create.assert_called_once()

    @patch("thorchain_fee_analysis.data.snowflake_conn.Path")
    def test_missing_credentials_raises_error(self, mock_path):
        """Test that missing credentials raises RuntimeError."""
        # Mock Path.exists() to return False (no connections.toml file)
        mock_path.home.return_value = MagicMock()
        mock_path.home.return_value.__truediv__.return_value.__truediv__.return_value.exists.return_value = False

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="Could not establish Snowflake connection"):
                get_snowpark_session(use_streamlit_secrets=False)


class TestGetSessionInfo:
    """Tests for get_session_info function."""

    def test_get_session_info(self, mock_snowpark_session):
        """Test extracting session information."""
        # Mock SQL result
        mock_result = [("test_user", "test_role", "test_db")]
        mock_snowpark_session.sql.return_value.collect.return_value = mock_result

        # Call function
        info = get_session_info(mock_snowpark_session)

        # Verify
        assert info["user"] == "test_user"
        assert info["role"] == "test_role"
        assert info["database"] == "test_db"
        mock_snowpark_session.sql.assert_called_once()


class TestTestConnection:
    """Tests for test_connection function."""

    def test_successful_connection(self, mock_snowpark_session):
        """Test successful connection test."""
        # Mock successful query
        mock_result = [(1,)]
        mock_snowpark_session.sql.return_value.collect.return_value = mock_result

        # Call function
        result = test_connection(mock_snowpark_session)

        # Verify
        assert result is True
        mock_snowpark_session.sql.assert_called_with("SELECT 1 as test")

    def test_failed_connection(self, mock_snowpark_session):
        """Test failed connection test."""
        # Mock failed query
        mock_snowpark_session.sql.side_effect = Exception("Connection failed")

        # Call function
        result = test_connection(mock_snowpark_session)

        # Verify
        assert result is False
