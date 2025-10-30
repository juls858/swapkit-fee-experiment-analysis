-- ============================================================================
-- Phase 1: Optional Materialization Scripts
-- ============================================================================
-- Purpose: Provide CTAS scripts to snapshot views into tables for performance or reproducibility
-- ============================================================================

-- NOTE: Run these only if persistence is required. Remove OR REPLACE if you want incremental refresh.

-- Snapshot fee change points
CREATE OR REPLACE TABLE "9R".FEE_EXPERIMENT.FEE_CHANGEPOINTS AS
SELECT * FROM "9R".FEE_EXPERIMENT.V_FEE_CHANGEPOINTS;

-- Snapshot weekly summary
CREATE OR REPLACE TABLE "9R".FEE_EXPERIMENT.WEEKLY_SUMMARY AS
SELECT * FROM "9R".FEE_EXPERIMENT.V_WEEKLY_SUMMARY;

-- Snapshot pool weekly summary
CREATE OR REPLACE TABLE "9R".FEE_EXPERIMENT.POOL_WEEKLY_SUMMARY AS
SELECT * FROM "9R".FEE_EXPERIMENT.V_POOL_WEEKLY_SUMMARY;

-- Snapshot user weekly summary
CREATE OR REPLACE TABLE "9R".FEE_EXPERIMENT.USER_WEEKLY_SUMMARY AS
SELECT * FROM "9R".FEE_EXPERIMENT.V_USER_WEEKLY_SUMMARY;

-- Snapshot affiliate weekly summary
CREATE OR REPLACE TABLE "9R".FEE_EXPERIMENT.AFFIL_WEEKLY_SUMMARY AS
SELECT * FROM "9R".FEE_EXPERIMENT.V_AFFIL_WEEKLY_SUMMARY;

-- Snapshot prior year comparison
CREATE OR REPLACE TABLE "9R".FEE_EXPERIMENT.PRIOR_YEAR_COMPARISON AS
SELECT * FROM "9R".FEE_EXPERIMENT.V_PRIOR_YEAR_COMPARISON;

-- Validation queries
SELECT COUNT(*) AS rows_change_points FROM "9R".FEE_EXPERIMENT.FEE_CHANGEPOINTS;
SELECT COUNT(*) AS rows_weekly_summary FROM "9R".FEE_EXPERIMENT.WEEKLY_SUMMARY;
