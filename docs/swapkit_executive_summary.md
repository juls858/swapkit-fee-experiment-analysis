# SwapKit BigQuery Dataset Analysis - Executive Summary

**Analysis Date:** October 17, 2025
**Analyst:** Claude (Anthropic AI)
**Dataset:** `swapkit-shared-analytics.api_data`

---

## Overview

This analysis provides comprehensive documentation for the SwapKit BigQuery dataset shared for analytics purposes. The dataset contains quote request and routing data from SwapKit's cross-chain cryptocurrency swap API, spanning nearly 6 months of production data.

## Key Deliverables

### 1. Business Context Report
**File:** SwapKit Cross-Chain DeFi Infrastructure Report
**Content:**
- Company overview and business model
- API structure and endpoint documentation
- Provider ecosystem (THORChain, Chainflip, Maya, NEAR Intents)
- Technical architecture and routing mechanics
- Asset naming conventions and data structures
- Integration patterns and use cases

### 2. Technical Data Dictionary
**File:** `swapkit_bigquery_data_dictionary.md`
**Content:**
- Complete schema documentation for all 3 tables
- Column-level field descriptions
- Nested structure breakdowns (fees, warnings, errors, metadata)
- Data ranges, volumes, and distributions
- Sample queries for common analyses
- Data quality notes and best practices

---

## Dataset Quick Facts

### Tables Overview

| Table | Type | Records | Date Range | Grain |
|-------|------|---------|------------|-------|
| **quote_requests** | VIEW | 33.9M | Aug 6 - Oct 17, 2025 (73 days) | One row per API request |
| **quote_routes** | VIEW | 83.1M | Apr 12 - Oct 17, 2025 (175 days) | One row per routing option |
| **quotes** | VIEW | 65.1M | Jul 19 - Oct 17, 2025 (91 days) | Filtered quote_routes (90-day) |

### Data Health

- **Success Rate:** 99.93% (status code 200)
- **Data Freshness:** Real-time (< 1 minute latency)
- **Completeness:** All critical fields populated
- **Quality:** Production-grade with minor parsing considerations

### Top Insights

**Provider Market Share:**
- THORChain (combined): 67.5%
- NEAR Intents: 7.5%
- Chainflip (combined): 6.6%
- DEX Aggregators: 18.4%

**Most Popular Pairs:**
1. ETH.ETH → BTC.BTC (864K routes/month)
2. ETH.ETH → ETH.USDC (645K routes/month)
3. BTC.BTC → ETH.ETH (572K routes/month)

**Performance:**
- Average routes per quote: 2.4
- Cross-chain swaps: 5-23 minutes avg
- On-chain swaps: <30 seconds avg

---

## Critical Schema Details

### Asset Format: CHAIN.SYMBOL[-CONTRACT]

**Examples:**
- Native: `BTC.BTC`, `ETH.ETH`, `AVAX.AVAX`
- Tokens: `ETH.USDT-0xdAC17F958D2ee523a2206206994597C13D831ec7`

**Parsing Pattern:**
```sql
SPLIT(asset, '.')[OFFSET(0)] as chain
SPLIT(SPLIT(asset, '.')[OFFSET(1)], '-')[OFFSET(0)] as symbol
```

### Nested Structures

**fees (REPEATED RECORD):**
- Array of fee objects per chain
- Types: liquidity, inbound, outbound, affiliate, service
- Values stored as fractions: `"1361/12500000"`

**estimated_time (RECORD):**
- total, swap, inbound, outbound (seconds)
- May contain fractions: `"85/2"` = 42.5 seconds

**provider_errors (REPEATED RECORD):**
- Array of errors from failed providers
- Common codes: `insufficientBalance`, `sellAssetAmountTooSmall`, `noQuoteResponse`

### Key Relationships

```
quote_requests (1)
       ↓ request_id
quote_routes (*)  ← Multiple routes per quote_id
       ↓ 90-day filter
quotes (*)
```

---

## Getting Started with Analysis

### Essential First Queries

**1. Daily Volume Trend:**
```sql
SELECT
  DATE(created_at) as date,
  COUNT(*) as total_routes,
  COUNT(DISTINCT quote_id) as unique_quotes
FROM `swapkit-shared-analytics.api_data.quote_routes`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
GROUP BY date
ORDER BY date DESC;
```

**2. Provider Performance:**
```sql
SELECT
  providers,
  COUNT(*) as routes,
  COUNTIF(status_code = 200) * 100.0 / COUNT(*) as success_rate,
  AVG(CAST(estimated_time.total AS FLOAT64)) as avg_time_sec
FROM `swapkit-shared-analytics.api_data.quote_routes`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY providers
ORDER BY routes DESC
LIMIT 10;
```

