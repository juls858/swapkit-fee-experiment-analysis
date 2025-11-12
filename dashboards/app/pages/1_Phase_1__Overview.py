import sys
from pathlib import Path

import pandas as pd
import streamlit as st
from snowflake.snowpark import Session

# Add src to path for imports
src_path = Path(__file__).parent.parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session as _get_session


@st.cache_resource(show_spinner=False)
def get_snowpark_session() -> Session:
    """Get cached Snowpark session for Streamlit dashboard."""
    return _get_session()


@st.cache_data(show_spinner=False, ttl=60)
def load_weekly_summary(_session: Session) -> pd.DataFrame:
    sql = 'SELECT * FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL'
    df = _session.sql(sql).to_pandas()
    # Normalize to lowercase
    df.columns = df.columns.str.lower()
    return df


@st.cache_data(show_spinner=False)
def load_manual_periods(_session: Session) -> pd.DataFrame | None:
    try:
        sql = 'SELECT * FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL'
        df = _session.sql(sql).to_pandas()
        df.columns = df.columns.str.lower()
        return df
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def load_period_revenue_ci(_session: Session) -> pd.DataFrame | None:
    try:
        sql = 'SELECT * FROM "9R".FEE_EXPERIMENT.V_PERIOD_REVENUE_CI'
        df = _session.sql(sql).to_pandas()
        df.columns = df.columns.str.lower()
        return df
    except Exception:
        return None


def compute_date_bounds(df: pd.DataFrame) -> tuple[pd.Timestamp, pd.Timestamp]:
    start = pd.to_datetime(df["period_start_date"].min()).tz_localize(None)
    end = pd.to_datetime(df["period_end_date"].max()).tz_localize(None)
    return start, end


def apply_filters(
    df: pd.DataFrame,
    start_date: pd.Timestamp | None,
    end_date: pd.Timestamp | None,
    fee_bps: list | None,
    source: str | None,
) -> pd.DataFrame:
    out = df.copy()
    if source:
        out = out[out["period_source"] == source]
    if start_date is not None:
        out = out[pd.to_datetime(out["period_start_date"]) >= pd.to_datetime(start_date)]
    if end_date is not None:
        out = out[pd.to_datetime(out["period_end_date"]) <= pd.to_datetime(end_date)]
    if fee_bps:
        out = out[out["final_fee_bps"].isin(fee_bps)]
    return out.sort_values("period_start_date")


@st.cache_data(show_spinner=False)
def load_validation_period_level(_session: Session) -> pd.DataFrame | None:
    """Period-level validation comparing intended vs realized fee tiers."""
    sql = (
        "WITH manual AS (\n"
        "    SELECT period_start_date, period_end_date, intended_fee_bps\n"
        '    FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL\n'
        "), realized AS (\n"
        "    SELECT period_id, period_start_date, period_end_date, days_in_period,\n"
        "           final_fee_bps, period_source, swaps_count, volume_usd, fees_usd, realized_fee_bps\n"
        '    FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL\n'
        "    WHERE period_source = 'manual'\n"
        "), joined AS (\n"
        "    SELECT r.period_id, r.period_start_date, r.period_end_date, r.days_in_period,\n"
        "           m.intended_fee_bps, r.realized_fee_bps,\n"
        "           ROUND(r.realized_fee_bps - m.intended_fee_bps, 2) AS delta_bps,\n"
        "           r.swaps_count, r.volume_usd, r.fees_usd\n"
        "    FROM realized r\n"
        "    LEFT JOIN manual m\n"
        "      ON r.period_start_date = m.period_start_date\n"
        "     AND r.period_end_date   = m.period_end_date\n"
        ")\n"
        "SELECT period_id, period_start_date, period_end_date, days_in_period, intended_fee_bps,\n"
        "       ROUND(realized_fee_bps, 2) AS realized_fee_bps, delta_bps,\n"
        "       CASE WHEN ABS(delta_bps) <= 1 THEN 'PASS' ELSE 'FAIL' END AS within_1bp,\n"
        "       swaps_count, volume_usd, fees_usd\n"
        "FROM joined\n"
        "ORDER BY period_start_date"
    )
    try:
        df = _session.sql(sql).to_pandas()
        df.columns = df.columns.str.lower()
        return df
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def load_validation_overall(_session: Session) -> pd.DataFrame | None:
    sql = (
        "WITH per AS (\n"
        "    SELECT CASE WHEN ABS(realized_fee_bps - intended_fee_bps) <= 1 THEN 1 ELSE 0 END AS pass_flag\n"
        "    FROM (\n"
        "        SELECT m.intended_fee_bps, r.realized_fee_bps\n"
        '        FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL m\n'
        '        LEFT JOIN "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL r\n'
        "          ON r.period_source = 'manual'\n"
        "         AND r.period_start_date = m.period_start_date\n"
        "         AND r.period_end_date   = m.period_end_date\n"
        "    ) x\n"
        ")\n"
        "SELECT SUM(pass_flag) AS periods_passing, COUNT(*) AS periods_total,\n"
        "       CASE WHEN SUM(pass_flag) = COUNT(*) THEN 'PASS' ELSE 'REVIEW' END AS overall\n"
        "FROM per"
    )
    try:
        df = _session.sql(sql).to_pandas()
        df.columns = df.columns.str.lower()
        return df
    except Exception:
        return None


