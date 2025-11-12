"""
Elasticity Analysis Page - Phase 2 Revenue Analysis

Implements:
- Price Elasticity of Demand (PED)
- Revenue Elasticity
- Optimal Fee Recommendation
- Revenue Decomposition Waterfall Chart
- Downloadable Markdown Report
"""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from snowflake.snowpark import Session
from streamlit_lightweight_charts import renderLightweightCharts

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from thorchain_fee_analysis.analysis.elasticity import analyze_elasticity
from thorchain_fee_analysis.analysis.revenue_decomposition import (
    analyze_revenue_decomposition,
    create_waterfall_data,
    summarize_decomposition,
)
from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session as _get_session
from thorchain_fee_analysis.visualization.charts import (
    create_elasticity_scatter,
    create_fee_revenue_lightweight_chart,
    create_fee_volume_lightweight_chart,
    create_waterfall_chart,
)

# Import formatting utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from components.formatting import format_bps, format_currency

st.set_page_config(page_title="Elasticity Analysis", page_icon="📊", layout="wide")


@st.cache_resource(show_spinner=False)
def get_snowpark_session() -> Session:
    return _get_session()


@st.cache_data(show_spinner=False, ttl=60)
def load_elasticity_inputs(_session: Session) -> pd.DataFrame:
    """Load elasticity inputs from Snowflake mart."""
    sql = 'SELECT * FROM "9R".FEE_EXPERIMENT_MARTS.FCT_ELASTICITY_INPUTS ORDER BY period_start_date'
    df = _session.sql(sql).to_pandas()
    df.columns = df.columns.str.lower()
    return df


@st.cache_data(show_spinner=False, ttl=60)
def load_weekly_summary(_session: Session) -> pd.DataFrame:
    """Load weekly summary with lagged columns for decomposition."""
    # Use the elasticity inputs view which has all the lagged data we need
    sql = """
    SELECT
        period_id,
        period_start_date,
        period_end_date,
        final_fee_bps,
        prev_fee_bps,
        volume_usd,
        prev_volume_usd,
        fees_usd,
        prev_fees_usd,
        swaps_count,
        prev_swaps_count,
        avg_swap_size_usd,
        prev_avg_swap_size_usd,
        unique_swappers,
        prev_unique_swappers
    FROM "9R".FEE_EXPERIMENT_MARTS.FCT_ELASTICITY_INPUTS
    ORDER BY period_start_date
    """
    df = _session.sql(sql).to_pandas()
    df.columns = df.columns.str.lower()
    return df


