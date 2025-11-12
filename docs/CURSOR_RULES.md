# THORChain Fee Experiment – Cursor Context Rules

This is the human-readable reference. Machine-readable rules for Cursor are in `.cursor/rules/*.mdc`:
- `.cursor/rules.mdc` - Umbrella rule (always applied)
- `.cursor/rules/python.mdc` - Python, PDM, Ruff, pytest
- `.cursor/rules/streamlit.mdc` - Streamlit dashboard conventions
- `.cursor/rules/dbt.mdc` - dbt model layers and documentation
- `.cursor/rules/sql.mdc` - SQL style and Snowflake specifics
- `.cursor/rules/visualization.mdc` - Chart best practices
- `.cursor/rules/security.mdc` - Credential handling and guardrails

## Scope & Intent

This project analyzes THORChain's fee experiment to determine optimal swap fee tiers through elasticity analysis and revenue decomposition.

**Current Status:**
- Phase 1: Complete (data validation)
- Phase 2: Complete (elasticity analysis & revenue decomposition)
- Phase 3: Planned (statistical testing)
- Phase 4: Planned (pool-level & user-level analysis)

**Focus Areas:**
- Price elasticity of demand (PED) and revenue elasticity
- Revenue decomposition: fee rate, volume, mix, and external effects
- Interactive Streamlit dashboard with multipage architecture
- dbt data transformation pipeline in Snowflake

## Technology Stack & Defaults

- **Python:** 3.13 (latest stable)
- **Package Manager:** PDM (not pip, not poetry, not conda)
- **Data Processing:** Polars (preferred), Pandas (compatibility only)
- **Database:** Snowflake (`9R.FEE_EXPERIMENT` schema)
- **Orchestration:** dbt for data transformation
- **Dashboard:** Streamlit with multipage architecture
- **Visualization:** Altair (declarative), Plotly (interactive), streamlit-lightweight-charts (overlays)
- **Linting/Formatting:** Ruff (replaces Black, isort, flake8)
- **Testing:** pytest with pytest-cov

## Workflow

### Package Management
- **Always use PDM:** `pdm add package-name`, `pdm install`, `pdm run <script>`
- **Never use:** pip, conda, poetry, or any other package manager
- Pre-commit hooks must pass before commits

### Dashboard Launch
- **Multipage app only:** `pdm run dashboard` or `.venv/bin/streamlit run dashboards/app/Home.py --server.port 8501`
- **Kill old processes first:** `pkill -9 -f "streamlit run"` if needed
- Old single-file dashboard (`dashboards/phase1_data_validation.py`) has been removed

### Data & SQL
- **Normalize columns:** Always `df.columns = df.columns.str.lower()` after Snowflake queries
- **Validate in Snowflake first:** Test all SQL queries directly in Snowflake before wiring into UI
- **dbt workflow:** Compile models locally, validate in Snowflake, then deploy

### Pre-Commit
- Runs automatically on commit: ruff lint, ruff format, trailing whitespace, EOF fixer, YAML/TOML/JSON checks
- Run manually: `pdm run lint` and `pdm run format`

## Coding Standards

### Python Style
- **PEP 8** with 100 character line length
- **Type hints** where beneficial (not required everywhere)
- **f-strings** over `.format()` or `%`
- **pathlib.Path** for file operations
- **UTC datetimes:** Handle timezone-aware datetimes properly

### Imports
```python
# Standard library
import os
from pathlib import Path

# Third-party
import pandas as pd
import streamlit as st

# Local
from thorchain_fee_analysis.data import get_snowpark_session
```

### Code Quality
- Avoid catching broad exceptions; handle specific errors
- Use early returns to reduce nesting
- Write docstrings for public functions
- Prefer composition over inheritance

### Naming Conventions
- Functions/variables: `snake_case`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private: `_leading_underscore`
- Allow `# noqa: N806` for conventional statistical names (e.g., `X` for design matrix)

## Data & Snowflake

### Connection
Always use the shared connection module:
```python
from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session

session = get_snowpark_session()
```

### Credential Sources (in priority order)
1. Streamlit secrets (`st.secrets["snowflake"]`)
2. `~/.snowflake/connections.toml` (local dev)
3. Environment variables (CI/CD)

**Never hardcode credentials**

