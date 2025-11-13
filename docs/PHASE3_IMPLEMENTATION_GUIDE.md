## Phase 3 Implementation Guide — User Behavior & Segmentation

Audience: Analysts and dashboard engineers

Objective: Implement retention/acquisition, trade-size segmentation, and LTV analyses to quantify user responses to fee tiers, and deliver actionable, production-ready visuals in the dashboard.

---

### 0) Prerequisites and environment

- Use the shared Snowflake connection helper:
  - `from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session`
- Package manager: PDM
  - Install deps: `pdm install`
  - Run dbt: `pdm run dbt-build`
  - Launch dashboard: `pdm run dashboard`
- Streamlit caching:
  - Data: `@st.cache_data(show_spinner=False, ttl=60)`
  - Session: `@st.cache_resource(show_spinner=False)`
- DataFrames: Prefer Polars for transformations; Pandas acceptable for Streamlit display.
- Timezone: All timestamps are UTC; weekly periods match `V_FEE_PERIODS_MANUAL` / `fct_weekly_summary_final`.

---

### 1) Data dependencies (must exist in Snowflake)

Primary marts/views (prefer marts; fallback to legacy views):
- `9R.FEE_EXPERIMENT_MARTS.fct_user_weekly_summary` (or `9R.FEE_EXPERIMENT.V_USER_WEEKLY_SUMMARY`)
- `9R.FEE_EXPERIMENT_MARTS.fct_weekly_summary_final` (or `9R.FEE_EXPERIMENT.V_WEEKLY_SUMMARY_FINAL`)
- `9R.FEE_EXPERIMENT.V_FEE_PERIODS_MANUAL` (period definitions)

Required columns (lower snake case in Python after `.to_pandas()`):
- Period: `period_id`, `period_start_date`, `final_fee_bps`
- User metrics: `user_address`, `swaps_count`, `volume_usd`, `fees_usd`
- New/returning: `new_swappers`, `returning_swappers` (weekly aggregates)
- Engagement: `engagement_level` (if not present, derive; see §3.2)

If any are missing:
1) Add/extend dbt models under `dbt/models/marts/` to include required fields.
2) Update `dbt/models/staging/` to normalize naming.
3) Rebuild: `pdm run dbt-build`.

Acceptance: Weekly totals reconcile to `fct_weekly_summary_final` within ±0.5% for `volume_usd` and `fees_usd`.

---

### 2) Analysis deliverables (data artifacts)

Produce these reproducible CSVs (saved locally for download via dashboard; do not commit large data files):
- `user_cohorts.csv`: `user_address`, `first_seen_period_id`, `first_seen_date`, `first_seen_fee_bps`, `k`, `retained_flag`
- `retention_by_fee.csv`: `acquisition_fee_bps`, `k`, `retention_rate`, `ci_low`, `ci_high`
- `acquisition_by_period.csv`: `period_id`, `period_start_date`, `final_fee_bps`, `new_swappers`, `returning_swappers`
- `segment_metrics.csv`: `period_id`, `final_fee_bps`, `segment`, `volume_share`, `fees_share`, `avg_fee_paid_usd`, `retention_rate`, `elasticity_est`
- `ltv_by_fee.csv`: `acquisition_fee_bps`, `horizon_weeks`, `discount_rate`, `ltv_mean`, `ci_low`, `ci_high`

Note: Use temporary directories for local caching in Streamlit. Never commit data files.

---

### 3) Implementation steps

#### 3.1 Build cohort table (first-seen and retention flags)

Goal: For each `user_address`, determine `first_seen_period_id` and track weekly retention for horizons k = 1..N.

Options (choose one):
- SQL-first (dbt):
  - Create `int_user_first_seen.sql` to compute `first_seen_period_id` and acquisition fee.
  - Create `fct_user_cohorts.sql` to expand to k-week retention flags per cohort/period.
- Python-first (Snowpark/Pandas/Polars):
  - Query `fct_user_weekly_summary`, derive `first_seen_period_id` in-memory, then generate k-step retention flags.

Checks:
- `retained_flag` must be 1.0 at k=0 by construction.
- Base cohort size equals unique users in acquisition week (by fee tier).

Outputs:
- Export `user_cohorts.csv` and `retention_by_fee.csv` (aggregate and bootstrap CIs).

#### 3.2 Engagement and trade-size segmentation