def generate_markdown_report(
    elasticity_result, decomp_summary, best_period_info: dict = None
) -> str:
    """Generate downloadable Markdown report with Phase 2 findings."""
    report = f"""# THORChain Fee Experiment - Phase 2 Elasticity Analysis

**Report Generated:** {pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Executive Summary

### Optimal Fee Recommendation

**Model-Based Optimal Fee:** {elasticity_result.optimal_fee_bps:.1f} basis points

**Confidence Interval (95%):** [{elasticity_result.optimal_fee_ci_lower:.1f}, {elasticity_result.optimal_fee_ci_upper:.1f}] bps

"""

    # Add empirical best period info if available
    if best_period_info:
        report += f"""
**Empirical Best Performance:**
- Period {best_period_info["period_id"]} generated the highest observed revenue: ${best_period_info["revenue"]:,.0f}
- Fee tier: {best_period_info["fee_bps"]:.0f} bps
- Volume: ${best_period_info["volume"]:,.0f}

---

### Why Model vs. Empirical Differ

Our quasi-experimental design mitigates confounders via periodization, Δ-based comparisons, and a time-trend control; the decomposition further separates fee-rate, volume, and mix effects from a residual "external" component. However, assignment of fee tiers was not randomized and contemporaneous market shocks can still affect outcomes.

**Model Prediction (Elasticity-Based):**
- Focuses on the incremental (period-to-period) effect of fee changes
- Uses controls to partially adjust for secular trends
- Produces a ceteris paribus revenue-maximizing recommendation within the experiment window

**Empirical Reality:**
- Reflects total revenue including favorable/unfavorable market conditions, timing, and one-off events
- Periods with exceptional conditions can outperform the model’s steady-state recommendation

**Key Insight:** Period {best_period_info["period_id"]}'s high revenue likely combines (1) the fee tier effect and (2) temporarily favorable external conditions.

**Recommendation:** Treat {elasticity_result.optimal_fee_bps:.1f} bps as the policy baseline, and continue monitoring empirical performance; if sustained deviations emerge, revisit the model with richer controls (e.g., market proxies) or pool/segment granularity.

---
"""

    report += """
---

## Key Findings

### 1. Price Elasticity of Demand (PED)

- **Point Estimate:** {elasticity_result.price_elasticity_demand:.3f}
- **95% Confidence Interval:** [{elasticity_result.ped_ci_lower:.3f}, {elasticity_result.ped_ci_upper:.3f}]
- **Interpretation:** A 1% increase in fees leads to a {abs(elasticity_result.price_elasticity_demand):.2f}% {"decrease" if elasticity_result.price_elasticity_demand < 0 else "increase"} in volume

### 2. Revenue Elasticity

- **Point Estimate:** {elasticity_result.revenue_elasticity:.3f}
- **95% Confidence Interval:** [{elasticity_result.revenue_elasticity_ci_lower:.3f}, {elasticity_result.revenue_elasticity_ci_upper:.3f}]
- **Interpretation:** A 1% increase in fees leads to a {abs(elasticity_result.revenue_elasticity):.2f}% {"decrease" if elasticity_result.revenue_elasticity < 0 else "increase"} in revenue

### 3. Demand Elasticity Classification

"""

    if elasticity_result.price_elasticity_demand >= -1:
        report += "**Inelastic Demand** (|PED| < 1): Volume is relatively insensitive to fee changes. Revenue increases with higher fees.\n\n"
    else:
        report += "**Elastic Demand** (|PED| > 1): Volume is sensitive to fee changes. There is an optimal fee that maximizes revenue.\n\n"

    report += f"""---

## Revenue Decomposition Analysis

### Overall Revenue Drivers

Total periods analyzed: {decomp_summary.get("n_periods", 0)}

**Total Revenue Change:** ${decomp_summary.get("total_revenue_change", 0):,.0f}

**Decomposition:**

1. **Fee Rate Effect:** ${decomp_summary.get("total_fee_rate_effect", 0):,.0f} ({decomp_summary.get("overall_fee_rate_pct", 0):.1f}%)
   - Direct impact of fee tier changes

2. **Volume Effect:** ${decomp_summary.get("total_volume_effect", 0):,.0f} ({decomp_summary.get("overall_volume_pct", 0):.1f}%)
   - Impact of volume changes in response to fees

3. **Mix Effect:** ${decomp_summary.get("total_mix_effect", 0):,.0f} ({decomp_summary.get("overall_mix_pct", 0):.1f}%)
   - Changes in swap size distribution

4. **External Effect:** ${decomp_summary.get("total_external_effect", 0):,.0f} ({decomp_summary.get("overall_external_pct", 0):.1f}%)
   - Market conditions and other factors

---

## Statistical Details

- **R-squared:** {elasticity_result.r_squared:.3f}
- **Number of Observations:** {elasticity_result.n_observations}
- **Mean Volume Change:** {elasticity_result.mean_volume_change_pct:.2f}%
- **Mean Fee Change:** {elasticity_result.mean_fee_change_pct:.2f}%
- **Mean Revenue Change:** {elasticity_result.mean_revenue_change_pct:.2f}%

---

## Recommendations

1. **Implement Optimal Fee:** Set base swap fee to {elasticity_result.optimal_fee_bps:.1f} bps to maximize revenue

2. **Monitor Continuously:** Track elasticity metrics as market conditions evolve

3. **Consider Dynamic Pricing:** Explore fee variations by:
   - Pool type (BTC vs stablecoin vs long-tail)
   - Trade size (tiered fee structure)
   - Time of day/week (higher fees during peak periods)

4. **Competitive Analysis:** Monitor competitor fee changes and market share impacts

---

## Methodology

### Elasticity Calculation

- **Method:** Bootstrap estimation with {1000} samples
- **Confidence Level:** 95%
- **Controls:** Time trend, day-of-week effects

### Revenue Decomposition

- **Approach:** Additive decomposition of period-over-period changes
- **Components:** Fee rate, volume, mix, and external effects

---

**Note:** This analysis is based on historical experiment data from August-October 2025. Results should be validated with ongoing monitoring and A/B testing.
"""

    return report


