# THORChain Fee Experiment - dbt Project

This dbt project contains SQL transformations for the THORChain fee experiment analysis.

## Project Structure

```
dbt/
├── models/
│   ├── sources/         # Source definitions (raw Snowflake tables/views)
│   ├── staging/         # Cleaned and normalized base tables
│   ├── intermediate/    # Intermediate transformations and joins
│   ├── marts/           # Final fact tables and reports for dashboard
│   └── analyses/        # Ad-hoc analytical queries
├── macros/              # Reusable Jinja macros
├── seeds/               # Static CSV data (e.g., manual period definitions)
├── snapshots/           # Slowly changing dimension snapshots
├── tests/               # Custom data tests
└── dbt_project.yml      # Project configuration
```

## Model Layers

### Sources (`models/sources/`)
- Defines connections to raw Snowflake tables in `9R.FEE_EXPERIMENT` schema
- Documents source freshness and schema expectations

### Staging (`models/staging/`)
- Cleaned and normalized versions of source tables
- Column renaming, type casting, basic filtering
- Prefix: `stg_*`

### Intermediate (`models/intermediate/`)
- Business logic transformations
- Joins between staging models
- Aggregations not yet ready for final consumption
- Prefix: `int_*`

### Marts (`models/marts/`)
- Final data products consumed by dashboards
- Fact tables: `fct_*`
- Reports: `rpt_*`
- Optimized for query performance

## Configuration

### Connection Profile

Create or update `~/.dbt/profiles.yml`:

```yaml
thorchain_snowflake:
  target: prod
  outputs:
    prod:
      type: snowflake
      account: '{{ env_var("SNOWFLAKE_ACCOUNT") }}'
      user: '{{ env_var("SNOWFLAKE_USER") }}'
      password: '{{ env_var("SNOWFLAKE_PASSWORD") }}'
      role: '{{ env_var("SNOWFLAKE_ROLE", "ANALYST") }}'
      warehouse: '{{ env_var("SNOWFLAKE_WAREHOUSE") }}'
      database: '{{ env_var("SNOWFLAKE_DATABASE", "9R") }}'
      schema: '{{ env_var("DBT_SCHEMA", "FEE_EXPERIMENT_MARTS") }}'
      threads: 4
      client_session_keep_alive: false
```

### Environment Variables

Required for local development:

```bash
export SNOWFLAKE_ACCOUNT=your_account
export SNOWFLAKE_USER=your_user
export SNOWFLAKE_PASSWORD=your_password
export SNOWFLAKE_ROLE=ANALYST
export SNOWFLAKE_WAREHOUSE=your_warehouse
export SNOWFLAKE_DATABASE=9R
export DBT_SCHEMA=FEE_EXPERIMENT_MARTS
```

For Streamlit deployment, set these in `.streamlit/secrets.toml` or cloud secrets.

## Commands

All commands should be run from the project root using PDM scripts:

```bash
# Validate connection and configuration
pdm run dbt-debug

# Install dbt packages (if any dependencies in packages.yml)
pdm run dbt-deps

# Run all models
pdm run dbt-run

# Run all tests
pdm run dbt-test

# Build everything (run + test)
pdm run dbt-build

# Run specific model and its downstream dependencies
cd dbt && dbt run --select stg_swaps_experiment_window+

# Run only marts
cd dbt && dbt run --select marts.*

# Generate and serve documentation
cd dbt && dbt docs generate && dbt docs serve
```

## Development Workflow

1. **Create/modify models**: Edit `.sql` files in appropriate layer
2. **Add schema tests**: Define tests in `schema.yml` files alongside models
3. **Run and test**: `pdm run dbt-build` to validate changes
4. **Document**: Add descriptions in YAML files and model docstrings
5. **Review in dashboard**: Streamlit app queries from `marts` schema

## Schema Naming Convention

Models are materialized into schemas based on their layer:
- Staging: `9R.FEE_EXPERIMENT_STAGING`
- Intermediate: `9R.FEE_EXPERIMENT_INTERMEDIATE`
- Marts: `9R.FEE_EXPERIMENT_MARTS`
- Seeds: `9R.FEE_EXPERIMENT_STAGING`

Dashboard queries should reference `FEE_EXPERIMENT_MARTS` for best performance.

## Testing

dbt tests validate data quality:

1. **Schema tests** (defined in YAML):
   - `not_null`, `unique`, `relationships`, `accepted_values`

2. **Custom data tests** (defined in `tests/`):
   - SQL queries that return failing rows

3. **Test failures** are stored in `9R.FEE_EXPERIMENT_TEST_RESULTS`

## Migration from Legacy SQL

Original SQL scripts in `sql/` have been migrated to dbt models:

| Legacy Script | dbt Model | Layer |
|---------------|-----------|-------|
| `01_stage_swaps_experiment_window.sql` | `stg_swaps_experiment_window.sql` | staging |
| `02_daily_fee_bps.sql` | `int_daily_fee_bps.sql` | intermediate |
| `05_weekly_summary.sql` | `int_weekly_summary.sql` | intermediate |
| `14_weekly_summary_final.sql` | `fct_weekly_summary_final.sql` | marts |
| ... | ... | ... |

See model migration map in project docs.
