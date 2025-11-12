"""
Reusable chart builders for elasticity and revenue analysis.
Provides composite visualizations that overlay independent and dependent variables.
"""

import altair as alt
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_fee_revenue_lightweight_chart(df: pd.DataFrame) -> list[dict]:
    """
    Create lightweight-charts configuration for FEE CHANGE + revenue overlay.
    Shows DELTA in fees (what changed) vs revenue response.

    Args:
        df: DataFrame with columns: period_start_date, final_fee_bps, prev_fee_bps,
                                    fees_usd, pct_change_fee_bps

    Returns:
        List of chart configurations for renderLightweightCharts
    """
    viz_df = df.copy()
    viz_df["period_start_date"] = pd.to_datetime(viz_df["period_start_date"])

    # Calculate fee change in bps (delta)
    viz_df["fee_change_bps"] = viz_df["final_fee_bps"] - viz_df["prev_fee_bps"]

    # Convert dates to Unix timestamps (seconds)
    viz_df["timestamp"] = (viz_df["period_start_date"].astype(int) / 10**9).astype(int)

    # Prepare FEE CHANGE data (area chart showing +/- changes)
    # Include current fee and change for tooltip
    fee_change_data = [
        {
            "time": int(row["timestamp"]),
            "value": float(row["fee_change_bps"]),
            "title": f"Fee: {row['final_fee_bps']:.0f} bps ({row['fee_change_bps']:+.0f})",
        }
        for _, row in viz_df.iterrows()
    ]

    # Prepare revenue data (line chart - PRIMARY METRIC)
    # Include current fee for context
    revenue_data = [
        {
            "time": int(row["timestamp"]),
            "value": float(row["fees_usd"]),
            "title": f"Revenue: ${row['fees_usd']:,.0f} | Fee: {row['final_fee_bps']:.0f} bps",
        }
        for _, row in viz_df.iterrows()
    ]

    # Chart configuration
    chart_options = {
        "layout": {
            "textColor": "black",
            "background": {"type": "solid", "color": "white"},
        },
        "rightPriceScale": {
            "visible": True,
        },
        "leftPriceScale": {
            "visible": True,
        },
        "timeScale": {
            "timeVisible": True,
            "secondsVisible": False,
        },
    }

    # Series configuration
    # Histogram for fee changes (bars with tooltips showing current fee)
    # Line for revenue
    series = [
        {
            "type": "Histogram",
            "data": fee_change_data,
            "options": {
                "color": "rgba(255, 107, 53, 0.6)",
                "priceScaleId": "right",
                "title": "Δ Fee (bps) - INDEPENDENT VARIABLE",
            },
        },
        {
            "type": "Line",
            "data": revenue_data,
            "options": {
                "color": "#2E7D32",
                "lineWidth": 3,
                "priceFormat": {"type": "price"},
                "priceScaleId": "left",
                "title": "Revenue (USD) - PRIMARY METRIC",
            },
        },
    ]

    return [{"chart": chart_options, "series": series}]


