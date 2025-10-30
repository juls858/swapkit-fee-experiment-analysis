"""Snowflake connection utilities.

This module provides a unified interface for connecting to Snowflake across
different environments (Streamlit, local development, CI/CD).

Connection methods (in order of precedence):
1. Streamlit secrets (when running in Streamlit Cloud)
2. ~/.snowflake/connections.toml (default profile '9R')
3. Environment variables (SNOWFLAKE_*)
"""

import os
from pathlib import Path

from snowflake.snowpark import Session


def get_snowpark_session(
    profile: str = "9R",
    use_streamlit_secrets: bool = True,
) -> Session:
    """Get a Snowpark session with automatic connection method detection.

    Args:
        profile: Profile name to use from ~/.snowflake/connections.toml
        use_streamlit_secrets: Whether to attempt using Streamlit secrets first

    Returns:
        Snowflake Snowpark Session

    Raises:
        RuntimeError: If no valid connection configuration is found
    """
    # Method 1: Try Streamlit secrets (when available)
    if use_streamlit_secrets:
        try:
            import streamlit as st

            if hasattr(st, "secrets") and "snowflake" in st.secrets:
                return Session.builder.configs(
                    {
                        "account": st.secrets.snowflake.account,
                        "user": st.secrets.snowflake.user,
                        "password": st.secrets.snowflake.password,
                        "role": st.secrets.snowflake.get("role", "ACCOUNTADMIN"),
                        "warehouse": st.secrets.snowflake.get("warehouse", "COMPUTE_WH"),
                        "database": st.secrets.snowflake.get("database", "9R"),
                        "schema": st.secrets.snowflake.get("schema", "FEE_EXPERIMENT"),
                    }
                ).create()
        except (ImportError, AttributeError, KeyError, Exception):
            # Catches StreamlitSecretNotFoundError and other exceptions
            # Falls back to next connection method
            pass

    # Method 2: Try connections.toml file
    connections_toml = Path.home() / ".snowflake" / "connections.toml"
    if connections_toml.exists():
        try:
            # Snowflake's built-in connection resolver handles toml parsing
            return Session.builder.config("connection_name", profile).create()
        except Exception:
            pass

    # Method 3: Try environment variables
    env_config = {
        "account": os.getenv("SNOWFLAKE_ACCOUNT"),
        "user": os.getenv("SNOWFLAKE_USER"),
        "password": os.getenv("SNOWFLAKE_PASSWORD"),
        "role": os.getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        "database": os.getenv("SNOWFLAKE_DATABASE", "9R"),
        "schema": os.getenv("SNOWFLAKE_SCHEMA", "FEE_EXPERIMENT"),
    }

    if all([env_config["account"], env_config["user"], env_config["password"]]):
        return Session.builder.configs(env_config).create()

    # No valid connection found
    msg = (
        "Could not establish Snowflake connection. Please configure one of:\n"
        "1. Streamlit secrets (st.secrets.snowflake)\n"
        f"2. ~/.snowflake/connections.toml (profile '{profile}')\n"
        "3. Environment variables (SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD)"
    )
    raise RuntimeError(msg)


def get_session_info(session: Session) -> dict:
    """Get information about the current Snowflake session.

    Args:
        session: Active Snowpark session

    Returns:
        Dictionary with session information
    """
    result = session.sql("SELECT CURRENT_USER(), CURRENT_ROLE(), CURRENT_DATABASE()").collect()
    row = result[0]
    return {
        "user": row[0],
        "role": row[1],
        "database": row[2],
    }


def test_connection(session: Session | None = None) -> bool:
    """Test if a Snowflake connection is working.

    Args:
        session: Session to test. If None, creates a new session.

    Returns:
        True if connection is working, False otherwise
    """
    try:
        if session is None:
            session = get_snowpark_session()

        result = session.sql("SELECT 1 as test").collect()
        return len(result) == 1 and result[0][0] == 1
    except Exception:
        return False
