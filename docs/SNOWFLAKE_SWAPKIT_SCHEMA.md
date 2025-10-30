# SwapKit Snowflake Schema Documentation

## Overview

This schema contains SwapKit cross-chain swap quote data extracted from BigQuery (`swapkit-shared-analytics.api_data`). The schema provides comprehensive visibility into cross-chain cryptocurrency swap quote generation across 30+ blockchains and 10,000+ crypto assets.

**Database:** `9R`
**Schema:** `SWAPKIT`
**Created:** October 18, 2025
**Source:** BigQuery `swapkit-shared-analytics.api_data`

---

## Schema Objects

### Tables

#### 1. `QUOTE_REQUESTS`
Captures user-initiated requests for swap quotes from the SwapKit API.

**Grain:** One row per quote request received by the SwapKit API

**Columns:**
| Column | Type | Description |
|--------|------|-------------|
| REQUEST_ID | VARCHAR(255) | Primary key - unique identifier for the quote request |
| SELL_ASSET | VARCHAR(500) | Asset to sell in CHAIN.SYMBOL format (e.g., "ETH.ETH") |
| SELL_AMOUNT | VARCHAR(100) | Amount of sell asset (stored as string to preserve precision) |
| BUY_ASSET | VARCHAR(500) | Asset to buy in CHAIN.SYMBOL format (e.g., "BTC.BTC") |
| SOURCE_ADDRESS | VARCHAR(500) | Blockchain address sending the sell asset |
| DESTINATION_ADDRESS | VARCHAR(500) | Blockchain address receiving the buy asset |
| SLIPPAGE | FLOAT | Maximum slippage tolerance as decimal (e.g., 0.03 = 3%) |
| INCLUDE_TX | BOOLEAN | Whether to include transaction details in response |
| STATUS_CODE | INTEGER | HTTP status code of the request (200, 400, 500) |
| CREATED_AT | TIMESTAMP_NTZ | Timestamp when request was received (UTC) |
| LOADED_AT | TIMESTAMP_NTZ | Timestamp when data was loaded into Snowflake |

**Example Query:**
```sql
SELECT
    COUNT(*) as total_requests,
    COUNT(DISTINCT SELL_ASSET) as unique_sell_assets,
    COUNT(DISTINCT BUY_ASSET) as unique_buy_assets,
    AVG(SLIPPAGE) as avg_slippage_tolerance
FROM "9R".SWAPKIT.QUOTE_REQUESTS
WHERE CREATED_AT >= DATEADD(day, -7, CURRENT_TIMESTAMP())
    AND STATUS_CODE = 200;
```

---

#### 2. `QUOTE_ROUTES`
Contains individual routing options (paths) generated for each quote request, showing different provider combinations and their expected outputs.

**Grain:** One row per routing option per quote. A single QUOTE_ID can have multiple routes (typically 1-7).

**Columns:**
| Column | Type | Description |
|--------|------|-------------|
| QUOTE_ID | VARCHAR(255) | Primary key (composite) - unique identifier linking routes to the same quote |
| PROVIDERS | VARCHAR(500) | Primary key (composite) - hyphen-delimited string of providers used |
| SELL_ASSET | VARCHAR(500) | Asset to sell in CHAIN.SYMBOL[-CONTRACT] format |
| SELL_AMOUNT | NUMBER(38,18) | Precise amount of sell asset |
| BUY_ASSET | VARCHAR(500) | Asset to buy in CHAIN.SYMBOL[-CONTRACT] format |
| EXPECTED_BUY_AMOUNT | NUMBER(38,18) | Expected output amount before slippage |
| FEES | VARIANT | Array of fee objects (nested JSON structure) |
| ESTIMATED_TIME | VARIANT | Time estimates for swap completion (nested JSON) |
| TOTAL_SLIPPAGE_BPS | NUMBER(38,18) | Total slippage in basis points (negative = price improvement) |
| WARNINGS | VARIANT | Array of warning objects for user alerts |
| META | VARIANT | Metadata including price impact, tags, affiliate info |
| PROVIDER_ERRORS | VARIANT | Errors from individual providers that couldn't quote |
| STATUS_CODE | INTEGER | HTTP status code (200 = success, 400 = bad request, 500 = error) |
| REQUEST_ID | VARCHAR(255) | Foreign key - links back to QUOTE_REQUESTS |
| ERROR | VARIANT | Top-level error object if entire quote failed |
| CREATED_AT | TIMESTAMP_NTZ | Timestamp when route was generated (UTC) |
| QUOTE_DATE | DATE | Date portion of CREATED_AT for partitioning |
| LOADED_AT | TIMESTAMP_NTZ | Timestamp when data was loaded into Snowflake |

