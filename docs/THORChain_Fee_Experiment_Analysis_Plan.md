# THORChain Fee Experiment Analysis Plan

## **I. Key Business Questions to Answer**

### **Primary Questions (Revenue Focus)**

1. **What is the revenue-optimal fee rate?** Which fee tier (5, 10, 15, 20, or 25 bps) generated the highest absolute revenue?
   1. take into account volume by swap pair
2. **What is the price elasticity of demand?** How much does volume drop for each bps increase in fees?
3. **What is the revenue elasticity?** At what point do volume decreases outweigh fee increases?
4. **Is there a "sweet spot"?** Do we see diminishing returns above/below certain thresholds?

### **Secondary Questions (User Behavior & Market Dynamics)**

1. **User retention vs. acquisition**: Do higher fees cause existing users to churn, or do they primarily deter new users?
2. **Trade size sensitivity**: Are large trades (whales) more or less fee-sensitive than small trades?
3. **Competitive leakage**: Did we lose market share to Chainflip/other protocols during high-fee weeks?
4. **Pool-specific responses**: Do different asset pairs (BTC-USD vs. ETH-USDC vs. long-tail assets) show different elasticities?
5. **Affiliate behavior**: Did affiliate interfaces change their behavior or routing during the experiment?

### **Operational Questions**

1. **Day-of-week effects**: Were certain fee rates more effective on high-volume days (e.g., weekends)?
2. **Statistical confidence**: Are our results statistically significant, or could they be explained by market noise?

---

## **II. Analysis Plan \- Phased Approach**

### **Phase 1: Data Foundation & Descriptive Analytics (Week 1\)**

A. Data Collection & Validation
**Tasks**:

* Extract all swap data for experiment period (define exact start/end dates for each week)
* Validate fee rates applied per week against intended experiment design
* Identify and handle any mid-week rate changes or anomalies
* Pull comparison data from pre-experiment period (same duration, prior year for seasonality)
* Gather affiliate data, pool-specific metrics, and liquidity snapshots

**Key Tables** (Flipside):

* `thorchain.defi.fact_swaps` \- core swap data
* `thorchain.defi.fact_liquidity_actions` \- LP behavior
* Revenue/fee tables for each week

**Deliverable**: Clean dataset with validated fee periods, flagged anomalies
---

B. Descriptive Statistics by Week
**Owner**: Analytics Team
**Metrics to Calculate Per Week**:

| Metric | Purpose |
| :---- | :---- |
| Total swap volume (USD) | Understand volume response |
| Total swap fees collected (USD) | **PRIMARY METRIC** |
| Number of swaps | Granularity of activity |
| Unique swappers | User retention signal |
| Avg swap size (USD) | Trade size distribution |
| Median swap size (USD) | Robustness to outliers |
| P75/P90/P99 swap sizes | Whale behavior |
| New vs. returning swappers | Acquisition vs. retention |
| Revenue per swap | Efficiency metric |
| Revenue per user | User value metric |

**Visualizations**:

* Line chart: Weekly revenue vs. fee rate (with confidence intervals)
* Line chart: Weekly volume vs. fee rate
* Bar chart: Revenue comparison across all weeks
* Scatter plot: Fee rate vs. revenue (to visualize relationship)

**Deliverable**: Summary dashboard with week-over-week comparisons
---

### **Phase 2: Core Revenue Analysis (Week 2\)**

C. Elasticity Analysis
**Analysis**:

1. **Calculate Price Elasticity of Demand (PED)**:
* PED \= % change in volume / % change in fee rate
* Calculate for each fee transition (e.g., 10→25 bps, 25→10 bps, etc.)
* Average elasticity across similar transitions
1. **Calculate Revenue Elasticity**:
* Revenue elasticity \= % change in revenue / % change in fee rate
* If revenue elasticity \> 0: fee increases are beneficial
* If revenue elasticity \< 0: fee increases hurt revenue
1. **Identify Optimal Fee Rate**:
* Model: Revenue \= Volume × Fee Rate
* Use regression to estimate demand curve: Volume \= α \- β × Fee Rate
* Solve for revenue-maximizing fee: dRevenue/dFee \= 0

**Statistical Methods**:

* Regression analysis (controlling for external factors)
* Bootstrap confidence intervals for elasticity estimates
* Sensitivity analysis for different model specifications

**Deliverable**: Elasticity report with optimal fee recommendation and confidence bounds
---

D. Revenue Attribution & Decomposition
**Analysis**:

* Decompose revenue changes into:
1. **Fee rate effect** (direct impact of rate change)
2. **Volume effect** (volume response to rate change)
3. **Mix effect** (changes in trade size distribution)
4. **External effect** (market conditions, crypto prices)
* Use difference-in-differences approach comparing to:
  * Pre-experiment baseline
  * Competitor protocols (if data available)

**Deliverable**: Waterfall chart showing revenue drivers by week
---

### **Phase 3: User Behavior & Segmentation (Week 2-3)**

E. Cohort Analysis
**Analysis**:

1. **User Retention by Fee Tier**:
* Track users who swapped in Week 0 (10 bps baseline)
* Measure retention in subsequent weeks by fee level
* Calculate churn rate for high-fee vs. low-fee weeks
1. **New User Acquisition**:
* Count new users (first swap ever) per week
* Compare acquisition during high vs. low fee weeks
* Calculate customer acquisition cost equivalent
1. **User Lifetime Value (LTV) Impact**:
* Estimate LTV for users acquired at different fee tiers
* Do users acquired during low-fee periods generate more long-term revenue?

