# THORChain Fee Experiment Dashboards

This directory contains the **multipage Streamlit application** for THORChain fee experiment analysis. The dashboard is organized by analysis phase with a central navigation hub.

## Architecture

**Multipage App Structure:**
```
dashboards/app/
├── Home.py                               # Main entry point (hero metrics + navigation)
├── pages/
│   ├── 1_Phase_1__Overview.py           # Phase 1: Weekly summary + data validation
│   ├── 5_Phase_2__Elasticity_Analysis.py # Phase 2: Elasticity & revenue decomposition
│   ├── 6_Phase_4__Pool_Analysis.py.disabled  # Phase 4: Pool-level (planned)
│   └── 7_Phase_3__User_Analysis.py.disabled  # Phase 3: User-level (planned)
└── components/
    ├── __init__.py
    └── formatting.py                     # Shared formatting utilities
```

**Launch the Dashboard:**
```bash
pdm run dashboard
# Runs: streamlit run dashboards/app/Home.py --server.port 8501
```

The app will open at **http://localhost:8501**

## Available Pages

### Home (Entry Point)
**File:** `app/Home.py`

**Purpose:** Hero metrics and phase navigation

**Features:**
- Total volume, fees, swaps, and average fee tier KPIs
- Navigation organized by phase with completion indicators
- Links to Phase 1, Phase 2, and future phases

---

### Phase 1: Overview
**File:** `app/pages/1_Phase_1__Overview.py`

**Status:** ✅ Complete

**Purpose:** Weekly summary and data validation

**Features:**
- Summary statistics by period
- Period details table with filters
- Volume and fees by fee tier (grouped bar charts)
- Revenue metrics over time (rect + rule bars colored by fee tier, fee in tooltips)
- Revenue per swap and per user trends
- Data validation section

**Data Sources:**
- `FCT_WEEKLY_SUMMARY_FINAL` - Weekly aggregated metrics
- `V_FEE_PERIODS_MANUAL` - Experiment period definitions

---

### Phase 2: Elasticity Analysis
**File:** `app/pages/5_Phase_2__Elasticity_Analysis.py`

**Status:** ✅ Complete

**Purpose:** Price elasticity of demand and revenue optimization

**Features:**
- Elasticity scatter plots with regression lines (fee change vs. volume/revenue)
- OLS regression results (PED, revenue elasticity, R²)
- Optimal fee recommendation with caveats
- Empirical best performance comparison
- Revenue decomposition waterfall chart (fee rate, volume, mix, external effects)
- Period-by-period change analysis
- Interactive lightweight-charts overlays (fee changes as histograms, revenue/volume as lines)
- Collapsible "How to Read This Chart" sections with formulas and interpretation

**Data Sources:**
- `FCT_ELASTICITY_INPUTS` - Elasticity analysis inputs with lagged columns
- `FCT_WEEKLY_SUMMARY_FINAL` - Weekly aggregated metrics

**Chart Builders Used:**
- `create_elasticity_scatter()` - Scatter with regression line
- `create_fee_revenue_lightweight_chart()` - Fee change + revenue overlay
- `create_fee_volume_lightweight_chart()` - Fee change + volume overlay
- `create_waterfall_chart()` - Revenue decomposition

---

### Phase 3: User Analysis (Planned)
**File:** `app/pages/7_Phase_3__User_Analysis.py.disabled`

**Status:** 📋 Planned

**Purpose:** User behavior and segmentation

**Planned Features:**
- User cohort analysis
- Retention and churn metrics
- User lifetime value by fee tier
- Segmentation by behavior patterns

---

### Phase 4: Pool Analysis (Planned)
**File:** `app/pages/6_Phase_4__Pool_Analysis.py.disabled`

**Status:** 📋 Planned

**Purpose:** Pool-level performance breakouts

**Planned Features:**
- Pool-specific volume and revenue trends
- Asset pair elasticity analysis
- Liquidity depth impact
- Pool concentration metrics

---

## Development Guidelines

### Creating a New Dashboard

1. **File Naming Convention:**
   - Use descriptive names: `phaseN_purpose.py`
   - Examples: `phase2_revenue_analysis.py`, `pool_comparison.py`