**VARIANT Column Structures:**

**FEES (Array):**
```json
[
  {
    "type": "liquidity",
    "chain": "THOR",
    "protocol": "THORCHAIN_STREAMING",
    "amount": "0.02178",
    "asset": "ETH.USDT-0xdAC17F958D2ee523a2206206994597C13D831ec7"
  },
  {
    "type": "affiliate",
    "chain": "THOR",
    "protocol": "THORCHAIN_STREAMING",
    "amount": "0.282933",
    "asset": "ETH.USDT-0xdAC17F958D2ee523a2206206994597C13D831ec7"
  }
]
```

**ESTIMATED_TIME (Object):**
```json
{
  "total": "618.5",
  "swap": 6,
  "inbound": 600,
  "outbound": "12.5"
}
```

**META (Object):**
```json
{
  "price_impact": -0.024631,
  "tags": ["RECOMMENDED", "FASTEST", "CHEAPEST"],
  "approval_address": null,
  "affiliate": "ll",
  "affiliate_fee": 130
}
```

**Example Query:**
```sql
-- Query routes with flattened metadata
SELECT
    QUOTE_ID,
    PROVIDERS,
    SELL_ASSET,
    BUY_ASSET,
    EXPECTED_BUY_AMOUNT,
    ESTIMATED_TIME:total::FLOAT as TOTAL_TIME_SECONDS,
    META:price_impact::FLOAT as PRICE_IMPACT,
    META:affiliate::STRING as AFFILIATE,
    ARRAY_SIZE(FEES) as FEE_COUNT
FROM "9R".SWAPKIT.QUOTE_ROUTES
WHERE QUOTE_DATE = CURRENT_DATE()
    AND STATUS_CODE = 200
LIMIT 10;
```

---

### Views

#### 3. `QUOTES`
Filtered view of `QUOTE_ROUTES` containing only the most recent 90 days of data, optimized for real-time analytics.

**Definition:**
```sql
SELECT *
FROM "9R".SWAPKIT.QUOTE_ROUTES
WHERE CREATED_AT >= DATEADD(DAY, -90, CURRENT_TIMESTAMP())
```

---

#### 4. `VW_QUOTE_ROUTES_FLATTENED`
Helper view that flattens the nested structures in quote_routes for easier querying.

**Key Features:**
- Parses CHAIN.SYMBOL[-CONTRACT] format into separate columns
- Extracts common metadata fields from VARIANT columns
- Adds derived fields (SWAP_TYPE, fee counts, etc.)
- Flattens estimated time fields

**Additional Columns:**
- SELL_CHAIN, SELL_SYMBOL, SELL_CONTRACT
- BUY_CHAIN, BUY_SYMBOL, BUY_CONTRACT
- ESTIMATED_TIME_TOTAL_SECONDS, ESTIMATED_TIME_SWAP_SECONDS, etc.
- PRICE_IMPACT, AFFILIATE, AFFILIATE_FEE_BPS
- SWAP_TYPE ('Same Chain' or 'Cross Chain')
- FEE_COUNT, WARNING_COUNT, PROVIDER_ERROR_COUNT

