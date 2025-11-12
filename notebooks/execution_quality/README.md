# Execution Quality Analysis Notebooks

## Overview

These notebooks extract and process data for execution quality analysis.

## Notebooks

### 01_extract_quotes_bq.ipynb
Extracts SwapKit quotes from BigQuery.

**Prerequisites:**
- BigQuery authentication configured
- Access to `swapkit-shared-analytics.api_data` dataset

**Run:**
```bash
jupyter notebook 01_extract_quotes_bq.ipynb
```

**Outputs:**
- `../../data/execution_quality/quotes_raw.parquet`
- `../../data/execution_quality/quotes_qa.json`

### 02_extract_executions_snowflake.ipynb
Extracts NEAR Intents execution data from Snowflake.

**Prerequisites:**
- Snowflake connection configured (`~/.snowflake/connections.toml`)
- Access to `9R.NEAR` schema

**Run:**
```bash
jupyter notebook 02_extract_executions_snowflake.ipynb
```

**Outputs:**
- `../../data/execution_quality/executions_raw.parquet`
- `../../data/execution_quality/executions_qa.json`

### 03_match_compute_eq.ipynb
Matches quotes to executions and computes execution quality metrics.

**Prerequisites:**
- Run notebooks 01 and 02 first
- Parquet files from previous steps exist

**Run:**
```bash
jupyter notebook 03_match_compute_eq.ipynb
```

**Outputs:**
- `../../data/execution_quality/quotes_normalized.parquet`
- `../../data/execution_quality/executions_normalized.parquet`
- `../../data/execution_quality/matched_pairs.parquet`
- `../../data/execution_quality/eq_metrics.parquet`
- `../../data/execution_quality/weekly_summary.parquet`
- `../../data/execution_quality/weekly_summary.csv`

## Quick Start

Run all notebooks in sequence:

```bash
cd notebooks/execution_quality
jupyter notebook
# Then run each notebook in order: 01 -> 02 -> 03
```

Or use the Python module directly:

```python
from thorchain_fee_analysis.analysis.execution_quality import (
    normalize_quotes,
    normalize_executions,
    compute_execution_quality,
    aggregate_weekly_summary
)
```

## Troubleshooting

### BigQuery Authentication Issues
```bash
gcloud auth application-default login
```

### Snowflake Connection Issues
Check `~/.snowflake/connections.toml` or set environment variables:
```bash
export SNOWFLAKE_ACCOUNT=...
export SNOWFLAKE_USER=...
export SNOWFLAKE_PASSWORD=...
```

### Memory Issues
If processing large datasets, increase available memory or process in chunks.

## Next Steps

After running notebooks, view results in the Streamlit dashboard:
```bash
pdm run dashboard
# Navigate to "Execution Quality" page
```
