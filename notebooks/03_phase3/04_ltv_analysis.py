"""
Phase 3: Lifetime Value (LTV) Analysis

Outputs:
- ltv_by_fee.csv
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# Add src to path
src_path = Path(__file__).parent.parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from thorchain_fee_analysis.analysis.ltv import (
    compare_ltv_by_fee,
    compute_ltv_sensitivity,
)
from thorchain_fee_analysis.data.snowflake_conn import get_snowpark_session
from thorchain_fee_analysis.data.user_data import load_user_period_detail


def main():
    print("=" * 60)
    print("PHASE 3: LIFETIME VALUE ANALYSIS")
    print("=" * 60)

    # Load data
    print("\n1. Loading data...")
    session = get_snowpark_session()
    user_df = load_user_period_detail(session)

    # Load cohort data
    cohort_path = Path(__file__).parent.parent.parent / "outputs" / "user_cohorts.csv"
    cohort_df = pd.read_csv(cohort_path)

    print(f"   Users: {len(cohort_df):,}")
    print(f"   User-period observations: {len(user_df):,}")

    # Compute LTV sensitivity
    print("\n2. Computing LTV over multiple horizons and discount rates...")
    print("   Horizons: 8, 12 weeks")
    print("   Discount rates: 0%, 5%, 10% annual")

    ltv_df = compute_ltv_sensitivity(
        cohort_df, user_df, horizons=[8, 12], discount_rates=[0.0, 0.05, 0.10]
    )

    print(f"   Calculated LTV for {len(ltv_df)} combinations")

    # Skip bootstrap CIs for now (too slow with 96k users)
    print("\n3. Skipping bootstrap CIs (use vectorized LTV only)...")
    ltv_with_ci = ltv_df.copy()
    ltv_with_ci["ci_low"] = np.nan
    ltv_with_ci["ci_high"] = np.nan
    print("   ✅ (CIs can be added later if needed)")

    # Export CSV
    output_dir = Path(__file__).parent.parent.parent / "outputs"

    print("\n4. Exporting CSV...")
    ltv_path = output_dir / "ltv_by_fee.csv"
    ltv_with_ci.to_csv(ltv_path, index=False)
    print(f"   ✅ {ltv_path}")

    # Summary stats
    print("\n" + "=" * 60)
    print("LTV ANALYSIS SUMMARY")
    print("=" * 60)

    # Compare at H=12, r=0%
    print("\nLTV at 12 weeks, 0% discount:")
    comparison = compare_ltv_by_fee(ltv_with_ci, horizon=12, discount_rate=0.0)
    for _, row in comparison.iterrows():
        print(
            f"  {row['acquisition_fee_bps']:5.1f} bps: ${row['ltv_mean']:8.2f} "
            f"[${row['ci_low']:8.2f}, ${row['ci_high']:8.2f}]"
        )

    # Compare at H=12, r=5%
    print("\nLTV at 12 weeks, 5% discount:")
    comparison = compare_ltv_by_fee(ltv_with_ci, horizon=12, discount_rate=0.05)
    for _, row in comparison.iterrows():
        print(
            f"  {row['acquisition_fee_bps']:5.1f} bps: ${row['ltv_mean']:8.2f} "
            f"[${row['ci_low']:8.2f}, ${row['ci_high']:8.2f}]"
        )

    # Horizon sensitivity for 5 bps cohort
    print("\nHorizon sensitivity (5 bps cohort, 0% discount):")
    fee_5bps = ltv_with_ci[
        (ltv_with_ci["acquisition_fee_bps"] == 5) & (ltv_with_ci["discount_rate"] == 0.0)
    ]
    for _, row in fee_5bps.iterrows():
        print(f"  H={int(row['horizon']):2d} weeks: ${row['ltv_mean']:8.2f}")

    print("\n" + "=" * 60)
    print("✅ LTV ANALYSIS COMPLETE")
    print("=" * 60)

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
