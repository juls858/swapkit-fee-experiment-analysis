"""
THORChain Fee Experiment Dashboard - Home Page

Main entry point for the multipage Streamlit dashboard.
Provides overview, key metrics, and navigation to detailed pages.
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from snowflake.snowpark import Session

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session as _get_session

# Page configuration
st.set_page_config(
    page_title="THORChain Fee Experiment",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def get_snowpark_session() -> Session:
    """Get cached Snowpark session for Streamlit dashboard."""
    return _get_session()


@st.cache_data(show_spinner=False, ttl=60)
def load_summary_metrics(_session: Session) -> dict:
    """Load high-level summary metrics for KPI cards."""
    try:
        sql = """
        SELECT
            COUNT(DISTINCT period_id) as total_periods,
            SUM(swaps_count) as total_swaps,
            SUM(volume_usd) as total_volume_usd,
            SUM(fees_usd) as total_fees_usd,
            AVG(final_fee_bps) as avg_fee_bps
        FROM "9R".FEE_EXPERIMENT_MARTS.FCT_WEEKLY_SUMMARY_FINAL
        """
        df = _session.sql(sql).to_pandas()
        df.columns = df.columns.str.lower()  # Normalize column names to lowercase
        return df.iloc[0].to_dict()
    except Exception as e:
        st.error(f"Failed to load summary metrics: {e}")
        return {}


def format_number(value, prefix="", suffix="", decimals=0):
    """Format large numbers with K/M/B suffixes."""
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


def main():
    st.title("⚡ THORChain Fee Experiment Dashboard")
    st.caption(
        "Analysis of swap fee tier experiment (Aug 15 - Oct 31, 2025) | Powered by dbt + Snowflake"
    )

    st.markdown("---")

    # Load session and metrics
    try:
        session = get_snowpark_session()
        metrics = load_summary_metrics(session)
    except Exception as e:
        st.error(f"Failed to connect to Snowflake: {e}")
        st.info(
            "Please ensure your Snowflake credentials are configured. "
            "See docs for setup instructions."
        )
        st.stop()

    if not metrics:
        st.warning("No data available. Check Snowflake connection and dbt models.")
        st.stop()

    # KPI Cards
    st.subheader("Experiment Overview")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric(
            "Fee Periods",
            f"{int(metrics.get('total_periods', 0))}",
        )

    with col2:
        st.metric(
            "Total Swaps",
            format_number(metrics.get("total_swaps", 0)),
        )

    with col3:
        st.metric(
            "Total Volume",
            format_number(metrics.get("total_volume_usd", 0), prefix="$", decimals=1),
        )

    with col4:
        st.metric(
            "Total Fees",
            format_number(metrics.get("total_fees_usd", 0), prefix="$", decimals=1),
        )

    with col5:
        st.metric(
            "Avg Fee Rate",
            f"{metrics.get('avg_fee_bps', 0):.1f} bps",
        )

    st.markdown("---")

    # Navigation guide
    st.subheader("📊 Dashboard Pages")

    # Phase 1: Data Foundation & Descriptive Analytics (Consolidated)
    st.markdown("### ✅ Phase 1: Data Foundation & Descriptive Analytics")
    st.page_link(
        "pages/1_Phase_1__Overview.py",
        label="📈 Phase 1 Overview",
        help="Weekly summary, trends, and validation in one page",
    )

    st.markdown("---")

    # Phase 2: Core Revenue Analysis (Complete)
    st.markdown("### ✅ Phase 2: Core Revenue Analysis")
    st.page_link(
        "pages/5_Phase_2__Elasticity_Analysis.py",
        label="📊 Elasticity Analysis",
        help="Price elasticity, optimal fee recommendation, and revenue decomposition",
    )

    st.markdown("---")

    # Future Phases (Planned)
    with st.expander("📋 Planned: Phase 3 & 4 (User & Pool Analysis)", expanded=False):
        st.info(
            """
            **Phase 3: User Behavior & Segmentation**
            - 👥 Cohort Analysis (retention by fee tier)
            - 📊 Trade Size Segmentation (whale vs. retail elasticity)

            **Phase 4: Pool & Asset Analysis**
            - 🏊 Pool-Level Revenue Analysis
            - 🔄 Competitive Analysis

            *These phases are planned but not yet implemented.*
            """
        )

    st.markdown("---")

    # About section
    with st.expander("ℹ️ About This Dashboard"):
        st.markdown(
            """
            ### THORChain Fee Experiment Analysis

            This dashboard analyzes the impact of different swap fee tiers on:
            - **Revenue**: Total fees collected and revenue per swap/user
            - **Volume**: Swap volume and user activity levels
            - **User Behavior**: New vs. returning users, cohort analysis
            - **Pool Performance**: Which pools are most affected by fee changes

            **Data Pipeline**:
            1. Raw swap data from `THORCHAIN.DEFI.FACT_SWAPS`
            2. Transformed via dbt models (staging → intermediate → marts)
            3. Visualized in this Streamlit dashboard

            **Experiment Window**: August 15 - October 31, 2025

            **Fee Tiers Tested**: 1, 5, 10, 15, 25 basis points

            For technical details, see the project documentation.
            """
        )

    # Footer
    st.markdown("---")
    st.caption(
        "Built with Streamlit, dbt, Snowflake | "
        "Data refreshes every 60 seconds | "
        "Questions? Check the README"
    )


if __name__ == "__main__":
    main()
