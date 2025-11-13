# Phase 4 SQL Validation Checklist

**Status:** ⏳ PENDING - SQL queries created but not yet executed/validated
**Date:** 2025-11-13
**Action Required:** Run validation checks before production deployment

---

## Summary

Phase 4 SQL models have been **created and documented** but have **not yet been executed** against Snowflake. The following validation steps must be completed before the dashboard can go live.

---

## SQL Models Created

### 1. Intermediate Model
- **File:** `dbt/models/intermediate/int_pool_elasticity_inputs.sql`
- **Purpose:** Add lagged metrics and % deltas per pool
- **Status:** ⏳ Not built

### 2. Mart Model
- **File:** `dbt/models/marts/fct_pool_elasticity_inputs.sql`
- **Purpose:** Curated pool elasticity inputs
- **Status:** ⏳ Not built

### 3. Schema Tests
- **File:** `dbt/models/marts/schema.yml`
- **Purpose:** Data quality tests (uniqueness, not-null, accepted-values)
- **Status:** ⏳ Not executed

---

## Required Validation Steps

### Step 1: Build dbt Models

```bash
# Navigate to dbt directory
cd dbt/

# Build the new models
dbt run --select int_pool_elasticity_inputs fct_pool_elasticity_inputs

# Expected output:
# ✓ int_pool_elasticity_inputs (view created)
# ✓ fct_pool_elasticity_inputs (view created)
```

**Expected Results:**
- Views created in Snowflake:
  - `9R.FEE_EXPERIMENT.INT_POOL_ELASTICITY_INPUTS`
  - `9R.FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS`

---

### Step 2: Run dbt Tests

```bash
# Run schema tests
dbt test --select fct_pool_weekly_summary fct_pool_elasticity_inputs

# Expected tests:
# ✓ unique_fct_pool_weekly_summary_period_id_pool_name
# ✓ not_null_fct_pool_weekly_summary_period_id
# ✓ not_null_fct_pool_weekly_summary_pool_name
# ✓ not_null_fct_pool_weekly_summary_pool_type
# ✓ accepted_values_fct_pool_weekly_summary_pool_type
# ✓ accepted_values_fct_pool_weekly_summary_final_fee_bps
# ✓ unique_fct_pool_elasticity_inputs_period_id_pool_name
# ✓ not_null_fct_pool_elasticity_inputs_period_id
# ✓ not_null_fct_pool_elasticity_inputs_pool_name
# ✓ not_null_fct_pool_elasticity_inputs_pool_type
# ✓ accepted_values_fct_pool_elasticity_inputs_pool_type
# ✓ accepted_values_fct_pool_elasticity_inputs_final_fee_bps
```

**Expected Results:** All tests pass ✅

---

### Step 3: Manual SQL QA Checks

#### 3.1 Row Count Check

```sql
-- Check that views have data
SELECT 'fct_pool_weekly_summary' AS table_name, COUNT(*) AS row_count
FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
UNION ALL
SELECT 'fct_pool_elasticity_inputs', COUNT(*)
FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS;
```

**Expected Results:**
- `fct_pool_weekly_summary`: 200-300 rows (pools × periods)
- `fct_pool_elasticity_inputs`: 120-180 rows (after filtering)

#### 3.2 Duplicate Check

```sql
-- Check for duplicates (should return 0 rows)
SELECT period_id, pool_name, COUNT(*) AS dup_count
FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
GROUP BY period_id, pool_name
HAVING COUNT(*) > 1;

-- Same for elasticity inputs
SELECT period_id, pool_name, COUNT(*) AS dup_count
FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS
GROUP BY period_id, pool_name
HAVING COUNT(*) > 1;
```

**Expected Results:** 0 rows (no duplicates)

#### 3.3 NULL Check

```sql
-- Check for NULLs in key columns (should return 0 for all)
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN period_id IS NULL THEN 1 ELSE 0 END) AS null_period_id,
    SUM(CASE WHEN pool_name IS NULL THEN 1 ELSE 0 END) AS null_pool_name,
    SUM(CASE WHEN pool_type IS NULL THEN 1 ELSE 0 END) AS null_pool_type,
    SUM(CASE WHEN final_fee_bps IS NULL THEN 1 ELSE 0 END) AS null_final_fee_bps,
    SUM(CASE WHEN volume_usd IS NULL THEN 1 ELSE 0 END) AS null_volume_usd,
    SUM(CASE WHEN fees_usd IS NULL THEN 1 ELSE 0 END) AS null_fees_usd
FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY;
```