def create_fee_volume_lightweight_chart(df: pd.DataFrame) -> list[dict]:
    """
    Create lightweight-charts configuration for FEE CHANGE + volume overlay.
    Shows DELTA in fees (what changed) vs volume response.

    Args:
        df: DataFrame with columns: period_start_date, final_fee_bps, prev_fee_bps,
                                    volume_usd, pct_change_fee_bps

    Returns:
        List of chart configurations for renderLightweightCharts
    """
    viz_df = df.copy()
    viz_df["period_start_date"] = pd.to_datetime(viz_df["period_start_date"])

    # Calculate fee change in bps (delta)
    viz_df["fee_change_bps"] = viz_df["final_fee_bps"] - viz_df["prev_fee_bps"]

    # Convert dates to Unix timestamps (seconds)
    viz_df["timestamp"] = (viz_df["period_start_date"].astype(int) / 10**9).astype(int)

    # Prepare FEE CHANGE data (area chart showing +/- changes)
    # Include current fee and change for tooltip
    fee_change_data = [
        {
            "time": int(row["timestamp"]),
            "value": float(row["fee_change_bps"]),
            "title": f"Fee: {row['final_fee_bps']:.0f} bps ({row['fee_change_bps']:+.0f})",
        }
        for _, row in viz_df.iterrows()
    ]

    # Prepare volume data (line chart)
    # Include current fee for context
    volume_data = [
        {
            "time": int(row["timestamp"]),
            "value": float(row["volume_usd"]),
            "title": f"Volume: ${row['volume_usd']:,.0f} | Fee: {row['final_fee_bps']:.0f} bps",
        }
        for _, row in viz_df.iterrows()
    ]

    # Chart configuration
    chart_options = {
        "layout": {
            "textColor": "black",
            "background": {"type": "solid", "color": "white"},
        },
        "rightPriceScale": {
            "visible": True,
        },
        "leftPriceScale": {
            "visible": True,
        },
        "timeScale": {
            "timeVisible": True,
            "secondsVisible": False,
        },
    }

    # Series configuration
    # Histogram for fee changes (bars with tooltips showing current fee)
    # Line for volume
    series = [
        {
            "type": "Histogram",
            "data": fee_change_data,
            "options": {
                "color": "rgba(255, 107, 53, 0.6)",
                "priceScaleId": "right",
                "title": "Δ Fee (bps) - INDEPENDENT VARIABLE",
            },
        },
        {
            "type": "Line",
            "data": volume_data,
            "options": {
                "color": "#2196F3",
                "lineWidth": 3,
                "priceFormat": {"type": "volume"},
                "priceScaleId": "left",
                "title": "Volume (USD) - Supporting Metric",
            },
        },
    ]

    return [{"chart": chart_options, "series": series}]


def create_simple_volume_revenue_bars(df: pd.DataFrame) -> go.Figure:
    """
    Create a simple, clear bar chart showing volume and revenue side-by-side.
    Follows visualization best practices: clear, direct, easy to interpret.

    Args:
        df: DataFrame with columns: period_start_date, volume_usd, fees_usd, final_fee_bps

    Returns:
        Plotly Figure with grouped bars
    """
    viz_df = df.copy()
    viz_df["period_start_date"] = pd.to_datetime(viz_df["period_start_date"])
    viz_df["period_label"] = viz_df["period_start_date"].dt.strftime("%b %d")

    # Normalize to same scale for comparison (0-100)
    max_volume = viz_df["volume_usd"].max()
    max_revenue = viz_df["fees_usd"].max()

    viz_df["volume_normalized"] = (viz_df["volume_usd"] / max_volume) * 100
    viz_df["revenue_normalized"] = (viz_df["fees_usd"] / max_revenue) * 100

    fig = go.Figure()

    # Volume bars
    fig.add_trace(
        go.Bar(
            name="Volume",
            x=viz_df["period_label"],
            y=viz_df["volume_normalized"],
            marker_color="#2196F3",
            customdata=viz_df[["volume_usd", "final_fee_bps"]],
            hovertemplate="<b>Volume</b><br>%{customdata[0]:$,.0f}<br>Fee: %{customdata[1]:.0f} bps<extra></extra>",
        )
    )

    # Revenue bars (PRIMARY METRIC)
    fig.add_trace(
        go.Bar(
            name="Revenue (PRIMARY)",
            x=viz_df["period_label"],
            y=viz_df["revenue_normalized"],
            marker_color="#2E7D32",
            customdata=viz_df[["fees_usd", "final_fee_bps"]],
            hovertemplate="<b>Revenue</b><br>%{customdata[0]:$,.0f}<br>Fee: %{customdata[1]:.0f} bps<extra></extra>",
        )
    )

    # Add fee tier as line overlay
    fig.add_trace(
        go.Scatter(
            name="Fee Tier",
            x=viz_df["period_label"],
            y=viz_df["final_fee_bps"] * 4,  # Scale to fit 0-100 range
            mode="lines+markers",
            line=dict(color="#FF6B35", width=3),
            marker=dict(size=10),
            yaxis="y2",
            hovertemplate="<b>Fee Tier</b><br>%{text} bps<extra></extra>",
            text=viz_df["final_fee_bps"],
        )
    )

    fig.update_layout(
        title="Volume & Revenue Response to Fee Changes (Normalized to 0-100 Scale)",
        xaxis_title="Period",
        yaxis_title="Normalized Index (0-100)",
        yaxis2=dict(title="Fee Tier (bps)", overlaying="y", side="right", range=[0, 100]),
        barmode="group",
        height=400,
        hovermode="x unified",
        template="plotly_white",
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )

    return fig