def format_number(value: float, decimal_places: int = 0) -> str:
    """Format large numbers with K/M/B suffixes for readability."""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"${value / 1_000_000_000:,.{decimal_places}f}B"
    elif abs_value >= 1_000_000:
        return f"${value / 1_000_000:,.{decimal_places}f}M"
    elif abs_value >= 1_000:
        return f"${value / 1_000:,.{decimal_places}f}K"
    else:
        return f"${value:,.{decimal_places}f}"


def kpi(title: str, value: float | None, fmt: str = "{:,.2f}", use_short: bool = False) -> None:
    if value is None:
        st.metric(title, "–")
    elif use_short:
        st.metric(title, format_number(value, decimal_places=2))
    else:
        st.metric(title, fmt.format(value))


def main() -> None:
    st.set_page_config(
        page_title="Phase 1: Data Foundation & Validation", page_icon="📈", layout="wide"
    )
    st.title("Phase 1: Data Foundation & Validation")
    st.caption('Data source: "9R".FEE_EXPERIMENT (validated)')

    with st.spinner("Connecting to Snowflake…"):
        session = get_snowpark_session()

    # Load base data
    weekly = load_weekly_summary(session)
    ci_df = load_period_revenue_ci(session)

    if weekly.empty:
        st.warning("No data returned from V_WEEKLY_SUMMARY_FINAL.")
        return

    min_date, max_date = compute_date_bounds(weekly)
    unique_bps = sorted(pd.Series(weekly["final_fee_bps"].unique()).dropna().tolist())

    # Sidebar controls
    with st.sidebar:
        st.header("Filters")
        source_choice = st.selectbox(
            "Period source",
            options=["manual", "all"],
            index=0,
            help="Use 'manual' to match Phase 1 validation scope",
        )
        date_range = st.date_input(
            "Date range",
            value=(min_date.date(), max_date.date()),
            min_value=min_date.date(),
            max_value=max_date.date(),
        )
        start_sel = (
            pd.to_datetime(date_range[0]) if isinstance(date_range, list | tuple) else min_date
        )
        end_sel = (
            pd.to_datetime(date_range[1]) if isinstance(date_range, list | tuple) else max_date
        )

        fee_sel = st.multiselect("Fee tiers (bps)", options=unique_bps, default=unique_bps)

        show_ci = st.checkbox("Show revenue confidence bands (if available)", value=False)

    # Apply filters
    selected_source = None if source_choice == "all" else "manual"
    filtered = apply_filters(weekly, start_sel, end_sel, fee_sel, selected_source)

    # KPIs
    kpi_cols = st.columns(6)
    with kpi_cols[0]:
        kpi("Total volume", float(filtered["volume_usd"].sum()), use_short=True)
    with kpi_cols[1]:
        kpi("Total fees", float(filtered["fees_usd"].sum()), use_short=True)
    with kpi_cols[2]:
        kpi("Swaps", float(filtered["swaps_count"].sum()), fmt="{:,.0f}")
    with kpi_cols[3]:
        kpi("Unique swappers", float(filtered["unique_swappers"].sum()), fmt="{:,.0f}")
    with kpi_cols[4]:
        kpi("Avg swap size", float(filtered["avg_swap_size_usd"].mean()), use_short=True)
    with kpi_cols[5]:
        kpi("Realized fee (bps)", float(filtered["realized_fee_bps"].mean()), fmt="{:.2f}")

    # Charts
    import altair as alt  # local import for faster cold start

    # Keep timestamps for segmentation charts
    filtered["period_start_date"] = pd.to_datetime(filtered["period_start_date"]).dt.tz_localize(
        None
    )
    filtered["period_end_date"] = pd.to_datetime(filtered["period_end_date"]).dt.tz_localize(None)

    st.subheader("Revenue and Volume by Fee Tier")
    c1, c2 = st.columns(2)
    with c1:
        fees_rect = (
            alt.Chart(filtered)
            .transform_calculate(zero="0")
            .mark_rect(opacity=0.25)
            .encode(
                x=alt.X("period_start_date:T", title="Period Start Date"),
                x2=alt.X2("period_end_date:T"),
                y=alt.Y(
                    "zero:Q",
                    title="Fees (millions)",
                    axis=alt.Axis(
                        format="$.1f", labelExpr="datum.value / 1000000 + 'M'", grid=True
                    ),
                ),
                y2=alt.Y2("fees_usd:Q"),
                color=alt.Color(
                    "final_fee_bps:N", title="Fee Tier (bps)", scale=alt.Scale(scheme="category10")
                ),
                detail="period_id:N",
            )
        )
        fees_rule = (
            alt.Chart(filtered)
            .mark_rule(size=6)
            .encode(
                x=alt.X("period_start_date:T", title="Period Start Date"),
                x2=alt.X2("period_end_date:T"),
                y=alt.Y(
                    "fees_usd:Q",
                    title="Fees (millions)",
                    axis=alt.Axis(
                        format="$.1f", labelExpr="datum.value / 1000000 + 'M'", grid=True
                    ),
                ),
                color=alt.Color(
                    "final_fee_bps:N", title="Fee Tier (bps)", scale=alt.Scale(scheme="category10")
                ),
                detail="period_id:N",
                tooltip=[
                    alt.Tooltip("period_start_date", title="Start", format="%Y-%m-%d %H:%M"),
                    alt.Tooltip("period_end_date", title="End", format="%Y-%m-%d %H:%M"),
                    alt.Tooltip("final_fee_bps", title="Fee bps", format=".1f"),
                    alt.Tooltip("fees_usd", title="Fees", format="$,.0f"),
                ],
            )
            .properties(height=350)
        )
        st.altair_chart((fees_rect + fees_rule).interactive(), use_container_width=True)
    with c2:
        vol_rect = (
            alt.Chart(filtered)
            .transform_calculate(zero="0")
            .mark_rect(opacity=0.25)
            .encode(
                x="period_start_date:T",
                x2="period_end_date:T",
                y=alt.Y(
                    "zero:Q",
                    title="Volume (billions)",
                    axis=alt.Axis(
                        format="$.2f", labelExpr="datum.value / 1000000000 + 'B'", grid=True
                    ),
                ),
                y2=alt.Y2("volume_usd:Q"),
                color=alt.Color(
                    "final_fee_bps:N", title="Fee Tier (bps)", scale=alt.Scale(scheme="category10")
                ),
                detail="period_id:N",
            )
        )
        vol_rule = (
            alt.Chart(filtered)
            .mark_rule(size=6)
            .encode(
                x="period_start_date:T",
                x2="period_end_date:T",
                y=alt.Y(
                    "volume_usd:Q",
                    title="Volume (billions)",
                    axis=alt.Axis(
                        format="$.2f", labelExpr="datum.value / 1000000000 + 'B'", grid=True
                    ),
                ),
                color=alt.Color(
                    "final_fee_bps:N", title="Fee Tier (bps)", scale=alt.Scale(scheme="category10")
                ),
                detail="period_id:N",
                tooltip=[
                    alt.Tooltip("period_start_date", title="Start", format="%Y-%m-%d %H:%M"),
                    alt.Tooltip("period_end_date", title="End", format="%Y-%m-%d %H:%M"),
                    alt.Tooltip("final_fee_bps", title="Fee bps", format=".1f"),
                    alt.Tooltip("volume_usd", title="Volume", format="$,.0f"),
                ],
            )
            .properties(height=350)
        )
        st.altair_chart((vol_rect + vol_rule).interactive(), use_container_width=True)

    # Optional CI bands (if provided)
    if show_ci and ci_df is not None and not ci_df.empty:
        st.subheader("Revenue confidence intervals (95%)")
        ci = ci_df.copy()
        ci["period_start_date"] = pd.to_datetime(ci["period_start_date"]).dt.date
        base = alt.Chart(ci).encode(x=alt.X("period_start_date:T", title="Period start"))
        band = base.mark_area(opacity=0.2, color="#1f77b4").encode(
            y=alt.Y(
                "mean_weekly_fees_lo95:Q",
                title="Fees (millions)",
                axis=alt.Axis(format="$.1f", labelExpr="datum.value / 1000000 + 'M'"),
            ),
            y2="mean_weekly_fees_hi95:Q",
        )
        mean_line = base.mark_line(color="#1f77b4").encode(y="mean_weekly_fees:Q")
        st.altair_chart((band + mean_line).interactive(), use_container_width=True)

    # Revenue per swap/user over time with fee-colored segments and fee in tooltips
    st.subheader("Revenue metrics over time")
    c3, c4 = st.columns(2)
    with c3:
        # Revert to bar-style (rect + rule) segments colored by fee
        rps_rect = (
            alt.Chart(filtered)
            .transform_calculate(zero="0")
            .mark_rect(opacity=0.2)
            .encode(
                x=alt.X("period_start_date:T", title="Period Start"),
                x2=alt.X2("period_end_date:T"),
                y=alt.Y(
                    "zero:Q",
                    title="Revenue per Swap (USD)",
                    axis=alt.Axis(format="$.2f", grid=True),
                ),
                y2=alt.Y2("revenue_per_swap_usd:Q"),
                color=alt.Color(
                    "final_fee_bps:N",
                    title="Fee Tier (bps)",
                    scale=alt.Scale(scheme="category10", domain=unique_bps),
                ),
                detail="period_id:N",
            )
        )
        rps_rule = (
            alt.Chart(filtered)
            .mark_rule(size=6)
            .encode(
                x=alt.X("period_start_date:T", title="Period Start"),
                x2=alt.X2("period_end_date:T"),
                y=alt.Y(
                    "revenue_per_swap_usd:Q",
                    title="Revenue per Swap (USD)",
                    axis=alt.Axis(format="$.2f", grid=True),
                ),
                color=alt.Color(
                    "final_fee_bps:N",
                    title="Fee Tier (bps)",
                    scale=alt.Scale(scheme="category10", domain=unique_bps),
                ),
                detail="period_id:N",
                tooltip=[
                    alt.Tooltip("period_start_date", title="Start", format="%Y-%m-%d"),
                    alt.Tooltip("period_end_date", title="End", format="%Y-%m-%d"),
                    alt.Tooltip("final_fee_bps", title="Fee bps", format=".1f"),
                    alt.Tooltip("revenue_per_swap_usd", title="Rev/Swap", format="$.2f"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart((rps_rect + rps_rule).interactive(), use_container_width=True)
    with c4:
        rpu_rect = (
            alt.Chart(filtered)
            .transform_calculate(zero="0")
            .mark_rect(opacity=0.2)
            .encode(
                x="period_start_date:T",
                x2="period_end_date:T",
                y=alt.Y(
                    "zero:Q",
                    title="Revenue per User (USD)",
                    axis=alt.Axis(format="$,.0f", grid=True),
                ),
                y2=alt.Y2("revenue_per_user_usd:Q"),
                color=alt.Color(
                    "final_fee_bps:N",
                    title="Fee Tier (bps)",
                    scale=alt.Scale(scheme="category10", domain=unique_bps),
                ),
                detail="period_id:N",
            )
        )
        rpu_rule = (
            alt.Chart(filtered)
            .mark_rule(size=6)
            .encode(
                x="period_start_date:T",
                x2="period_end_date:T",
                y=alt.Y(
                    "revenue_per_user_usd:Q",
                    title="Revenue per User (USD)",
                    axis=alt.Axis(format="$,.0f", grid=True),
                ),
                color=alt.Color(
                    "final_fee_bps:N",
                    title="Fee Tier (bps)",
                    scale=alt.Scale(scheme="category10", domain=unique_bps),
                ),
                detail="period_id:N",
                tooltip=[
                    alt.Tooltip("period_start_date", title="Start", format="%Y-%m-%d"),
                    alt.Tooltip("period_end_date", title="End", format="%Y-%m-%d"),
                    alt.Tooltip("final_fee_bps", title="Fee bps", format=".1f"),
                    alt.Tooltip("revenue_per_user_usd", title="Rev/User", format="$,.0f"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart((rpu_rect + rpu_rule).interactive(), use_container_width=True)

    # Weekly metrics table (formatted)
    st.subheader("Weekly metrics table")
    display_cols = [
        "period_id",
        "period_start_date",
        "period_end_date",
        "days_in_period",
        "final_fee_bps",
        "swaps_count",
        "unique_swappers",
        "volume_usd",
        "fees_usd",
        "avg_swap_size_usd",
        "realized_fee_bps",
        "revenue_per_swap_usd",
        "revenue_per_user_usd",
    ]
    display_df = filtered[display_cols].copy()
    display_df["period_start_date"] = pd.to_datetime(display_df["period_start_date"]).dt.strftime(
        "%Y-%m-%d"
    )
    display_df["period_end_date"] = pd.to_datetime(display_df["period_end_date"]).dt.strftime(
        "%Y-%m-%d"
    )
    for col in [
        "volume_usd",
        "fees_usd",
        "avg_swap_size_usd",
        "revenue_per_swap_usd",
        "revenue_per_user_usd",
    ]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "–")
    for col in ["final_fee_bps", "realized_fee_bps"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "–")
    for col in ["swaps_count", "unique_swappers"]:
        if col in display_df.columns:
            display_df[col] = display_df[col].apply(lambda x: f"{int(x):,}" if pd.notna(x) else "–")
    display_df = display_df.rename(
        columns={
            "period_id": "Period",
            "period_start_date": "Start Date",
            "period_end_date": "End Date",
            "days_in_period": "Days",
            "final_fee_bps": "Fee (bps)",
            "swaps_count": "Swaps",
            "unique_swappers": "Unique Users",
            "volume_usd": "Volume",
            "fees_usd": "Revenue",
            "avg_swap_size_usd": "Avg Swap",
            "realized_fee_bps": "Realized Fee (bps)",
            "revenue_per_swap_usd": "Revenue/Swap",
            "revenue_per_user_usd": "Revenue/User",
        }
    )
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    csv = filtered[display_cols].to_csv(index=False).encode("utf-8")
    st.download_button("Download weekly metrics (CSV)", data=csv, file_name="weekly_metrics.csv")

    # Validation
    st.divider()
    st.subheader("Experiment Validation (Manual Periods)")
    st.caption("Comparing intended fee tiers vs realized fees from swap data")

    per_df = load_validation_period_level(session)
    overall_df = load_validation_overall(session)
    if per_df is None or per_df.empty:
        st.info("Validation query not available or returned no rows.")
    else:
        val_df = per_df.copy()
        val_df["period_start_date"] = pd.to_datetime(val_df["period_start_date"]).dt.strftime(
            "%Y-%m-%d"
        )
        val_df["period_end_date"] = pd.to_datetime(val_df["period_end_date"]).dt.strftime(
            "%Y-%m-%d"
        )
        for col in ["volume_usd", "fees_usd"]:
            if col in val_df.columns:
                val_df[col] = val_df[col].apply(lambda x: f"${x:,.0f}" if pd.notna(x) else "–")
        val_df["swaps_count"] = val_df["swaps_count"].apply(
            lambda x: f"{int(x):,}" if pd.notna(x) else "–"
        )
        val_df = val_df.rename(
            columns={
                "period_id": "Period",
                "period_start_date": "Start",
                "period_end_date": "End",
                "days_in_period": "Days",
                "intended_fee_bps": "Intended (bps)",
                "realized_fee_bps": "Realized (bps)",
                "delta_bps": "Δ (bps)",
                "within_1bp": "Status",
                "swaps_count": "Swaps",
                "volume_usd": "Volume",
                "fees_usd": "Fees",
            }
        )
        left, right = st.columns([3, 1])
        with left:
            st.dataframe(val_df, use_container_width=True, hide_index=True)
        with right:
            if overall_df is not None and not overall_df.empty:
                row = overall_df.iloc[0]
                st.metric("Validation Status", str(row["overall"]))
                st.metric(
                    "Periods Passing", f"{int(row['periods_passing'])}/{int(row['periods_total'])}"
                )
                pass_rate = (int(row["periods_passing"]) / int(row["periods_total"])) * 100
                st.metric("Pass Rate", f"{pass_rate:.0f}%")
            else:
                st.info("Overall summary not available.")

    st.caption(
        "Phase 1 views: V_SWAPS_EXPERIMENT_WINDOW, V_FEE_PERIODS_MANUAL, V_FEE_PERIODS_FINAL, V_WEEKLY_SUMMARY_FINAL, optional V_PERIOD_REVENUE_CI"
    )


if __name__ == "__main__":
    main()
