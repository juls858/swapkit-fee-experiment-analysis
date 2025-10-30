# SwapKit BigQuery Dataset: Technical Data Dictionary & Metadata Report

**Dataset:** `swapkit-shared-analytics.api_data`
**Location:** US
**Description:** Shared analytics views for cross-project data access
**Report Generated:** October 17, 2025
**Data Coverage:** April 12, 2025 - October 17, 2025 (189 days)

---

## Executive Summary

This dataset contains SwapKit API quote request and routing data, providing comprehensive visibility into cross-chain cryptocurrency swap quote generation across 30+ blockchains. The dataset comprises three views that expose different aspects of the quote lifecycle:

- **quote_requests**: User-initiated swap quote requests (~34M records)
- **quote_routes**: Individual routing options returned for each quote (~83M records)
- **quotes**: Filtered view of recent routes (last 90 days, ~65M records)

**Key Statistics (As of October 17, 2025):**
- **Total Quote Routes:** 83,107,168 routes across 175 days
- **Total Quote Requests:** 33,949,410 requests across 73 days
- **Active Providers:** 37 unique provider combinations
- **Asset Coverage:** 752 unique sell assets, 324 unique buy assets
- **Success Rate:** 99.93% (status code 200)
- **Average Routes per Quote:** 1-7 routes (median ~2)

---

## Table of Contents

