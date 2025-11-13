"""
Phase 3: User Analysis - Cohorts, Segmentation, and LTV
"""

import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

# Add src and components to path
src_path = Path(__file__).parent.parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

sys.path.insert(0, str(Path(__file__).parent.parent))
from components.formatting import format_currency, format_number

st.set_page_config(page_title="Phase 3: User Analysis", page_icon="👥", layout="wide")


@st.cache_data(show_spinner=False)
def load_csv_data():
    """Load all Phase 3 CSV outputs."""
    outputs_dir = Path(__file__).parent.parent.parent.parent / "outputs"

    data = {}
    try:
        data["cohorts"] = pd.read_csv(outputs_dir / "user_cohorts.csv")
        data["retention"] = pd.read_csv(outputs_dir / "retention_by_fee.csv")
        data["acquisition"] = pd.read_csv(outputs_dir / "acquisition_by_period.csv")
        data["segments"] = pd.read_csv(outputs_dir / "segment_metrics.csv")
        data["segment_summary"] = pd.read_csv(outputs_dir / "segment_summary.csv")
        data["ltv"] = pd.read_csv(outputs_dir / "ltv_by_fee.csv")
    except FileNotFoundError as e:
        st.error(f"Data files not found. Please run Phase 3 analysis scripts first: {e}")
        st.stop()

    return data