Goal: Assign `segment` to each user-period using period volume or median swap size.

Default thresholds (tunable):
- micro: < $100
- small: $100–$1,000
- medium: $1,000–$10,000
- large: $10,000–$100,000
- whale: > $100,000

Implementation:
- If `engagement_level` not in mart, derive with a pure function:
  - Based on `swaps_count` or `volume_usd` per user-period.
- Compute per-segment metrics by week and fee tier:
  - `volume_share`, `fees_share`, `avg_fee_paid_usd`, `retention_rate` (merge with cohorts), and elasticity estimate (see §3.3).

Outputs:
- Export `segment_metrics.csv`.

#### 3.3 Elasticity by segment

Goal: Estimate fee sensitivity for segments.

Model:
- OLS on `log(volume_usd + 1)` ~ `final_fee_bps` + `controls` with interactions:
  - Interactions: `final_fee_bps × segment`
  - Controls: BTC/ETH price proxy, day-of-week (if daily), linear time trend
  - Cluster SEs by `period_id`

Reporting:
- Report marginal effects for +5 bps per segment with 95% CIs.
- Sanity check residuals; consider robust regressions if heavy tails.

Outputs:
- Add `elasticity_est` per segment-period (model-based or smoothed) into `segment_metrics.csv`.

#### 3.4 LTV by acquisition fee tier

Goal: Compare expected LTV across acquisition fee tiers over horizon H (8–12 weeks).

Process:
- Aggregate `fees_usd` per user over horizons relative to `first_seen_period_id`.
+- Weight by observed retention (or compute unconditional averages with zeros for churned users).
+- Optional discounting: `r ∈ {0%, 5%, 10%}` annualized.
+- Bootstrap user-level resamples to form 95% CIs.

Outputs:
- Export `ltv_by_fee.csv` with sensitivity over H and r.

---

### 4) Dashboard implementation (Streamlit)

File: `dashboards/app/pages/7_Phase_3__User_Analysis.py.disabled`

Data loading (add functions):
- `load_user_summary(session)`: already present (legacy view). Prefer marts if available.
- New: `load_cohort_summary(session)`, `load_segment_metrics(session)`, `load_ltv(session)`
  - Each returns Pandas DataFrame with lower snake case columns.
  - Use `@st.cache_data(ttl=60)`.

Visual modules (Altair preferred):
- Cohorts/retention
  - Retention curves (line with ribbons) by acquisition fee tier.
  - Cohort heatmap: x = weeks since acquisition, y = acquisition fee tier, color = retention_rate.
- New vs. returning
  - Stacked bars per `period_start_date`; toggle normalized shares.
- Segmentation
  - Stacked normalized bars of `volume_share` by `segment` over time.
  - Small multiples: fee vs. log(volume) with fitted line and CI per segment.
  - Pareto chart: cumulative volume by user, annotated by `segment`.
- LTV
  - LTV curves by acquisition tier with ribbons; end-horizon dot+interval plot.

UI/UX details:
- KPI cards: total unique users; new users; retention at k=+1/+4; whale fee share.
- Controls: date range; fee tier multiselect; segment multiselect; horizon (H), discount (r) selectors.
- Formatting: currency `$1.2M`, percentages `12.3%`, bps `25 bps`.
- Downloads: CSV buttons for each data section.

Performance:
- Avoid wide queries; select only needed columns.
- Consider server-side aggregation in SQL for heavy groupbys.

---

### 5) Python analysis modules (src) and tests

New or extended modules in `src/thorchain_fee_analysis/analysis/`:
- `retention.py`
  - `build_retention_table(user_weekly_df, horizons: list[int]) -> pd.DataFrame`
  - `fit_retention_model(retention_df) -> dict[str, Any]` (AMEs and CIs)
- `segmentation.py`
  - `assign_trade_size_segment(df, thresholds: dict) -> pd.DataFrame`
  - `compute_segment_metrics(df) -> pd.DataFrame`
- `ltv.py`
  - `compute_ltv_by_cohort(cohort_df, horizons: list[int], discount_rates: list[float]) -> pd.DataFrame`

Notes:
- Prefer Polars for transformations where feasible; convert to Pandas for statsmodels/Altair.
- Do not hardcode credentials; always use `get_snowpark_session()` in data access layers.

