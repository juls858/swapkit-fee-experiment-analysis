"""
Revenue decomposition analysis for THORChain fee experiment.

Decomposes revenue changes into:
1. Fee rate effect (direct impact of rate change)
2. Volume effect (volume response to rate change)
3. Mix effect (changes in trade size distribution)
4. External effect (residual/market conditions)
"""

from dataclasses import dataclass

import pandas as pd
import polars as pl


@dataclass
class DecompositionResult:
    """Container for revenue decomposition results."""

    period_id: int
    period_start_date: str

    # Total revenue change
    total_revenue_change: float

    # Decomposition components
    fee_rate_effect: float
    volume_effect: float
    mix_effect: float
    external_effect: float

    # Component percentages
    fee_rate_pct: float
    volume_pct: float
    mix_pct: float
    external_pct: float

    # Supporting metrics
    prev_revenue: float
    current_revenue: float
    prev_fee_bps: float
    current_fee_bps: float
    prev_volume: float
    current_volume: float


def decompose_revenue_change(
    current_period: dict,
    prev_period: dict,
) -> DecompositionResult:
    """
    Decompose revenue change between two periods.

    Decomposition:
    ΔRevenue = Revenue_t - Revenue_{t-1}

    1. Fee Rate Effect = (Fee_t - Fee_{t-1}) * Volume_{t-1}
       Direct impact of fee change at previous volume

    2. Volume Effect = Fee_{t-1} * (Volume_t - Volume_{t-1})
       Impact of volume change at previous fee rate

    3. Mix Effect = (AvgSwapSize_t - AvgSwapSize_{t-1}) * Swaps_t * Fee_t
       Impact of changes in swap size distribution

    4. External Effect = Residual
       Everything else (interaction effects, measurement error, external factors)

    Args:
        current_period: Dictionary with current period metrics
        prev_period: Dictionary with previous period metrics

    Returns:
        DecompositionResult with all components
    """
    # Extract metrics
    prev_revenue = prev_period["fees_usd"]
    current_revenue = current_period["fees_usd"]
    prev_fee_bps = prev_period["final_fee_bps"] / 10000  # Convert to decimal
    current_fee_bps = current_period["final_fee_bps"] / 10000
    prev_volume = prev_period["volume_usd"]
    current_volume = current_period["volume_usd"]
    prev_avg_swap = prev_period.get("avg_swap_size_usd", 0)
    current_avg_swap = current_period.get("avg_swap_size_usd", 0)
    current_swaps = current_period.get("swaps_count", 0)

    # Total revenue change
    total_change = current_revenue - prev_revenue

    # 1. Fee Rate Effect
    # Impact of fee change at previous volume level
    fee_rate_effect = (current_fee_bps - prev_fee_bps) * prev_volume

    # 2. Volume Effect
    # Impact of volume change at previous fee rate
    volume_effect = prev_fee_bps * (current_volume - prev_volume)

    # 3. Mix Effect
    # Impact of swap size distribution change
    # Approximation: change in avg swap size * number of swaps * current fee rate
    if current_swaps > 0 and prev_avg_swap > 0:
        mix_effect = (current_avg_swap - prev_avg_swap) * current_swaps * current_fee_bps
    else:
        mix_effect = 0.0

    # 4. External Effect (Residual)
    # This captures interaction effects and other factors
    external_effect = total_change - (fee_rate_effect + volume_effect + mix_effect)

    # Calculate percentages
    if total_change != 0:
        fee_rate_pct = (fee_rate_effect / total_change) * 100
        volume_pct = (volume_effect / total_change) * 100
        mix_pct = (mix_effect / total_change) * 100
        external_pct = (external_effect / total_change) * 100
    else:
        fee_rate_pct = volume_pct = mix_pct = external_pct = 0.0

    return DecompositionResult(
        period_id=current_period["period_id"],
        period_start_date=str(current_period["period_start_date"]),
        total_revenue_change=total_change,
        fee_rate_effect=fee_rate_effect,
        volume_effect=volume_effect,
        mix_effect=mix_effect,
        external_effect=external_effect,
        fee_rate_pct=fee_rate_pct,
        volume_pct=volume_pct,
        mix_pct=mix_pct,
        external_pct=external_pct,
        prev_revenue=prev_revenue,
        current_revenue=current_revenue,
        prev_fee_bps=prev_period["final_fee_bps"],
        current_fee_bps=current_period["final_fee_bps"],
        prev_volume=prev_volume,
        current_volume=current_volume,
    )


def analyze_revenue_decomposition(
    df: pd.DataFrame | pl.DataFrame,
) -> list[DecompositionResult]:
    """
    Perform revenue decomposition for all period transitions.

    Args:
        df: DataFrame with elasticity inputs (from fct_elasticity_inputs)

    Returns:
        List of DecompositionResult, one per period transition
    """
    # Convert to pandas if polars
    if isinstance(df, pl.DataFrame):
        df = df.to_pandas()

    # Sort by period
    df = df.sort_values("period_start_date").reset_index(drop=True)

    results = []

    # Iterate through periods (starting from second period)
    for i in range(1, len(df)):
        prev_period = df.iloc[i - 1].to_dict()
        current_period = df.iloc[i].to_dict()

        result = decompose_revenue_change(current_period, prev_period)
        results.append(result)

    return results