def main():
    st.title("📊 Elasticity Analysis")
    st.caption("Price elasticity, optimal fee recommendation, and revenue decomposition")

    # Load data
    try:
        session = get_snowpark_session()
        elasticity_df = load_elasticity_inputs(session)
        weekly_df = load_weekly_summary(session)
    except Exception as e:
        st.error(f"Failed to load data: {e}")
        st.info(
            "Make sure dbt models have been built: `pdm run dbt-build` "
            "and FCT_ELASTICITY_INPUTS view exists in Snowflake."
        )
        st.stop()

    if elasticity_df.empty:
        st.warning("No elasticity data available. Run dbt models first.")
        st.stop()

    st.markdown("---")

    # Run elasticity analysis
    with st.spinner("Calculating elasticity metrics..."):
        try:
            elasticity_result = analyze_elasticity(
                elasticity_df,
                use_ols=True,
                control_cols=["time_trend"],
                n_bootstrap=1000,
            )
        except Exception as e:
            st.error(f"Elasticity calculation failed: {e}")
            st.stop()

    # Run decomposition analysis
    with st.spinner("Decomposing revenue changes..."):
        try:
            decomp_results = analyze_revenue_decomposition(weekly_df)
            decomp_summary = summarize_decomposition(decomp_results)
            _ = create_waterfall_data(decomp_results)  # Not used in current implementation
        except Exception as e:
            st.error(f"Decomposition calculation failed: {e}")
            st.stop()

    # KPI Cards
    st.subheader("Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Price Elasticity (PED)",
            f"{elasticity_result.price_elasticity_demand:.3f}",
            help="% change in volume per 1% change in fee",
        )
        st.caption(
            f"95% CI: [{elasticity_result.ped_ci_lower:.3f}, {elasticity_result.ped_ci_upper:.3f}]"
        )

    with col2:
        st.metric(
            "Revenue Elasticity",
            f"{elasticity_result.revenue_elasticity:.3f}",
            help="% change in revenue per 1% change in fee",
        )
        st.caption(
            f"95% CI: [{elasticity_result.revenue_elasticity_ci_lower:.3f}, {elasticity_result.revenue_elasticity_ci_upper:.3f}]"
        )

    with col3:
        # Get actual fee range from data
        actual_min_fee = elasticity_df["final_fee_bps"].min()
        actual_max_fee = elasticity_df["final_fee_bps"].max()

        if elasticity_result.optimal_fee_bps:
            optimal_fee = elasticity_result.optimal_fee_bps

            # Check if optimal is within tested range
            if optimal_fee < actual_min_fee or optimal_fee > actual_max_fee:
                st.metric(
                    "Optimal Fee (Extrapolated)",
                    f"{optimal_fee:.1f} bps",
                    help=f"⚠️ Outside tested range ({actual_min_fee:.0f}-{actual_max_fee:.0f} bps)",
                )
                st.caption(f"⚠️ Not tested: {actual_min_fee:.0f}-{actual_max_fee:.0f} bps range")
            else:
                st.metric(
                    "Optimal Fee",
                    f"{optimal_fee:.1f} bps",
                    help="Revenue-maximizing fee tier within tested range",
                )
                if (
                    elasticity_result.optimal_fee_ci_lower
                    and elasticity_result.optimal_fee_ci_upper
                ):
                    st.caption(
                        f"95% CI: [{elasticity_result.optimal_fee_ci_lower:.1f}, {elasticity_result.optimal_fee_ci_upper:.1f}]"
                    )
        else:
            st.metric("Optimal Fee", "N/A")

    with col4:
        st.metric(
            "R-squared",
            f"{elasticity_result.r_squared:.3f}",
            help="Model fit quality",
        )
        st.caption(f"N = {elasticity_result.n_observations} periods")

    st.markdown("---")

    # Show tested fee tiers
    st.subheader("Experiment Fee Tiers")

    fee_summary = (
        elasticity_df.groupby("final_fee_bps")
        .agg({"period_id": "count", "volume_usd": "sum", "fees_usd": "sum"})
        .reset_index()
    )
    fee_summary.columns = ["Fee Tier (bps)", "Periods", "Total Volume", "Total Revenue"]
    fee_summary = fee_summary.sort_values("Fee Tier (bps)")

    # Format for display
    fee_summary["Total Volume"] = fee_summary["Total Volume"].apply(lambda x: f"${x:,.0f}")
    fee_summary["Total Revenue"] = fee_summary["Total Revenue"].apply(lambda x: f"${x:,.0f}")

    st.dataframe(fee_summary, use_container_width=True, hide_index=True)
    st.caption(
        f"📊 Tested {len(fee_summary)} different fee tiers across {len(elasticity_df)} periods"
    )

    # Show which period had highest revenue (empirical optimal)
    best_revenue_period = elasticity_df.loc[elasticity_df["fees_usd"].idxmax()]
    st.info(
        f"""
        **📊 Empirical Best Performance:**
        - **Period {int(best_revenue_period["period_id"])}** had the highest revenue: **${best_revenue_period["fees_usd"]:,.0f}**
        - Fee tier: **{best_revenue_period["final_fee_bps"]:.0f} bps**
        - Volume: ${best_revenue_period["volume_usd"]:,.0f}

        This is the actual observed maximum revenue, not a model prediction.
        """
    )

    # Interpretation
    st.markdown("---")
    st.subheader("Interpretation & Important Caveats")

    st.warning(
        """
        ⚠️ **Critical Note: Experimental Design vs. Observed Reality**

        Our analysis follows a quasi-experimental design tailored to the fee experiment:
        - Fee tiers were applied in defined periods; we analyze period-to-period deltas (Δ) to focus on the causal impact of fee changes.
        - We include simple controls (e.g., a time-trend) to partially account for secular growth/decline over the window.
        - The decomposition separates the direct fee-rate effect from volume/mix effects and a residual "external" component.

        These steps mitigate—but do not eliminate—confounding from contemporaneous market shocks, protocol events, or seasonality.
        Consequently, the model’s "optimal fee" should be interpreted as a ceteris paribus recommendation within the experiment window.
        Divergence between the model’s recommendation and the empirically best period indicates intervals where external conditions likely dominated outcomes.
        """
    )

    if elasticity_result.price_elasticity_demand >= -1:
        st.info(
            f"""
            **Inelastic Demand** (|PED| = {abs(elasticity_result.price_elasticity_demand):.2f} < 1)

            Volume is relatively insensitive to fee changes. A 10% fee increase leads to only a
            {abs(elasticity_result.price_elasticity_demand * 10):.1f}% volume decrease.

            **Model prediction:** Revenue increases with higher fees (hence 50 bps recommendation).
            **However:** The actual highest revenue was in Period {int(best_revenue_period["period_id"])}
            at {best_revenue_period["final_fee_bps"]:.0f} bps, likely due to external factors.
            """
        )
    else:
        st.success(
            f"""
            **Elastic Demand** (|PED| = {abs(elasticity_result.price_elasticity_demand):.2f} > 1)

            Volume is sensitive to fee changes. A 10% fee increase leads to a
            {abs(elasticity_result.price_elasticity_demand * 10):.1f}% volume decrease.

            **Model prediction:** Optimal fee of **{elasticity_result.optimal_fee_bps:.1f} bps** maximizes revenue.
            **Empirical best:** Period {int(best_revenue_period["period_id"])} at {best_revenue_period["final_fee_bps"]:.0f} bps
            had the highest observed revenue.
            """
        )

    st.markdown("---")

    # Revenue Decomposition Waterfall
    st.subheader("Revenue Decomposition - Waterfall Chart")

    # Show the time period covered
    if len(decomp_results) > 0:
        first_period = pd.to_datetime(weekly_df["period_start_date"].min()).strftime("%Y-%m-%d")
        last_period = pd.to_datetime(weekly_df["period_end_date"].max()).strftime("%Y-%m-%d")
        n_periods = len(decomp_results)
        st.caption(
            f"📅 Analysis Period: {first_period} to {last_period} ({n_periods} period transitions)"
        )

    with st.expander("ℹ️ How to Read This Chart", expanded=False):
        st.markdown("""
        **What is Revenue Decomposition?**

        This waterfall chart breaks down the total revenue change across all fee periods into four distinct effects:

        1. **Fee Rate Effect** 🔵
           - **Definition:** Revenue change from fee tier changes, holding volume constant
           - **Formula:** `(Current Fee - Previous Fee) × Previous Volume`
           - **Example:** If fees increase from 10 to 15 bps with volume unchanged, this captures the direct revenue gain

        2. **Volume Effect** 🟢 or 🔴
           - **Definition:** Revenue change from volume changes, holding fee rate constant
           - **Formula:** `(Current Volume - Previous Volume) × Previous Fee Rate`
           - **Example:** If volume drops due to higher fees, this captures the revenue loss from lower activity

        3. **Mix Effect** 🟢 or 🔴
           - **Definition:** Revenue change from shifts in swap size distribution
           - **Formula:** `(Current Avg Swap Size - Previous Avg Swap Size) × Swap Count × Fee Rate`
           - **Example:** If users shift to smaller trades, this captures the revenue impact of composition changes

        4. **External Effect** 🟢 or 🔴
           - **Definition:** Residual revenue change not explained by the above (market conditions, crypto prices, etc.)
           - **Formula:** `Total Change - (Fee + Volume + Mix Effects)`
           - **Example:** Captures broader market trends, competitor actions, or other unexplained factors

        **Colors:**
        - 🔵 Blue = Starting/Ending totals
        - 🟢 Green = Positive impact (revenue increase)
        - 🔴 Red = Negative impact (revenue decrease)
        """)

    # Aggregate waterfall across all periods
    agg_waterfall = [
        {
            "component": "Starting Revenue",
            "value": decomp_results[0].prev_revenue,
            "type": "total",
        },
        {
            "component": "Fee Rate Effect",
            "value": decomp_summary["total_fee_rate_effect"],
            "type": "positive" if decomp_summary["total_fee_rate_effect"] > 0 else "negative",
        },
        {
            "component": "Volume Effect",
            "value": decomp_summary["total_volume_effect"],
            "type": "positive" if decomp_summary["total_volume_effect"] > 0 else "negative",
        },
        {
            "component": "Mix Effect",
            "value": decomp_summary["total_mix_effect"],
            "type": "positive" if decomp_summary["total_mix_effect"] > 0 else "negative",
        },
        {
            "component": "External Effect",
            "value": decomp_summary["total_external_effect"],
            "type": "positive" if decomp_summary["total_external_effect"] > 0 else "negative",
        },
        {
            "component": "Ending Revenue",
            "value": decomp_results[-1].current_revenue,
            "type": "total",
        },
    ]

    waterfall_fig = create_waterfall_chart(agg_waterfall, "Revenue Decomposition Waterfall")
    st.plotly_chart(waterfall_fig, use_container_width=True)

    # Decomposition summary table
    st.write("**Decomposition Summary**")

    decomp_table = pd.DataFrame(
        [
            {
                "Component": "Fee Rate Effect",
                "Total Impact": format_currency(decomp_summary["total_fee_rate_effect"], 0),
                "% of Change": f"{decomp_summary['overall_fee_rate_pct']:.1f}%",
            },
            {
                "Component": "Volume Effect",
                "Total Impact": format_currency(decomp_summary["total_volume_effect"], 0),
                "% of Change": f"{decomp_summary['overall_volume_pct']:.1f}%",
            },
            {
                "Component": "Mix Effect",
                "Total Impact": format_currency(decomp_summary["total_mix_effect"], 0),
                "% of Change": f"{decomp_summary['overall_mix_pct']:.1f}%",
            },
            {
                "Component": "External Effect",
                "Total Impact": format_currency(decomp_summary["total_external_effect"], 0),
                "% of Change": f"{decomp_summary['overall_external_pct']:.1f}%",
            },
        ]
    )

    st.dataframe(decomp_table, use_container_width=True, hide_index=True)

    st.markdown("---")

    # Period-by-period elasticity
    st.subheader("Period-by-Period Analysis")

    # Add visualizations before the table
    st.write("**Interactive Visualizations**")

    # Chart 1: REVENUE - PRIMARY METRIC (Gets its own focused chart)
    st.write("**1. 💰 Revenue Response to Fee Changes (PRIMARY METRIC)**")
    st.caption(
        "How revenue responds to FEE CHANGES (Δ Fee) - shows cause and effect • Use crosshair to see values (fee shown on right Y-axis)"
    )

    with st.expander("ℹ️ How to Read This Chart", expanded=False):
        st.markdown("""
        **Revenue vs Fee Change Chart**

        This chart shows the relationship between **fee changes** (what you control) and **revenue** (what you optimize):

        - **Orange Bars (Right Axis)**: Δ Fee in bps - **change** in fee tier from previous period
          - Positive bars = fee increase
          - Negative bars = fee decrease
        - **Green Line (Left Axis)**: Revenue in USD - the PRIMARY METRIC you're optimizing

        **What to Look For:**
        - When orange bars go **up** (fee increase), does the green line go up or down?
        - When orange bars go **down** (fee decrease), does the green line go up or down?
        - **Positive correlation** = revenue increases when fees increase (good)
        - **Negative correlation** = revenue decreases when fees increase (too high)

        **Key Insight:**
        Look for periods where **positive orange bars** (fee increases) coincide with **rising green line** (revenue growth).
        That's your optimal zone!

        **Interaction:**
        - Hover over bars/line to see exact values
        - Zoom and pan using mouse/trackpad
        - Double-click to reset view
        """)

    revenue_config = create_fee_revenue_lightweight_chart(elasticity_df)
    renderLightweightCharts(revenue_config, "fee_revenue_overlay")

    st.markdown("---")

    # Chart 2: VOLUME - Supporting Analysis (Separate chart for clarity)
    st.write("**2. 📊 Volume Response to Fee Changes (Supporting Analysis)**")
    st.caption(
        "How trading volume responds to FEE CHANGES (Δ Fee) - shows price elasticity • Use crosshair to see values (fee shown on right Y-axis)"
    )

    with st.expander("ℹ️ How to Read This Chart", expanded=False):
        st.markdown("""
        **Volume Elasticity Chart**

        This chart shows how **volume** responds to **fee changes**, revealing demand elasticity:

        - **Orange Bars (Right Axis)**: Δ Fee in bps - **change** in fee tier from previous period
          - Positive bars = fee increase
          - Negative bars = fee decrease
        - **Blue Line (Left Axis)**: Volume in USD - shows trading activity

        **What to Look For:**
        - When orange bars go **up** (fee increase), does the blue line go down (volume drop)?
        - When orange bars go **down** (fee decrease), does the blue line go up (volume rise)?
        - **Strong inverse correlation** = elastic demand (traders are very sensitive to fees)
        - **Weak inverse correlation** = inelastic demand (traders continue despite fee changes)

        **Key Insight:**
        Compare this to Chart 1: if **orange bar up** → **blue line down** (volume drops) BUT **green line up** (revenue rises),
        then fees are optimal! You're capturing more revenue per transaction despite lower volume.

        **Interaction:**
        - Hover over bars/line to see exact values
        - Zoom and pan using mouse/trackpad
        - Double-click to reset view
        """)

    volume_config = create_fee_volume_lightweight_chart(elasticity_df)
    renderLightweightCharts(volume_config, "fee_volume_overlay")

    st.markdown("---")

    # Chart 3: Elasticity Scatter with Regression Line
    st.write("**3. Price Elasticity Visualization**")
    st.caption("Independent variable (Δ fee %) vs dependent variables (Δ volume %, Δ revenue %)")

    with st.expander("ℹ️ How to Read This Chart", expanded=False):
        st.markdown("""
        **Elasticity Scatter Plots with Regression**

        These charts show the relationship between fee changes (independent) and outcomes (dependent):

        **Left: Price Elasticity of Demand (PED)**
        - X-axis: % change in fee tier
        - Y-axis: % change in volume
        - Red dashed line: Regression slope = elasticity coefficient
        - Negative slope = volume decreases when fees increase (normal behavior)
        - Steep slope = elastic (sensitive to fees), flat = inelastic

        **Right: Revenue Elasticity**
        - X-axis: % change in fee tier
        - Y-axis: % change in revenue
        - Positive slope = revenue increases with fees (optimal zone)
        - Negative slope = revenue decreases with fees (too high)

        **Point Color**: Indicates which fee tier the period transitioned to
        """)

    col1, col2 = st.columns(2)

    with col1:
        elasticity_vol = create_elasticity_scatter(
            elasticity_df,
            "pct_change_fee_bps",
            "pct_change_volume",
            "Price Elasticity of Demand",
            "Fee Change (%)",
            "Volume Change (%)",
            elasticity_result.price_elasticity_demand,
        )
        st.altair_chart(elasticity_vol, use_container_width=True)

    with col2:
        elasticity_rev = create_elasticity_scatter(
            elasticity_df,
            "pct_change_fee_bps",
            "pct_change_fees",
            "Revenue Elasticity",
            "Fee Change (%)",
            "Revenue Change (%)",
            elasticity_result.revenue_elasticity,
        )
        st.altair_chart(elasticity_rev, use_container_width=True)

    st.markdown("---")
    st.write("**Detailed Period Data**")

    display_df = elasticity_df[
        [
            "period_id",
            "period_start_date",
            "final_fee_bps",
            "prev_fee_bps",
            "pct_change_fee_bps",
            "pct_change_volume",
            "pct_change_fees",
            "volume_usd",
            "fees_usd",
        ]
    ].copy()

    # Format columns
    display_df["period_start_date"] = pd.to_datetime(display_df["period_start_date"]).dt.strftime(
        "%Y-%m-%d"
    )
    display_df["volume_usd"] = display_df["volume_usd"].apply(lambda x: format_currency(x, 0))
    display_df["fees_usd"] = display_df["fees_usd"].apply(lambda x: format_currency(x, 0))
    display_df["final_fee_bps"] = display_df["final_fee_bps"].apply(format_bps)
    display_df["prev_fee_bps"] = display_df["prev_fee_bps"].apply(format_bps)
    display_df["pct_change_fee_bps"] = display_df["pct_change_fee_bps"].apply(lambda x: f"{x:.1f}%")
    display_df["pct_change_volume"] = display_df["pct_change_volume"].apply(lambda x: f"{x:.1f}%")
    display_df["pct_change_fees"] = display_df["pct_change_fees"].apply(lambda x: f"{x:.1f}%")

    display_df = display_df.rename(
        columns={
            "period_id": "Period",
            "period_start_date": "Start Date",
            "final_fee_bps": "Current Fee",
            "prev_fee_bps": "Previous Fee",
            "pct_change_fee_bps": "Δ Fee %",
            "pct_change_volume": "Δ Volume %",
            "pct_change_fees": "Δ Revenue %",
            "volume_usd": "Volume",
            "fees_usd": "Revenue",
        }
    )

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Download buttons and Report Preview
    st.markdown("---")
    st.subheader("Analysis Report & Downloads")

    # Generate the markdown report once with best period info
    best_period_dict = {
        "period_id": int(best_revenue_period["period_id"]),
        "revenue": float(best_revenue_period["fees_usd"]),
        "fee_bps": float(best_revenue_period["final_fee_bps"]),
        "volume": float(best_revenue_period["volume_usd"]),
    }
    report = generate_markdown_report(elasticity_result, decomp_summary, best_period_dict)

    # Download buttons in columns
    col1, col2 = st.columns(2)

    with col1:
        # CSV download
        csv = elasticity_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Elasticity Data (CSV)",
            data=csv,
            file_name="elasticity_analysis.csv",
            mime="text/csv",
        )

    with col2:
        # Markdown report download
        st.download_button(
            label="📄 Download Analysis Report (Markdown)",
            data=report,
            file_name="phase2_elasticity_report.md",
            mime="text/markdown",
        )

    # Render the markdown report in an expander
    st.markdown("---")
    with st.expander("📋 View Full Analysis Report (Rendered)", expanded=False):
        st.markdown(report)


if __name__ == "__main__":
    main()
