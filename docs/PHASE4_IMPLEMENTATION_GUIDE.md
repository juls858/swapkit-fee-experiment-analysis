# Phase 4 Implementation Guide: Pool & Asset Analysis

## Overview

Phase 4 analyzes pool-level performance and fee sensitivity during the THORChain fee experiment. This guide documents the data models, validation procedures, dashboard features, and analytical insights for pool-level analysis.

**Deliverables:**
- Pool-level elasticity inputs (dbt marts)
- Comprehensive validation and reconciliation
- Interactive Streamlit dashboard with pool insights
- Pool-specific elasticity metrics and visualizations

---

## Data Models

### Source Tables

- **`V_SWAPS_EXPERIMENT_WINDOW`**: Staged swap data for experiment period
- **`V_FEE_PERIODS_FINAL`**: Fee period definitions (manual + auto)
- **`V_WEEKLY_SUMMARY_FINAL`**: Aggregated weekly metrics (for reconciliation)

### Intermediate Models

#### `int_pool_elasticity_inputs.sql`

**Purpose:** Add lagged metrics and period-over-period changes per pool

**Grain:** One row per pool per fee period transition (excludes first period per pool)

**Key Features:**
- Lagged metrics partitioned by `pool_name` (prev_fee_bps, prev_volume_usd, prev_fees_usd, etc.)
- Percentage changes: `pct_change_fee_bps`, `pct_change_volume`, `pct_change_fees`
- Market share changes: `pct_change_market_share_volume`, `pct_change_market_share_fees`
- Time trends: `time_trend_pool` (per pool), `time_trend_global` (overall)

**Filters:**
- Excludes first period per pool (no lagged data)
- Includes all pools with activity in experiment window

**Location:** `dbt/models/intermediate/int_pool_elasticity_inputs.sql`

### Mart Models

#### `fct_pool_weekly_summary.sql`

**Purpose:** Pool-level summary metrics by fee period

**Grain:** One row per pool per fee period

**Key Columns:**
- `period_id`, `period_start_date`, `period_end_date`, `final_fee_bps`
- `pool_name`, `pool_type` (BTC Pool, ETH Pool, Stablecoin Pool, Other Pool)
- `swaps_count`, `volume_usd`, `fees_usd`, `unique_swappers`, `avg_swap_size_usd`
- `pct_of_period_swaps`, `pct_of_period_volume`, `pct_of_period_fees` (market share)

**Tests:**
- Unique by (period_id, pool_name)
- Not null: period_id, pool_name, pool_type, volume_usd, fees_usd, swaps_count
- Accepted values: final_fee_bps ∈ {5, 10, 15, 20, 25}
- Accepted values: pool_type ∈ {BTC Pool, ETH Pool, Stablecoin Pool, Other Pool}

**Location:** `dbt/models/marts/fct_pool_weekly_summary.sql`

#### `fct_pool_elasticity_inputs.sql`

**Purpose:** Curated pool elasticity inputs for Phase 4 analysis

**Grain:** One row per pool per fee period transition

**Key Columns:**
- All columns from `int_pool_elasticity_inputs`
- Standardized `pool_type` (BTC, ETH, STABLE, LONG_TAIL)
- Revenue metrics: `revenue_per_swap_usd`, `revenue_per_user_usd`

**Filters:**
- Valid elasticity data (non-null pct_change_fee_bps, pct_change_volume, pct_change_fees)
- Minimum activity threshold: swaps_count >= 10 AND prev_swaps_count >= 10

**Tests:**
- Unique by (period_id, pool_name)
- Not null: period_id, pool_name, pool_type, final_fee_bps, prev_fee_bps
- Accepted values: pool_type ∈ {BTC, ETH, STABLE, LONG_TAIL}
- Accepted values: final_fee_bps ∈ {5, 10, 15, 20, 25}

**Location:** `dbt/models/marts/fct_pool_elasticity_inputs.sql`

---

## Data Dictionary

### Pool Type Classification

| Pool Type | Description | Examples |
|-----------|-------------|----------|
| BTC | Bitcoin pools | BTC.BTC, BTC-ETH |
| ETH | Ethereum pools | ETH.ETH, ETH-USDC |
| STABLE | Stablecoin pairs | USDC.USDC, USDT-USDC |
| LONG_TAIL | Other assets | RUNE, ATOM, DOGE |

### Key Metrics

