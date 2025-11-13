"""
Phase 3: Build User Cohorts and Retention Tables

Outputs:
- user_cohorts.csv
- retention_by_fee.csv
- acquisition_by_period.csv
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from thorchain_fee_analysis.analysis.retention import (
    add_retention_confidence_intervals,
    build_cohort_table,
    calculate_acquisition_by_period,
    calculate_retention_by_fee,
)
from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session
from thorchain_fee_analysis.data.user_data import load_user_period_detail


def main():
    print("=" * 60)
    print("PHASE 3: BUILD USER COHORTS")
    print("=" * 60)

    # Load data
    print("\n1. Loading user period detail...")
    session = get_snowpark_session()
    user_df = load_user_period_detail(session)
    print(f"   Loaded {len(user_df):,} user-period observations")
    print(f"   Unique users: {user_df['user_address'].nunique():,}")

    # Build cohort table
    print("\n2. Building cohort table...")
    cohort_df = build_cohort_table(user_df)
    print(f"   Created cohort table with {len(cohort_df):,} users")
    print(f"   Acquisition fee tiers: {sorted(cohort_df['first_seen_fee_bps'].unique())}")

    # Calculate retention by fee
    print("\n3. Calculating retention rates by acquisition fee...")
    retention_df = calculate_retention_by_fee(cohort_df, max_k=12)
    print(f"   Calculated retention for {len(retention_df)} fee-tier × k combinations")

    # Add confidence intervals
    print("\n4. Computing bootstrap confidence intervals...")
    retention_with_ci = add_retention_confidence_intervals(
        retention_df, cohort_df, n_bootstrap=1000
    )
    print("   ✅ Confidence intervals computed")

    # Calculate acquisition by period
    print("\n5. Calculating new user acquisition by period...")
    acquisition_df = calculate_acquisition_by_period(user_df)
    print(f"   Calculated acquisition for {len(acquisition_df)} periods")

    # Export CSVs
    output_dir = Path(__file__).parent.parent.parent / "outputs"
    output_dir.mkdir(exist_ok=True)

    print("\n6. Exporting CSVs...")

    cohort_path = output_dir / "user_cohorts.csv"
    cohort_df.to_csv(cohort_path, index=False)
    print(f"   ✅ {cohort_path}")

    retention_path = output_dir / "retention_by_fee.csv"
    retention_with_ci.to_csv(retention_path, index=False)
    print(f"   ✅ {retention_path}")

    acquisition_path = output_dir / "acquisition_by_period.csv"
    acquisition_df.to_csv(acquisition_path, index=False)
    print(f"   ✅ {acquisition_path}")

    # Summary stats
    print("\n" + "=" * 60)
    print("COHORT ANALYSIS SUMMARY")
    print("=" * 60)

    print("\nUsers by acquisition fee tier:")
    for fee_bps in sorted(cohort_df["first_seen_fee_bps"].unique()):
        count = (cohort_df["first_seen_fee_bps"] == fee_bps).sum()
        pct = count / len(cohort_df) * 100
        print(f"  {fee_bps:5.1f} bps: {count:6,} users ({pct:5.1f}%)")

    print("\nRetention at k=1 (1 week later):")
    k1_retention = retention_with_ci[retention_with_ci["k"] == 1]
    for _, row in k1_retention.iterrows():
        print(
            f"  {row['acquisition_fee_bps']:5.1f} bps: {row['retention_rate']*100:5.1f}% "
            f"[{row['ci_low']*100:5.1f}%, {row['ci_high']*100:5.1f}%]"
        )

    print("\nRetention at k=4 (4 weeks later):")
    k4_retention = retention_with_ci[retention_with_ci["k"] == 4]
    for _, row in k4_retention.iterrows():
        print(
            f"  {row['acquisition_fee_bps']:5.1f} bps: {row['retention_rate']*100:5.1f}% "
            f"[{row['ci_low']*100:5.1f}%, {row['ci_high']*100:5.1f}%]"
        )

    print("\n" + "=" * 60)
    print("✅ COHORT ANALYSIS COMPLETE")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
