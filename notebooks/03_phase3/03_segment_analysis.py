"""
Phase 3: Trade-Size Segmentation and Elasticity Analysis

Outputs:
- segment_metrics.csv
"""

import sys
from pathlib import Path

import pandas as pd

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from thorchain_fee_analysis.analysis.segmentation import (
    add_elasticity_to_metrics,
    assign_trade_size_segment,
    compute_segment_metrics,
    estimate_segment_elasticity,
    get_segment_summary,
)
from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session
from thorchain_fee_analysis.data.user_data import load_user_period_detail, load_weekly_summary


def main():
    print("=" * 60)
    print("PHASE 3: TRADE-SIZE SEGMENTATION")
    print("=" * 60)

    # Load data
    print("\n1. Loading data...")
    session = get_snowpark_session()
    user_df = load_user_period_detail(session)
    weekly_df = load_weekly_summary(session)
    print(f"   User-period observations: {len(user_df):,}")
    print(f"   Weekly periods: {len(weekly_df)}")

    # Assign segments
    print("\n2. Assigning trade-size segments...")
    user_with_segments = assign_trade_size_segment(user_df)
    print("   Segment distribution:")
    for segment in ["micro", "small", "medium", "large", "whale"]:
        count = (user_with_segments["segment"] == segment).sum()
        pct = count / len(user_with_segments) * 100
        print(f"     {segment:8s}: {count:7,} ({pct:5.1f}%)")

    # Compute segment metrics
    print("\n3. Computing segment metrics by period...")
    segment_metrics = compute_segment_metrics(user_with_segments, weekly_df)
    print(f"   Calculated metrics for {len(segment_metrics)} period-segment combinations")

    # Estimate elasticity by segment
    print("\n4. Estimating elasticity by segment...")
    elasticity_df = estimate_segment_elasticity(segment_metrics)
    print("   Elasticity estimates:")
    for _, row in elasticity_df.iterrows():
        if pd.notna(row["elasticity"]):
            print(
                f"     {row['segment']:8s}: {row['elasticity']:8.4f} "
                f"(p={row['pvalue']:.3f}, R²={row['r_squared']:.3f})"
            )
        else:
            print(f"     {row['segment']:8s}: insufficient data")

    # Add elasticity to metrics
    segment_metrics_final = add_elasticity_to_metrics(segment_metrics, elasticity_df)

    # Get summary
    print("\n5. Computing segment summary...")
    summary = get_segment_summary(segment_metrics_final)

    # Export CSVs
    output_dir = Path(__file__).parent.parent.parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    print("\n6. Exporting CSVs...")

    metrics_path = output_dir / "segment_metrics.csv"
    segment_metrics_final.to_csv(metrics_path, index=False)
    print(f"   ✅ {metrics_path}")

    elasticity_path = output_dir / "segment_elasticity.csv"
    elasticity_df.to_csv(elasticity_path, index=False)
    print(f"   ✅ {elasticity_path}")

    summary_path = output_dir / "segment_summary.csv"
    summary.to_csv(summary_path, index=False)
    print(f"   ✅ {summary_path}")

    # Summary stats
    print("\n" + "=" * 60)
    print("SEGMENT ANALYSIS SUMMARY")
    print("=" * 60)

    print("\nOverall volume contribution by segment:")
    for _, row in summary.iterrows():
        print(
            f"  {row['segment']:8s}: {row['overall_volume_share']*100:5.1f}% of volume, "
            f"{row['overall_fees_share']*100:5.1f}% of fees"
        )

    print("\nAverage fees paid per user by segment:")
    for _, row in summary.iterrows():
        print(f"  {row['segment']:8s}: ${row['avg_fees_paid_usd']:.2f}")

    print("\nAverage retention rate by segment:")
    for _, row in summary.iterrows():
        if pd.notna(row["retention_rate"]):
            print(f"  {row['segment']:8s}: {row['retention_rate']*100:5.1f}%")

    print("\n" + "=" * 60)
    print("✅ SEGMENT ANALYSIS COMPLETE")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