1. [Dataset Architecture](#dataset-architecture)
2. [Table Definitions](#table-definitions)
3. [Schema Documentation](#schema-documentation)
4. [Data Grain & Relationships](#data-grain--relationships)
5. [Column Reference Guide](#column-reference-guide)
6. [Nested Field Structures](#nested-field-structures)
7. [Data Distributions & Patterns](#data-distributions--patterns)
8. [Sample Queries](#sample-queries)
9. [Data Quality Notes](#data-quality-notes)
10. [SwapKit Business Context](#swapkit-business-context)

---

## Dataset Architecture

### Source System
All three views are sourced from the production SwapKit API database (`swapkit-api.prod`):
- `quote_requests` → `swapkit-api.prod.quote_requests`
- `quote_routes` → `swapkit-api.prod.quote_routes`
- `quotes` → `swapkit-api.prod.quote_routes` (filtered)

### View Definitions

```sql
-- quote_requests view
SELECT
  request_id,
  sell_asset,
  sell_amount,
  buy_asset,
  source_address,
  destination_address,
  slippage,
  include_tx,
  status_code,
  created_at
FROM `swapkit-api.prod.quote_requests`

-- quote_routes view
SELECT
  quote_id,
  providers,
  sell_asset,
  sell_amount,
  buy_asset,
  expected_buy_amount,
  fees,
  estimated_time,
  total_slippage_bps,
  warnings,
  meta,
  provider_errors,
  status_code,
  request_id,
  error,
  created_at,
  DATE(created_at) as quote_date
FROM `swapkit-api.prod.quote_routes`

-- quotes view (90-day filtered)
SELECT
  quote_id,
  providers,
  sell_asset,
  sell_amount,
  buy_asset,
  expected_buy_amount,
  fees,
  estimated_time,
  total_slippage_bps,
  warnings,
  meta,
  provider_errors,
  status_code,
  error,
  created_at,
  DATE(created_at) as quote_date
FROM `swapkit-api.prod.quote_routes`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
```

---

## Table Definitions

### 1. quote_requests

**Purpose:** Captures user-initiated requests for swap quotes from the SwapKit API
**Type:** VIEW
**Source:** `swapkit-api.prod.quote_requests`
**Created:** September 4, 2025
**Last Modified:** September 11, 2025

**Data Coverage:**
- **Earliest Record:** August 6, 2025 13:51:09 UTC
- **Latest Record:** October 17, 2025 22:52:42 UTC
- **Total Records:** 33,949,410
- **Days with Data:** 73 days
- **Unique Request IDs:** 33,949,296 (99.999% unique)

**Grain:** One row per quote request received by the SwapKit API

---

### 2. quote_routes

**Purpose:** Contains individual routing options (paths) generated for each quote request, showing different provider combinations and their expected outputs
**Type:** VIEW
**Source:** `swapkit-api.prod.quote_routes`
**Created:** September 4, 2025
**Last Modified:** September 10, 2025

**Data Coverage:**
- **Earliest Record:** April 12, 2025 02:06:04 UTC
- **Latest Record:** October 17, 2025 22:52:50 UTC
- **Total Records:** 83,107,168
- **Days with Data:** 175 days
- **Unique Quote IDs:** 34,596,256

**Grain:** One row per routing option/path per quote. A single quote_id can have multiple routes (typically 1-7)

**Routes per Quote Distribution:**
- 1 route: 137,541 quotes (32%)
- 2 routes: 116,130 quotes (27%)
- 3 routes: 80,063 quotes (19%)
- 4 routes: 46,022 quotes (11%)
- 5 routes: 28,110 quotes (6%)
- 6 routes: 14,866 quotes (3%)
- 7+ routes: 5,721 quotes (1%)

---

### 3. quotes

**Purpose:** Filtered view of quote_routes containing only the most recent 90 days of data, optimized for real-time analytics
**Type:** VIEW
**Source:** `swapkit-api.prod.quote_routes`
**Created:** August 18, 2025
**Last Modified:** August 18, 2025

**Data Coverage:**
- **Earliest Record:** July 19, 2025 22:53:08 UTC
- **Latest Record:** October 17, 2025 22:53:05 UTC
- **Total Records:** 65,069,779
- **Days with Data:** 91 days
- **Unique Quote IDs:** 27,723,862

**Grain:** Same as quote_routes (one row per routing option), but filtered to last 90 days

**Filter Condition:** `WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)`

---

## Schema Documentation

### quote_requests Schema

| Column | Type | Mode | Description |
|--------|------|------|-------------|
| request_id | STRING | NULLABLE | Unique identifier for the quote request |
| sell_asset | STRING | NULLABLE | Asset to sell in CHAIN.SYMBOL format (e.g., "ETH.ETH") |
| sell_amount | STRING | NULLABLE | Amount of sell asset (stored as string to preserve precision) |
| buy_asset | STRING | NULLABLE | Asset to buy in CHAIN.SYMBOL format (e.g., "BTC.BTC") |
| source_address | STRING | NULLABLE | Blockchain address sending the sell asset |
| destination_address | STRING | NULLABLE | Blockchain address receiving the buy asset |
| slippage | FLOAT | NULLABLE | Maximum slippage tolerance as decimal (e.g., 0.03 = 3%) |
| include_tx | BOOLEAN | NULLABLE | Whether to include transaction details in response |
| status_code | INTEGER | NULLABLE | HTTP status code of the request (200, 400, 500) |
| created_at | TIMESTAMP | NULLABLE | Timestamp when request was received (UTC) |

---

### quote_routes Schema

| Column | Type | Mode | Description |
|--------|------|------|-------------|
| quote_id | STRING | NULLABLE | Unique identifier linking routes to the same quote |
| providers | STRING | NULLABLE | Hyphen-delimited string of providers used (e.g., "THORCHAIN_STREAMING") |
| sell_asset | STRING | NULLABLE | Asset to sell in CHAIN.SYMBOL[-CONTRACT] format |
| sell_amount | BIGNUMERIC | NULLABLE | Precise amount of sell asset as big numeric |
| buy_asset | STRING | NULLABLE | Asset to buy in CHAIN.SYMBOL[-CONTRACT] format |
| expected_buy_amount | BIGNUMERIC | NULLABLE | Expected output amount before slippage |
| expected_buy_amount_max_slippage | BIGNUMERIC | NULLABLE | Minimum guaranteed output with max slippage |
| fees | RECORD | REPEATED | Array of fee objects (see nested structure section) |
| estimated_time | RECORD | NULLABLE | Time estimates for swap completion (see nested structure) |
| total_slippage_bps | BIGNUMERIC | NULLABLE | Total slippage in basis points (negative = price improvement) |
| warnings | RECORD | REPEATED | Array of warning objects for user alerts |
| meta | RECORD | NULLABLE | Metadata including price impact, tags, affiliate info |
| provider_errors | RECORD | REPEATED | Errors from individual providers that couldn't quote |
| status_code | INTEGER | NULLABLE | HTTP status code (200 = success, 400 = bad request, 500 = error) |
| request_id | STRING | NULLABLE | Links back to the original quote_request |
| error | RECORD | NULLABLE | Top-level error object if entire quote failed |
| created_at | TIMESTAMP | NULLABLE | Timestamp when route was generated (UTC) |
| quote_date | DATE | NULLABLE | Date portion of created_at for partitioning |

---

### quotes Schema

Identical to quote_routes schema (see above). The only difference is the 90-day filter applied to created_at.

---

## Data Grain & Relationships

### Table Grain Summary

| Table | Grain | Primary Key | Foreign Keys |
|-------|-------|-------------|--------------|
| quote_requests | One row per API quote request | request_id | None |
| quote_routes | One row per routing option per quote | (quote_id, providers) composite | request_id → quote_requests |
| quotes | One row per routing option (90-day filtered) | (quote_id, providers) composite | None (view only) |

### Relationship Diagram

```
quote_requests (1)
       ↓
       ├─ request_id
       ↓
quote_routes (*) ← Multiple routes per quote_id
       ↓
       └─ Filtered by 90 days
              ↓
          quotes (*)
```

### Cardinality Notes

1. **quote_requests → quote_routes**: 1:Many
   - One request can generate multiple quote_routes (different providers)
   - Average: 2.4 routes per request
   - Range: 1-14 routes per quote_id

2. **quote_id Relationship**:
   - Multiple routes share the same quote_id (returned together)
   - Routes are ordered by best expected output
   - First route in array is typically optimal

3. **request_id Linking**:
   - Links quote_routes back to the original request parameters
   - Not all quote_routes have a request_id (may be null)

---

## Column Reference Guide

### Asset Naming Convention (CRITICAL)

SwapKit uses a strict **CHAIN.SYMBOL[-CONTRACT_ADDRESS]** format for all assets:

**Native Assets (Two Parts):**
- `BTC.BTC` - Bitcoin
- `ETH.ETH` - Ethereum (native)
- `AVAX.AVAX` - Avalanche
- `BSC.BNB` - BNB on BSC
- `THOR.RUNE` - THORChain RUNE
- `MAYA.CACAO` - Maya Protocol CACAO
- `GAIA.ATOM` - Cosmos ATOM
- `DOGE.DOGE` - Dogecoin
- `LTC.LTC` - Litecoin
- `BCH.BCH` - Bitcoin Cash

**Token Assets (Three Parts):**
- `ETH.USDT-0xdAC17F958D2ee523a2206206994597C13D831ec7` - USDT on Ethereum
- `ETH.USDC-0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48` - USDC on Ethereum
- `BSC.USDT-0x55d398326f99059fF775485246999027B3197955` - USDT on BSC

**Parsing Logic:**
```sql
-- Extract chain
SPLIT(sell_asset, '.')[OFFSET(0)] as chain

-- Extract symbol (may include contract)
SPLIT(sell_asset, '.')[OFFSET(1)] as symbol_with_contract

-- Extract symbol only (before hyphen)
SPLIT(SPLIT(sell_asset, '.')[OFFSET(1)], '-')[OFFSET(0)] as symbol

-- Extract contract address (after hyphen, if exists)
CASE
  WHEN ARRAY_LENGTH(SPLIT(sell_asset, '-')) > 1
  THEN SPLIT(sell_asset, '-')[OFFSET(1)]
  ELSE NULL
END as contract_address
```

### Provider Field Format

The `providers` field contains hyphen-delimited provider names indicating the routing path:

**Single Provider Examples:**
- `THORCHAIN` - Direct THORChain swap
- `THORCHAIN_STREAMING` - THORChain streaming swap
- `CHAINFLIP` - Chainflip cross-chain
- `NEAR` - NEAR Intents
- `ONEINCH` - 1inch DEX aggregator
- `UNISWAP_V3` - Uniswap V3

**Multi-Provider Examples:**
- `ONEINCH-THORCHAIN` - 1inch → THORChain multi-hop
- `UNISWAP_V3-THORCHAIN_STREAMING` - Uniswap → THORChain streaming
- `CHAINFLIP-JUPITER` - Chainflip → Jupiter (cross-chain to Solana)

**Provider Distribution (Last 30 Days):**
- THORCHAIN_STREAMING: 34.94% (29.0M routes)
- THORCHAIN: 32.61% (27.1M routes)
- NEAR: 7.48% (6.2M routes)
- CHAINFLIP: 4.61% (3.8M routes)
- ONEINCH-THORCHAIN: 3.67% (3.1M routes)
- Other: 16.69% (13.9M routes)

### Status Code Field

| Code | Meaning | Frequency | Description |
|------|---------|-----------|-------------|
| 200 | Success | 99.93% | Quote generated successfully |
| 400 | Bad Request | 0.05% | Invalid parameters (e.g., unsupported asset, amount too small) |
| 500 | Server Error | 0.02% | Internal error during quote generation |

### Slippage Fields

**slippage (quote_requests):**
- Type: FLOAT
- Format: Decimal percentage (e.g., 0.03 = 3%)
- Average: 2.5-3.3% depending on asset pair
- Common values: 1% (0.01), 3% (0.03), 5% (0.05)

**total_slippage_bps (quote_routes):**
- Type: BIGNUMERIC
- Format: Basis points (1 bps = 0.01%)
- **Negative values = Price Improvement** (better than expected)
- Common range: -55 to -78 bps (-0.55% to -0.78%)
- Interpretation: Negative slippage means the user gets MORE than expected output

---

## Nested Field Structures

### fees (REPEATED RECORD)

Array of fee objects, with one object per fee type per chain involved in the swap.

**Schema:**
```sql
fees ARRAY<STRUCT<
  type STRING,        -- Fee type identifier
  chain STRING,       -- Chain where fee is charged
  protocol STRING,    -- Protocol collecting the fee
  amount BIGNUMERIC,  -- Fee amount (often as fraction)
  asset STRING        -- Asset denomination (CHAIN.SYMBOL format)
>>
```

**Fee Types:**
- `liquidity` - Liquidity provider fees (pool fees)
- `outbound` - Outbound transaction fees (gas on destination)
- `inbound` - Inbound transaction fees (gas on source)
- `affiliate` - Affiliate/integrator fees
- `service` - SwapKit platform service fees (10-15 bps)
- `network` - Network/gas fees

**Sample Data:**
```json
{
  "fees": [
    {
      "type": "liquidity",
      "chain": "THOR",
      "protocol": "THORCHAIN_STREAMING",
      "amount": "1361/12500000",  // Stored as fraction
      "asset": "ETH.ETH"
    },
    {
      "type": "affiliate",
      "chain": "THOR",
      "protocol": "THORCHAIN_STREAMING",
      "amount": "81591/100000000",
      "asset": "ETH.ETH"
    },
    {
      "type": "inbound",
      "chain": "ETH",
      "protocol": "THORCHAIN_STREAMING",
      "amount": "6087968161/25000000000000",
      "asset": "ETH.ETH"
    }
  ]
}
```

**Querying Fees:**
```sql
-- Unnest fees to analyze by type
SELECT
  quote_id,
  providers,
  fee.type,
  fee.chain,
  fee.protocol,
  CAST(fee.amount AS FLOAT64) as fee_amount_float,
  fee.asset
FROM `swapkit-shared-analytics.api_data.quote_routes`,
UNNEST(fees) as fee
WHERE DATE(created_at) = CURRENT_DATE()
```

---

### estimated_time (RECORD)

Contains time estimates in seconds for different phases of the swap.

**Schema:**
```sql
estimated_time STRUCT<
  total BIGNUMERIC,     -- Total estimated completion time
  swap BIGNUMERIC,      -- Time for actual swap execution
  inbound BIGNUMERIC,   -- Time for inbound confirmation
  outbound BIGNUMERIC   -- Time for outbound confirmation
>
```

**Time Estimates by Provider (Seconds):**

| Provider | Avg Total | Avg Inbound | Avg Swap | Avg Outbound |
|----------|-----------|-------------|----------|--------------|
| THORCHAIN_STREAMING | 1,427.6 | 497.3 | 733.3 | 357.1 |
| THORCHAIN | 786.3 | 487.8 | 6.0 | 292.4 |
| NEAR | 504.8 | 304.3 | 113.6 | 86.9 |
| CHAINFLIP | 350.6 | 159.8 | 12.0 | 178.8 |
| CHAINFLIP_STREAMING | 674.4 | 193.1 | 319.6 | 161.7 |
| ONEINCH | 10.1 | 10.1 | 0 | 0 |
| UNISWAP_V3 | 10.1 | 10.1 | 0 | 0 |
| MAYACHAIN | 1,272.0 | 326.5 | 6.0 | 939.5 |

**Notes:**
- Cross-chain swaps take significantly longer (5-23 minutes avg)
- On-chain DEX swaps complete in seconds
- Streaming variants add time for improved pricing
- Values may be stored as fractions (e.g., "85/2" = 42.5 seconds)

---

### warnings (REPEATED RECORD)

Array of warning messages to display to users about potential issues with the route.

**Schema:**
```sql
warnings ARRAY<STRUCT<
  code STRING,      -- Machine-readable warning code
  display STRING,   -- Human-readable warning text
  tooltip STRING    -- Optional detailed explanation
>>
```

**Common Warning Codes:**
- `high_slippage` - Slippage exceeds typical range
- `low_liquidity` - Limited liquidity in pools
- `price_impact` - High price impact due to trade size
- `experimental` - Provider is in beta/testing
- `slow_route` - Route has long execution time

**Sample Data:**
```json
{
  "warnings": [
    {
      "code": "high_slippage",
      "display": "High slippage expected",
      "tooltip": "Trade size is large relative to pool depth"
    }
  ]
}
```

**Note:** Most routes have empty warnings array (typical successful quotes)

---

### meta (RECORD)

Metadata about the route including price impact, tags, and affiliate information.

**Schema:**
```sql
meta STRUCT<
  price_impact FLOAT,         -- Price impact as decimal (-0.01 = -1%)
  tags ARRAY<STRING>,         -- Descriptive tags for the route
  approval_address STRING,    -- Contract address for token approval (EVM)
  affiliate STRING,           -- Affiliate identifier
  affiliate_fee BIGNUMERIC,   -- Affiliate fee in basis points
  streaming_interval INTEGER, -- Interval for streaming swaps (seconds)
  max_streaming_quantity BIGNUMERIC, -- Max quantity per stream
  assets ARRAY<STRUCT<        -- Asset metadata
    asset STRING,             -- Asset identifier
    price FLOAT,              -- USD price
    image STRING              -- Image URL
  >>
>
```

**Field Descriptions:**

- **price_impact**: Negative = unfavorable, typical range: -0.005 to -0.015 (-0.5% to -1.5%)
- **tags**: Examples: `["RECOMMENDED"]`, `["FASTEST"]`, `["BEST_RETURN"]`
- **approval_address**: Only present for ERC-20 tokens requiring approval
- **affiliate**: Short identifier like "ll" (integrator code)
- **affiliate_fee**: Basis points, e.g., 75 = 0.75% fee

**Sample Data:**
```json
{
  "meta": {
    "price_impact": -0.009510434896729222,
    "tags": [],
    "approval_address": null,
    "affiliate": "ll",
    "affiliate_fee": "75",
    "assets": []
  }
}
```

---

### provider_errors (REPEATED RECORD)

Contains errors from individual providers that couldn't generate a quote for this request.

**Schema:**
```sql
provider_errors ARRAY<STRUCT<
  error_code STRING,  -- Machine-readable error code
  provider STRING,    -- Provider that failed
  message STRING      -- Human-readable error message
>>
```

**Common Error Codes:**

| Error Code | Description | Typical Cause |
|------------|-------------|---------------|
| `noQuoteResponse` | Provider didn't return a quote | Provider unavailable or unsupported pair |
| `insufficientBalance` | Insufficient balance in source address | User doesn't have enough of sell_asset |
| `sellAssetAmountTooSmall` | Amount below minimum | Trade size below provider's minimum |
| `unsupportedAsset` | Asset not supported | Provider doesn't support the asset pair |
| `unknownError` | Generic error | Various technical issues |

**Sample Data:**
```json
{
  "provider_errors": [
    {
      "error_code": "insufficientBalance",
      "provider": "THORCHAIN_STREAMING",
      "message": "Cannot build transaction. Insufficient balance for asset BTC.BTC amount 0.007582 address bc1qkwzq3xrqxqs90wrrqml9j8fdjxeykmz5ypm3s8"
    },
    {
      "error_code": "sellAssetAmountTooSmall",
      "provider": "THORCHAIN",
      "message": "Sell asset amount too small for provider THORCHAIN. Min amount is N/A BSC.BNB"
    }
  ]
}
```

**Interpretation:**
- Routes can still be successful even if some providers errored
- Providers in the errors array were attempted but couldn't quote
- Final `providers` field contains only successful providers

---

### error (RECORD)

Top-level error object when the entire quote request fails (not provider-specific).

**Schema:**
```sql
error STRUCT<
  error STRING,     -- Error type/category
  message STRING,   -- Human-readable error message
  data STRUCT<      -- Additional error context
    sell_asset STRING,
    buy_asset STRING
  >
>
```

**When Present:**
- `status_code` will be 400 or 500
- All provider_errors will typically be populated
- No successful routes available

**Sample Data:**
```json
{
  "error": {
    "error": "ValidationError",
    "message": "Unsupported asset pair",
    "data": {
      "sell_asset": "INVALID.ASSET",
      "buy_asset": "BTC.BTC"
    }
  }
}
```

---

## Data Distributions & Patterns

### Top Asset Pairs (Last 30 Days)

| Sell Asset | Buy Asset | Route Count | Avg Sell | Avg Buy |
|------------|-----------|-------------|----------|---------|
| ETH.ETH | BTC.BTC | 864,269 | 29.87 | 1.02 |
| ETH.ETH | ETH.USDC-* | 645,319 | 38.25 | 145,818.87 |
| BTC.BTC | ETH.ETH | 572,350 | 1.76 | 35.79 |
| ETH.ETH | BSC.BNB | 559,792 | 19.78 | 61.86 |
| ETH.USDT-* | BTC.BTC | 552,704 | 89,045.85 | 0.63 |

*Full contract addresses omitted for readability*

### Provider Performance Metrics

| Provider | Routes | Success Rate | Avg Time (s) | Market Share |
|----------|--------|--------------|--------------|--------------|
| THORCHAIN_STREAMING | 29.0M | 99.94% | 1,427.6 | 34.94% |
| THORCHAIN | 27.1M | 99.95% | 786.3 | 32.61% |
| NEAR | 6.2M | 99.89% | 504.8 | 7.48% |
| CHAINFLIP | 3.8M | 99.91% | 350.6 | 4.61% |
| ONEINCH-THORCHAIN | 3.1M | 99.93% | 420.0 | 3.67% |

### Slippage Distribution

**Requested Slippage (quote_requests):**
- Average: 2.5-3.3% depending on pair
- Median: ~2.5%
- Common values: 1%, 3%, 5%

**Actual Slippage (quote_routes total_slippage_bps):**
- Mean: ~-70 bps (-0.70%)
- Most common: -65 to -78 bps
- **Negative = Price Improvement** (better than expected)

### Temporal Patterns

**Daily Volume Distribution:**
- Peak days: 600,000+ routes per day
- Average: ~475,000 routes per day
- Data available: 175 consecutive days

**Hourly Patterns (UTC):**
- Peak hours: 12:00-18:00 UTC (US business hours)
- Low hours: 04:00-08:00 UTC (US night)

---

## Sample Queries

### 1. Basic Route Analysis

```sql
-- Top 10 asset pairs by volume (last 7 days)
SELECT
  sell_asset,
  buy_asset,
  COUNT(*) as route_count,
  AVG(CAST(sell_amount AS FLOAT64)) as avg_sell_amount,
  AVG(CAST(expected_buy_amount AS FLOAT64)) as avg_buy_amount
FROM `swapkit-shared-analytics.api_data.quote_routes`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND status_code = 200
GROUP BY sell_asset, buy_asset
ORDER BY route_count DESC
LIMIT 10;
```

### 2. Provider Performance Comparison

```sql
-- Provider success rates and timing
SELECT
  providers,
  COUNT(*) as total_routes,
  COUNTIF(status_code = 200) as successful_routes,
  ROUND(COUNTIF(status_code = 200) * 100.0 / COUNT(*), 2) as success_rate_pct,
  ROUND(AVG(CAST(estimated_time.total AS FLOAT64)), 1) as avg_time_seconds,
  ROUND(AVG(CAST(total_slippage_bps AS FLOAT64)), 1) as avg_slippage_bps
FROM `swapkit-shared-analytics.api_data.quote_routes`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY providers
HAVING total_routes > 1000
ORDER BY total_routes DESC
LIMIT 20;
```

### 3. Fee Analysis

```sql
-- Aggregate fees by type across all routes
SELECT
  fee.type as fee_type,
  fee.chain,
  COUNT(*) as fee_count,
  AVG(CAST(fee.amount AS FLOAT64)) as avg_fee_amount,
  fee.asset
FROM `swapkit-shared-analytics.api_data.quote_routes`,
UNNEST(fees) as fee
WHERE DATE(created_at) >= CURRENT_DATE() - 7
GROUP BY fee.type, fee.chain, fee.asset
ORDER BY fee_count DESC;
```

### 4. Routing Complexity Analysis

```sql
-- Distribution of routes per quote
SELECT
  routes_per_quote,
  COUNT(*) as quote_count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM (
  SELECT
    quote_id,
    COUNT(*) as routes_per_quote
  FROM `swapkit-shared-analytics.api_data.quote_routes`
  WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  GROUP BY quote_id
)
GROUP BY routes_per_quote
ORDER BY routes_per_quote;
```

### 5. Error Analysis

```sql
-- Most common provider errors
SELECT
  provider_error.error_code,
  provider_error.provider,
  COUNT(*) as error_count,
  APPROX_TOP_COUNT(provider_error.message, 3) as top_messages
FROM `swapkit-shared-analytics.api_data.quote_routes`,
UNNEST(provider_errors) as provider_error
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY provider_error.error_code, provider_error.provider
ORDER BY error_count DESC
LIMIT 20;
```

### 6. Asset Popularity & Liquidity

```sql
-- Most traded assets (both buy and sell side)
WITH sell_assets AS (
  SELECT sell_asset as asset, COUNT(*) as count
  FROM `swapkit-shared-analytics.api_data.quote_routes`
  WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY sell_asset
),
buy_assets AS (
  SELECT buy_asset as asset, COUNT(*) as count
  FROM `swapkit-shared-analytics.api_data.quote_routes`
  WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  GROUP BY buy_asset
)
SELECT
  COALESCE(s.asset, b.asset) as asset,
  COALESCE(s.count, 0) as times_sold,
  COALESCE(b.count, 0) as times_bought,
  COALESCE(s.count, 0) + COALESCE(b.count, 0) as total_volume
FROM sell_assets s
FULL OUTER JOIN buy_assets b ON s.asset = b.asset
ORDER BY total_volume DESC
LIMIT 30;
```

### 7. Time-Series Volume Analysis

```sql
-- Daily quote volume trend
SELECT
  DATE(created_at) as quote_date,
  COUNT(*) as total_routes,
  COUNT(DISTINCT quote_id) as unique_quotes,
  ROUND(COUNT(*) * 1.0 / COUNT(DISTINCT quote_id), 2) as avg_routes_per_quote,
  COUNTIF(status_code = 200) as successful_routes
FROM `swapkit-shared-analytics.api_data.quote_routes`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY quote_date
ORDER BY quote_date DESC;
```

### 8. Cross-Chain vs Same-Chain Analysis

```sql
-- Identify cross-chain vs same-chain swaps
SELECT
  CASE
    WHEN SPLIT(sell_asset, '.')[OFFSET(0)] = SPLIT(buy_asset, '.')[OFFSET(0)]
    THEN 'Same Chain'
    ELSE 'Cross Chain'
  END as swap_type,
  COUNT(*) as route_count,
  ROUND(AVG(CAST(estimated_time.total AS FLOAT64)), 1) as avg_time_seconds,
  ROUND(AVG(CAST(total_slippage_bps AS FLOAT64)), 1) as avg_slippage_bps
FROM `swapkit-shared-analytics.api_data.quote_routes`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND status_code = 200
GROUP BY swap_type;
```

### 9. Affiliate Revenue Analysis

```sql
-- Top affiliates by volume and revenue
SELECT
  meta.affiliate,
  COUNT(*) as quote_count,
  ROUND(AVG(CAST(meta.affiliate_fee AS FLOAT64)), 2) as avg_affiliate_fee_bps,
  SUM(CAST(sell_amount AS FLOAT64)) as total_sell_volume
FROM `swapkit-shared-analytics.api_data.quote_routes`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
  AND meta.affiliate IS NOT NULL
  AND status_code = 200
GROUP BY meta.affiliate
ORDER BY quote_count DESC
LIMIT 20;
```

### 10. Quote Request to Route Conversion

```sql
-- Join requests to routes to analyze conversion
SELECT
  DATE(qreq.created_at) as request_date,
  COUNT(DISTINCT qreq.request_id) as total_requests,
  COUNT(DISTINCT qroute.quote_id) as quotes_with_routes,
  ROUND(COUNT(DISTINCT qroute.quote_id) * 100.0 / COUNT(DISTINCT qreq.request_id), 2) as conversion_rate_pct
FROM `swapkit-shared-analytics.api_data.quote_requests` qreq
LEFT JOIN `swapkit-shared-analytics.api_data.quote_routes` qroute
  ON qreq.request_id = qroute.request_id
WHERE qreq.created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY request_date
ORDER BY request_date DESC;
```

---

## Data Quality Notes

### Completeness

**quote_requests:**
- ✅ All records have created_at timestamps
- ✅ 99.999% unique request_ids
- ⚠️ source_address and destination_address may be null
- ⚠️ sell_amount stored as STRING (parse to numeric for calculations)

**quote_routes:**
- ✅ All records have created_at and quote_date
- ✅ High success rate (99.93% status 200)
- ⚠️ request_id may be null (not all routes link back to requests)
- ⚠️ Nested arrays (fees, warnings, provider_errors) can be empty
- ⚠️ BIGNUMERIC fields may contain fractions (e.g., "1361/12500000")

**quotes:**
- ✅ Same quality as quote_routes
- ⚠️ Only contains last 90 days (rolling window)

### Data Freshness

- **Real-time:** Data appears within seconds of API calls
- **Latency:** < 1 minute typical delay from production to analytics
- **Availability:** 24/7 continuous data flow

### Known Issues & Limitations

1. **Fractional Values:** Many BIGNUMERIC fields store values as fractions (numerator/denominator) to preserve exact precision
   - Solution: Cast to FLOAT64 for calculations: `CAST(field AS FLOAT64)`

2. **Missing request_id:** Not all quote_routes have a request_id linking back to quote_requests
   - Impact: Cannot always trace routes back to original request parameters
   - Workaround: Use quote_id grouping instead

3. **Provider String Format:** Hyphen-delimited string makes parsing complex
   - Solution: Use `SPLIT(providers, '-')` to get array

4. **Asset Contract Addresses:** Full contract addresses make asset grouping difficult
   - Solution: Extract symbol before hyphen for aggregation

5. **Empty Nested Arrays:** fees, warnings, and provider_errors can be empty arrays
   - Solution: Check `ARRAY_LENGTH(field) > 0` before unnesting

6. **Time Zone:** All timestamps in UTC
   - Solution: Convert to local time zones as needed using `TIMESTAMP(created_at, 'America/New_York')`

### Recommended Filters

For most analyses, apply these filters to improve data quality:

```sql
WHERE status_code = 200  -- Only successful quotes
  AND sell_amount > 0    -- Valid amounts
  AND buy_amount > 0
  AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)  -- Recent data
```

---

## SwapKit Business Context

### What is SwapKit?

SwapKit is an open-source SDK and REST API developed by THORSwap that enables seamless cross-chain cryptocurrency swaps across **30+ blockchains and 10,000+ crypto assets**. The platform aggregates liquidity from multiple decentralized protocols and DEX aggregators, allowing developers to integrate native cross-chain swap functionality in under 100 lines of code.

### Core Liquidity Providers

**Cross-Chain Protocols:**
- **THORChain** (THORCHAIN / THORCHAIN_STREAMING) - 67.55% of routes
  - Supports: BTC, ETH, BSC, AVAX, ATOM, DOGE, LTC, BCH, Base, Arbitrum
  - Avg time: 786-1,427 seconds depending on streaming

- **NEAR Intents** (NEAR) - 7.48% of routes
  - Supports: 15+ chains with gas abstraction
  - Avg time: 504 seconds

- **Chainflip** (CHAINFLIP / CHAINFLIP_STREAMING) - 6.64% of routes
  - Supports: BTC, ETH, Solana, Arbitrum
  - Avg time: 350-674 seconds

- **Maya Protocol** (MAYACHAIN / MAYACHAIN_STREAMING) - 3.40% of routes
  - THORChain fork with unique chains (Dash, ZCash, Kujira, Radix)
  - Avg time: 1,272-1,332 seconds

**On-Chain DEX Aggregators:**
- **1inch** (ONEINCH) - 3.41% of routes
- **Uniswap V2/V3** (UNISWAP_V2 / UNISWAP_V3) - 1.98% of routes
- **SushiSwap** (SUSHISWAP_V2) - 1.81% of routes
- **Jupiter** (JUPITER) - Solana DEX aggregator
- **TraderJoe V2** (TRADERJOE_V2) - Avalanche

### Revenue Model

**SwapKit Platform Fees:**
- **10-15 basis points** (0.10%-0.15%) on swaps between:
  - Gas assets: BTC, ETH, AVAX, SOL, XRP, TRX, ATOM, NEAR, BNB, ZEC, RUNE, LTC, BCH, DOGE
  - Stablecoins: USDC, USDT
- **No fees** on other pairs (e.g., ERC-20 to ERC-20)
- Fees collected transparently via on-chain router contracts

**Affiliate Program:**
- Integrators set custom `affiliate_fee` in basis points
- Stored in `meta.affiliate` and `meta.affiliate_fee` fields
- Examples from data:
  - "ll" affiliate: 75-85 bps (0.75%-0.85%)
  - Major integrators (Trust Wallet, Edge) earn $100K-$12M annually

### Quote Lifecycle

1. **Request Phase** (quote_requests table)
   - User/integrator calls `/quote` endpoint
   - Provides: sell_asset, sell_amount, buy_asset, addresses, slippage
   - Receives: quote_id and array of routes

2. **Route Generation Phase** (quote_routes table)
   - SwapKit queries multiple providers simultaneously
   - Each provider returns a routing option (or error)
   - Routes ordered by best expected output
   - Multiple routes per quote_id (typically 1-7)

3. **Route Selection**
   - User selects best route (usually first in array)
   - Route marked as `optimal` if recommended by algorithm

4. **Execution** (not in this dataset)
   - User executes selected route via transaction
   - Tracked via `/track` endpoint (separate system)

### Key Integrations

Over 50+ protocols use SwapKit, including:
- **Ledger Live** - Hardware wallet integration
- **Trust Wallet** - Multi-chain mobile wallet
- **Edge Wallet** - Self-custody wallet
- **BitPay** - Payment processor
- **LI.FI** - Powers MetaMask, Robinhood, Phantom swaps
- **THORSwap** - Native DEX (self-dogfooding)

### Data Use Cases

This dataset enables analysis of:

1. **Provider Performance:** Success rates, timing, pricing across providers
2. **Liquidity Patterns:** Which asset pairs have deepest liquidity
3. **User Behavior:** Slippage tolerance, preferred routes, cross-chain vs same-chain
4. **Fee Economics:** Total fees by type, affiliate revenue, platform earnings
5. **Market Trends:** Asset popularity, trading volume, chain adoption
6. **Error Analytics:** Common failure modes, provider reliability
7. **Product Optimization:** Route selection effectiveness, API performance

---

## Appendix: Asset Format Examples

### Popular Native Assets

| Asset Code | Full Name | Chain |
|------------|-----------|-------|
| BTC.BTC | Bitcoin | Bitcoin |
| ETH.ETH | Ethereum | Ethereum |
| BSC.BNB | BNB | BSC |
| AVAX.AVAX | Avalanche | Avalanche |
| THOR.RUNE | RUNE | THORChain |
| MAYA.CACAO | CACAO | Maya Protocol |
| GAIA.ATOM | Cosmos ATOM | Cosmos Hub |
| SOL.SOL | Solana | Solana |
| DOT.DOT | Polkadot | Polkadot |
| DOGE.DOGE | Dogecoin | Dogecoin |
| LTC.LTC | Litecoin | Litecoin |
| BCH.BCH | Bitcoin Cash | Bitcoin Cash |

### Popular Token Assets

| Asset Code | Full Name | Contract |
|------------|-----------|----------|
| ETH.USDT-0xdAC17F958D2ee523a2206206994597C13D831ec7 | Tether USD | Ethereum |
| ETH.USDC-0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48 | USD Coin | Ethereum |
| BSC.USDT-0x55d398326f99059fF775485246999027B3197955 | Tether USD | BSC |
| ETH.WBTC-0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599 | Wrapped BTC | Ethereum |

### Chain Identifier Reference

| Chain ID | Name | Native Asset |
|----------|------|--------------|
| BTC | Bitcoin | BTC.BTC |
| ETH | Ethereum | ETH.ETH |
| BSC | BNB Smart Chain | BSC.BNB |
| AVAX | Avalanche C-Chain | AVAX.AVAX |
| THOR | THORChain | THOR.RUNE |
| MAYA | Maya Protocol | MAYA.CACAO |
| GAIA | Cosmos Hub | GAIA.ATOM |
| SOL | Solana | SOL.SOL |
| DOT | Polkadot | DOT.DOT |
| ARB | Arbitrum | ARB.ETH |
| OP | Optimism | OP.ETH |
| BASE | Base | BASE.ETH |
| MATIC | Polygon | MATIC.MATIC |
| DOGE | Dogecoin | DOGE.DOGE |
| LTC | Litecoin | LTC.LTC |
| BCH | Bitcoin Cash | BCH.BCH |

---

## Data Governance & Access

### Access Control
- **Dataset:** Read-only access via shared analytics views
- **Location:** US (multi-region)
- **Authentication:** Google Cloud IAM with role-based access
- **Permissions:** BigQuery Data Viewer role required

### Data Retention
- **quote_requests:** Full history from August 6, 2025
- **quote_routes:** Full history from April 12, 2025
- **quotes:** Rolling 90-day window (automatically filtered)

### Privacy Considerations
- **No PII:** Blockchain addresses are public data
- **Anonymization:** request_id and quote_id are system-generated UUIDs
- **Aggregation Recommended:** For external sharing, aggregate to remove individual transaction details

### Support & Contact
- **Dataset Owner:** SwapKit Analytics Team (robot@swapkit.dev)
- **Documentation Issues:** Report via internal data team channels
- **Data Quality Issues:** Submit ticket with affected quote_id/request_id

---

## Changelog

### Version 1.0 (October 17, 2025)
- Initial comprehensive data dictionary
- Documented all three views (quote_requests, quote_routes, quotes)
- Added nested field structures and sample queries
- Included SwapKit business context and provider information
- Analyzed 83M+ quote routes and 34M+ requests

---

**Report Generated:** October 17, 2025
**Data Coverage Through:** October 17, 2025 22:52:50 UTC
**Next Update:** As needed when schema changes occur
