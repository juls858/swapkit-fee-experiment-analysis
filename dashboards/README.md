# THORChain Fee Experiment Dashboards

This directory contains multiple Streamlit dashboards for different phases and aspects of the THORChain fee experiment analysis.

## Available Dashboards

### Phase 1: Data Validation
**File:** `phase1_data_validation.py`

**Purpose:** Validate data quality and experiment design integrity

**Features:**
- Weekly swap volume and revenue metrics
- Fee tier period visualization
- Revenue confidence intervals
- Experiment timeline validation
- Pool-level analysis
- Data quality checks

**Launch:**
```bash
pdm run phase1
# or
pdm run dashboard  # default
# or
streamlit run dashboards/phase1_data_validation.py
```

**Data Sources:**
- `V_WEEKLY_SUMMARY_FINAL` - Aggregated weekly metrics
- `V_FEE_PERIODS_MANUAL` - Experiment period definitions
- `V_PERIOD_REVENUE_CI` - Revenue confidence intervals

---

### Phase 2: Revenue Analysis (Planned)
**File:** `phase2_revenue_analysis.py` (to be created)

**Purpose:** Deep dive into revenue patterns and optimization

**Planned Features:**
- Revenue by fee tier comparison
- Pool-specific revenue analysis
- Affiliate impact analysis
- Time-series revenue trends
- Breakeven analysis
- Revenue forecasting

**Launch:**
```bash
pdm run phase2
```

---

### Phase 3: Statistical Analysis (Planned)
**File:** `phase3_statistical_analysis.py` (to be created)

**Purpose:** Statistical tests and elasticity modeling

**Planned Features:**
- Demand elasticity calculations
- Statistical significance tests
- A/B test analysis
- Causal inference models
- Sensitivity analysis
- Recommendation engine

**Launch:**
```bash
pdm run phase3
```

---

### Main Landing Page (Planned)
**File:** `main.py` (to be created)

**Purpose:** Navigation hub for all dashboards

**Features:**
- Overview of all available dashboards
- Quick links to each phase
- Project status summary
- Data freshness indicators

**Launch:**
```bash
pdm run dashboards
```

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
