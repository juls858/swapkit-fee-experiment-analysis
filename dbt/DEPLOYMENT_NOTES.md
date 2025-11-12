# dbt Deployment Configuration

## Schema and Naming Strategy

This dbt project is configured to deploy into the **existing** `9R.FEE_EXPERIMENT` schema with matching view names for **backward compatibility**.

### Why This Approach?

- ✅ No breaking changes to existing queries
- ✅ Dashboard continues to work with existing views
- ✅ Other tools/reports referencing these views remain functional
- ✅ Gradual migration path from legacy SQL to dbt

## Deployment Mapping

dbt models are aliased to match the original view names:

| dbt Model | Deployed As | Materialization |
|-----------|-------------|-----------------|
| `stg_swaps_experiment_window` | `V_SWAPS_EXPERIMENT_WINDOW` | view |
| `stg_fee_periods_manual` | `V_FEE_PERIODS_MANUAL` | view |
| `int_daily_fee_bps` | `V_DAILY_FEE_BPS` | view |
| `int_fee_periods_final` | `V_FEE_PERIODS_FINAL` | view |
| `fct_weekly_summary_final` | `V_WEEKLY_SUMMARY_FINAL` | **table** |
| `fct_pool_weekly_summary` | `V_POOL_WEEKLY_SUMMARY` | view |
| `fct_user_weekly_summary` | `V_USER_WEEKLY_SUMMARY` | view |

### Target Schema

All models deploy to: **`"9R".FEE_EXPERIMENT`**

This matches the legacy SQL structure exactly.

## Configuration Details

In `dbt_project.yml`:

```yaml
models:
  thorchain_fee_experiment:
    staging:
      +schema: fee_experiment  # Deploys to 9R.FEE_EXPERIMENT
      stg_swaps_experiment_window:
        +alias: V_SWAPS_EXPERIMENT_WINDOW

    intermediate:
      +schema: fee_experiment
      int_daily_fee_bps:
        +alias: V_DAILY_FEE_BPS

    marts:
      +schema: fee_experiment
      fct_weekly_summary_final:
        +materialized: table
        +alias: V_WEEKLY_SUMMARY_FINAL
```

## Database Quoting

The project is configured with:

```yaml
quoting:
  database: true  # Quotes database name: "9R"
```

This ensures proper handling of the numeric database name.

## Migration Path

When you run `dbt build`:

1. **First run**: dbt will CREATE OR REPLACE the views in `9R.FEE_EXPERIMENT`
2. **Subsequent runs**: dbt will update the existing views with new logic
3. **Dashboard**: Continues querying the same view names, now powered by dbt

## What Gets Replaced

Running dbt will **replace** these legacy views:
- ✅ `V_SWAPS_EXPERIMENT_WINDOW` (from `sql/01_stage_swaps_experiment_window.sql`)
- ✅ `V_FEE_PERIODS_MANUAL` (from `sql/12_fee_periods_manual.sql`)
- ✅ `V_DAILY_FEE_BPS` (from `sql/02_daily_fee_bps.sql`)
- ✅ `V_FEE_PERIODS_FINAL` (from `sql/13_fee_periods_final.sql`)
- ✅ `V_WEEKLY_SUMMARY_FINAL` (from `sql/14_weekly_summary_final.sql`)

New views created by dbt:
- 🆕 `V_POOL_WEEKLY_SUMMARY` (new mart)
- 🆕 `V_USER_WEEKLY_SUMMARY` (new mart)

## Safety Notes

### Before Running dbt build:

1. ✅ Legacy views will be replaced (CREATE OR REPLACE)
2. ✅ Downstream queries continue to work (same names)
3. ⚠️ Any custom logic in legacy SQL will be replaced by dbt models

### Rollback Plan:

If issues arise, you can rollback by:

1. Re-run the legacy SQL scripts from `sql/` directory
2. This will restore the original view definitions

### Testing Before Production:

Recommended approach:
1. Test dbt in a separate schema first: `+schema: fee_experiment_test`
2. Compare outputs with legacy views
3. Once validated, update to `+schema: fee_experiment` for production

## Dashboard Queries

The dashboard now queries:
- `"9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL`
- `"9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY`
- `"9R".FEE_EXPERIMENT.V_USER_WEEKLY_SUMMARY`

These match exactly with the dbt-deployed views, ensuring seamless operation.

## Benefits of This Approach

1. **Zero Downtime**: Dashboard continues working during migration
2. **Backward Compatible**: Existing queries, reports, tools continue to function
3. **Gradual Adoption**: Can test dbt models alongside legacy SQL
4. **Easy Rollback**: Simply re-run legacy SQL if needed
5. **Clear Lineage**: dbt docs show data flow while maintaining familiar names

## Future Considerations

Once fully validated, you might consider:
- Moving to a dedicated `FEE_EXPERIMENT_MARTS` schema for clarity
- Using dbt semantic layer for metric definitions
- Adding incremental models for large fact tables
- Setting up dbt Cloud for automated runs

For now, this configuration provides the **safest migration path** with full backward compatibility.
