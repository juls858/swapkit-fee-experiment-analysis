"""
Comprehensive SQL and Data Validation for Phase 3

Checks:
- Row counts
- Duplicates
- Null values
- Data integrity
- Reconciliation
"""

import sys
from pathlib import Path

import pandas as pd

src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session
from thorchain_fee_analysis.data.user_data import load_user_period_detail, load_weekly_summary


def main():
    print("=" * 70)
    print("PHASE 3 SQL & DATA VALIDATION")
    print("=" * 70)

    session = get_snowpark_session()

    # === 1. Load data ===
    print("\n1. Loading data from Snowflake...")
    user_df = load_user_period_detail(session)
    weekly_df = load_weekly_summary(session)

    print(f"   User-period detail: {len(user_df):,} rows")
    print(f"   Weekly summary: {len(weekly_df):,} rows")

    # === 2. Check for duplicates ===
    print("\n2. Checking for duplicates...")

    # User-period should be unique on (user_address, period_id)
    user_dupes = user_df.duplicated(subset=["user_address", "period_id"]).sum()
    if user_dupes > 0:
        print(f"   ❌ Found {user_dupes} duplicate user-period combinations!")
    else:
        print("   ✅ No duplicates in user-period data")

    # Weekly should be unique on period_id
    weekly_dupes = weekly_df.duplicated(subset=["period_id"]).sum()
    if weekly_dupes > 0:
        print(f"   ❌ Found {weekly_dupes} duplicate periods in weekly data!")
    else:
        print("   ✅ No duplicates in weekly data")

    # === 3. Check for nulls in key columns ===
    print("\n3. Checking for null values in key columns...")

    user_key_cols = [
        "user_address",
        "period_id",
        "volume_usd",
        "fees_usd",
        "swaps_count",
        "final_fee_bps",
    ]
    user_nulls = user_df[user_key_cols].isnull().sum()

    if user_nulls.sum() > 0:
        print("   ⚠️  Null values found in user data:")
        for col, count in user_nulls[user_nulls > 0].items():
            print(f"      {col}: {count} nulls")
    else:
        print("   ✅ No nulls in key user columns")

    weekly_key_cols = [
        "period_id",
        "volume_usd",
        "fees_usd",
        "swaps_count",
        "unique_swappers",
        "final_fee_bps",
    ]
    weekly_nulls = weekly_df[weekly_key_cols].isnull().sum()

    if weekly_nulls.sum() > 0:
        print("   ⚠️  Null values found in weekly data:")
        for col, count in weekly_nulls[weekly_nulls > 0].items():
            print(f"      {col}: {count} nulls")
    else:
        print("   ✅ No nulls in key weekly columns")

    # === 4. Validate row counts ===
    print("\n4. Validating row counts...")

    # Check unique users
    unique_users = user_df["user_address"].nunique()
    print(f"   Unique users: {unique_users:,}")

    # Check periods
    unique_periods = user_df["period_id"].nunique()
    expected_periods = len(weekly_df)
    if unique_periods == expected_periods:
        print(f"   ✅ Period count matches: {unique_periods} periods")
    else:
        print(
            f"   ❌ Period mismatch: {unique_periods} in user data vs {expected_periods} in weekly"
        )

    # Check user-period combinations
    expected_max = unique_users * unique_periods
    actual = len(user_df)
    pct_coverage = (actual / expected_max) * 100
    print(f"   User-period coverage: {actual:,} / {expected_max:,} ({pct_coverage:.1f}%)")
    print("   (Lower % is normal - not all users active in all periods)")

    # === 5. Reconcile aggregations ===
    print("\n5. Reconciling user-level vs weekly aggregations...")

    user_agg = (
        user_df.groupby("period_id")
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

    user_agg.columns = ["period_id", "user_volume", "user_fees", "user_swaps", "user_count"]

    comparison = weekly_df[
        ["period_id", "volume_usd", "fees_usd", "swaps_count", "unique_swappers"]
    ].merge(user_agg, on="period_id", how="left")

    comparison["volume_diff_pct"] = abs(
        (comparison["user_volume"] - comparison["volume_usd"]) / comparison["volume_usd"] * 100
    )
    comparison["fees_diff_pct"] = abs(
        (comparison["user_fees"] - comparison["fees_usd"]) / comparison["fees_usd"] * 100
    )
    comparison["swaps_diff_pct"] = abs(
        (comparison["user_swaps"] - comparison["swaps_count"]) / comparison["swaps_count"] * 100
    )
    comparison["users_diff_pct"] = abs(
        (comparison["user_count"] - comparison["unique_swappers"])
        / comparison["unique_swappers"]
        * 100
    )

    max_vol_diff = comparison["volume_diff_pct"].max()
    max_fee_diff = comparison["fees_diff_pct"].max()
    max_swap_diff = comparison["swaps_diff_pct"].max()
    max_user_diff = comparison["users_diff_pct"].max()

    tolerance = 0.5

    if max_vol_diff <= tolerance:
        print(f"   ✅ Volume reconciles (max diff: {max_vol_diff:.3f}%)")
    else:
        print(f"   ❌ Volume mismatch (max diff: {max_vol_diff:.3f}%)")

    if max_fee_diff <= tolerance:
        print(f"   ✅ Fees reconcile (max diff: {max_fee_diff:.3f}%)")
    else:
        print(f"   ❌ Fees mismatch (max diff: {max_fee_diff:.3f}%)")

    if max_swap_diff <= tolerance:
        print(f"   ✅ Swaps reconcile (max diff: {max_swap_diff:.3f}%)")
    else:
        print(f"   ❌ Swaps mismatch (max diff: {max_swap_diff:.3f}%)")

    if max_user_diff <= tolerance:
        print(f"   ✅ Users reconcile (max diff: {max_user_diff:.3f}%)")
    else:
        print(f"   ❌ Users mismatch (max diff: {max_user_diff:.3f}%)")

    # === 6. Check data ranges ===
    print("\n6. Validating data ranges...")

    # Check for negative values
    neg_volume = (user_df["volume_usd"] < 0).sum()
    neg_fees = (user_df["fees_usd"] < 0).sum()
    neg_swaps = (user_df["swaps_count"] < 0).sum()

    if neg_volume > 0:
        print(f"   ❌ Found {neg_volume} negative volume values!")
    else:
        print("   ✅ No negative volumes")

    if neg_fees > 0:
        print(f"   ❌ Found {neg_fees} negative fee values!")
    else:
        print("   ✅ No negative fees")

    if neg_swaps > 0:
        print(f"   ❌ Found {neg_swaps} negative swap counts!")
    else:
        print("   ✅ No negative swap counts")

    # Check fee tier values
    valid_fees = [1, 5, 10, 15, 25]
    invalid_fees = ~user_df["final_fee_bps"].isin(valid_fees)
    if invalid_fees.sum() > 0:
        print(f"   ❌ Found {invalid_fees.sum()} rows with invalid fee tiers!")
        print(f"      Invalid values: {user_df[invalid_fees]['final_fee_bps'].unique()}")
    else:
        print(f"   ✅ All fee tiers valid: {valid_fees}")

    # === 7. Check CSV outputs ===
    print("\n7. Validating CSV outputs...")

    outputs_dir = Path(__file__).parent.parent.parent / "outputs"
    csv_files = [
        "user_cohorts.csv",
        "retention_by_fee.csv",
        "acquisition_by_period.csv",
        "segment_metrics.csv",
        "segment_elasticity.csv",
        "segment_summary.csv",
        "ltv_by_fee.csv",
    ]

    for csv_file in csv_files:
        csv_path = outputs_dir / csv_file
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            print(f"   ✅ {csv_file}: {len(df):,} rows")

            # Check for duplicates in key CSVs
            if csv_file == "user_cohorts.csv":
                dupes = df.duplicated(subset=["user_address"]).sum()
                if dupes > 0:
                    print(f"      ❌ {dupes} duplicate users!")
            elif csv_file == "retention_by_fee.csv":
                dupes = df.duplicated(subset=["acquisition_fee_bps", "k"]).sum()
                if dupes > 0:
                    print(f"      ❌ {dupes} duplicate fee-k combinations!")
        else:
            print(f"   ❌ {csv_file}: NOT FOUND")

    # === Summary ===
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    all_checks_passed = (
        user_dupes == 0
        and weekly_dupes == 0
        and user_nulls.sum() == 0
        and weekly_nulls.sum() == 0
        and max_vol_diff <= tolerance
        and max_fee_diff <= tolerance
        and max_swap_diff <= tolerance
        and max_user_diff <= tolerance
        and neg_volume == 0
        and neg_fees == 0
        and neg_swaps == 0
        and invalid_fees.sum() == 0
    )

    if all_checks_passed:
        print("\n✅ ALL VALIDATION CHECKS PASSED")
        print("\nData is clean and ready for analysis:")
        print(f"  - {unique_users:,} unique users")
        print(f"  - {len(user_df):,} user-period observations")
        print(f"  - {len(weekly_df)} periods")
        print(f"  - Reconciliation within ±{tolerance}%")
        print("  - No duplicates, nulls, or invalid values")
        return True
    else:
        print("\n⚠️  SOME VALIDATION CHECKS FAILED")
        print("\nPlease review the issues above before proceeding.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