**Example Query:**
```sql
-- Analyze cross-chain vs same-chain swaps
SELECT
    SWAP_TYPE,
    COUNT(*) as route_count,
    AVG(ESTIMATED_TIME_TOTAL_SECONDS) as avg_time_seconds,
    AVG(PRICE_IMPACT) as avg_price_impact
FROM "9R".SWAPKIT.VW_QUOTE_ROUTES_FLATTENED
WHERE QUOTE_DATE >= DATEADD(day, -7, CURRENT_DATE())
GROUP BY SWAP_TYPE;
```

---

#### 5. `VW_QUOTE_FEES`
Helper view that unnests the fees array from quote_routes for fee analysis.

**Key Features:**
- One row per fee per quote
- Flattened fee structure for aggregation
- Preserves all fee metadata

**Columns:**
- All base columns from QUOTE_ROUTES
- FEE_TYPE, FEE_CHAIN, FEE_PROTOCOL
- FEE_AMOUNT, FEE_ASSET

**Example Query:**
```sql
-- Aggregate fees by type
SELECT
    FEE_TYPE,
    FEE_CHAIN,
    COUNT(*) as fee_count,
    AVG(FEE_AMOUNT) as avg_fee_amount,
    COUNT(DISTINCT QUOTE_ID) as quotes_with_fee
FROM "9R".SWAPKIT.VW_QUOTE_FEES
WHERE QUOTE_DATE >= DATEADD(day, -30, CURRENT_DATE())
GROUP BY FEE_TYPE, FEE_CHAIN
ORDER BY fee_count DESC;
```

---

## Asset Naming Convention (CRITICAL)

SwapKit uses a strict **CHAIN.SYMBOL[-CONTRACT_ADDRESS]** format for all assets:

### Native Assets (Two Parts):
- `BTC.BTC` - Bitcoin
- `ETH.ETH` - Ethereum (native)
- `AVAX.AVAX` - Avalanche
- `BSC.BNB` - BNB on BSC
- `THOR.RUNE` - THORChain RUNE
- `MAYA.CACAO` - Maya Protocol CACAO
- `GAIA.ATOM` - Cosmos ATOM

### Token Assets (Three Parts):
- `ETH.USDT-0xdAC17F958D2ee523a2206206994597C13D831ec7` - USDT on Ethereum
- `ETH.USDC-0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` - USDC on Ethereum
- `BSC.USDT-0x55d398326f99059fF775485246999027B3197955` - USDT on BSC

### Parsing in SQL:
```sql
-- Extract chain
SPLIT_PART(sell_asset, '.', 1) as chain

-- Extract symbol only (before hyphen)
SPLIT_PART(SPLIT_PART(sell_asset, '.', 2), '-', 1) as symbol

-- Extract contract address (after hyphen, if exists)
CASE
  WHEN CONTAINS(sell_asset, '-')
  THEN SPLIT_PART(sell_asset, '-', 2)
  ELSE NULL
END as contract_address
```

---

## Provider Field Format

The `PROVIDERS` field contains hyphen-delimited provider names indicating the routing path:

### Single Provider Examples:
- `THORCHAIN` - Direct THORChain swap
- `THORCHAIN_STREAMING` - THORChain streaming swap
- `CHAINFLIP` - Chainflip cross-chain
- `NEAR` - NEAR Intents
- `ONEINCH` - 1inch DEX aggregator

### Multi-Provider Examples:
- `ONEINCH-THORCHAIN` - 1inch → THORChain multi-hop
- `UNISWAP_V3-THORCHAIN_STREAMING` - Uniswap → THORChain streaming
- `CHAINFLIP-JUPITER` - Chainflip → Jupiter (cross-chain to Solana)

---

## Working with VARIANT Columns

Snowflake's VARIANT type stores semi-structured data (JSON). Here are common patterns:

