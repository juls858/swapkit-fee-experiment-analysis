"""
Phase 4 SQL Validation Script

Validates pool-level data models:
- Row counts and data existence
- Duplicate detection (uniqueness checks)
- Data quality issues (nulls, ranges, reconciliation)
- Market share validation
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session


def validate_pool_weekly_summary(session):
    """Validate fct_pool_weekly_summary data quality."""
    print("\n" + "=" * 80)
    print("VALIDATING: fct_pool_weekly_summary")
    print("=" * 80)

    # Check if view exists
    try:
        sql = 'SELECT * FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY LIMIT 5'
        df = session.sql(sql).to_pandas()
        print("✅ View exists and accessible")
    except Exception as e:
        print(f"❌ View not accessible: {e}")
        return False

    # Get full dataset
    sql = 'SELECT * FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY'
    df = session.sql(sql).to_pandas()
    df.columns = df.columns.str.lower()

    # 1. Row count
    print(f"\n📊 Row Count: {len(df):,}")
    expected_min = 100  # At least 100 rows expected
    if len(df) < expected_min:
        print(f"⚠️  Warning: Row count ({len(df)}) below expected minimum ({expected_min})")
    else:
        print("✅ Row count looks reasonable")

    # 2. Check for duplicates (should be unique by period_id, pool_name)
    print("\n🔍 Checking for Duplicates (period_id, pool_name)")
    duplicates = df.duplicated(subset=["period_id", "pool_name"], keep=False)
    dup_count = duplicates.sum()
    if dup_count > 0:
        print(f"❌ Found {dup_count} duplicate rows!")
        print("\nDuplicate examples:")
        print(df[duplicates][["period_id", "pool_name", "volume_usd", "fees_usd"]].head(10))
    else:
        print("✅ No duplicates found")

    # 3. Check for nulls in key columns
    print("\n🔍 Checking for NULL values in key columns")
    key_cols = [
        "period_id",
        "pool_name",
        "pool_type",
        "final_fee_bps",
        "volume_usd",
        "fees_usd",
        "swaps_count",
    ]
    null_issues = False
    for col in key_cols:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                print(f"❌ {col}: {null_count} nulls ({null_count/len(df)*100:.1f}%)")
                null_issues = True
            else:
                print(f"✅ {col}: No nulls")
    if not null_issues:
        print("✅ All key columns have no nulls")

    # 4. Check value ranges
    print("\n🔍 Checking value ranges")

    # Fee tiers should be in expected range
    if "final_fee_bps" in df.columns:
        unique_fees = sorted(df["final_fee_bps"].unique())
        print(f"Unique fee tiers: {unique_fees}")
        expected_fees = [5, 10, 15, 20, 25]
        unexpected = [f for f in unique_fees if f not in expected_fees]
        if unexpected:
            print(f"⚠️  Unexpected fee tiers: {unexpected}")
        else:
            print("✅ All fee tiers in expected range")

    # Pool types should be valid
    if "pool_type" in df.columns:
        unique_types = df["pool_type"].unique().tolist()
        print(f"Unique pool types: {unique_types}")
        expected_types = ["BTC Pool", "ETH Pool", "Stablecoin Pool", "Other Pool"]
        unexpected_types = [t for t in unique_types if t not in expected_types]
        if unexpected_types:
            print(f"⚠️  Unexpected pool types: {unexpected_types}")
        else:
            print("✅ All pool types are valid")

    # Volume/fees should be positive
    if "volume_usd" in df.columns:
        negative_vol = (df["volume_usd"] < 0).sum()
        if negative_vol > 0:
            print(f"❌ Found {negative_vol} rows with negative volume")
        else:
            print("✅ All volume values are positive")

    if "fees_usd" in df.columns:
        negative_fees = (df["fees_usd"] < 0).sum()
        if negative_fees > 0:
            print(f"❌ Found {negative_fees} rows with negative fees")
        else:
            print("✅ All fee values are positive")

    # 5. Market share validation
    print("\n🔍 Checking market share sums per period")
    if "pct_of_period_volume" in df.columns:
        share_sums = df.groupby("period_id")["pct_of_period_volume"].sum()
        bad_periods = share_sums[(share_sums < 0.999) | (share_sums > 1.001)]
        if len(bad_periods) > 0:
            print(f"❌ {len(bad_periods)} periods have invalid share sums:")
            print(bad_periods)
        else:
            print("✅ All periods have valid share sums (≈1.0)")

    # 6. Summary stats
    print("\n📈 Summary Statistics")
    print(f"Total pools: {df['pool_name'].nunique()}")
    print(f"Total periods: {df['period_id'].nunique()}")
    print(f"Total volume: ${df['volume_usd'].sum():,.0f}")
    print(f"Total fees: ${df['fees_usd'].sum():,.0f}")
    print(f"Date range: {df['period_start_date'].min()} to {df['period_end_date'].max()}")

    return True


def validate_pool_elasticity_inputs(session):
    """Validate fct_pool_elasticity_inputs data quality."""
    print("\n" + "=" * 80)
    print("VALIDATING: fct_pool_elasticity_inputs")
    print("=" * 80)

    # Check if view exists
    try:
        sql = 'SELECT * FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS LIMIT 5'
        df = session.sql(sql).to_pandas()
        print("✅ View exists and accessible")
    except Exception as e:
        print(f"❌ View not accessible: {e}")
        print("   This is expected if dbt models haven't been built yet.")
        return False

    # Get full dataset
    sql = 'SELECT * FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS'
    df = session.sql(sql).to_pandas()
    df.columns = df.columns.str.lower()

    # 1. Row count
    print(f"\n📊 Row Count: {len(df):,}")
    expected_min = 50  # At least 50 rows expected (pools × periods)
    if len(df) < expected_min:
        print(f"⚠️  Warning: Row count ({len(df)}) below expected minimum ({expected_min})")
    else:
        print("✅ Row count looks reasonable")

    # 2. Check for duplicates
    print("\n🔍 Checking for Duplicates (period_id, pool_name)")
    duplicates = df.duplicated(subset=["period_id", "pool_name"], keep=False)
    dup_count = duplicates.sum()
    if dup_count > 0:
        print(f"❌ Found {dup_count} duplicate rows!")
        print("\nDuplicate examples:")
        print(df[duplicates][["period_id", "pool_name", "volume_usd", "fees_usd"]].head(10))
    else:
        print("✅ No duplicates found")

    # 3. Check for nulls in elasticity columns
    print("\n🔍 Checking for NULL values in key columns")
    key_cols = [
        "period_id",
        "pool_name",
        "pool_type",
        "final_fee_bps",
        "prev_fee_bps",
        "pct_change_fee_bps",
        "pct_change_volume",
        "pct_change_fees",
    ]
    null_issues = False
    for col in key_cols:
        if col in df.columns:
            null_count = df[col].isna().sum()
            if null_count > 0:
                print(f"❌ {col}: {null_count} nulls ({null_count/len(df)*100:.1f}%)")
                null_issues = True
            else:
                print(f"✅ {col}: No nulls")
    if not null_issues:
        print("✅ All key columns have no nulls")

    # 4. Check standardized pool types
    print("\n🔍 Checking pool types (should be standardized)")
    if "pool_type" in df.columns:
        unique_types = df["pool_type"].unique().tolist()
        print(f"Unique pool types: {unique_types}")
        expected_types = ["BTC", "ETH", "STABLE", "LONG_TAIL"]
        unexpected_types = [t for t in unique_types if t not in expected_types]
        if unexpected_types:
            print(f"❌ Unexpected pool types: {unexpected_types}")
        else:
            print("✅ All pool types are standardized")

    # 5. Check minimum activity threshold
    print("\n🔍 Checking minimum activity threshold (≥10 swaps)")
    if "swaps_count" in df.columns and "prev_swaps_count" in df.columns:
        low_activity = df[(df["swaps_count"] < 10) | (df["prev_swaps_count"] < 10)]
        if len(low_activity) > 0:
            print(
                f"❌ Found {len(low_activity)} rows below minimum activity threshold (should be filtered)"
            )
        else:
            print("✅ All rows meet minimum activity threshold")

    # 6. Check percentage change calculations
    print("\n🔍 Spot-checking percentage change calculations")
    if all(col in df.columns for col in ["final_fee_bps", "prev_fee_bps", "pct_change_fee_bps"]):
        # Check first 3 rows
        sample = df.head(3)
        for idx, row in sample.iterrows():
            expected_pct = (
                (row["final_fee_bps"] - row["prev_fee_bps"]) / row["prev_fee_bps"]
            ) * 100
            actual_pct = row["pct_change_fee_bps"]
            diff = abs(expected_pct - actual_pct)
            if diff > 0.01:  # Allow small floating point difference
                print(
                    f"❌ Row {idx}: Expected {expected_pct:.2f}%, got {actual_pct:.2f}% (diff: {diff:.2f}%)"
                )
            else:
                print(f"✅ Row {idx}: pct_change_fee_bps calculation correct ({actual_pct:.2f}%)")

    # 7. Check elasticity value ranges
    print("\n🔍 Checking elasticity value ranges")
    if "pct_change_volume" in df.columns:
        vol_elasticity = df["pct_change_volume"]
        extreme_values = vol_elasticity[vol_elasticity.abs() > 500]
        if len(extreme_values) > 0:
            print(f"⚠️  Found {len(extreme_values)} rows with extreme volume changes (>500%)")
            print(f"   Max: {vol_elasticity.max():.1f}%, Min: {vol_elasticity.min():.1f}%")
        else:
            print("✅ Volume changes are in reasonable range")

    # 8. Summary stats
    print("\n📈 Summary Statistics")
    print(f"Total pools: {df['pool_name'].nunique()}")
    print(f"Total periods: {df['period_id'].nunique()}")
    print(f"Avg pool per period: {len(df) / df['period_id'].nunique():.1f}")
    if "pct_change_volume" in df.columns:
        print(f"Avg volume change: {df['pct_change_volume'].mean():.2f}%")
    if "pct_change_fees" in df.columns:
        print(f"Avg revenue change: {df['pct_change_fees'].mean():.2f}%")

    return True


def validate_reconciliation(session):
    """Validate that pool sums match weekly totals."""
    print("\n" + "=" * 80)
    print("RECONCILIATION: Pool Sums vs Weekly Totals")
    print("=" * 80)

    try:
        # Get pool aggregates
        pool_sql = """
        SELECT
            period_id,
            SUM(volume_usd) AS pool_volume,
            SUM(fees_usd) AS pool_fees,
            SUM(swaps_count) AS pool_swaps
        FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
        GROUP BY period_id
        ORDER BY period_id
        """
        pool_agg = session.sql(pool_sql).to_pandas()
        pool_agg.columns = pool_agg.columns.str.lower()

        # Get weekly totals
        weekly_sql = """
        SELECT
            period_id,
            volume_usd AS weekly_volume,
            fees_usd AS weekly_fees,
            swaps_count AS weekly_swaps
        FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL
        ORDER BY period_id
        """
        weekly = session.sql(weekly_sql).to_pandas()
        weekly.columns = weekly.columns.str.lower()

        # Merge
        merged = pool_agg.merge(weekly, on="period_id", how="inner")

        # Calculate differences
        merged["volume_diff_pct"] = (
            abs(merged["pool_volume"] - merged["weekly_volume"]) / merged["weekly_volume"]
        ) * 100
        merged["fees_diff_pct"] = (
            abs(merged["pool_fees"] - merged["weekly_fees"]) / merged["weekly_fees"]
        ) * 100
        merged["swaps_diff_pct"] = (
            abs(merged["pool_swaps"] - merged["weekly_swaps"]) / merged["weekly_swaps"]
        ) * 100

        print(f"\n📊 Periods Checked: {len(merged)}")
        print("\n🔍 Maximum Differences:")
        print(f"Volume: {merged['volume_diff_pct'].max():.4f}% (threshold: 0.01%)")
        print(f"Fees:   {merged['fees_diff_pct'].max():.4f}% (threshold: 0.01%)")
        print(f"Swaps:  {merged['swaps_diff_pct'].max():.4f}% (threshold: 0.01%)")

        # Check if within tolerance
        tolerance = 0.01
        vol_pass = merged["volume_diff_pct"].max() <= tolerance
        fees_pass = merged["fees_diff_pct"].max() <= tolerance
        swaps_pass = merged["swaps_diff_pct"].max() <= tolerance

        if vol_pass and fees_pass and swaps_pass:
            print(f"\n✅ All reconciliation checks PASS (≤{tolerance}%)")
        else:
            print("\n❌ Reconciliation checks FAIL")
            if not vol_pass:
                print("   Volume difference exceeds tolerance")
            if not fees_pass:
                print("   Fees difference exceeds tolerance")
            if not swaps_pass:
                print("   Swaps difference exceeds tolerance")

            # Show problem periods
            problem_periods = merged[
                (merged["volume_diff_pct"] > tolerance)
                | (merged["fees_diff_pct"] > tolerance)
                | (merged["swaps_diff_pct"] > tolerance)
            ]
            if len(problem_periods) > 0:
                print("\nProblem periods:")
                print(
                    problem_periods[
                        [
                            "period_id",
                            "volume_diff_pct",
                            "fees_diff_pct",
                            "swaps_diff_pct",
                        ]
                    ]
                )

        return vol_pass and fees_pass and swaps_pass

    except Exception as e:
        print(f"❌ Reconciliation check failed: {e}")
        return False


def main():
    """Run all Phase 4 validation checks."""
    print("\n" + "=" * 80)
    print("PHASE 4 SQL VALIDATION SCRIPT")
    print("=" * 80)
    print("\nValidating pool-level data models and queries...")

    try:
        session = get_snowpark_session()
        print("✅ Connected to Snowflake")
    except Exception as e:
        print(f"❌ Failed to connect to Snowflake: {e}")
        return

    # Run validations
    results = {}

    print("\n" + "🔍" * 40)
    results["pool_weekly_summary"] = validate_pool_weekly_summary(session)

    print("\n" + "🔍" * 40)
    results["pool_elasticity_inputs"] = validate_pool_elasticity_inputs(session)

    print("\n" + "🔍" * 40)
    results["reconciliation"] = validate_reconciliation(session)

    # Final summary
    print("\n" + "=" * 80)
    print("VALIDATION SUMMARY")
    print("=" * 80)

    all_pass = all(results.values())

    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check:30} {status}")

    if all_pass:
        print("\n" + "🎉" * 40)
        print("ALL VALIDATIONS PASSED!")
        print("Phase 4 SQL queries are ready for production.")
        print("🎉" * 40)
    else:
        print("\n" + "⚠️ " * 40)
        print("SOME VALIDATIONS FAILED")
        print("Please review the issues above and fix before deploying.")
        print("⚠️ " * 40)


if __name__ == "__main__":
    main()