### Caching
```python
# For connections
@st.cache_resource
def get_session():
    return get_snowpark_session()

# For data queries (with TTL for live data)
@st.cache_data(ttl=60, show_spinner=False)
def load_data(_session: Session) -> pd.DataFrame:
    df = _session.sql("SELECT ...").to_pandas()
    df.columns = df.columns.str.lower()  # Always normalize
    return df
```

### Key Schema Objects
- `V_WEEKLY_SUMMARY_FINAL` → Use `FCT_WEEKLY_SUMMARY_FINAL` (mart)
- `V_ELASTICITY_INPUTS` → Use `FCT_ELASTICITY_INPUTS` (mart with lagged fields)
- `V_FEE_PERIODS_MANUAL` → Manual fee period definitions
- `V_SWAPS_EXPERIMENT_WINDOW` → Raw swap data

## dbt Conventions

### Model Layers
- **Staging (`stg_`):** Light transformations on sources, type casting, renaming
- **Intermediate (`int_`):** Business logic, joins, aggregations
- **Marts (`fct_`, `dim_`):** Final analytics-ready tables

### Key Models
- `stg_fee_periods_manual.sql` → Manual fee period staging
- `stg_swaps_experiment_window.sql` → Swaps data staging
- `int_daily_fee_bps.sql` → Daily fee tier calculations
- `int_elasticity_inputs.sql` → Elasticity analysis inputs with lags
- `int_fee_periods_final.sql` → Final period definitions
- `fct_weekly_summary_final.sql` → Weekly aggregated metrics
- `fct_elasticity_inputs.sql` → Mart for elasticity analysis (has lagged columns)
- `fct_pool_weekly_summary.sql` → Pool-level breakouts
- `fct_user_weekly_summary.sql` → User-level breakouts

### Documentation
- All models must have schema YAML with column descriptions
- Use `schema.yml` in each model directory
- Document sources in `sources.yml`

## Dashboard Guidelines

### Architecture
- **Multipage app:** `dashboards/app/Home.py` + pages in `dashboards/app/pages/`
- **Naming:** `N_Phase_M__Page_Title.py` (e.g., `1_Phase_1__Overview.py`, `5_Phase_2__Elasticity_Analysis.py`)
- **Sidebar:** Organized by phase with completion indicators

### Layout
- Use `st.columns()` for side-by-side content
- Provide meaningful help text with `help=` parameter
- Use expanders for optional/advanced sections

### Component Reuse
- Shared formatting utilities in `dashboards/app/components/formatting.py`
- Reusable chart builders in `src/thorchain_fee_analysis/visualization/charts.py`

### Phase 1 Conventions
- Revenue metrics over time: rect + rule bars, colored by fee tier, with fee in tooltips
- Show period start/end dates clearly
- Aggregate metrics (no per-fee breakouts for time series where fee is independent variable)

### Phase 2 Conventions
- Plot fee **changes (deltas)** as independent variable, not absolute fees
- Prioritize revenue over volume in visualizations
- Include model explanations and empirical comparisons
- Clarify ceteris paribus assumptions vs. real-world confounders

## Visualization Best Practices

### Library Selection
- **Altair:** Declarative charts, scatter plots, simple bar/line charts
- **Plotly:** Interactive charts, waterfall charts, custom layouts
- **streamlit-lightweight-charts:** Financial-grade overlays, time-series with multiple series

### Chart Builders
Centralize chart logic in `src/thorchain_fee_analysis/visualization/charts.py`:
- `create_elasticity_scatter()` → Scatter with regression line
- `create_fee_revenue_lightweight_chart()` → Fee change + revenue overlay
- `create_fee_volume_lightweight_chart()` → Fee change + volume overlay
- `create_waterfall_chart()` → Revenue decomposition waterfall

### Visual Design
- **Lightweight-charts overlays:**
  - Histograms for fee changes: transparent (opacity 0.3), orange
  - Lines for revenue/volume: stronger colors, full opacity
  - Hover titles include current fee tier and change context
- **Color consistency:** Use `category10` scheme for fee tiers across Phase 1 charts
- **Tooltips:** Always include current fee, change (delta), and metric value
- **Axis labels:** Clear units (USD, bps, %)