**Expected Results:** All null counts = 0

#### 3.4 Reconciliation Check

```sql
-- Pool sums should match weekly totals (within 0.01%)
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
    p.period_id,
    p.pool_volume,
    w.weekly_volume,
    ABS((p.pool_volume - w.weekly_volume) / w.weekly_volume) * 100 AS volume_diff_pct,
    ABS((p.pool_fees - w.weekly_fees) / w.weekly_fees) * 100 AS fees_diff_pct,
    ABS((p.pool_swaps - w.weekly_swaps) / w.weekly_swaps) * 100 AS swaps_diff_pct,
    CASE
        WHEN ABS((p.pool_volume - w.weekly_volume) / w.weekly_volume) * 100 > 0.01 THEN 'FAIL'
        WHEN ABS((p.pool_fees - w.weekly_fees) / w.weekly_fees) * 100 > 0.01 THEN 'FAIL'
        WHEN ABS((p.pool_swaps - w.weekly_swaps) / w.weekly_swaps) * 100 > 0.01 THEN 'FAIL'
        ELSE 'PASS'
    END AS status
FROM pool_agg p
JOIN weekly w ON p.period_id = w.period_id
ORDER BY p.period_id;
```

**Expected Results:** All rows have status = 'PASS'

#### 3.5 Market Share Sum Check

```sql
-- Market shares should sum to ~1.0 per period
SELECT
    period_id,
    SUM(pct_of_period_volume) AS volume_share_sum,
    SUM(pct_of_period_fees) AS fees_share_sum,
    SUM(pct_of_period_swaps) AS swaps_share_sum,
    CASE
        WHEN ABS(SUM(pct_of_period_volume) - 1.0) > 0.001 THEN 'FAIL'
        WHEN ABS(SUM(pct_of_period_fees) - 1.0) > 0.001 THEN 'FAIL'
        WHEN ABS(SUM(pct_of_period_swaps) - 1.0) > 0.001 THEN 'FAIL'
        ELSE 'PASS'
    END AS status
FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
GROUP BY period_id
HAVING status = 'FAIL';
```

**Expected Results:** 0 rows (all periods pass)

#### 3.6 Value Range Check

```sql
-- Check for unexpected values
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
UNION ALL
SELECT
    'Invalid pool type',
    COUNT(*)
FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
WHERE pool_type NOT IN ('BTC Pool', 'ETH Pool', 'Stablecoin Pool', 'Other Pool');
```

**Expected Results:** All issue_count = 0

#### 3.7 Elasticity Inputs Validation

```sql
-- Check elasticity inputs quality
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN pct_change_fee_bps IS NULL THEN 1 ELSE 0 END) AS null_pct_change_fee,
    SUM(CASE WHEN pct_change_volume IS NULL THEN 1 ELSE 0 END) AS null_pct_change_vol,
    SUM(CASE WHEN pct_change_fees IS NULL THEN 1 ELSE 0 END) AS null_pct_change_fees,
    SUM(CASE WHEN swaps_count < 10 THEN 1 ELSE 0 END) AS below_min_activity,
    SUM(CASE WHEN prev_swaps_count < 10 THEN 1 ELSE 0 END) AS prev_below_min_activity,
    SUM(CASE WHEN pool_type NOT IN ('BTC', 'ETH', 'STABLE', 'LONG_TAIL') THEN 1 ELSE 0 END) AS invalid_pool_type
FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS;
```

**Expected Results:** All issue counts = 0

#### 3.8 Spot Check Calculations

```sql
-- Verify percentage change calculations (spot check first 5 rows)
SELECT
    period_id,
    pool_name,
    final_fee_bps,
    prev_fee_bps,
    pct_change_fee_bps AS calculated_pct,
    ((final_fee_bps - prev_fee_bps) / prev_fee_bps) * 100 AS expected_pct,
    ABS(pct_change_fee_bps - ((final_fee_bps - prev_fee_bps) / prev_fee_bps) * 100) AS diff,
    CASE WHEN ABS(pct_change_fee_bps - ((final_fee_bps - prev_fee_bps) / prev_fee_bps) * 100) > 0.01
         THEN 'FAIL' ELSE 'PASS' END AS status
FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS
LIMIT 5;
```

