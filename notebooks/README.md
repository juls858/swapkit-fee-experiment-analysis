# Notebooks Directory

This directory contains Jupyter notebooks for exploratory data analysis and experimentation.

## Opening Notebooks

### Option 1: JupyterLab (Recommended)

Launch JupyterLab from the terminal:

```bash
pdm run notebook
```

This will open JupyterLab in your browser at `http://localhost:8888`

### Option 2: Cursor/VSCode

To open notebooks directly in Cursor, you need to install the Jupyter extension:

1. Open Command Palette (`Cmd+Shift+P` on macOS, `Ctrl+Shift+P` on Windows/Linux)
2. Type "Extensions: Install Extensions"
3. Search for "Jupyter"
4. Install the official **Jupyter** extension by Microsoft
5. Reload Cursor
6. Click on any `.ipynb` file to open it

## Creating New Notebooks

### From JupyterLab:
1. Run `pdm run notebook`
2. Click "New" → "Python 3" in JupyterLab
3. Save with a descriptive name (e.g., `01_fee_analysis.ipynb`)

### From Cursor (with Jupyter extension):
1. Create a new file with `.ipynb` extension
2. Cursor will automatically recognize it as a notebook
3. Select the Python kernel from the project's virtual environment

## Kernel Setup

The notebooks use the project's virtual environment. To ensure the kernel is available:

```bash
# The kernel should be automatically detected
# If not, you can manually register it:
pdm run python -m ipykernel install --user --name=thorchain-fee-analysis
```

## Best Practices

1. **Naming Convention**: Use numbered prefixes for sequential analysis
   - `01_data_exploration.ipynb`
   - `02_fee_impact_analysis.ipynb`
   - `03_elasticity_modeling.ipynb`

2. **Documentation**: Include markdown cells with:
   - Author name
   - Date
   - Purpose/objective
   - Key findings

3. **Code Quality**:
   - Keep cells focused and modular
   - Extract reusable code to `src/thorchain_fee_analysis/`
   - Use the project's modules: `from thorchain_fee_analysis.data import snowflake_conn`

4. **Data Sources**:
   - Use the Snowflake connection from the shared module
   - Document any external data sources
   - Don't commit large data files

## Example Usage

```python
# Import project modules
from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session

# Get Snowflake session
session = get_snowpark_session()

# Query data
df = session.sql("""
    SELECT * FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY
    LIMIT 10
""").to_pandas()

# Analyze
print(df.head())
```

## Troubleshooting

### "No kernel found"
- Make sure you've run `pdm install` to set up the virtual environment
- Restart Cursor/JupyterLab

### "Module not found" errors
- Ensure you're using the correct kernel (project's venv)
- The project package should be installed: `pdm install`

### Cursor can't open notebooks
- Install the Jupyter extension (see Option 2 above)
- Or use JupyterLab instead (see Option 1)

### Snowflake connection issues
- Configure credentials (see main README.md)
- Test connection: `python verify_setup.py`