### Data Visualization Principles
- Independent variables (fee changes) on X-axis
- Dependent variables (revenue, volume) on Y-axis
- Handle NaN/Inf values before plotting
- Provide "How to Read This Chart" guidance for complex visualizations

## Testing & Quality

### Test Structure
```
tests/
  analysis/
    test_elasticity.py
    test_revenue_decomposition.py
    test_execution_quality.py
  visualization/
    test_charts.py
  data/
    test_snowflake_conn.py
```

### Best Practices
- Use pytest fixtures for common setup
- Mock Snowflake connections in tests
- Test edge cases (empty data, single observation, NaN/Inf)
- Aim for >80% code coverage

### Known Issues
- **Polars segfault on Python 3.13:** Mark affected tests with `@pytest.mark.skip` and document reason
- Possible future fix: pin Polars version or use fallback to Pandas in CI

### Linting
- Ruff handles linting and formatting (single tool)
- Allow targeted `# noqa: N806` for conventional statistical variable names (e.g., `X` for design matrix)
- Pre-commit hooks enforce all rules

## Do / Don't

### ✅ Do
- Use PDM for all package management
- Cache Snowflake connections and data queries
- Validate all SQL queries in Snowflake before wiring into dashboard
- Centralize chart builders in `visualization/charts.py`
- Write tests for all new functionality
- Normalize Snowflake column names to lowercase
- Use UTC for all timestamps
- Document assumptions and caveats
- Commit with descriptive messages

### ❌ Don't
- Don't use pip, conda, poetry, or other package managers
- Don't hardcode credentials
- Don't commit large data files (CSV, Parquet, JSON)
- Don't bypass pre-commit hooks (`--no-verify`)
- Don't use deprecated Pandas methods
- Don't catch broad exceptions without re-raising
- Don't extrapolate models beyond tested fee ranges without warnings
- Don't plot absolute fees when analyzing fee changes

## Helpful Commands (PDM)

```bash
# Install dependencies
pdm install

# Launch dashboard
pdm run dashboard

# Run tests
pdm run test

# Lint code
pdm run lint

# Format code
pdm run format

# Add dependency
pdm add package-name

# Add dev dependency
pdm add -d package-name
```

## dbt Commands

```bash
# Compile models (check SQL syntax)
cd dbt && dbt compile

# Run models
cd dbt && dbt run

# Test models
cd dbt && dbt test

# Generate documentation
cd dbt && dbt docs generate
cd dbt && dbt docs serve
```

## Model Interpretation Guidelines

### Elasticity Analysis
- **Price Elasticity of Demand (PED):** Measures volume response to fee changes
  - PED < -1: Elastic (volume decreases more than fee increases)
  - PED > -1: Inelastic (volume decreases less than fee increases)
- **Revenue Elasticity:** Measures revenue response to fee changes
  - Positive: Revenue increases with fees
  - Negative: Revenue decreases with fees
- **Optimal Fee:** Where marginal revenue = 0 (ceteris paribus)

### Model vs. Empirical Reality
- **Model predictions:** Assume ceteris paribus (all else equal)
- **Empirical observations:** Include external factors, market conditions, mix effects
- **Discrepancies are expected:** Real-world confounders (crypto volatility, user composition, competing platforms)
- **Always present both:** Model-based optimal fee + empirically best-performing period

### Revenue Decomposition
- **Fee Rate Effect:** Pure impact of changing fee tier
- **Volume Effect:** Impact of volume changes (elasticity response)
- **Mix Effect:** Changes in swap size distribution or asset mix
- **External Effect:** Market conditions, seasonality, competition

## When to Ask

If uncertain about:
- Database schema or query performance
- Statistical methods for Phase 3
- Deployment strategy for production
- New dependencies (check if already available)
- Breaking changes to existing dashboard

## Resources

- **Schema docs:** `docs/SNOWFLAKE_SWAPKIT_SCHEMA.md`
- **Data dictionary:** `docs/swapkit_bigquery_data_dictionary.md`
- **Phase 2 completion report:** `PHASE2_COMPLETE.md`
- **SQL validation:** `SQL_VALIDATION_REPORT.md`
- **Main dashboard:** `dashboards/app/Home.py`
- **Snowflake connection:** `src/thorchain_fee_analysis/data/snowflake_conn.py`
- **Chart builders:** `src/thorchain_fee_analysis/visualization/charts.py`
