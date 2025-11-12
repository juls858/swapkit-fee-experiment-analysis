# SQL Query Validation Report

**Date:** November 5, 2025
**Purpose:** Verify all SQL queries in dashboard pages execute successfully

## Summary

✅ **Phase 2 Elasticity Analysis:** All queries validated and working
⚠️ **Phase 1 Pages:** 2 pages reference non-existent views

---

## Query Validation Results

### ✅ Home.py
```sql
SELECT * FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL
```
**Status:** ✅ PASS - View exists, query executes successfully

---

### ✅ 01_Weekly_Summary.py
```sql
SELECT * FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL ORDER BY period_start_date
```
**Status:** ✅ PASS - View exists, query executes successfully

---

### ❌ 02_Pool_Analysis.py
```sql
SELECT * FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY ORDER BY period_start_date, volume_usd DESC
```
**Status:** ❌ FAIL - View does not exist
**Error:** `SQL compilation error: Object '"9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY' does not exist or not authorized`

**Impact:** Pool Analysis page will fail to load

**Recommendation:** This view was never created in Phase 1. Options:
1. Create the view from swap-level data aggregated by pool
2. Remove or disable this page until the view is created
3. Use V_SWAPS_EXPERIMENT_WINDOW and aggregate in Python

---

### ❌ 03_User_Analysis.py
```sql
SELECT * FROM "9R".FEE_EXPERIMENT.V_USER_WEEKLY_SUMMARY ORDER BY period_start_date, volume_usd DESC
```
**Status:** ❌ FAIL - View does not exist
**Error:** `SQL compilation error: Object '"9R".FEE_EXPERIMENT.V_USER_WEEKLY_SUMMARY' does not exist or not authorized`

**Impact:** User Analysis page will fail to load

**Recommendation:** This view was never created in Phase 1. Options:
1. Create the view from swap-level data aggregated by user
2. Remove or disable this page until the view is created
3. Use V_SWAPS_EXPERIMENT_WINDOW and aggregate in Python

---

### ✅ 04_Data_Validation.py

**Query 1:**
```sql
SELECT * FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL
```
**Status:** ✅ PASS

**Query 2:**
```sql
SELECT * FROM "9R".FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL
```
**Status:** ✅ PASS

**Query 3:**
```sql
SELECT * FROM "9R".FEE_EXPERIMENT.V_PERIOD_REVENUE_CI
```
**Status:** ✅ PASS

---

### ✅ 05_Elasticity_Analysis.py (Phase 2)

**Query 1:**
```sql
SELECT * FROM "9R".FEE_EXPERIMENT_MARTS.FCT_ELASTICITY_INPUTS ORDER BY period_start_date
```
**Status:** ✅ PASS - 7 rows returned

**Query 2:**
```sql
SELECT
    period_id,
    period_start_date,
    period_end_date,
    final_fee_bps,
    prev_fee_bps,
    volume_usd,
    prev_volume_usd,
    fees_usd,
    prev_fees_usd,
    swaps_count,
    prev_swaps_count,
    avg_swap_size_usd,
    prev_avg_swap_size_usd,
    unique_swappers,
    prev_unique_swappers
FROM "9R".FEE_EXPERIMENT_MARTS.FCT_ELASTICITY_INPUTS
ORDER BY period_start_date
```
**Status:** ✅ PASS - All columns exist, query executes successfully

---

## Available Views in 9R.FEE_EXPERIMENT

| View Name | Purpose | Status |
|-----------|---------|--------|
| `V_WEEKLY_SUMMARY_FINAL` | Weekly aggregated metrics | ✅ Exists |
| `V_FEE_PERIODS_MANUAL` | Manual fee period definitions | ✅ Exists |
| `V_PERIOD_REVENUE_CI` | Revenue confidence intervals | ✅ Exists |
| `V_SWAPS_EXPERIMENT_WINDOW` | Swap-level detail data | ✅ Exists |
| `V_ELASTICITY_INPUTS` | Intermediate elasticity data | ✅ Exists |
| `FCT_ELASTICITY_INPUTS` | Final elasticity mart | ✅ Exists |
| `V_DAILY_FEE_BPS` | Daily fee aggregates | ✅ Exists |
| `V_FEE_ANOMALIES` | Fee deviation detection | ✅ Exists |
| `V_FEE_PERIODS_FINAL` | Final fee period definitions | ✅ Exists |
| `V_POOL_WEEKLY_SUMMARY` | Pool-level weekly metrics | ❌ Does not exist |
| `V_USER_WEEKLY_SUMMARY` | User-level weekly metrics | ❌ Does not exist |

---

