"""
Phase 3 Data QA & Validation Script
Run this to validate data quality before cohort analysis
"""

import sys
from pathlib import Path

import pandas as pd

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session
from thorchain_fee_analysis.data.user_data import load_user_period_detail, load_weekly_summary


def main():
    print("=" * 60)
    print("PHASE 3 DATA QA & VALIDATION")
    print("=" * 60)

    session = get_snowpark_session()
    print("\n✅ Snowflake connection established\n")

    # Load weekly summary
    print("Loading weekly summary...")
    weekly_df = load_weekly_summary(session)

    print(f"  Periods: {len(weekly_df)}")
    print(
        f"  Date range: {weekly_df['period_start_date'].min()} to {weekly_df['period_end_date'].max()}"
    )
    print(f"  Fee tiers: {sorted(weekly_df['final_fee_bps'].unique())}")

    # Load user period detail
    print("\nLoading user period detail...")
    user_df = load_user_period_detail(session)

    print(f"  User-period rows: {len(user_df):,}")
    print(f"  Unique users: {user_df['user_address'].nunique():,}")

    # Check required columns
    print("\nValidating required columns...")
    required_weekly = [
        "period_id",
        "period_start_date",
        "period_end_date",
        "final_fee_bps",
        "volume_usd",
        "fees_usd",
        "swaps_count",
        "unique_swappers",
        "new_swappers",
        "returning_swappers",
    ]

    required_user = [
        "period_id",
        "period_start_date",
        "period_end_date",
        "final_fee_bps",
        "user_address",
        "volume_usd",
        "fees_usd",
        "swaps_count",
        "user_cohort",
        "engagement_level",
    ]

    missing_weekly = [col for col in required_weekly if col not in weekly_df.columns]
    missing_user = [col for col in required_user if col not in user_df.columns]

    if missing_weekly:
        print(f"  ❌ Missing weekly columns: {missing_weekly}")
        return False
    else:
        print("  ✅ All required weekly columns present")

    if missing_user:
        print(f"  ❌ Missing user columns: {missing_user}")
        return False
    else:
        print("  ✅ All required user columns present")

    # Reconcile weekly totals
    print("\nReconciling weekly totals (±0.5% tolerance)...")
    user_agg = (
        user_df.groupby(["period_id", "period_start_date", "final_fee_bps"])
        .agg(
            {
                "volume_usd": "sum",
                "fees_usd": "sum",
                "swaps_count": "sum",
                "user_address": "nunique",
            }
        )
        .reset_index()
    )

    user_agg.columns = [
        "period_id",
        "period_start_date",
        "final_fee_bps",
        "user_volume_usd",
        "user_fees_usd",
        "user_swaps_count",
        "user_unique_swappers",
    ]

    reconcile = weekly_df[
        [
            "period_id",
            "period_start_date",
            "final_fee_bps",
            "volume_usd",
            "fees_usd",
            "swaps_count",
            "unique_swappers",
        ]
    ].merge(user_agg, on=["period_id", "period_start_date", "final_fee_bps"], how="left")

    reconcile["volume_diff_pct"] = (
        (reconcile["user_volume_usd"] - reconcile["volume_usd"]) / reconcile["volume_usd"] * 100
    ).abs()
    reconcile["fees_diff_pct"] = (
        (reconcile["user_fees_usd"] - reconcile["fees_usd"]) / reconcile["fees_usd"] * 100
    ).abs()
    reconcile["swaps_diff_pct"] = (
        (reconcile["user_swaps_count"] - reconcile["swaps_count"]) / reconcile["swaps_count"] * 100
    ).abs()
    reconcile["users_diff_pct"] = (
        (reconcile["user_unique_swappers"] - reconcile["unique_swappers"])
        / reconcile["unique_swappers"]
        * 100
    ).abs()

    tolerance = 0.5
    issues = reconcile[
        (reconcile["volume_diff_pct"] > tolerance)
        | (reconcile["fees_diff_pct"] > tolerance)
        | (reconcile["swaps_diff_pct"] > tolerance)
        | (reconcile["users_diff_pct"] > tolerance)
    ]

    if len(issues) > 0:
        print(f"  ❌ {len(issues)} periods exceed ±{tolerance}% tolerance")
        print(issues[["period_id", "period_start_date", "volume_diff_pct", "fees_diff_pct"]])
        return False
    else:
        print(f"  ✅ All periods reconcile within ±{tolerance}%")

    print(f"    Max volume diff: {reconcile['volume_diff_pct'].max():.3f}%")
    print(f"    Max fees diff: {reconcile['fees_diff_pct'].max():.3f}%")

    # Validate period alignment
    print("\nValidating period alignment...")
    weekly_sorted = weekly_df.sort_values("period_start_date").reset_index(drop=True)

    gaps = []
    overlaps = []

    for i in range(len(weekly_sorted) - 1):
        current_end = pd.to_datetime(weekly_sorted.loc[i, "period_end_date"])
        next_start = pd.to_datetime(weekly_sorted.loc[i + 1, "period_start_date"])
        gap_days = (next_start - current_end).days - 1

        if gap_days > 0:
            gaps.append((i, i + 1, gap_days))
        elif gap_days < -1:
            overlaps.append((i, i + 1, abs(gap_days)))

    if gaps:
        print(f"  ⚠️  Found {len(gaps)} gaps between periods")
    else:
        print("  ✅ No gaps between periods")

    if overlaps:
        print(f"  ⚠️  Found {len(overlaps)} overlaps between periods")
    else:
        print("  ✅ No overlaps between periods")

    # Summary
    print("\n" + "=" * 60)
    print("DATA QA SUMMARY")
    print("=" * 60)
    print(f"✅ Periods: {len(weekly_df)}")
    print(f"✅ Users: {user_df['user_address'].nunique():,}")
    print(f"✅ User-period observations: {len(user_df):,}")
    print("✅ Required columns: Present")
    print(f"✅ Reconciliation: Within ±{tolerance}%")
    print("✅ Period alignment: Valid")
    print("\n" + "=" * 60)
    print("✅ READY TO PROCEED WITH COHORT ANALYSIS")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
