-- ============================================================================
-- Phase 1: THORChain Fee Experiment - Schema Setup
-- ============================================================================
-- Purpose: Create dedicated schema for fee experiment analysis
-- Database: "9R"
-- Schema: FEE_EXPERIMENT
-- ============================================================================

-- Create schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS "9R".FEE_EXPERIMENT
    COMMENT = 'THORChain fee experiment analysis (2025 Q3-Q4) - Phase 1 data foundation';

-- Grant usage to analytics roles (adjust role names as needed)
GRANT USAGE ON SCHEMA "9R".FEE_EXPERIMENT TO ROLE SYSADMIN;
GRANT ALL ON SCHEMA "9R".FEE_EXPERIMENT TO ROLE SYSADMIN;

-- Grant select on future views to analytics users
GRANT SELECT ON ALL VIEWS IN SCHEMA "9R".FEE_EXPERIMENT TO ROLE SYSADMIN;
GRANT SELECT ON FUTURE VIEWS IN SCHEMA "9R".FEE_EXPERIMENT TO ROLE SYSADMIN;

-- Grant select on future tables to analytics users
GRANT SELECT ON ALL TABLES IN SCHEMA "9R".FEE_EXPERIMENT TO ROLE SYSADMIN;
GRANT SELECT ON FUTURE TABLES IN SCHEMA "9R".FEE_EXPERIMENT TO ROLE SYSADMIN;

-- Verify schema creation
SHOW SCHEMAS LIKE 'FEE_EXPERIMENT' IN DATABASE "9R";

SELECT 'Schema "9R".FEE_EXPERIMENT created successfully' AS status;