def create_volume_footprint_chart(df: pd.DataFrame) -> go.Figure:
    """
    Create a volume footprint chart where:
    - Bar height = volume (USD)
    - Bar width = |Δ volume| (absolute change)
    - Bar color = fee tier (bps)

    Args:
        df: DataFrame with columns: period_start_date, period_end_date, volume_usd,
            prev_volume_usd, final_fee_bps, period_id, pct_change_volume

    Returns:
        Plotly Figure object
    """
    viz_df = df.copy()
    viz_df["volume_delta"] = viz_df["volume_usd"] - viz_df["prev_volume_usd"]
    viz_df["abs_volume_delta"] = viz_df["volume_delta"].abs()
    viz_df["period_start_date"] = pd.to_datetime(viz_df["period_start_date"])

    # Calculate bar widths proportional to volume delta
    max_delta = viz_df["abs_volume_delta"].max()
    if max_delta > 0:
        viz_df["bar_width_days"] = (viz_df["abs_volume_delta"] / max_delta) * 5  # Max 5 days
    else:
        viz_df["bar_width_days"] = 1

    fig = go.Figure()

    # Add volume bars with varying widths
    for idx, row in viz_df.iterrows():
        fig.add_trace(
            go.Bar(
                x=[row["period_start_date"]],
                y=[row["volume_usd"]],
                width=[row["bar_width_days"] * 24 * 60 * 60 * 1000],  # Convert to milliseconds
                marker=dict(
                    color=row["final_fee_bps"],
                    colorscale="Blues",
                    cmin=viz_df["final_fee_bps"].min(),
                    cmax=viz_df["final_fee_bps"].max(),
                    colorbar=dict(title="Fee (bps)", x=1.02) if idx == 0 else None,
                    line=dict(color="white", width=1),
                ),
                name=f"Period {row['period_id']}",
                hovertemplate=(
                    f"<b>Period {row['period_id']}</b><br>"
                    f"Date: {row['period_start_date'].strftime('%Y-%m-%d')}<br>"
                    f"Volume: ${row['volume_usd']:,.0f}<br>"
                    f"Δ Volume: ${row['volume_delta']:+,.0f}<br>"
                    f"Fee: {row['final_fee_bps']:.1f} bps<br>"
                    f"Δ Volume %: {row['pct_change_volume']:+.1f}%<br>"
                    "<extra></extra>"
                ),
                showlegend=False,
            )
        )

    fig.update_layout(
        title="Volume Footprint: Bar Width ∝ |Δ Volume|, Color = Fee Tier",
        xaxis_title="Period",
        yaxis_title="Volume (USD)",
        yaxis=dict(tickformat="$,.0s"),
        height=400,
        hovermode="closest",
        bargap=0.1,
        template="plotly_white",
    )

    return fig