## Available Views in 9R.FEE_EXPERIMENT_MARTS

| View Name | Purpose | Status |
|-----------|---------|--------|
| `FCT_ELASTICITY_INPUTS` | Elasticity analysis mart | ✅ Exists |
| `FCT_WEEKLY_SUMMARY_FINAL` | Weekly summary mart | ✅ Exists |

---

## Recommendations

### Immediate Actions

1. **Phase 2 (Elasticity Analysis):** ✅ No action needed - all queries validated
2. **Phase 1 (Pool & User Analysis):** ⚠️ Two options:
   - **Option A:** Create the missing views in Snowflake
   - **Option B:** Comment out or hide the broken pages in navigation

### Option A: Create Missing Views

**V_POOL_WEEKLY_SUMMARY:**
```sql
CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY AS
WITH swaps_with_period AS (
    SELECT
        s.*,
        p.period_id,
        p.period_start_date,
        p.period_end_date,
        p.fee_bps AS final_fee_bps
    FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW s
    LEFT JOIN "9R".FEE_EXPERIMENT.V_FEE_PERIODS_FINAL p
        ON s.swap_date BETWEEN p.period_start_date AND p.period_end_date
)
SELECT
    period_id,
    period_start_date,
    period_end_date,
    pool_name,
    pool_type,
    COUNT(*) AS swaps_count,
    SUM(gross_volume_usd) AS volume_usd,
    SUM(total_fee_usd) AS fees_usd,
    COUNT(DISTINCT from_address) AS unique_swappers,
    AVG(gross_volume_usd) AS avg_swap_size_usd,
    MEDIAN(gross_volume_usd) AS median_swap_size_usd
FROM swaps_with_period
WHERE period_id IS NOT NULL
GROUP BY 1,2,3,4,5
ORDER BY period_start_date, volume_usd DESC;
```

**V_USER_WEEKLY_SUMMARY:**
```sql
CREATE OR REPLACE VIEW "9R".FEE_EXPERIMENT.V_USER_WEEKLY_SUMMARY AS
WITH swaps_with_period AS (
    SELECT
        s.*,
        p.period_id,
        p.period_start_date,
        p.period_end_date,
        p.fee_bps AS final_fee_bps,
        MIN(s.swap_date) OVER (PARTITION BY s.from_address) AS first_swap_date
    FROM "9R".FEE_EXPERIMENT.V_SWAPS_EXPERIMENT_WINDOW s
    LEFT JOIN "9R".FEE_EXPERIMENT.V_FEE_PERIODS_FINAL p
        ON s.swap_date BETWEEN p.period_start_date AND p.period_end_date
)
SELECT
    period_id,
    period_start_date,
    period_end_date,
    from_address AS user_address,
    COUNT(*) AS swaps_count,
    SUM(gross_volume_usd) AS volume_usd,
    SUM(total_fee_usd) AS fees_usd,
    AVG(gross_volume_usd) AS avg_swap_size_usd,
    MIN(swap_date) AS first_swap_in_period,
    MAX(swap_date) AS last_swap_in_period,
    (MIN(swap_date) = first_swap_date) AS is_new_user
FROM swaps_with_period
WHERE period_id IS NOT NULL
GROUP BY 1,2,3,4
ORDER BY period_start_date, volume_usd DESC;
```

### Option B: Hide Broken Pages

Update `dashboards/app/Home.py` to comment out the broken page links:

```python
# Phase 1: Data Validation & Exploratory Analysis
st.markdown("### Phase 1: Data Validation & Exploratory Analysis")
col1, col2 = st.columns(2)

with col1:
    st.page_link(
        "pages/01_Weekly_Summary.py",
        label="📈 Weekly Summary",
        help="Period-by-period metrics and trends",
    )
    # st.page_link(
    #     "pages/02_Pool_Analysis.py",
    #     label="🏊 Pool Analysis",
    #     help="Pool-level performance and sensitivity",
    # )

with col2:
    # st.page_link(
    #     "pages/03_User_Analysis.py",
    #     label="👥 User Analysis",
    #     help="User behavior and cohort analysis",
    # )
    st.page_link(
        "pages/04_Data_Validation.py",
        label="✅ Data Validation",
        help="Quality checks and validation report",
    )
```

---

## Conclusion

**Phase 2 Implementation:** ✅ Fully validated - all SQL queries execute successfully

**Phase 1 Pages:** ⚠️ 2 out of 4 pages have SQL errors due to missing views that were never created

**Next Steps:**
1. Decide whether to create missing views or hide broken pages
2. Update dashboard navigation accordingly
3. Document which Phase 1 features are available vs. planned
