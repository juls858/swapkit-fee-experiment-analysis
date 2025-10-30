# Quick Start Guide

## Complete Setup (First Time)

### 1. Install PDM (if not already installed)

```bash
# Check if PDM is installed
pdm --version

# If not installed, use one of these methods:

# Option A: Official installer (recommended)
curl -sSL https://pdm-project.org/install-pdm.py | python3 -

# Option B: Homebrew (macOS)
brew install pdm

# Option C: pip
pip install --user pdm

# Verify installation
pdm --version

# If command not found, add to PATH:
export PATH="$HOME/.local/bin:$PATH"
```

### 2. Install Project Dependencies

```bash
# Navigate to project directory
cd /path/to/swapkit-fee-experiment-analysis

# Install all dependencies (takes 2-5 minutes)
pdm install

# This creates .venv/ and installs:
# - pandas, polars, streamlit, altair, plotly
# - snowflake-snowpark-python
# - pytest, ruff, pre-commit, jupyter
```

### 3. Set Up Pre-commit Hooks

```bash
# Install git hooks
pdm run precommit-install

# (Optional) Test hooks
pdm run precommit-run
```

### 4. Verify Setup

```bash
# Run verification script
python verify_setup.py

# Should show all ✅ checks passing
```

## Snowflake Connection Setup

**Option 1: Config File (Recommended)**
```bash
mkdir -p ~/.snowflake
cat > ~/.snowflake/connections.toml << EOF
[9R]
account = "your-account"
user = "your-username"
password = "your-password"
warehouse = "COMPUTE_WH"
database = "9R"
schema = "FEE_EXPERIMENT"
role = "ACCOUNTADMIN"
EOF
```

**Option 2: Environment Variables**
```bash
export SNOWFLAKE_ACCOUNT="your-account"
export SNOWFLAKE_USER="your-username"
export SNOWFLAKE_PASSWORD="your-password"
```

## Common Commands

### Development
```bash
pdm run dashboard      # Launch Streamlit dashboard
pdm run test          # Run all tests
pdm run test-cov      # Run tests with coverage
pdm run lint          # Check code quality
pdm run format        # Auto-format code
```

### Package Management
```bash
pdm add package-name      # Add dependency
pdm add -d package-name   # Add dev dependency
pdm install              # Install all dependencies
pdm update               # Update dependencies
pdm list                 # List packages
```

### Git Workflow
```bash
git add .
git commit -m "message"   # Pre-commit hooks run automatically
git push
```

## Project Structure

```
├── src/thorchain_fee_analysis/  # Main package
│   ├── data/                    # Data loading & Snowflake
│   ├── analysis/                # Statistical analysis
│   ├── visualization/           # Charts
│   └── utils/                   # Helpers
├── dashboards/                  # Streamlit apps
├── notebooks/                   # Jupyter notebooks
├── tests/                       # Test suite
└── docs/                        # Documentation
```

## Key Files

- `pyproject.toml` - Project configuration
- `README.md` - Full documentation
- `.cursorrules` - Cursor AI guidelines
- `verify_setup.py` - Setup verification script

## Getting Help

- Full docs: See `README.md`
- Setup complete: See `SETUP_COMPLETE.md`
- Schema docs: See `docs/SNOWFLAKE_SWAPKIT_SCHEMA.md`
- Troubleshooting: See README.md "Troubleshooting" section

## Quick Test

```bash
# Test imports
python -c "from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session; print('✅ Module loaded')"

# Run tests
pdm run test

# Launch dashboard
pdm run dashboard
```

## Next Steps

1. ✅ Install dependencies: `pdm install`
2. ✅ Configure Snowflake connection (see above)
3. ✅ Verify setup: `python verify_setup.py`
4. ✅ Launch dashboard: `pdm run dashboard`
5. 🚀 Start building Phase 2 features!