**3. Top Asset Pairs:**
```sql
SELECT
  sell_asset,
  buy_asset,
  COUNT(*) as route_count
FROM `swapkit-shared-analytics.api_data.quote_routes`
WHERE created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
  AND status_code = 200
GROUP BY sell_asset, buy_asset
ORDER BY route_count DESC
LIMIT 20;
```

### Recommended Filters

```sql
-- Standard quality filter
WHERE status_code = 200  -- Successful quotes only
  AND sell_amount > 0
  AND expected_buy_amount > 0
  AND created_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
```

---

## Common Pitfalls & Solutions

### 1. Fractional Values
**Problem:** BIGNUMERIC fields contain fractions like `"1361/12500000"`
**Solution:** Cast to FLOAT64: `CAST(field AS FLOAT64)`

### 2. Multiple Routes per Quote
**Problem:** Can't tell which route user selected
**Solution:** Assume first route (ordered by best output) or aggregate all routes

### 3. Nested Array Unnesting
**Problem:** Need to flatten fees/errors arrays
**Solution:** Use UNNEST: `FROM table, UNNEST(fees) as fee`

### 4. Missing request_id
**Problem:** Not all routes link back to requests
**Solution:** Use quote_id for grouping instead

### 5. Provider String Parsing
**Problem:** Hyphen-delimited provider combinations
**Solution:** `SPLIT(providers, '-')` or use as-is for aggregation

---

## Use Case Examples

### Market Analysis
- Asset pair popularity and trends
- Cross-chain vs same-chain swap patterns
- Liquidity depth by provider and pair
- Geographic/temporal trading patterns

### Provider Analytics
- Success rates and reliability metrics
- Execution time benchmarking
- Fee competitiveness analysis
- Error patterns and debugging

### Revenue Attribution
- Affiliate fee tracking (`meta.affiliate`, `meta.affiliate_fee`)
- Platform fee estimation (10-15 bps on gas-stablecoin pairs)
- Provider split analysis

### Product Optimization
- Route selection effectiveness
- API performance and latency
- Error rate reduction opportunities
- User slippage tolerance patterns

### Data Science Applications
- Price prediction modeling
- Optimal routing algorithms
- Anomaly detection (unusual swaps)
- Time series forecasting

---

## Data Limitations & Caveats

1. **Quote vs Execution:** Dataset contains quotes only, not actual executed swaps
2. **90-Day Retention:** `quotes` table only retains recent data
3. **No User IDs:** Cannot track individual users across requests (by design)
4. **Incomplete Linkage:** request_id may be null in quote_routes
5. **UTC Timestamps:** All times in UTC, convert as needed for local analysis

---

## Next Steps for Analysts

### Immediate Actions
1. ✅ Review technical data dictionary (`swapkit_bigquery_data_dictionary.md`)
2. ✅ Run sample queries to familiarize with data structure
3. ✅ Test nested field unnesting with small date ranges
4. ✅ Validate asset format parsing logic

### Analysis Planning
1. Define specific business questions
2. Identify required fields and joins
3. Determine appropriate time windows
4. Plan aggregation strategy for large datasets
5. Consider data refresh requirements

### Advanced Topics
1. **Time Series Analysis:** Daily/hourly patterns, seasonality
2. **Cohort Analysis:** Provider adoption over time
3. **Network Analysis:** Asset pair relationships
4. **Predictive Modeling:** Route success prediction
5. **Real-time Dashboards:** Streaming analytics setup

---

## Support & Resources

### Documentation Files
- **Business Context:** SwapKit Cross-Chain DeFi Infrastructure Report (artifact)
- **Technical Reference:** `swapkit_bigquery_data_dictionary.md`
- **This Summary:** Quick reference guide

### External Resources
- SwapKit Docs: https://docs.swapkit.dev
- SwapKit API: https://docs.swapkit.dev/swapkit-api/introduction
- THORSwap Docs: https://docs.thorswap.finance

### Contact
- **Dataset Owner:** robot@swapkit.dev
- **Access Issues:** Google Cloud IAM administrators
- **Data Questions:** Internal data team

---

## Conclusion

The SwapKit BigQuery dataset provides rich, production-quality data for analyzing cross-chain cryptocurrency swap patterns. With 83M+ quote routes across 175 days, covering 30+ blockchains and 1,000+ asset pairs, this dataset enables comprehensive analysis of:

- **Market dynamics:** Asset popularity, liquidity flows, trading patterns
- **Provider performance:** Success rates, speed, pricing competitiveness
- **Revenue attribution:** Affiliate fees, platform economics
- **Product insights:** User behavior, routing effectiveness, API performance

The combination of detailed technical documentation and business context empowers analysts to conduct sophisticated analyses while understanding the underlying SwapKit architecture and cross-chain DeFi ecosystem.

**Ready to dive deeper?** Start with the technical data dictionary and sample queries, then explore the full dataset using the patterns documented in this analysis.

---

**Report Generated:** October 17, 2025
**Version:** 1.0
**Status:** Complete & Production-Ready
