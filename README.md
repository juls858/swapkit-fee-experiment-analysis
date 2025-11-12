# THORChain Fee Experiment Analysis

A comprehensive analysis toolkit for analyzing THORChain fee experiment data from Snowflake, featuring interactive Streamlit dashboards and statistical analysis tools.

## Project Status

> ✅ **Setup Validated:** All dependencies installed, tests passing, linting clean. See [SETUP_COMPLETE.md](SETUP_COMPLETE.md) for details.

- ✅ **Phase 1**: Complete - Data Foundation & Descriptive Analytics
- ✅ **Phase 2**: Complete - Core Revenue Analysis (Elasticity & Decomposition)
- 📋 **Phase 3**: Planned - User Behavior & Segmentation
- 📋 **Phase 4**: Planned - Pool & Asset Analysis
- 📋 **Phase 5**: Planned - Statistical Validation & Modeling

## Overview

This project analyzes THORChain's fee experiment data to understand the impact of different fee tiers on swap volume, revenue, and user behavior. The analysis uses data from Snowflake's `9R.FEE_EXPERIMENT` schema and provides interactive visualizations through Streamlit dashboards.

### Key Features

- **Phase 2 Elasticity Analysis**: Price elasticity of demand, revenue optimization, and decomposition
- **Optimal Fee Recommendation**: Data-driven fee tier recommendation with confidence intervals
- **Revenue Decomposition**: Waterfall analysis of fee rate, volume, mix, and external effects
- **Multipage Dashboard**: Interactive Streamlit app with 5 analysis pages
- **dbt Data Pipeline**: SQL transformations organized in staging/intermediate/marts layers
- **Data Quality**: Automated dbt tests ensure data integrity
- **Robust Connection**: Snowflake connection with multiple authentication methods
- **Modern Python**: Built with Python 3.13, PDM, and the Astral toolchain (Ruff, uv)

## Quick Start

### Prerequisites

- **Python 3.12+** (you have 3.12.8 ✅)
- **PDM** (Python Dependency Manager) - will install below
- **Snowflake account** with access to `9R.FEE_EXPERIMENT` schema

### Step-by-Step Installation

#### 1. Install PDM

PDM is not yet installed on your system. Choose one method:

**Option A: Using the official installer (recommended)**
```bash
curl -sSL https://pdm-project.org/install-pdm.py | python3 -
```

**Option B: Using Homebrew (macOS)**
```bash
brew install pdm
```

**Option C: Using pip**
```bash
pip install --user pdm
```

After installation, verify it works:
```bash
pdm --version
# Should show: PDM, version 2.x.x
```

If `pdm` command is not found, add it to your PATH:
```bash
# For bash/zsh, add to ~/.bashrc or ~/.zshrc:
export PATH="$HOME/.local/bin:$PATH"

# Then reload your shell:
source ~/.bashrc  # or source ~/.zshrc
```

#### 2. Install Project Dependencies

```bash
# Navigate to project directory (if not already there)
cd /path/to/swapkit-fee-experiment-analysis

# Install all dependencies (production + dev)
pdm install

# This will:
# - Create a virtual environment in .venv/
# - Install pandas, polars, streamlit, snowflake-snowpark-python, etc.
# - Install dev tools: pytest, ruff, pre-commit, jupyter
# - Take 2-5 minutes depending on your connection
```

#### 3. Set Up Pre-commit Hooks

Pre-commit hooks automatically format and lint your code before each commit:

```bash
# Install pre-commit hooks into git
pdm run precommit-install

# (Optional) Run hooks on all files to verify setup
pdm run precommit-run
```

#### 4. Configure Snowflake Connection

Choose **ONE** of these methods (in order of preference):

**Option A: Connection file** (recommended for local development)
```bash
# Create the Snowflake config directory
mkdir -p ~/.snowflake

# Create the connections file with your credentials
cat > ~/.snowflake/connections.toml << 'EOF'
[9R]
account = "your-account-identifier"
user = "your-username"
password = "your-password"
warehouse = "COMPUTE_WH"
database = "9R"
schema = "FEE_EXPERIMENT"
role = "ACCOUNTADMIN"
EOF

# Secure the file (only you can read it)
chmod 600 ~/.snowflake/connections.toml
```

Replace the placeholder values:
- `your-account-identifier`: e.g., `xy12345.us-east-1`
- `your-username`: Your Snowflake username
- `your-password`: Your Snowflake password