Tests (`tests/analysis/`):
- `test_retention.py`: k=0 = 100%; monotone non-increasing retention; model AMEs sign sanity.
- `test_segmentation.py`: boundary conditions for thresholds; shares sum to ~1.
- `test_ltv.py`: discounting correctness; bootstrap CI shape and ordering.

Target coverage: ≥80% overall; skip heavy Polars cases on Python 3.13 if needed (see existing skips).

---

### 6) dbt model guidance (if marts need updates)

Location: `dbt/models/`

Add/extend models (names illustrative):
- `intermediate/int_user_first_seen.sql`: earliest `period_id` per `user_address`, join fee tier.
- `marts/fct_user_cohorts.sql`: expand to k-week retention at the user×k level or aggregate to cohort level.
- Ensure `marts/fct_user_weekly_summary.sql` exposes: `new_swappers`, `returning_swappers`, `engagement_level` (if defined here).

Validation:
- `dbt test` uniqueness on (`user_address`, `period_id`) for weekly summary.
- Freshness and not_null tests for key columns.

---

### 7) Statistical specification (concise, reproducible)

Controls:
- BTC/ETH price proxy (daily/weekly), day-of-week dummies (if daily), linear time trend.

Estimators:
- Retention: logistic/GLM with robust SEs; report average marginal effects per +5 bps.
- Volume: OLS on log(volume + 1) with segment interactions; cluster SE by `period_id`.
- LTV: cohort aggregation; bootstrap users (≥1,000 resamples recommended).

Exclusions:
- Documented anomalous outlier weeks/swaps from execution quality notes.

---

### 8) Visual specification (Altair defaults)

Encoding:
- Color: fee tiers mapped to a consistent palette across charts.
- Tooltips: include `period_id`, `final_fee_bps`, metric value, and cohort/segment labels.
- Axes: format currency and percentages properly; rotate dates if crowded.

Chart types:
- Line with ribbons (CIs): retention and LTV curves.
- Stacked bars (normalized): new vs. returning; segment shares.
- Heatmap: cohort retention across horizons.
- Small multiples: elasticity by segment.
- Dot+interval: end-horizon LTV by tier with 95% CI.

Accessibility:
- Provide clear legends and titles; avoid over-coloring.
- Ensure sufficient contrast; add descriptive captions.

---

### 9) QA & acceptance criteria

- Reproducibility: All CSVs regenerate from notebooks/scripts without manual edits.
- Statistical reporting: 95% CIs for retention deltas, elasticity, and LTV comparisons.
- Data integrity: Weekly aggregates reconcile within ±0.5% to `fct_weekly_summary_final`.
- Dashboard: Charts render within 2s on local; formatting (currency, bps, %) consistent.
- Documentation: Methods and exclusions clearly stated in notebooks and README-style docstrings.

---

### 10) Execution workflow and estimates

1) Data QA (0.5–1 day)
2) Cohorts (0.5–1 day)
3) Retention & acquisition (0.5–1 day)
4) Segmentation & elasticity (0.5–1 day)
5) LTV (0.5–1 day)
6) Dashboard integration & polish (0.5 day)

Total: ~3–4 analyst days.

---

### 11) Notebooks to create (scaffolds)

- `notebooks/03_phase3/01_cohorts_retention.ipynb`
  - Connect → query → build cohorts → retention curves → export CSVs.
- `notebooks/03_phase3/02_trade_size_segmentation.ipynb`
  - Assign segments → compute metrics → elasticity by segment → export CSV.
- `notebooks/03_phase3/03_ltv_by_acquisition_fee.ipynb`
  - Compute LTV vs H and r → bootstrap CIs → export CSV.

Use `get_snowpark_session()`; cache intermediate DataFrames locally during development only.

---

### 12) Security & performance notes

- Never hardcode credentials. Use connection file, env vars, or Streamlit secrets.
- Avoid exporting PII in logs; mask or aggregate user identifiers in public outputs.
- Push aggregations to Snowflake where feasible to reduce data transfer.
- Use `@st.cache_data(ttl=60)` in dashboard to minimize repeated queries.

---

### 13) Handoff checklist

- [ ] CSVs generated in local temp folder and verified against acceptance criteria
- [ ] Dashboard updated with new data loaders, visuals, and download buttons
- [ ] Unit tests added for retention, segmentation, and LTV modules
- [ ] dbt models updated (if needed) and `dbt test` passing
- [ ] Short methods appendix included in notebooks and docstrings