def create_fee_revenue_dual_axis(df: pd.DataFrame) -> go.Figure:
    """
    Create dual-axis chart overlaying fee tier and revenue:
    - Left Y-axis: Fee tier (area + line)
    - Right Y-axis: Revenue (line + markers)

    Args:
        df: DataFrame with columns: period_start_date, final_fee_bps, fees_usd,
            period_id, pct_change_fees

    Returns:
        Plotly Figure with dual y-axes
    """
    viz_df = df.copy()
    viz_df["period_start_date"] = pd.to_datetime(viz_df["period_start_date"])

    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Fee tier as area (left axis)
    fig.add_trace(
        go.Scatter(
            x=viz_df["period_start_date"],
            y=viz_df["final_fee_bps"],
            fill="tozeroy",
            fillcolor="rgba(255, 165, 0, 0.3)",
            line=dict(color="darkorange", width=2),
            name="Fee Tier",
            hovertemplate="<b>Fee Tier</b><br>%{x|%Y-%m-%d}<br>%{y:.1f} bps<extra></extra>",
        ),
        secondary_y=False,
    )

    # Revenue as line with markers (right axis)
    fig.add_trace(
        go.Scatter(
            x=viz_df["period_start_date"],
            y=viz_df["fees_usd"],
            mode="lines+markers",
            line=dict(color="darkgreen", width=3),
            marker=dict(size=10, color="green"),
            name="Revenue",
            hovertemplate=("<b>Revenue</b><br>%{x|%Y-%m-%d}<br>$%{y:,.0f}<br><extra></extra>"),
        ),
        secondary_y=True,
    )

    # Update axes
    fig.update_xaxes(title_text="Period")
    fig.update_yaxes(
        title_text="Fee Tier (bps)",
        secondary_y=False,
        range=[0, viz_df["final_fee_bps"].max() * 1.2],
    )
    fig.update_yaxes(title_text="Revenue (USD)", secondary_y=True, tickformat="$,.0s")

    fig.update_layout(
        title="Fee Tier vs Revenue (Dual Axis)",
        height=400,
        hovermode="x unified",
        template="plotly_white",
        legend=dict(x=0.01, y=0.99, bgcolor="rgba(255,255,255,0.8)"),
    )

    return fig


def create_elasticity_scatter(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    x_label: str,
    y_label: str,
    elasticity_value: float | None = None,
) -> alt.Chart:
    """
    Create scatter plot with regression line for elasticity visualization.

    Args:
        df: DataFrame with elasticity data
        x_col: Column name for x-axis (e.g., 'pct_change_fee_bps')
        y_col: Column name for y-axis (e.g., 'pct_change_volume')
        title: Chart title
        x_label: X-axis label
        y_label: Y-axis label
        elasticity_value: Optional elasticity coefficient to display in title

    Returns:
        Altair Chart object
    """
    if elasticity_value is not None:
        title = f"{title} (Elasticity = {elasticity_value:.3f})"

    # Filter out rows with NaN or infinite values in the columns we need
    viz_df = df[[x_col, y_col, "final_fee_bps", "period_id"]].copy()
    viz_df = viz_df.replace([float("inf"), float("-inf")], float("nan"))
    viz_df = viz_df.dropna()

    # Check if we have enough data points for regression
    if len(viz_df) < 2:
        # Not enough data for regression, just show scatter
        scatter = (
            alt.Chart(viz_df)
            .mark_circle(size=200)
            .encode(
                x=alt.X(f"{x_col}:Q", title=x_label, scale=alt.Scale(zero=False)),
                y=alt.Y(f"{y_col}:Q", title=y_label, scale=alt.Scale(zero=False)),
                color=alt.Color(
                    "final_fee_bps:Q", title="Fee Tier (bps)", scale=alt.Scale(scheme="viridis")
                ),
                tooltip=[
                    alt.Tooltip("period_id:Q", title="Period"),
                    alt.Tooltip(f"{x_col}:Q", title=x_label, format="+.1f"),
                    alt.Tooltip(f"{y_col}:Q", title=y_label, format="+.1f"),
                    alt.Tooltip("final_fee_bps:Q", title="Fee (bps)", format=".1f"),
                ],
            )
            .properties(title=f"{title} (Insufficient data for regression)", height=300, width=400)
        )
        return scatter

    # Scatter plot
    scatter = (
        alt.Chart(viz_df)
        .mark_circle(size=200, opacity=0.8)
        .encode(
            x=alt.X(f"{x_col}:Q", title=x_label, scale=alt.Scale(zero=False)),
            y=alt.Y(f"{y_col}:Q", title=y_label, scale=alt.Scale(zero=False)),
            color=alt.Color(
                "final_fee_bps:Q", title="Fee Tier (bps)", scale=alt.Scale(scheme="viridis")
            ),
            tooltip=[
                alt.Tooltip("period_id:Q", title="Period"),
                alt.Tooltip(f"{x_col}:Q", title=x_label, format="+.1f"),
                alt.Tooltip(f"{y_col}:Q", title=y_label, format="+.1f"),
                alt.Tooltip("final_fee_bps:Q", title="Fee (bps)", format=".1f"),
            ],
        )
    )

    # Regression line - create separately to ensure it renders
    regression = (
        alt.Chart(viz_df)
        .mark_line(color="red", strokeDash=[5, 5], strokeWidth=3)
        .transform_regression(
            x_col,
            y_col,
            method="linear",
        )
        .encode(
            x=alt.X(f"{x_col}:Q"),
            y=alt.Y(f"{y_col}:Q"),
        )
    )

    # Combine and configure
    chart = (
        (scatter + regression)
        .properties(title=title, height=300, width=400)
        .configure_mark(opacity=0.8)
    )

    return chart


