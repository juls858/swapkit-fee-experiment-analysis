# Phase 1 Snowflake SQL Scripts

This directory contains the Phase 1 SQL scripts used to materialize views and tables for the THORChain fee experiment analysis. These scripts were originally delivered as part of the Phase 1 validation work and have been migrated from the legacy repository structure.

## Usage

The files can be executed in order to recreate the Phase 1 analytical tables inside Snowflake. The scripts assume you have access to the `9R.FEE_EXPERIMENT` schema and appropriate warehouse permissions.

```sql
-- Example: create the base schema and stage data
!source 00_create_schema.sql
!source 01_stage_swaps_experiment_window.sql
```

> Tip: the numbering prefix (00, 01, …, 16) reflects the execution order.

## File Overview

| File | Purpose |
| --- | --- |
| 00_create_schema.sql | Creates required database objects and schemas |
| 01_stage_swaps_experiment_window.sql | Stages swap transactions within the experiment window |
| 02_daily_fee_bps.sql | Calculates daily fee basis points |
| 03_detect_fee_changepoints.sql | Detects fee schedule change points |
| 04_validate_vs_schedule.sql | Validates realized fees versus scheduled fees |
| 05_weekly_summary.sql | Produces weekly metrics summary |
| 06_pool_weekly_summary.sql | Produces weekly metrics by pool |
| 07_user_weekly_summary.sql | Produces weekly metrics by user |
| 08_affiliate_weekly_summary.sql | Produces weekly metrics by affiliate |
| 09_prior_year_comparison.sql | Compares experiment metrics to prior year |
| 10_option_materialize_tables.sql | Optional script to materialize derived tables |
| 11_fee_changes_chrono.sql | Chronological log of fee changes |
| 12_fee_periods_manual.sql | Manual adjustments to fee periods |
| 13_fee_periods_final.sql | Final fee periods table |
| 14_weekly_summary_final.sql | Final weekly summary table |
| 15_experiment_validation_report.sql | Report summarizing validation checks |
| 16_affiliate_exclusion_check.sql | Validates affiliate exclusion rules |
| debug_periods.sql | Helper script for debugging specific periods |

## Notes

- Scripts are written for Snowflake and leverage Snowpark-friendly SQL patterns.
- Execute using SnowSQL, Snowsight Worksheets, or any Snowflake-compatible client.
- Outputs feed the Phase 1 Streamlit dashboard located in `dashboards/phase1_data_validation.py`.
- See `README.md` for broader project context and Phase 1 validation details.