**Deliverable**: Cohort retention curves and LTV estimates by acquisition fee tier
---

F. Trade Size Segmentation
**Segments**:

* Micro: \<$100
* Small: $100-$1,000
* Medium: $1,000-$10,000
* Large: $10,000-$100,000
* Whale: \>$100,000

**Analysis for Each Segment**:

* Volume and revenue contribution by week
* Fee sensitivity (elasticity) by segment
* Average fee paid (absolute $) by segment
* Retention/churn patterns

**Key Question**: Are whales fee-insensitive (they pay anyway), making them the target for higher fees?
**Deliverable**: Segment-level elasticity report with revenue optimization by segment
---

### **Phase 4: Pool & Asset Analysis (Week 3\)**

G. Pool-Level Revenue Analysis
**Analysis**:

* Top 10 pools by revenue contribution
* Elasticity by pool type:
  * **BTC pools** (BTC.BTC, BTC-ETH, BTC-stablecoins)
  * **ETH pools**
  * **Stablecoin pairs**
  * **Long-tail assets**

**Hypothesis**:

* BTC/stablecoin pairs (high utility) may be less elastic
* Long-tail pairs (speculative) may be more elastic

**Deliverable**: Pool-level elasticity matrix and revenue recommendations
---

H. Competitive Analysis
**Owner**: Market Intelligence Analyst
**External Data Needed**:

* Chainflip volumes during experiment period
* Near Intents (if available)
* Wrapped BTC trading on CEXs (Binance, Coinbase)

**Analysis**:

* Did THORChain market share change during high-fee weeks?
* Correlation between THORChain fees and competitor volumes
* Cross-elasticity: how much volume shifts to competitors at each fee tier?

**Deliverable**: Competitive dynamics report with market share trends
---

### **Phase 5: Statistical Validation & Modeling (Week 4\)**

I. Causal Inference & Controls
**Challenges**:

* Crypto market volatility (BTC price swings, overall market sentiment)
* Day-of-week effects (weekends typically higher volume)
* External events (regulatory news, protocol upgrades)
  * large swaps without streaming that collected a lot of fees

**Methods**:

1. **Regression with Controls**:
* Dependent variable: Log(Revenue) or Log(Volume)
* Independent variables: Fee rate, BTC price, ETH price, day-of-week dummies, time trend
* Clustered standard errors by week
1. **Synthetic Control Method**:
* Create synthetic THORChain using pre-experiment data
* Compare actual experiment outcomes to synthetic counterfactual
1. **Bayesian Structural Time Series**:
* Model baseline trend and seasonality
* Isolate causal impact of fee changes

**Deliverable**: Causal inference report with p-values and confidence intervals
---

J. Forecasting & Simulation
**Analysis**:

1. **Demand Curve Estimation**:
* Fit demand curve: Volume \= f(Fee, Controls)
* Use machine learning (gradient boosting, random forest) for non-linear effects
* Cross-validate on held-out weeks
1. **Revenue Simulation**:
* Simulate revenue for fee rates not tested (e.g., 12 bps, 18 bps, 30 bps)
* Monte Carlo simulation with uncertainty bounds
* Stress test: what if volume drops 50% at 30 bps?
1. **Dynamic Pricing Strategy**:
* Should fees vary by day-of-week? (higher on weekends?)
* Should fees vary by pool? (higher for BTC, lower for long-tail?)
* Should fees vary by trade size? (tiered fee structure?)

**Deliverable**: Revenue forecast model and dynamic pricing recommendations
---

### **Phase 6: Affiliate & Liquidity Impact (Week 4\)**

K. Affiliate Response Analysis
**Analysis**:

* Did affiliates change routing behavior during high-fee weeks?
* Top 10 affiliates: volume and earnings by week
* Did any affiliates disappear/reduce activity during high fees?

**Key Question**: If we raise fees permanently, will affiliates switch to competitors?
**Deliverable**: Affiliate impact report with retention risk assessment
---

## **III. Final Deliverables & Stakeholder Presentation**

### **Phase 7: Synthesis & Recommendations (Week 5\)**

M. Executive Summary Report
**Contents**:

1. **Headline Finding**: "The revenue-optimal fee rate is XX bps, generating $YY.YM per quarter"
2. **Key Insights**:
* Price elasticity: volume drops X% for every 5 bps increase
* Revenue elasticity: revenue increases up to XX bps, then declines
* User impact: churn rate increases Y% at fees above XX bps
* Competitive risk: market share drops Z% at fees above XX bps
1. **Recommendations**:
* **Primary**: Set base fee to XX bps
* **Secondary**: Consider dynamic pricing (higher fees on weekends, for BTC pools, for large trades)
* **Risk mitigation**: Monitor competitor pricing; implement gradual rollout
* **Next steps**: A/B test dynamic pricing strategy
1. **Financial Impact**:
* Current quarterly revenue (Q3): $7.25M
* Projected quarterly revenue at optimal fee: $XX.XM (+/-Y%)
* Upside potential: $X.XM incremental revenue per year

**Format**:

* Executive slide deck (10-15 slides)
* Detailed technical appendix (30-50 pages)
* Interactive dashboard for ongoing monitoring

---