**Option B: Environment variables** (for CI/CD or temporary use)
```bash
# Add to your ~/.bashrc or ~/.zshrc for persistence
export SNOWFLAKE_ACCOUNT="your-account-identifier"
export SNOWFLAKE_USER="your-username"
export SNOWFLAKE_PASSWORD="your-password"
export SNOWFLAKE_WAREHOUSE="COMPUTE_WH"
export SNOWFLAKE_DATABASE="9R"
export SNOWFLAKE_SCHEMA="FEE_EXPERIMENT"

# Or create a .env file in the project root (add to .gitignore!)
cat > .env << 'EOF'
SNOWFLAKE_ACCOUNT=your-account-identifier
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=9R
SNOWFLAKE_SCHEMA=FEE_EXPERIMENT
EOF
```

**Option C: Streamlit secrets** (for Streamlit Cloud deployment)
```bash
# Create .streamlit directory
mkdir -p .streamlit

# Create secrets file
cat > .streamlit/secrets.toml << 'EOF'
[snowflake]
account = "your-account-identifier"
user = "your-username"
password = "your-password"
warehouse = "COMPUTE_WH"
database = "9R"
schema = "FEE_EXPERIMENT"
role = "ACCOUNTADMIN"
EOF

# Secure the file
chmod 600 .streamlit/secrets.toml
```

⚠️ **Important**: Never commit credentials to git! The `.gitignore` already excludes these files.

#### 5. Verify Your Setup

Run the verification script to check everything is working:

```bash
python verify_setup.py
```

Expected output:
```
✅ Python 3.12.8
✅ pandas
✅ polars
✅ streamlit
✅ altair
✅ plotly
✅ snowflake-snowpark-python
✅ Snowflake connection module importable
✅ Snowflake connection working
🎉 Setup complete! Run: pdm run dashboard
```

If you see any ❌, follow the suggestions in the output.

#### 6. Set Up dbt Profile

dbt needs a profile to connect to Snowflake. Create `~/.dbt/profiles.yml`:

```yaml
thorchain_snowflake:
  target: prod
  outputs:
    prod:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      role: "{{ env_var('SNOWFLAKE_ROLE', 'ANALYST') }}"
      warehouse: "{{ env_var('SNOWFLAKE_WAREHOUSE') }}"
      database: "{{ env_var('SNOWFLAKE_DATABASE', '9R') }}"
      schema: "{{ env_var('DBT_SCHEMA', 'FEE_EXPERIMENT_MARTS') }}"
      threads: 4
      client_session_keep_alive: false
```

Set environment variables (add to your shell rc file):
```bash
export SNOWFLAKE_ACCOUNT="your-account-identifier"
export SNOWFLAKE_USER="your-username"
export SNOWFLAKE_PASSWORD="your-password"
export SNOWFLAKE_ROLE="ANALYST"
export SNOWFLAKE_WAREHOUSE="COMPUTE_WH"
export SNOWFLAKE_DATABASE="9R"
export DBT_SCHEMA="FEE_EXPERIMENT_MARTS"
```

#### 7. Run dbt Models

```bash
# Test dbt connection
pdm run dbt-debug

# Build all models and run tests
pdm run dbt-build

# Or just run models (skip tests)
pdm run dbt-run
```

#### 8. Run the Dashboard

```bash
# Launch the multipage Streamlit dashboard
pdm run dashboard

# The dashboard will open automatically in your browser at:
# http://localhost:8501
```

**First-time tips:**
- Dashboard loads data from Snowflake views in `9R.FEE_EXPERIMENT` and `9R.FEE_EXPERIMENT_MARTS`
- **Phase 1 Pages**: Weekly Summary, Data Validation
- **Phase 2 Page**: Elasticity Analysis (price elasticity, optimal fee, revenue decomposition)
- Use filters to explore different date ranges and fee tiers
- Download CSV exports and Markdown reports using download buttons
- Phase 3 & 4 pages are planned but not yet implemented

### Troubleshooting Installation

**Problem: `pdm: command not found`**
```bash
# Check if PDM is installed
which pdm

# If not found, try the full path
~/.local/bin/pdm --version

# Add to PATH permanently
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**Problem: `pdm install` fails with SSL errors**
```bash
# Try with pip fallback
pdm install --no-isolation

# Or use system Python
pdm install --python $(which python3)
```

**Problem: Snowflake connection fails**
```bash
# Test connection manually
python -c "
from thorchain_fee_analysis.data.snowflake_conn import test_connection
result = test_connection()
print(f'Connection: {'✅ Working' if result else '❌ Failed'}')
"

# Check your credentials
cat ~/.snowflake/connections.toml

# Verify account identifier format (should be: account.region)
# Example: xy12345.us-east-1 NOT xy12345.snowflakecomputing.com
```

**Problem: Import errors when running scripts**
```bash
# Activate the PDM virtual environment
eval $(pdm venv activate)

# Or use pdm run for all commands
pdm run python your_script.py
```

**Problem: Dashboard won't start**
```bash
# Check if port 8501 is already in use
lsof -ti:8501

# Kill the process if needed
kill $(lsof -ti:8501)