### Extract Simple Values:
```sql
SELECT
    META:affiliate::STRING as affiliate,
    META:affiliate_fee::FLOAT as affiliate_fee,
    ESTIMATED_TIME:total::FLOAT as total_time
FROM "9R".SWAPKIT.QUOTE_ROUTES;
```

### Flatten Arrays:
```sql
-- Unnest fees array
SELECT
    QUOTE_ID,
    fee.value:type::STRING as fee_type,
    fee.value:amount::FLOAT as fee_amount
FROM "9R".SWAPKIT.QUOTE_ROUTES,
LATERAL FLATTEN(input => FEES) fee;
```

### Check Array Size:
```sql
SELECT
    QUOTE_ID,
    ARRAY_SIZE(FEES) as fee_count,
    ARRAY_SIZE(WARNINGS) as warning_count
FROM "9R".SWAPKIT.QUOTE_ROUTES;
```

### Filter on Nested Values:
```sql
SELECT *
FROM "9R".SWAPKIT.QUOTE_ROUTES
WHERE META:affiliate::STRING = 'll'
    AND META:affiliate_fee::FLOAT >= 75;
```

---

## Common Analysis Queries

### 1. Top Asset Pairs by Volume
```sql
SELECT
    SELL_ASSET,
    BUY_ASSET,
    COUNT(*) as route_count,
    AVG(SELL_AMOUNT) as avg_sell_amount,
    AVG(EXPECTED_BUY_AMOUNT) as avg_buy_amount
FROM "9R".SWAPKIT.QUOTE_ROUTES
WHERE QUOTE_DATE >= DATEADD(day, -7, CURRENT_DATE())
    AND STATUS_CODE = 200
GROUP BY SELL_ASSET, BUY_ASSET
ORDER BY route_count DESC
LIMIT 20;
```

### 2. Provider Performance Comparison
```sql
SELECT
    PROVIDERS,
    COUNT(*) as total_routes,
    COUNT_IF(STATUS_CODE = 200) as successful_routes,
    ROUND(COUNT_IF(STATUS_CODE = 200) * 100.0 / COUNT(*), 2) as success_rate_pct,
    ROUND(AVG(ESTIMATED_TIME:total::FLOAT), 1) as avg_time_seconds,
    ROUND(AVG(TOTAL_SLIPPAGE_BPS), 1) as avg_slippage_bps
FROM "9R".SWAPKIT.QUOTE_ROUTES
WHERE QUOTE_DATE >= DATEADD(day, -30, CURRENT_DATE())
GROUP BY PROVIDERS
HAVING total_routes > 1000
ORDER BY total_routes DESC
LIMIT 20;
```

### 3. Fee Analysis by Type
```sql
SELECT
    FEE_TYPE,
    FEE_CHAIN,
    COUNT(*) as fee_count,
    AVG(FEE_AMOUNT) as avg_fee_amount,
    MIN(FEE_AMOUNT) as min_fee_amount,
    MAX(FEE_AMOUNT) as max_fee_amount
FROM "9R".SWAPKIT.VW_QUOTE_FEES
WHERE QUOTE_DATE >= DATEADD(day, -7, CURRENT_DATE())
GROUP BY FEE_TYPE, FEE_CHAIN
ORDER BY fee_count DESC;
```

### 4. Cross-Chain vs Same-Chain Analysis
```sql
SELECT
    SWAP_TYPE,
    COUNT(*) as route_count,
    AVG(ESTIMATED_TIME_TOTAL_SECONDS) as avg_time_seconds,
    AVG(PRICE_IMPACT) as avg_price_impact,
    AVG(TOTAL_SLIPPAGE_BPS) as avg_slippage_bps
FROM "9R".SWAPKIT.VW_QUOTE_ROUTES_FLATTENED
WHERE QUOTE_DATE >= DATEADD(day, -7, CURRENT_DATE())
    AND STATUS_CODE = 200
GROUP BY SWAP_TYPE;
```