**Expected Results:** All status = 'PASS'

---

### Step 4: Run Python Validation Script

```bash
# Activate environment with dependencies
pdm install

# Run validation script
python notebooks/03_phase3/validate_phase4_sql.py
```

**Script performs:**
- ✅ Row count checks
- ✅ Duplicate detection
- ✅ NULL value checks
- ✅ Value range validation
- ✅ Market share sum validation
- ✅ Reconciliation checks
- ✅ Spot-check calculations
- ✅ Summary statistics

**Expected Output:**
```
================================================================================
PHASE 4 SQL VALIDATION SCRIPT
================================================================================
✅ Connected to Snowflake

🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍🔍
================================================================================
VALIDATING: fct_pool_weekly_summary
================================================================================
✅ View exists and accessible
📊 Row Count: 250
✅ Row count looks reasonable
✅ No duplicates found
✅ All key columns have no nulls
✅ All fee tiers in expected range
✅ All pool types are valid
✅ All volume values are positive
✅ All fee values are positive
✅ All periods have valid share sums (≈1.0)

[... similar for elasticity inputs and reconciliation ...]

================================================================================
VALIDATION SUMMARY
================================================================================
pool_weekly_summary            ✅ PASS
pool_elasticity_inputs         ✅ PASS
reconciliation                 ✅ PASS

🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉
ALL VALIDATIONS PASSED!
Phase 4 SQL queries are ready for production.
🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉
```

---

### Step 5: Test Dashboard

```bash
# Launch dashboard
pdm run dashboard

# Or if using app structure:
streamlit run dashboards/app/Home.py
```

**Manual Testing:**
1. Navigate to "Phase 4: Pool Analysis" page
2. Verify data loads without errors
3. Test all filters (pool type, date range, top N, fee tiers)
4. Check that all visualizations render correctly
5. Expand validation panel - verify all checks pass
6. Download CSVs and validation report - verify completeness
7. Review executive summary - verify insights are accurate

---

## Validation Checklist

Before marking Phase 4 as production-ready, complete this checklist:

- [ ] **dbt models built** - Views exist in Snowflake
- [ ] **dbt tests pass** - All schema tests green
- [ ] **Row counts reasonable** - 200-300 rows (pool summary), 120-180 rows (elasticity)
- [ ] **No duplicates** - Unique by (period_id, pool_name)
- [ ] **No NULLs** - All key columns populated
- [ ] **Value ranges valid** - Fees in {5,10,15,20,25}, pool types valid
- [ ] **Reconciliation passes** - Pool sums match weekly totals (≤0.01%)
- [ ] **Market shares sum to 100%** - All periods ≈1.0 ± 0.001
- [ ] **Calculations correct** - Spot-checked % changes match formulas
- [ ] **Python validation passes** - All automated checks green
- [ ] **Dashboard loads** - No errors in UI
- [ ] **Filters work** - All filter combinations functional
- [ ] **Charts render** - All 6 visualizations display correctly
- [ ] **Validation panel passes** - Built-in reconciliation checks green
- [ ] **Downloads work** - CSV and report files generate

---

## Known Issues / To-Do

- [ ] **dbt models not yet built** - Need to run `dbt run` first
- [ ] **Dependencies not installed** - Need `pdm install` for validation script
- [ ] **Snowflake connection required** - Need valid credentials in `~/.snowflake/connections.toml` or `.streamlit/secrets.toml`

---

## Deployment Blockers

**Current Status:** 🔴 BLOCKED

**Blockers:**
1. dbt models must be built in Snowflake
2. Schema tests must be executed and pass
3. Manual QA checks must be completed
4. Dashboard must be tested with real data

**Once blockers resolved:** 🟢 READY FOR PRODUCTION

---

## Contact / Questions

If validation checks fail:
1. Review error messages in dbt output
2. Check Snowflake query history for failed queries
3. Review validation script output for specific issues
4. Consult `PHASE4_IMPLEMENTATION_GUIDE.md` for troubleshooting

---

**Document Version:** 1.0
**Last Updated:** 2025-11-13
**Status:** ⏳ Validation Pending