def main():
    st.title("👥 Phase 3: User Behavior & Segmentation")
    st.caption(
        "Cohort analysis, trade-size segmentation, and lifetime value by acquisition fee tier"
    )

    # Load data
    data = load_csv_data()

    cohorts_df = data["cohorts"]
    retention_df = data["retention"]
    acquisition_df = data["acquisition"]
    segments_df = data["segments"]
    segment_summary_df = data["segment_summary"]
    ltv_df = data["ltv"]

    # === KPI Cards ===
    st.subheader("📊 Key Metrics")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_users = len(cohorts_df)
        st.metric("Total Users", format_number(total_users))

    with col2:
        new_users = acquisition_df["new_users"].sum()
        st.metric("New Users (All Periods)", format_number(new_users))

    with col3:
        # Retention at k=1 (average across fee tiers)
        k1_retention = retention_df[retention_df["k"] == 1]["retention_rate"].mean()
        st.metric("Avg 1-Week Retention", f"{k1_retention*100:.1f}%")

    with col4:
        # Whale share of fees
        whale_share = segment_summary_df[segment_summary_df["segment"] == "whale"][
            "overall_fees_share"
        ].iloc[0]
        st.metric("Whale Fee Share", f"{whale_share*100:.1f}%")

    st.markdown("---")

    # === Tab Navigation ===
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📈 Cohorts & Retention", "💰 Trade-Size Segments", "🎯 Lifetime Value", "📥 Downloads"]
    )

    # === TAB 1: Cohorts & Retention ===
    with tab1:
        st.subheader("User Acquisition by Fee Tier")

        # Acquisition by period
        acq_chart = (
            alt.Chart(acquisition_df)
            .mark_bar()
            .encode(
                x=alt.X("period_start_date:T", title="Period Start"),
                y=alt.Y("new_users:Q", title="New Users"),
                color=alt.Color(
                    "final_fee_bps:N", title="Fee Tier (bps)", scale=alt.Scale(scheme="category10")
                ),
                tooltip=[
                    alt.Tooltip("period_id:N", title="Period"),
                    alt.Tooltip("final_fee_bps:Q", title="Fee (bps)"),
                    alt.Tooltip("new_users:Q", title="New Users", format=","),
                    alt.Tooltip("returning_users:Q", title="Returning Users", format=","),
                ],
            )
            .properties(height=400, title="New User Acquisition by Period and Fee Tier")
        )

        st.altair_chart(acq_chart, use_container_width=True)

        st.markdown("---")

        # Retention curves
        st.subheader("Retention Curves by Acquisition Fee Tier")

        retention_chart = (
            alt.Chart(retention_df)
            .mark_line(point=True)
            .encode(
                x=alt.X("k:Q", title="Weeks Since Acquisition", scale=alt.Scale(domain=[1, 12])),
                y=alt.Y("retention_rate:Q", title="Retention Rate", axis=alt.Axis(format="%")),
                color=alt.Color(
                    "acquisition_fee_bps:N",
                    title="Acquisition Fee (bps)",
                    scale=alt.Scale(scheme="category10"),
                ),
                tooltip=[
                    alt.Tooltip("acquisition_fee_bps:Q", title="Acquisition Fee (bps)"),
                    alt.Tooltip("k:Q", title="Weeks"),
                    alt.Tooltip("retention_rate:Q", title="Retention", format=".2%"),
                    alt.Tooltip("base_users:Q", title="Cohort Size", format=","),
                ],
            )
            .properties(height=400, title="User Retention by Acquisition Fee Tier")
        )

        st.altair_chart(retention_chart, use_container_width=True)

        # Cohort distribution
        st.markdown("---")
        st.subheader("Users by Acquisition Fee Tier")

        cohort_dist = cohorts_df.groupby("first_seen_fee_bps").size().reset_index(name="user_count")
        cohort_dist["pct"] = cohort_dist["user_count"] / cohort_dist["user_count"].sum() * 100

        col1, col2 = st.columns([2, 1])

        with col1:
            dist_chart = (
                alt.Chart(cohort_dist)
                .mark_bar()
                .encode(
                    x=alt.X("first_seen_fee_bps:N", title="Acquisition Fee (bps)"),
                    y=alt.Y("user_count:Q", title="User Count"),
                    color=alt.Color(
                        "first_seen_fee_bps:N", legend=None, scale=alt.Scale(scheme="category10")
                    ),
                    tooltip=[
                        alt.Tooltip("first_seen_fee_bps:Q", title="Fee (bps)"),
                        alt.Tooltip("user_count:Q", title="Users", format=","),
                        alt.Tooltip("pct:Q", title="Share", format=".1f"),
                    ],
                )
                .properties(height=300)
            )

            st.altair_chart(dist_chart, use_container_width=True)

        with col2:
            st.dataframe(
                cohort_dist.rename(
                    columns={
                        "first_seen_fee_bps": "Fee (bps)",
                        "user_count": "Users",
                        "pct": "Share (%)",
                    }
                ).style.format({"Share (%)": "{:.1f}%", "Users": "{:,}"}),
                hide_index=True,
                use_container_width=True,
            )

    # === TAB 2: Trade-Size Segments ===
    with tab2:
        st.subheader("Trade-Size Segmentation")

        # Segment summary
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Volume Contribution by Segment**")
            vol_chart = (
                alt.Chart(segment_summary_df)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "segment:N",
                        title="Segment",
                        sort=["micro", "small", "medium", "large", "whale"],
                    ),
                    y=alt.Y(
                        "overall_volume_share:Q", title="Volume Share", axis=alt.Axis(format="%")
                    ),
                    color=alt.Color("segment:N", legend=None, scale=alt.Scale(scheme="tableau10")),
                    tooltip=[
                        alt.Tooltip("segment:N", title="Segment"),
                        alt.Tooltip("overall_volume_share:Q", title="Volume Share", format=".1%"),
                        alt.Tooltip("volume_usd:Q", title="Total Volume", format="$,.0f"),
                    ],
                )
                .properties(height=300)
            )

            st.altair_chart(vol_chart, use_container_width=True)

        with col2:
            st.markdown("**Fee Contribution by Segment**")
            fee_chart = (
                alt.Chart(segment_summary_df)
                .mark_bar()
                .encode(
                    x=alt.X(
                        "segment:N",
                        title="Segment",
                        sort=["micro", "small", "medium", "large", "whale"],
                    ),
                    y=alt.Y("overall_fees_share:Q", title="Fee Share", axis=alt.Axis(format="%")),
                    color=alt.Color("segment:N", legend=None, scale=alt.Scale(scheme="tableau10")),
                    tooltip=[
                        alt.Tooltip("segment:N", title="Segment"),
                        alt.Tooltip("overall_fees_share:Q", title="Fee Share", format=".1%"),
                        alt.Tooltip("fees_usd:Q", title="Total Fees", format="$,.0f"),
                    ],
                )
                .properties(height=300)
            )

            st.altair_chart(fee_chart, use_container_width=True)

        st.markdown("---")

        # Segment metrics table
        st.subheader("Segment Metrics Summary")

        summary_display = segment_summary_df.copy()
        summary_display["volume_usd"] = summary_display["volume_usd"].apply(
            lambda x: format_currency(x, 0)
        )
        summary_display["fees_usd"] = summary_display["fees_usd"].apply(
            lambda x: format_currency(x, 0)
        )
        summary_display["avg_fees_paid_usd"] = summary_display["avg_fees_paid_usd"].apply(
            lambda x: format_currency(x, 2)
        )
        summary_display["overall_volume_share"] = summary_display["overall_volume_share"].apply(
            lambda x: f"{x*100:.1f}%"
        )
        summary_display["overall_fees_share"] = summary_display["overall_fees_share"].apply(
            lambda x: f"{x*100:.1f}%"
        )
        summary_display["retention_rate"] = summary_display["retention_rate"].apply(
            lambda x: f"{x*100:.1f}%" if pd.notna(x) else "N/A"
        )

        st.dataframe(
            summary_display[
                [
                    "segment",
                    "user_count",
                    "volume_usd",
                    "fees_usd",
                    "overall_volume_share",
                    "overall_fees_share",
                    "avg_fees_paid_usd",
                    "retention_rate",
                ]
            ].rename(
                columns={
                    "segment": "Segment",
                    "user_count": "Users",
                    "volume_usd": "Total Volume",
                    "fees_usd": "Total Fees",
                    "overall_volume_share": "Vol %",
                    "overall_fees_share": "Fee %",
                    "avg_fees_paid_usd": "Avg Fee/User",
                    "retention_rate": "Retention",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )

    # === TAB 3: Lifetime Value ===
    with tab3:
        st.subheader("Lifetime Value by Acquisition Fee Tier")

        # LTV comparison at H=12, r=0%
        ltv_12_0 = ltv_df[(ltv_df["horizon"] == 12) & (ltv_df["discount_rate"] == 0.0)]

        col1, col2 = st.columns([2, 1])

        with col1:
            ltv_chart = (
                alt.Chart(ltv_12_0)
                .mark_bar()
                .encode(
                    x=alt.X("acquisition_fee_bps:N", title="Acquisition Fee (bps)"),
                    y=alt.Y("ltv_mean:Q", title="Average LTV (USD)"),
                    color=alt.Color(
                        "acquisition_fee_bps:N", legend=None, scale=alt.Scale(scheme="category10")
                    ),
                    tooltip=[
                        alt.Tooltip("acquisition_fee_bps:Q", title="Fee (bps)"),
                        alt.Tooltip("ltv_mean:Q", title="Avg LTV", format="$,.2f"),
                        alt.Tooltip("ltv_median:Q", title="Median LTV", format="$,.2f"),
                        alt.Tooltip("user_count:Q", title="Users", format=","),
                    ],
                )
                .properties(
                    height=400, title="Average LTV by Acquisition Fee (12 weeks, 0% discount)"
                )
            )

            st.altair_chart(ltv_chart, use_container_width=True)

        with col2:
            st.markdown("**LTV Summary (12 weeks)**")
            ltv_display = ltv_12_0.copy()
            ltv_display["ltv_mean"] = ltv_display["ltv_mean"].apply(lambda x: format_currency(x, 2))
            ltv_display["ltv_median"] = ltv_display["ltv_median"].apply(
                lambda x: format_currency(x, 2)
            )

            st.dataframe(
                ltv_display[["acquisition_fee_bps", "ltv_mean", "ltv_median", "user_count"]].rename(
                    columns={
                        "acquisition_fee_bps": "Fee (bps)",
                        "ltv_mean": "Avg LTV",
                        "ltv_median": "Median LTV",
                        "user_count": "Users",
                    }
                ),
                hide_index=True,
                use_container_width=True,
            )

        st.markdown("---")

        # LTV sensitivity
        st.subheader("LTV Sensitivity Analysis")

        # Pivot for horizon comparison
        ltv_pivot = (
            ltv_df[ltv_df["discount_rate"] == 0.0]
            .pivot(index="acquisition_fee_bps", columns="horizon", values="ltv_mean")
            .reset_index()
        )

        st.markdown("**LTV by Horizon (0% discount)**")
        st.dataframe(
            ltv_pivot.style.format(
                {col: "${:,.2f}" for col in ltv_pivot.columns if col != "acquisition_fee_bps"}
            ).format({"acquisition_fee_bps": "{:.0f} bps"}),
            hide_index=True,
            use_container_width=True,
        )

    # === TAB 4: Downloads ===
    with tab4:
        st.subheader("📥 Download Analysis Data")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Cohort & Retention Data**")

            st.download_button(
                label="Download Cohort Table",
                data=cohorts_df.to_csv(index=False),
                file_name="user_cohorts.csv",
                mime="text/csv",
            )

            st.download_button(
                label="Download Retention by Fee",
                data=retention_df.to_csv(index=False),
                file_name="retention_by_fee.csv",
                mime="text/csv",
            )

            st.download_button(
                label="Download Acquisition by Period",
                data=acquisition_df.to_csv(index=False),
                file_name="acquisition_by_period.csv",
                mime="text/csv",
            )

        with col2:
            st.markdown("**Segmentation & LTV Data**")

            st.download_button(
                label="Download Segment Metrics",
                data=segments_df.to_csv(index=False),
                file_name="segment_metrics.csv",
                mime="text/csv",
            )

            st.download_button(
                label="Download Segment Summary",
                data=segment_summary_df.to_csv(index=False),
                file_name="segment_summary.csv",
                mime="text/csv",
            )

            st.download_button(
                label="Download LTV by Fee",
                data=ltv_df.to_csv(index=False),
                file_name="ltv_by_fee.csv",
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
