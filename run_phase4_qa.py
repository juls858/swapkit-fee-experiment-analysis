"""
Build Phase 4 models and run QA checks
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session


def create_views(session):
    """Create/replace Phase 4 views in Snowflake."""
    print("\n" + "=" * 80)
    print("STEP 1: BUILDING DBT MODELS (Creating Views)")
    print("=" * 80)

    # Read SQL files
    int_pool_elasticity = Path("dbt/models/intermediate/int_pool_elasticity_inputs.sql").read_text()
    fct_pool_elasticity = Path("dbt/models/marts/fct_pool_elasticity_inputs.sql").read_text()

    # Remove dbt templating and create views
    # int_pool_elasticity_inputs
    print("\n📝 Creating INT_POOL_ELASTICITY_INPUTS...")

    # Extract SQL (remove config block)
    sql_start = int_pool_elasticity.find("WITH base AS")
    if sql_start == -1:
        print("❌ Could not parse int_pool_elasticity_inputs.sql")
        return False

    int_sql = int_pool_elasticity[sql_start:]
    # Replace dbt refs
    int_sql = int_sql.replace(
        "{{ ref('fct_pool_weekly_summary') }}", '"9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY'
    )

    create_int = f"""
    CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.INT_POOL_ELASTICITY_INPUTS AS
    {int_sql}
    """

    try:
        session.sql(create_int).collect()
        print("✅ INT_POOL_ELASTICITY_INPUTS created successfully")
    except Exception as e:
        print(f"❌ Failed to create INT_POOL_ELASTICITY_INPUTS: {e}")
        return False

    # fct_pool_elasticity_inputs
    print("\n📝 Creating FCT_POOL_ELASTICITY_INPUTS...")

    sql_start = fct_pool_elasticity.find("SELECT")
    if sql_start == -1:
        print("❌ Could not parse fct_pool_elasticity_inputs.sql")
        return False

    fct_sql = fct_pool_elasticity[sql_start:]
    # Replace dbt refs
    fct_sql = fct_sql.replace(
        "{{ ref('int_pool_elasticity_inputs') }}", '"9R".FEE_EXPERIMENT.INT_POOL_ELASTICITY_INPUTS'
    )

    # Create schema if it doesn't exist
    try:
        session.sql('CREATE SCHEMA IF NOT EXISTS "9R".FEE_EXPERIMENT_MARTS').collect()
    except Exception:
        pass

    create_fct = f"""
    CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS AS
    {fct_sql}
    """

    try:
        session.sql(create_fct).collect()
        print("✅ FCT_POOL_ELASTICITY_INPUTS created successfully")
    except Exception as e:
        print(f"❌ Failed to create FCT_POOL_ELASTICITY_INPUTS: {e}")
        return False

    print("\n✅ All views created successfully!")
    return True


def run_qa_checks(session):
    """Run QA validation queries."""
    print("\n" + "=" * 80)
    print("STEP 2: RUNNING QA CHECKS")
    print("=" * 80)

    all_passed = True

    # QA 1: Row counts
    print("\n🔍 QA Check 1: Row Counts")
    print("-" * 80)

    sql = """
    SELECT 'V_POOL_WEEKLY_SUMMARY' AS table_name, COUNT(*) AS row_count
    FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
    UNION ALL
    SELECT 'INT_POOL_ELASTICITY_INPUTS', COUNT(*)
    FROM "9R".FEE_EXPERIMENT.INT_POOL_ELASTICITY_INPUTS
    UNION ALL
    SELECT 'FCT_POOL_ELASTICITY_INPUTS', COUNT(*)
    FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS
    """

    result = session.sql(sql).to_pandas()
    print(result.to_string(index=False))

    pool_summary_count = result[result["TABLE_NAME"] == "V_POOL_WEEKLY_SUMMARY"][
        "ROW_COUNT"
    ].values[0]
    elasticity_count = result[result["TABLE_NAME"] == "FCT_POOL_ELASTICITY_INPUTS"][
        "ROW_COUNT"
    ].values[0]

    if pool_summary_count >= 100:
        print(f"✅ V_POOL_WEEKLY_SUMMARY has {pool_summary_count} rows (≥100 expected)")
    else:
        print(f"⚠️  V_POOL_WEEKLY_SUMMARY has {pool_summary_count} rows (<100)")
        all_passed = False

    if elasticity_count >= 50:
        print(f"✅ FCT_POOL_ELASTICITY_INPUTS has {elasticity_count} rows (≥50 expected)")
    else:
        print(f"⚠️  FCT_POOL_ELASTICITY_INPUTS has {elasticity_count} rows (<50)")
        all_passed = False

    # QA 2: Duplicate check
    print("\n🔍 QA Check 2: Duplicate Detection")
    print("-" * 80)

    sql = """
    SELECT 'V_POOL_WEEKLY_SUMMARY' AS table_name, COUNT(*) AS duplicate_count
    FROM (
        SELECT period_id, pool_name, COUNT(*) AS cnt
        FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
        GROUP BY period_id, pool_name
        HAVING COUNT(*) > 1
    )
    UNION ALL
    SELECT 'FCT_POOL_ELASTICITY_INPUTS', COUNT(*)
    FROM (
        SELECT period_id, pool_name, COUNT(*) AS cnt
        FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS
        GROUP BY period_id, pool_name
        HAVING COUNT(*) > 1
    )
    """

    result = session.sql(sql).to_pandas()
    print(result.to_string(index=False))

    for _, row in result.iterrows():
        if row["DUPLICATE_COUNT"] == 0:
            print(f"✅ {row['TABLE_NAME']}: No duplicates")
        else:
            print(f"❌ {row['TABLE_NAME']}: Found {row['DUPLICATE_COUNT']} duplicates!")
            all_passed = False

    # QA 3: NULL checks
    print("\n🔍 QA Check 3: NULL Value Detection")
    print("-" * 80)

    sql = """
    SELECT
        'V_POOL_WEEKLY_SUMMARY' AS table_name,
        SUM(CASE WHEN period_id IS NULL THEN 1 ELSE 0 END) AS null_period_id,
        SUM(CASE WHEN pool_name IS NULL THEN 1 ELSE 0 END) AS null_pool_name,
        SUM(CASE WHEN pool_type IS NULL THEN 1 ELSE 0 END) AS null_pool_type,
        SUM(CASE WHEN final_fee_bps IS NULL THEN 1 ELSE 0 END) AS null_final_fee_bps,
        SUM(CASE WHEN volume_usd IS NULL THEN 1 ELSE 0 END) AS null_volume_usd,
        SUM(CASE WHEN fees_usd IS NULL THEN 1 ELSE 0 END) AS null_fees_usd
    FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
    """

    result = session.sql(sql).to_pandas()
    print(result.to_string(index=False))

    null_cols = [col for col in result.columns if "null_" in col.lower()]
    has_nulls = False
    for col in null_cols:
        if result[col].values[0] > 0:
            print(f"❌ {col}: {result[col].values[0]} nulls found")
            has_nulls = True
            all_passed = False

    if not has_nulls:
        print("✅ No NULLs in key columns")

    # QA 4: Reconciliation
    print("\n🔍 QA Check 4: Reconciliation (Pool Sums vs Weekly Totals)")
    print("-" * 80)

    sql = """
    WITH pool_agg AS (
        SELECT
            period_id,
            SUM(volume_usd) AS pool_volume,
            SUM(fees_usd) AS pool_fees,
            SUM(swaps_count) AS pool_swaps
        FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
        GROUP BY period_id
    ),
    weekly AS (
        SELECT
            period_id,
            volume_usd AS weekly_volume,
            fees_usd AS weekly_fees,
            swaps_count AS weekly_swaps
        FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL
    )
    SELECT
        MAX(ABS((p.pool_volume - w.weekly_volume) / w.weekly_volume) * 100) AS max_volume_diff_pct,
        MAX(ABS((p.pool_fees - w.weekly_fees) / w.weekly_fees) * 100) AS max_fees_diff_pct,
        MAX(ABS((p.pool_swaps - w.weekly_swaps) / w.weekly_swaps) * 100) AS max_swaps_diff_pct
    FROM pool_agg p
    JOIN weekly w ON p.period_id = w.period_id
    """

    result = session.sql(sql).to_pandas()
    print(result.to_string(index=False))

    tolerance = 0.01
    vol_diff = result["MAX_VOLUME_DIFF_PCT"].values[0]
    fees_diff = result["MAX_FEES_DIFF_PCT"].values[0]
    swaps_diff = result["MAX_SWAPS_DIFF_PCT"].values[0]

    if vol_diff <= tolerance:
        print(f"✅ Volume reconciliation: {vol_diff:.6f}% (≤{tolerance}%)")
    else:
        print(f"❌ Volume reconciliation: {vol_diff:.6f}% (>{tolerance}%)")
        all_passed = False

    if fees_diff <= tolerance:
        print(f"✅ Fees reconciliation: {fees_diff:.6f}% (≤{tolerance}%)")
    else:
        print(f"❌ Fees reconciliation: {fees_diff:.6f}% (>{tolerance}%)")
        all_passed = False

    if swaps_diff <= tolerance:
        print(f"✅ Swaps reconciliation: {swaps_diff:.6f}% (≤{tolerance}%)")
    else:
        print(f"❌ Swaps reconciliation: {swaps_diff:.6f}% (>{tolerance}%)")
        all_passed = False

    # QA 5: Market share validation
    print("\n🔍 QA Check 5: Market Share Sum Validation")
    print("-" * 80)

    sql = """
    SELECT
        COUNT(*) AS total_periods,
        SUM(CASE WHEN ABS(volume_share_sum - 1.0) <= 0.001 THEN 1 ELSE 0 END) AS periods_passing,
        SUM(CASE WHEN ABS(volume_share_sum - 1.0) > 0.001 THEN 1 ELSE 0 END) AS periods_failing
    FROM (
        SELECT
            period_id,
            SUM(pct_of_period_volume) AS volume_share_sum
        FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
        GROUP BY period_id
    )
    """

    result = session.sql(sql).to_pandas()
    print(result.to_string(index=False))

    if result["PERIODS_FAILING"].values[0] == 0:
        print(f"✅ All {result['TOTAL_PERIODS'].values[0]} periods have valid share sums (≈1.0)")
    else:
        print(f"❌ {result['PERIODS_FAILING'].values[0]} periods have invalid share sums")
        all_passed = False

    # QA 6: Value ranges
    print("\n🔍 QA Check 6: Value Range Validation")
    print("-" * 80)

    sql = """
    SELECT
        'Negative volume' AS check_type,
        COUNT(*) AS issue_count
    FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
    WHERE volume_usd < 0
    UNION ALL
    SELECT
        'Negative fees',
        COUNT(*)
    FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
    WHERE fees_usd < 0
    UNION ALL
    SELECT
        'Invalid fee tier',
        COUNT(*)
    FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
    WHERE final_fee_bps NOT IN (5, 10, 15, 20, 25)
    """

    result = session.sql(sql).to_pandas()
    print(result.to_string(index=False))

    has_issues = False
    for _, row in result.iterrows():
        if row["ISSUE_COUNT"] > 0:
            print(f"❌ {row['CHECK_TYPE']}: {row['ISSUE_COUNT']} issues found")
            has_issues = True
            all_passed = False

    if not has_issues:
        print("✅ All value ranges are valid")

    return all_passed


def main():
    print("\n" + "🚀" * 40)
    print("PHASE 4: BUILD MODELS & RUN QA CHECKS")
    print("🚀" * 40)

    try:
        print("\n📡 Connecting to Snowflake...")
        session = get_snowpark_session()
        print(f"✅ Connected to: {session.get_current_database()}.{session.get_current_schema()}")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    # Step 1: Create views
    if not create_views(session):
        print("\n❌ Failed to create views. Aborting QA checks.")
        return

    # Step 2: Run QA checks
    all_passed = run_qa_checks(session)

    # Summary
    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    if all_passed:
        print("\n" + "🎉" * 40)
        print("✅ ALL QA CHECKS PASSED!")
        print("Phase 4 models are validated and ready for production.")
        print("🎉" * 40)
        print("\n📋 Next step: Launch the dashboard with `pdm run dashboard`")
    else:
        print("\n" + "⚠️ " * 40)
        print("❌ SOME QA CHECKS FAILED")
        print("Please review the issues above.")
        print("⚠️ " * 40)


if __name__ == "__main__":
    main()
