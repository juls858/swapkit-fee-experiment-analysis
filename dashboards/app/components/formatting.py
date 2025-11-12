"""Formatting utilities for dashboard displays."""

import pandas as pd


def format_number(value, prefix="", suffix="", decimals=0):
    """
    Format large numbers with K/M/B suffixes.

    Args:
        value: Number to format
        prefix: String to prepend (e.g., "$")
        suffix: String to append (e.g., " USD")
        decimals: Number of decimal places

    Returns:
        Formatted string
    """
    if pd.isna(value):
        return "N/A"

    if abs(value) >= 1_000_000_000:
        return f"{prefix}{value / 1_000_000_000:.{decimals}f}B{suffix}"
    elif abs(value) >= 1_000_000:
        return f"{prefix}{value / 1_000_000:.{decimals}f}M{suffix}"
    elif abs(value) >= 1_000:
        return f"{prefix}{value / 1_000:.{decimals}f}K{suffix}"
    else:
        return f"{prefix}{value:.{decimals}f}{suffix}"


def format_currency(value, decimals=2):
    """Format value as USD currency."""
    return format_number(value, prefix="$", decimals=decimals)


def format_bps(value, decimals=1):
    """Format value as basis points."""
    if pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f} bps"


def format_percent(value, decimals=1):
    """Format value as percentage."""
    if pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f}%"