### 5. Affiliate Revenue Analysis
```sql
SELECT
    AFFILIATE,
    COUNT(*) as quote_count,
    AVG(AFFILIATE_FEE_BPS) as avg_affiliate_fee_bps,
    SUM(SELL_AMOUNT) as total_sell_volume
FROM "9R".SWAPKIT.VW_QUOTE_ROUTES_FLATTENED
WHERE QUOTE_DATE >= DATEADD(day, -30, CURRENT_DATE())
    AND AFFILIATE IS NOT NULL
    AND STATUS_CODE = 200
GROUP BY AFFILIATE
ORDER BY quote_count DESC;
```

### 6. Daily Volume Trend
```sql
SELECT
    QUOTE_DATE,
    COUNT(*) as total_routes,
    COUNT(DISTINCT QUOTE_ID) as unique_quotes,
    ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT QUOTE_ID), 2) as avg_routes_per_quote,
    COUNT_IF(STATUS_CODE = 200) as successful_routes
FROM "9R".SWAPKIT.QUOTE_ROUTES
WHERE QUOTE_DATE >= DATEADD(day, -30, CURRENT_DATE())
GROUP BY QUOTE_DATE
ORDER BY QUOTE_DATE DESC;
```

---

## Data Loading Strategy

### Option 1: Manual Incremental Load via BigQuery Export
```sql
-- In BigQuery, export new data to CSV/JSON
SELECT *
FROM `swapkit-shared-analytics.api_data.quote_routes`
WHERE created_at >= TIMESTAMP('2025-10-18 00:00:00')

-- Then use Snowflake COPY INTO to load
COPY INTO "9R".SWAPKIT.QUOTE_ROUTES
FROM @my_stage/quote_routes_20251018.json
FILE_FORMAT = (TYPE = JSON);
```

### Option 2: Automated ETL Pipeline
Consider using tools like:
- **Fivetran** - Direct BigQuery to Snowflake replication
- **dbt** - Data transformation and orchestration
- **Airflow** - Custom ETL orchestration
- **Matillion** - Visual ETL for Snowflake

### Option 3: Direct BigQuery Federation (Read-Only)
```sql
-- Create external table pointing to BigQuery
-- Note: Requires Snowflake Enterprise Edition with Data Lake support
```

---

## Data Quality Notes

### Completeness
- ✅ All records have CREATED_AT timestamps
- ✅ High success rate (99.93% status 200)
- ⚠️ REQUEST_ID may be null (not all routes link back to requests)
- ⚠️ Nested arrays (FEES, WARNINGS, PROVIDER_ERRORS) can be empty

### Data Types
- BIGNUMERIC fields in BigQuery are mapped to NUMBER(38,18) in Snowflake
- VARIANT columns preserve all nested structure
- Timestamps are stored as TIMESTAMP_NTZ (no timezone)

### Known Limitations
1. **Fractional Values:** Some amounts in BigQuery are stored as fractions (e.g., "1361/12500000")
   - Solution: Cast to FLOAT for calculations
2. **Empty Arrays:** FEES, WARNINGS, and PROVIDER_ERRORS can be empty
   - Solution: Check `ARRAY_SIZE(field) > 0` before unnesting
3. **Missing REQUEST_ID:** Not all routes have a request_id
   - Workaround: Use QUOTE_ID grouping instead

---

## Support & Contact

- **Schema Owner:** Nine Realms Data Team
- **Source Data:** SwapKit Analytics Team (robot@swapkit.dev)
- **Documentation:** See `/queries-test/SWAPKIT_DATASHARE.md` for business context
- **Data Dictionary:** See `/queries-test/swapkit_bigquery_data_dictionary.md`

---

## Changelog

### Version 1.0 (October 18, 2025)
- Initial schema creation in Snowflake 9R database
- Created QUOTE_REQUESTS and QUOTE_ROUTES tables
- Created QUOTES view (90-day filter)
- Created helper views: VW_QUOTE_ROUTES_FLATTENED, VW_QUOTE_FEES
- Documented schema structure and common queries
