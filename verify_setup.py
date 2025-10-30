#!/usr/bin/env python3
"""Verify project setup and configuration.

Run this script after installation to verify everything is working:
    python verify_setup.py
"""

import sys
from pathlib import Path


def check_python_version():
    """Check Python version is 3.13+."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 13:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
        return True
    print(f"❌ Python {version.major}.{version.minor}.{version.micro} (need 3.13+)")
    return False


def check_imports():
    """Check required packages can be imported."""
    required_packages = {
        "pandas": "pandas",
        "polars": "polars",
        "streamlit": "streamlit",
        "altair": "altair",
        "plotly": "plotly",
        "snowflake.snowpark": "snowflake-snowpark-python",
    }

    all_ok = True
    for module, package in required_packages.items():
        try:
            __import__(module)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - run: pdm install")
            all_ok = False

    return all_ok


def check_project_structure():
    """Check project structure is correct."""
    required_paths = [
        "src/thorchain_fee_analysis",
        "dashboards",
        "tests",
        "docs",
        "notebooks",
        "pyproject.toml",
        "README.md",
        ".cursorrules",
        ".pre-commit-config.yaml",
    ]

    all_ok = True
    for path in required_paths:
        if Path(path).exists():
            print(f"✅ {path}")
        else:
            print(f"❌ {path} missing")
            all_ok = False

    return all_ok


def check_snowflake_module():
    """Check Snowflake connection module exists and is importable."""
    try:
        sys.path.insert(0, str(Path("src")))
        from thorchain_fee_analysis.data.snowflake_conn import (
            get_snowpark_session,
            test_connection,
        )

        print("✅ Snowflake connection module importable")
        return True
    except ImportError as e:
        print(f"❌ Snowflake connection module: {e}")
        return False


def check_snowflake_connection():
    """Check if Snowflake connection is configured (optional)."""
    try:
        sys.path.insert(0, str(Path("src")))
        from thorchain_fee_analysis.data.snowflake_conn import test_connection

        if test_connection():
            print("✅ Snowflake connection working")
            return True
        print("⚠️  Snowflake connection not configured (see README.md)")
        return None  # Not a failure, just not configured
    except Exception as e:
        print(f"⚠️  Snowflake connection: {e}")
        return None


def main():
    """Run all verification checks."""
    print("=" * 60)
    print("THORChain Fee Analysis - Setup Verification")
    print("=" * 60)

    print("\n1. Python Version")
    print("-" * 40)
    python_ok = check_python_version()

    print("\n2. Required Packages")
    print("-" * 40)
    imports_ok = check_imports()

    print("\n3. Project Structure")
    print("-" * 40)
    structure_ok = check_project_structure()

    print("\n4. Snowflake Module")
    print("-" * 40)
    module_ok = check_snowflake_module()

    print("\n5. Snowflake Connection (Optional)")
    print("-" * 40)
    connection_ok = check_snowflake_connection()

    print("\n" + "=" * 60)
    print("Summary")
    print("=" * 60)

    required_checks = [python_ok, imports_ok, structure_ok, module_ok]
    passed = sum(required_checks)
    total = len(required_checks)

    if all(required_checks):
        print(f"✅ All required checks passed ({passed}/{total})")
        if connection_ok:
            print("✅ Snowflake connection configured")
        else:
            print("⚠️  Snowflake connection not configured (optional)")
        print("\n🎉 Setup complete! Run: pdm run dashboard")
        return 0
    print(f"❌ Some checks failed ({passed}/{total})")
    print("\nTo fix:")
    if not python_ok:
        print("  - Install Python 3.13+")
    if not imports_ok:
        print("  - Run: pdm install")
    if not structure_ok:
        print("  - Check project structure")
    if not module_ok:
        print("  - Check src/thorchain_fee_analysis/")
    return 1


if __name__ == "__main__":
    sys.exit(main())