2. **Import Snowflake Connection:**
```python
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session as _get_session

@st.cache_resource(show_spinner=False)
def get_snowpark_session() -> Session:
    return _get_session()
```

3. **Cache Data Loading:**
```python
@st.cache_data(show_spinner=False, ttl=60)
def load_data(_session: Session) -> pd.DataFrame:
    sql = 'SELECT * FROM "9R".FEE_EXPERIMENT.VIEW_NAME'
    df = _session.sql(sql).to_pandas()
    df.columns = df.columns.str.lower()
    return df
```

4. **Add PDM Script:**
Update `pyproject.toml`:
```toml
[tool.pdm.scripts]
my_dashboard = "streamlit run dashboards/my_dashboard.py"
```

5. **Add Ruff Exceptions (if needed):**
```toml
[tool.ruff.lint.per-file-ignores]
"dashboards/my_dashboard.py" = ["F841"]  # Unused variables
```

### Best Practices

#### Performance
- Use `@st.cache_data` for data loading
- Use `@st.cache_resource` for database connections
- Set appropriate TTL for live data: `ttl=60` (seconds)
- Load only necessary columns from Snowflake

#### Layout
- Use `st.set_page_config(layout="wide")` for dashboards with multiple columns
- Organize with `st.columns()`, `st.tabs()`, `st.expander()`
- Keep the UI clean with progressive disclosure

#### User Experience
- Add loading spinners for long operations
- Provide clear error messages
- Include help text and tooltips
- Allow CSV downloads for tables
- Use consistent number formatting

#### Code Organization
- Keep chart functions separate from main logic
- Use components from `dashboards/components/` for reusability
- Document complex queries with comments
- Handle edge cases gracefully (empty data, null values)

### Shared Components

Place reusable components in `dashboards/components/`:
- `metrics.py` - KPI card formatters
- `charts.py` - Common chart templates
- `filters.py` - Shared filter widgets
- `formatters.py` - Number/date formatting utilities

Example usage:
```python
from dashboards.components.metrics import format_currency, format_percentage
```

### Testing Dashboards

Run the dashboard locally:
```bash
pdm run dashboard  # or specific script name
```

Test with different data scenarios:
- Empty results
- Single data point
- Large datasets
- Null/missing values
- Edge date ranges

### Deployment

Streamlit Cloud deployment:
1. Ensure Streamlit secrets are configured in `.streamlit/secrets.toml`
2. Each dashboard can be deployed independently
3. Set appropriate resource limits for large datasets

---

## Dashboard Comparison Matrix

| Dashboard | Phase | Status | Data Volume | Complexity | Target Users |
|-----------|-------|--------|-------------|------------|--------------|
| phase1_data_validation | 1 | ✅ Live | Medium | Low | Data engineers, analysts |
| phase2_revenue_analysis | 2 | 📋 Planned | High | Medium | Business analysts, stakeholders |
| phase3_statistical_analysis | 3 | 📋 Planned | Medium | High | Data scientists, researchers |
| main (landing) | - | 📋 Planned | Low | Low | All users |

---

## Troubleshooting

### Dashboard Won't Start
1. Check Snowflake connection: `pdm run python -c "from thorchain_fee_analysis.data.snowflake_conn import test_connection; print(test_connection())"`
2. Verify port availability: `lsof -ti:8501`
3. Check error logs in terminal

### Slow Performance
1. Add/increase caching with `@st.cache_data`
2. Reduce data volume with WHERE clauses
3. Pre-aggregate data in Snowflake views
4. Use Polars instead of Pandas for large datasets

### Data Not Updating
1. Check cache TTL settings
2. Clear Streamlit cache: Press 'C' in dashboard or restart
3. Verify Snowflake views are refreshed

---

## Resources

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Altair Gallery](https://altair-viz.github.io/gallery/)
- [Plotly Python](https://plotly.com/python/)
- [Snowpark Documentation](https://docs.snowflake.com/en/developer-guide/snowpark/python/index)

---

**Last Updated:** October 30, 2025
**Maintainer:** Julius Remigio