| Metric | Description | Formula |
|--------|-------------|---------|
| `fees_usd` | Pool revenue (USD) | Sum of total_fee_usd per pool |
| `volume_usd` | Pool volume (USD) | Sum of gross_volume_usd per pool |
| `pct_of_period_volume` | Pool market share (volume) | pool_volume / period_total_volume |
| `pct_of_period_fees` | Pool market share (revenue) | pool_fees / period_total_fees |
| `pct_change_volume` | Volume elasticity | ((current - prev) / prev) × 100 |
| `pct_change_fees` | Revenue elasticity | ((current - prev) / prev) × 100 |
| `revenue_per_swap_usd` | Efficiency metric | fees_usd / swaps_count |

---

## Validation & QA

### dbt Tests

Run all pool-level tests:

```bash
pdm run dbt-test -s fct_pool_weekly_summary fct_pool_elasticity_inputs
```

**Expected Results:**
- All uniqueness tests pass (period_id, pool_name combinations)
- All not-null tests pass
- All accepted-values tests pass (pool_type, final_fee_bps)

### Reconciliation Checks

#### 1. Pool Sums vs Weekly Totals

**Purpose:** Ensure pool-level aggregations match weekly summary

**Query:**
```sql
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
    ABS((p.pool_volume - w.weekly_volume) / w.weekly_volume) * 100 AS volume_diff_pct,
    ABS((p.pool_fees - w.weekly_fees) / w.weekly_fees) * 100 AS fees_diff_pct,
    ABS((p.pool_swaps - w.weekly_swaps) / w.weekly_swaps) * 100 AS swaps_diff_pct
FROM pool_agg p
JOIN weekly w ON p.period_id = w.period_id
WHERE volume_diff_pct > 0.01 OR fees_diff_pct > 0.01 OR swaps_diff_pct > 0.01;
```

**Expected:** Zero rows (all differences ≤ 0.01%)

#### 2. Market Share Sum Validation

**Purpose:** Ensure market shares sum to 100% per period

**Query:**
```sql
SELECT
    period_id,
    SUM(pct_of_period_volume) AS volume_share_sum,
    SUM(pct_of_period_fees) AS fees_share_sum,
    SUM(pct_of_period_swaps) AS swaps_share_sum
FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
GROUP BY period_id
HAVING
    ABS(volume_share_sum - 1.0) > 0.001
    OR ABS(fees_share_sum - 1.0) > 0.001
    OR ABS(swaps_share_sum - 1.0) > 0.001;
```

**Expected:** Zero rows (all sums ≈ 1.0 ± 0.001)

#### 3. Minimum Activity Threshold

**Purpose:** Verify pools meet minimum activity requirements

**Query:**
```sql
SELECT
    COUNT(*) AS low_activity_rows
FROM "9R".FEE_EXPERIMENT_MARTS.FCT_POOL_ELASTICITY_INPUTS
WHERE swaps_count < 10 OR prev_swaps_count < 10;
```

**Expected:** Zero rows (all pools have ≥10 swaps per period)

---

## Dashboard Features

### Location

`dashboards/app/pages/6_Phase_4__Pool_Analysis.py`

### Data Sources

- **`V_POOL_WEEKLY_SUMMARY`**: Pool summary metrics
- **`FCT_POOL_ELASTICITY_INPUTS`**: Pool elasticity data
- **`V_WEEKLY_SUMMARY_FINAL`**: Weekly totals (for reconciliation)

### Filters

- **Pool Type:** All, BTC, ETH, STABLE, LONG_TAIL
- **Date Range:** Derived from data (Aug 15 - Oct 31, 2025)
- **Top N Pools:** 5-30 (default: 10)
- **Fee Tiers:** Multi-select (5, 10, 15, 20, 25 bps)

### KPI Cards

1. **Total Fees:** Sum of fees_usd (selected range)
2. **Total Volume:** Sum of volume_usd (selected range)
3. **Total Swaps:** Sum of swaps_count
4. **Unique Pools:** Count of distinct pool_name
5. **Realized Fee:** Weighted average fee rate (bps)
6. **Unique Swappers:** Sum of unique_swappers

### Visualizations

#### 1. Leaderboard Table

**Purpose:** Rank pools by revenue contribution

**Columns:**
- Pool name
- Pool type
- Total volume (formatted: $1.2M)
- Total revenue (formatted: $123K)
- Total swaps (formatted: 1,234)
- Share of fees (formatted: 12.3%)