# Or use a different port
pdm run streamlit run dashboards/phase1_data_validation.py --server.port 8502
```

## Project Structure

```
swapkit-fee-experiment-analysis/
├── dbt/                             # dbt project for SQL transformations
│   ├── models/
│   │   ├── sources/                 # Source definitions
│   │   ├── staging/                 # Base cleaned tables
│   │   ├── intermediate/            # Business logic transformations
│   │   └── marts/                   # Final dashboard-ready tables
│   ├── seeds/                       # Static CSV data
│   ├── macros/                      # Reusable SQL functions
│   ├── tests/                       # Custom data tests
│   └── dbt_project.yml             # dbt configuration
├── src/
│   └── thorchain_fee_analysis/      # Main Python package
│       ├── data/                    # Data loading and Snowflake connection
│       ├── analysis/                # Statistical analysis modules (Phase 3)
│       ├── visualization/           # Chart generation utilities
│       └── utils/                   # Shared helper functions
├── dashboards/
│   └── app/                         # Multipage Streamlit dashboard
│       ├── Home.py                  # Dashboard entry point
│       ├── pages/                   # Dashboard pages
│       │   ├── 01_Weekly_Summary.py
│       │   ├── 02_Pool_Analysis.py
│       │   ├── 03_User_Analysis.py
│       │   └── 04_Data_Validation.py
│       └── components/              # Reusable UI components
├── sql/                             # Legacy SQL scripts (replaced by dbt)
│   └── README.md                    # Documentation
├── notebooks/                       # Jupyter notebooks for exploration
├── tests/                          # Pytest test suite
├── docs/                           # Documentation
├── pyproject.toml                  # Project configuration
└── README.md                       # This file
```

### dbt Models

SQL transformations are now managed by dbt in the `dbt/` directory:

- **Sources**: Raw Snowflake tables from `THORCHAIN.DEFI` and `9R.FEE_EXPERIMENT`
- **Staging**: Cleaned, normalized base tables (`stg_*`)
- **Intermediate**: Business logic and aggregations (`int_*`)
- **Marts**: Final fact tables for dashboard (`fct_*`)

See `dbt/README.md` for detailed model documentation and lineage.

## Execution Quality (SwapKit Quotes Only)

Minimal artifacts to answer execution quality from quotes, grouped by provider and USD size buckets by week:

- SQL: `sql/execution_quality/weekly_eq_quotes.sql`
- CSV: `outputs/weekly_eq_quotes.csv`
- Data dictionary: `docs/execution_quality/weekly_eq_data_dictionary.md`

Re-generate the CSV via BigQuery CLI:

```bash
bq query --use_legacy_sql=false --format=csv \
  < sql/execution_quality/weekly_eq_quotes.sql \
  > outputs/weekly_eq_quotes.csv
```

Notes:
- Uses only `swapkit-shared-analytics.api_data.quotes` (BigQuery)
- EQ from quotes: `eq_bps = -total_slippage_bps` (positive = improvement)
- USD size buckets applied only when either leg is USD stable (no external pricing)

## Data Sources

### Snowflake Database

The analysis uses data from:

**Source Tables:**
- `THORCHAIN.DEFI.FACT_SWAPS`: Raw swap transactions
- `THORCHAIN.CORE.DIM_BLOCK`: Block height to timestamp mapping

**dbt-Generated Marts** (in `9R.FEE_EXPERIMENT_MARTS`):**
- `fct_weekly_summary_final`: Weekly aggregated metrics by fee tier
- `fct_pool_weekly_summary`: Pool-level performance metrics
- `fct_user_weekly_summary`: User-level behavior metrics

**Legacy Views** (in `9R.FEE_EXPERIMENT`):**
- Still available for reference, but dashboard now queries dbt marts

For detailed schema documentation, see:
- [`docs/SNOWFLAKE_SWAPKIT_SCHEMA.md`](docs/SNOWFLAKE_SWAPKIT_SCHEMA.md)
- [`dbt/README.md`](dbt/README.md) for dbt model documentation

## Development

### Common Commands

```bash
# dbt commands
pdm run dbt-debug      # Test dbt connection
pdm run dbt-deps       # Install dbt packages
pdm run dbt-run        # Run all models
pdm run dbt-test       # Run data tests
pdm run dbt-build      # Run models + tests

# Dashboard
pdm run dashboard      # Launch multipage Streamlit app

# Python development
pdm run test           # Run pytest tests
pdm run test-cov       # Run tests with coverage
pdm run lint           # Lint code with Ruff
pdm run format         # Format code with Ruff
pdm run format-check   # Check formatting

# Notebooks
pdm run notebook       # Launch JupyterLab
```

### Setting Up Pre-commit Hooks

```bash
pdm run precommit-install
```

This will automatically run linting and formatting checks before each commit.

### Running Tests

```bash
# Run all tests
pdm run test