def create_waterfall_chart(
    components: list[dict], title: str = "Revenue Decomposition Waterfall"
) -> go.Figure:
    """
    Create a waterfall chart for revenue decomposition.

    Args:
        components: List of dicts with keys: 'component', 'value', 'type'
                   type should be 'total', 'positive', or 'negative'
        title: Chart title

    Returns:
        Plotly Figure object
    """
    df = pd.DataFrame(components)

    # Prepare waterfall data
    measure = []
    text = []
    for comp in components:
        if comp["type"] == "total":
            measure.append("total")
            text.append(f"${comp['value']:,.0f}")
        else:
            measure.append("relative")
            text.append(f"${comp['value']:+,.0f}")

    fig = go.Figure(
        go.Waterfall(
            name="Revenue",
            orientation="v",
            measure=measure,
            x=df["component"],
            textposition="outside",
            text=text,
            y=df["value"],
            connector={"line": {"color": "rgb(63, 63, 63)"}},
            decreasing={"marker": {"color": "#d62728"}},
            increasing={"marker": {"color": "#2ca02c"}},
            totals={"marker": {"color": "#1f77b4"}},
            hovertemplate="<b>%{x}</b><br>Impact: $%{y:,.0f}<extra></extra>",
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Component",
        yaxis_title="Revenue Impact (USD)",
        yaxis=dict(tickformat="$,.0s"),
        height=400,
        template="plotly_white",
        showlegend=False,
    )

    return fig


def create_period_comparison_heatmap(df: pd.DataFrame) -> alt.Chart:
    """
    Create a heatmap comparing metrics across periods.

    Args:
        df: DataFrame with period metrics

    Returns:
        Altair Chart object
    """
    # Prepare data for heatmap
    metrics = ["pct_change_volume", "pct_change_fees", "pct_change_swaps"]
    heatmap_data = []

    for metric in metrics:
        for _, row in df.iterrows():
            heatmap_data.append(
                {
                    "period": f"P{row['period_id']}",
                    "metric": metric.replace("pct_change_", "Δ ").replace("_", " ").title(),
                    "value": row[metric],
                }
            )

    heatmap_df = pd.DataFrame(heatmap_data)

    chart = (
        alt.Chart(heatmap_df)
        .mark_rect()
        .encode(
            x=alt.X("period:N", title="Period"),
            y=alt.Y("metric:N", title="Metric"),
            color=alt.Color(
                "value:Q",
                title="Change (%)",
                scale=alt.Scale(scheme="redyellowgreen", domain=[-100, 0, 100]),
            ),
            tooltip=[
                alt.Tooltip("period:N", title="Period"),
                alt.Tooltip("metric:N", title="Metric"),
                alt.Tooltip("value:Q", title="Change (%)", format="+.1f"),
            ],
        )
        .properties(title="Period-over-Period Changes Heatmap", height=200)
    )

    return chart