**Sorting:** Descending by revenue

#### 2. Revenue Treemap

**Chart Type:** Plotly Treemap

**Purpose:** Show pool revenue distribution by type

**Features:**
- Hierarchical: pool_type → pool_name
- Size: fees_usd
- Color: pool_type (BTC=#F7931A, ETH=#627EEA, STABLE=#26A17B, LONG_TAIL=#95A5A6)
- Tooltip: Pool name, revenue, share %

#### 3. Small Multiples: Revenue Trends

**Chart Type:** Altair Faceted Line Charts

**Purpose:** Show revenue trends for top pools

**Features:**
- Facets: Top 6 pools (3 columns × 2 rows)
- X-axis: Period start date
- Y-axis: Revenue (USD)
- Color: Fee tier (bps)
- Tooltip: Pool, date, revenue, fee tier

#### 4. Elasticity Scatter Plots

**Chart Type:** Altair Scatter + Regression

**Purpose:** Visualize pool-level price and revenue elasticity

**Two Panels:**
- **Left:** Price Elasticity (x=Δ fee %, y=Δ volume %)
- **Right:** Revenue Elasticity (x=Δ fee %, y=Δ revenue %)

**Features:**
- Points colored by pool_type
- Regression line (red dashed)
- Tooltip: Pool name, period, changes, fee tier

#### 5. Pool × Fee Tier Heatmap

**Chart Type:** Altair Heatmap

**Purpose:** Show average revenue response by pool and fee tier

**Features:**
- X-axis: Fee tier (bps)
- Y-axis: Pool name (top 15 by revenue)
- Color: Average pct_change_fees (red-yellow-green scale)
- Text annotations: Percentage values

#### 6. Market Share Evolution

**Chart Type:** Altair Stacked Area

**Purpose:** Show how pool market share changed over time

**Features:**
- X-axis: Period start date
- Y-axis: Market share (normalized to 100%)
- Color: Pool name (top 10 + "Other")
- Tooltip: Pool, date, share %

### Validation Panel

**Location:** Expandable section at bottom of dashboard

**Features:**
1. **Reconciliation Metrics:**
   - Periods checked
   - Max volume difference (%)
   - Max fees difference (%)
   - Max swaps difference (%)
   - Status: PASS (≤0.01%) or REVIEW

2. **Share Sum Validation:**
   - Volume share sum pass rate (%)
   - Fees share sum pass rate (%)
   - Expected: ≥99%

3. **Download Buttons:**
   - Pool weekly summary CSV
   - Pool elasticity inputs CSV
   - Validation report (Markdown)

---

## Analytical Insights

### Key Questions Answered

1. **Which pools drive revenue?**
   - Leaderboard and treemap show top revenue contributors
   - BTC and ETH pools typically dominate

2. **How do pools respond to fee changes?**
   - Elasticity scatter plots reveal pool-level sensitivity
   - Heatmap shows response patterns by fee tier

3. **Do different pool types have different elasticities?**
   - Color-coded scatter plots group by pool type
   - BTC pools may be less elastic (high utility)
   - Long-tail pools may be more elastic (speculative)

4. **How did market share shift during the experiment?**
   - Stacked area chart shows share evolution
   - Identify pools that gained/lost share at different fee tiers

### Interpretation Guidelines

#### Price Elasticity of Demand (PED)

- **PED < -1 (Elastic):** Volume drops significantly when fees increase
  - Revenue-maximizing fee is lower
  - Pool is fee-sensitive

- **-1 ≤ PED < 0 (Inelastic):** Volume drops slightly when fees increase
  - Revenue increases with higher fees
  - Pool is fee-insensitive

#### Revenue Elasticity

- **Positive:** Revenue increases when fees increase (optimal zone)
- **Negative:** Revenue decreases when fees increase (fees too high)

#### Pool Type Patterns (Hypotheses)

1. **BTC Pools:** Likely inelastic (high utility, limited alternatives)
2. **Stablecoin Pools:** Moderately elastic (competitive landscape)
3. **Long-Tail Pools:** Highly elastic (speculative, price-sensitive users)

---

## Usage Examples

### 1. Identify Revenue-Optimal Pools

**Goal:** Find pools that generate most revenue at each fee tier

**Steps:**
1. Set fee tier filter to single value (e.g., 15 bps)
2. Review leaderboard table
3. Note top 5 pools by revenue
4. Check elasticity scatter to see if they're fee-sensitive

**Insight:** Prioritize fee optimization for high-revenue, elastic pools

### 2. Detect Market Share Shifts

**Goal:** Identify pools that gained/lost share during high-fee periods

**Steps:**
1. View market share evolution chart
2. Identify periods with fee increases (check fee tier legend)
3. Observe which pools' shares expanded/contracted
4. Cross-reference with elasticity heatmap

**Insight:** Pools gaining share at high fees are less elastic

### 3. Validate Pool Data Quality

**Goal:** Ensure pool-level data reconciles with weekly totals

**Steps:**
1. Expand validation panel
2. Check reconciliation metrics (all should be ≤0.01%)
3. Verify share sum pass rates (should be ≥99%)
4. Download validation report if issues detected

**Insight:** High-quality data enables confident analysis

---

## Performance Optimization

### Caching Strategy

```python
@st.cache_resource(show_spinner=False)
def get_snowpark_session() -> Session:
    return _get_session()

@st.cache_data(show_spinner=False, ttl=60)
def load_pool_summary(_session: Session) -> pd.DataFrame:
    # Cache for 60 seconds
    ...
```

**Benefits:**
- Snowpark session cached across reruns
- Data cached with 60-second TTL (balances freshness and performance)
- Filters and visualizations update instantly (no re-query)

### Query Optimization

- **Indexed columns:** period_id, pool_name (composite unique key)
- **Partition pruning:** Filter by period_start_date for date ranges
- **Aggregation pushdown:** Use Snowflake aggregations (SUM, AVG) before pulling to Python

---

## Troubleshooting

### Issue: "No data available"

**Cause:** dbt models not built or views not materialized

**Solution:**
```bash
pdm run dbt-build -s fct_pool_weekly_summary fct_pool_elasticity_inputs
```

### Issue: Reconciliation differences > 0.01%

**Cause:** Pool-level sums don't match weekly totals

**Diagnosis:**
1. Check for missing pools in `V_POOL_WEEKLY_SUMMARY`
2. Verify period_id alignment between tables
3. Inspect outlier periods in validation query

**Solution:** Re-run dbt models or investigate data quality issues

### Issue: Market share sums ≠ 100%

**Cause:** Calculation error or missing pools

**Diagnosis:**
```sql
SELECT period_id, SUM(pct_of_period_volume) AS share_sum
FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY
GROUP BY period_id
HAVING ABS(share_sum - 1.0) > 0.001;
```

**Solution:** Review window function logic in `fct_pool_weekly_summary.sql`

### Issue: Charts not rendering

**Cause:** Missing required columns or data type mismatch

**Diagnosis:**
- Check browser console for JavaScript errors
- Verify DataFrame columns match chart expectations
- Test with sample data in pytest

**Solution:** Update chart function or fix data pipeline

---

## Next Steps

### Phase 5: Statistical Validation & Modeling

1. **Causal Inference:**
   - Apply regression with controls (BTC price, day-of-week) at pool level
   - Test for heterogeneous treatment effects across pool types

2. **Forecasting:**
   - Build pool-specific demand curves
   - Simulate revenue under different fee scenarios per pool

3. **Dynamic Pricing:**
   - Recommend pool-specific fee tiers
   - Optimize for total revenue across all pools

### Phase 6: Affiliate & Liquidity Impact

1. **Affiliate Analysis:**
   - Cross-reference pool performance with affiliate routing
   - Identify affiliate-pool pairings sensitive to fees

2. **Liquidity Depth:**
   - Correlate pool depth with elasticity
   - Test if deeper pools are less elastic

---

## References

- **dbt Models:** `dbt/models/marts/fct_pool_*.sql`
- **Dashboard:** `dashboards/app/pages/6_Phase_4__Pool_Analysis.py`
- **Chart Helpers:** `src/thorchain_fee_analysis/visualization/charts.py`
- **Tests:** `tests/analysis/test_pool_elasticity.py`, `tests/visualization/test_charts.py`
- **Schema Docs:** `docs/SNOWFLAKE_SWAPKIT_SCHEMA.md`
- **Phase 2 Guide:** `docs/PHASE2_COMPLETE.md` (global elasticity reference)
- **Phase 3 Guide:** `docs/PHASE3_COMPLETE.md` (user segmentation context)

---

**Document Version:** 1.0
**Last Updated:** 2025-11-13
**Author:** Chief Data Scientist
**Status:** Phase 4 Complete
