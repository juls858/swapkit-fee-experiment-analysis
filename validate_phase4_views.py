"""
Validate Phase 4 Views (Read-Only)
Views have already been created, this script just validates the data
"""

import snowflake.connector

# Connect with thorchain_prod (read-only is fine for validation)
conn = snowflake.connector.connect(
    account="DIPQQTY-EIC35197",
    user="popsql",
    password="AFA-wct_xzr0gax_uwg",
    database="9R",
    schema="FEE_EXPERIMENT",
    warehouse="SNOWFLAKE_LEARNING_WH",
    role="DATASHARES_RO",
)

print("\n" + "=" * 80)
print("PHASE 4 SQL VALIDATION - READ-ONLY")
print("=" * 80)
print("\n✅ Connected to Snowflake\n")

cursor = conn.cursor()
all_passed = True

# QA 1: Row counts
print("=" * 80)
print("QA Check 1: Row Counts")
print("=" * 80)

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

cursor.execute(sql)
results = cursor.fetchall()
print()
for row in results:
    print(f"  {row[0]}: {row[1]:,} rows")

pool_summary_count = [r[1] for r in results if r[0] == "V_POOL_WEEKLY_SUMMARY"][0]
elasticity_count = [r[1] for r in results if r[0] == "FCT_POOL_ELASTICITY_INPUTS"][0]

if pool_summary_count >= 100:
    print(f"\n✅ V_POOL_WEEKLY_SUMMARY has {pool_summary_count} rows (≥100 expected)")
else:
    print(f"\n⚠️  V_POOL_WEEKLY_SUMMARY has {pool_summary_count} rows (<100)")
    all_passed = False

if elasticity_count >= 50:
    print(f"✅ FCT_POOL_ELASTICITY_INPUTS has {elasticity_count} rows (≥50 expected)")
else:
    print(f"⚠️  FCT_POOL_ELASTICITY_INPUTS has {elasticity_count} rows (<50)")
    all_passed = False

# QA 2: Duplicate check
print("\n" + "=" * 80)
print("QA Check 2: Duplicate Detection")
print("=" * 80)

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

cursor.execute(sql)
results = cursor.fetchall()
print()
for row in results:
    if row[1] == 0:
        print(f"✅ {row[0]}: No duplicates")
    else:
        print(f"❌ {row[0]}: Found {row[1]} duplicates!")
        all_passed = False

# QA 3: NULL checks
print("\n" + "=" * 80)
print("QA Check 3: NULL Value Detection")
print("=" * 80)

sql = """
SELECT
    SUM(CASE WHEN period_id IS NULL THEN 1 ELSE 0 END) AS null_period_id,
    SUM(CASE WHEN pool_name IS NULL THEN 1 ELSE 0 END) AS null_pool_name,
    SUM(CASE WHEN pool_type IS NULL THEN 1 ELSE 0 END) AS null_pool_type,
    SUM(CASE WHEN final_fee_bps IS NULL THEN 1 ELSE 0 END) AS null_final_fee_bps,
    SUM(CASE WHEN volume_usd IS NULL THEN 1 ELSE 0 END) AS null_volume_usd,
    SUM(CASE WHEN fees_usd IS NULL THEN 1 ELSE 0 END) AS null_fees_usd
FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
"""

cursor.execute(sql)
result = cursor.fetchone()
has_nulls = False
print()
for i, col in enumerate(
    ["period_id", "pool_name", "pool_type", "final_fee_bps", "volume_usd", "fees_usd"]
):
    if result[i] > 0:
        print(f"❌ {col}: {result[i]} nulls found")
        has_nulls = True
        all_passed = False

if not has_nulls:
    print("✅ No NULLs in key columns")

# QA 4: Reconciliation
print("\n" + "=" * 80)
print("QA Check 4: Reconciliation (Pool Sums vs Weekly Totals)")
print("=" * 80)

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

cursor.execute(sql)
result = cursor.fetchone()
tolerance = 0.01
vol_diff = result[0]
fees_diff = result[1]
swaps_diff = result[2]

print()
print(f"Max Volume Difference: {vol_diff:.6f}%")
print(f"Max Fees Difference:   {fees_diff:.6f}%")
print(f"Max Swaps Difference:  {swaps_diff:.6f}%")

if vol_diff <= tolerance:
    print(f"\n✅ Volume reconciliation: {vol_diff:.6f}% (≤{tolerance}%)")
else:
    print(f"\n❌ Volume reconciliation: {vol_diff:.6f}% (>{tolerance}%)")
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
print("\n" + "=" * 80)
print("QA Check 5: Market Share Sum Validation")
print("=" * 80)

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

cursor.execute(sql)
result = cursor.fetchone()
print()
print(f"Total periods: {result[0]}")
print(f"Periods passing: {result[1]}")
print(f"Periods failing: {result[2]}")

if result[2] == 0:
    print(f"\n✅ All {result[0]} periods have valid share sums (≈1.0)")
else:
    print(f"\n❌ {result[2]} periods have invalid share sums")
    all_passed = False

# QA 6: Value ranges
print("\n" + "=" * 80)
print("QA Check 6: Value Range Validation")
print("=" * 80)

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
WHERE final_fee_bps NOT IN (1, 5, 10, 15, 20, 25)
"""

cursor.execute(sql)
results = cursor.fetchall()
has_issues = False
print()
for row in results:
    if row[1] > 0:
        print(f"❌ {row[0]}: {row[1]} issues found")
        has_issues = True
        all_passed = False

if not has_issues:
    print("✅ All value ranges are valid")

# QA 7: Sample data preview
print("\n" + "=" * 80)
print("QA Check 7: Sample Data Preview")
print("=" * 80)

sql = """
SELECT
    period_id,
    pool_name,
    pool_type,
    final_fee_bps,
    pct_change_fee_bps,
    pct_change_volume,
    pct_change_fees
FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS
ORDER BY period_start_date, pool_name
LIMIT 5
"""

cursor.execute(sql)
results = cursor.fetchall()
print("\nFirst 5 rows of FCT_POOL_ELASTICITY_INPUTS:")
print(
    f"\n{'Period':<8} {'Pool':<20} {'Type':<12} {'Fee':<6} {'Δ Fee %':<10} {'Δ Vol %':<10} {'Δ Rev %':<10}"
)
print("-" * 86)
for row in results:
    print(
        f"{row[0]:<8} {row[1][:18]:<20} {row[2]:<12} {row[3]:<6.0f} {row[4]:>9.2f} {row[5]:>9.2f} {row[6]:>9.2f}"
    )

cursor.close()
conn.close()

# Final summary
print("\n" + "=" * 80)
print("FINAL SUMMARY")
print("=" * 80)

if all_passed:
    print("\n" + "🎉" * 40)
    print("✅ ALL QA CHECKS PASSED!")
    print("Phase 4 models are validated and ready for production.")
    print("🎉" * 40)
    print("\n📋 Next step: Launch the dashboard")
    print("   Run: pdm run dashboard")
    print("   Or:  streamlit run dashboards/app/Home.py")
else:
    print("\n" + "⚠️ " * 40)
    print("❌ SOME QA CHECKS FAILED")
    print("Please review the issues above.")
    print("⚠️ " * 40)