# Run specific test file
pdm run pytest tests/test_snowflake_conn.py

# Run with coverage report
pdm run test-cov
```

### Working with Notebooks

```bash
# Launch JupyterLab
pdm run notebook
```

**Note**: If you see a "No file system provider found" error when opening `.ipynb` files in Cursor:
1. Install the **Jupyter** extension in Cursor (search "Jupyter" in Extensions)
2. Or use JupyterLab instead: `pdm run notebook`

See `notebooks/README.md` for detailed notebook setup instructions.

### Code Style

This project uses:
- **Ruff**: For linting and formatting (replaces Black, isort, flake8)
- **Line length**: 100 characters
- **Style**: Follow PEP 8 with modern Python idioms

The codebase is automatically formatted on commit via pre-commit hooks.

## Phase 2 Results - Elasticity Analysis

Phase 2 delivers revenue optimization through elasticity analysis:

✅ **Deliverables**:
- **Price Elasticity of Demand (PED)**: Measures volume sensitivity to fee changes
- **Revenue Elasticity**: Quantifies revenue impact of fee adjustments
- **Optimal Fee Recommendation**: Data-driven fee tier with 95% confidence intervals
- **Revenue Decomposition**: Waterfall analysis breaking down fee rate, volume, mix, and external effects
- **Interactive Dashboard Page**: Visualizations, KPIs, and downloadable Markdown report
- **Comprehensive Tests**: 25+ unit tests for elasticity and decomposition modules

**Key Capabilities**:
- Bootstrap confidence intervals for statistical rigor
- OLS regression with time trend controls
- Period-over-period decomposition analysis
- Downloadable analysis report in Markdown format

**Access Phase 2 Results**:
Run the dashboard (`pdm run dashboard`) and navigate to "📊 Elasticity Analysis" page.

## Phase 1 Results

Phase 1 focused on data validation and infrastructure:

✅ **Achievements**:
- Validated fee period data accuracy (all periods within 1 bps tolerance)
- Built Snowflake data pipeline with multiple authentication methods
- Created interactive dashboard for Phase 1 metrics
- Established testing and CI/CD infrastructure

**Key Findings**:
- 100% of manual fee periods validated successfully
- Average realized fees within 1 basis point of intended fees
- Data quality suitable for statistical analysis

## Contributing

### Adding New Features

1. Create a new branch: `git checkout -b feature/your-feature`
2. Make your changes following the code style
3. Add tests for new functionality
4. Run tests and linting: `pdm run test && pdm run lint`
5. Commit your changes (pre-commit hooks will run automatically)
6. Push and create a pull request

### Code Review Guidelines

- All code must pass linting and formatting checks
- Test coverage should not decrease
- New features require tests
- Update documentation for user-facing changes

## Documentation

- **[Snowflake Schema](docs/SNOWFLAKE_SWAPKIT_SCHEMA.md)**: Database schema and query examples
- **[SwapKit Overview](docs/SWAPKIT_DATASHARE.md)**: SwapKit business context
- **[BigQuery Dictionary](docs/swapkit_bigquery_data_dictionary.md)**: BigQuery data source documentation
- **[Executive Summary](docs/swapkit_executive_summary.md)**: Project overview and key insights

## Technology Stack

- **Python 3.13**: Latest stable Python release
- **PDM**: Modern Python dependency manager
- **dbt**: SQL transformation and testing framework
- **Ruff**: Ultra-fast Python linter and formatter
- **Streamlit**: Interactive multipage dashboard framework
- **Snowflake**: Data warehouse and analytics platform
- **Polars**: High-performance DataFrame library
- **Pandas**: Data manipulation and analysis
- **Altair/Plotly**: Data visualization

## Troubleshooting

### Snowflake Connection Issues

If you encounter connection errors:

1. Verify your credentials are correct
2. Check network connectivity to Snowflake
3. Ensure your user has access to the `9R.FEE_EXPERIMENT` schema
4. Try the connection test:
   ```python
   from thorchain_fee_analysis.data.snowflake_conn import test_connection
   print(test_connection())  # Should return True
   ```

### Import Errors

If you see import errors when running scripts:
```bash
# Ensure dependencies are installed
pdm install

# Activate the virtual environment
eval $(pdm venv activate)
```

### Dashboard Not Loading

If the dashboard doesn't load:
1. Check that port 8501 is not in use
2. Verify Snowflake connection is configured
3. Check the terminal for error messages
4. Try running with debug logging: `pdm run streamlit run dashboards/phase1_data_validation.py --logger.level=debug`

## License

MIT License - See LICENSE file for details

## Contact

For questions or issues:
- Open an issue on GitHub
- Contact the data team
- See documentation in the `docs/` directory

---

**Built with** ❤️ **using Python 3.13, PDM, and the Astral toolchain**