def create_waterfall_data(
    decomposition_results: list[DecompositionResult],
) -> pd.DataFrame:
    """
    Create waterfall chart data from decomposition results.

    Args:
        decomposition_results: List of decomposition results

    Returns:
        DataFrame formatted for waterfall visualization
    """
    waterfall_data = []

    for result in decomposition_results:
        # Starting point (previous revenue)
        waterfall_data.append(
            {
                "period_id": result.period_id,
                "period_start_date": result.period_start_date,
                "component": "Previous Revenue",
                "value": result.prev_revenue,
                "cumulative": result.prev_revenue,
                "is_total": False,
            }
        )

        # Fee rate effect
        cumulative = result.prev_revenue + result.fee_rate_effect
        waterfall_data.append(
            {
                "period_id": result.period_id,
                "period_start_date": result.period_start_date,
                "component": "Fee Rate Effect",
                "value": result.fee_rate_effect,
                "cumulative": cumulative,
                "is_total": False,
            }
        )

        # Volume effect
        cumulative += result.volume_effect
        waterfall_data.append(
            {
                "period_id": result.period_id,
                "period_start_date": result.period_start_date,
                "component": "Volume Effect",
                "value": result.volume_effect,
                "cumulative": cumulative,
                "is_total": False,
            }
        )

        # Mix effect
        cumulative += result.mix_effect
        waterfall_data.append(
            {
                "period_id": result.period_id,
                "period_start_date": result.period_start_date,
                "component": "Mix Effect",
                "value": result.mix_effect,
                "cumulative": cumulative,
                "is_total": False,
            }
        )

        # External effect
        cumulative += result.external_effect
        waterfall_data.append(
            {
                "period_id": result.period_id,
                "period_start_date": result.period_start_date,
                "component": "External Effect",
                "value": result.external_effect,
                "cumulative": cumulative,
                "is_total": False,
            }
        )

        # Ending point (current revenue)
        waterfall_data.append(
            {
                "period_id": result.period_id,
                "period_start_date": result.period_start_date,
                "component": "Current Revenue",
                "value": result.current_revenue,
                "cumulative": result.current_revenue,
                "is_total": True,
            }
        )

    return pd.DataFrame(waterfall_data)


def summarize_decomposition(
    decomposition_results: list[DecompositionResult],
) -> dict:
    """
    Create summary statistics across all periods.

    Args:
        decomposition_results: List of decomposition results

    Returns:
        Dictionary with summary metrics
    """
    if not decomposition_results:
        return {}

    # Aggregate effects
    total_fee_effect = sum(r.fee_rate_effect for r in decomposition_results)
    total_volume_effect = sum(r.volume_effect for r in decomposition_results)
    total_mix_effect = sum(r.mix_effect for r in decomposition_results)
    total_external_effect = sum(r.external_effect for r in decomposition_results)
    total_change = sum(r.total_revenue_change for r in decomposition_results)

    # Average percentages
    avg_fee_pct = sum(r.fee_rate_pct for r in decomposition_results) / len(decomposition_results)
    avg_volume_pct = sum(r.volume_pct for r in decomposition_results) / len(decomposition_results)
    avg_mix_pct = sum(r.mix_pct for r in decomposition_results) / len(decomposition_results)
    avg_external_pct = sum(r.external_pct for r in decomposition_results) / len(
        decomposition_results
    )

    # Overall percentages
    if total_change != 0:
        overall_fee_pct = (total_fee_effect / total_change) * 100
        overall_volume_pct = (total_volume_effect / total_change) * 100
        overall_mix_pct = (total_mix_effect / total_change) * 100
        overall_external_pct = (total_external_effect / total_change) * 100
    else:
        overall_fee_pct = overall_volume_pct = overall_mix_pct = overall_external_pct = 0.0

    return {
        "n_periods": len(decomposition_results),
        "total_revenue_change": total_change,
        "total_fee_rate_effect": total_fee_effect,
        "total_volume_effect": total_volume_effect,
        "total_mix_effect": total_mix_effect,
        "total_external_effect": total_external_effect,
        "avg_fee_rate_pct": avg_fee_pct,
        "avg_volume_pct": avg_volume_pct,
        "avg_mix_pct": avg_mix_pct,
        "avg_external_pct": avg_external_pct,
        "overall_fee_rate_pct": overall_fee_pct,
        "overall_volume_pct": overall_volume_pct,
        "overall_mix_pct": overall_mix_pct,
        "overall_external_pct": overall_external_pct,
    }
