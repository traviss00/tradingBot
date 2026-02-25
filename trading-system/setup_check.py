"""Configuration validation and setup script."""

import os
import sys
from pathlib import Path

def check_environment():
    """Check if environment is properly configured."""
    
    print("🔍 Checking Trading System Configuration...\n")
    
    checks = {
        "Python version": check_python_version(),
        "Dependencies installed": check_dependencies(),
        ".env file exists": check_env_file(),
        "Data directory exists": check_data_directory(),
        "Models directory exists": check_models_directory(),
        "Logs directory exists": check_logs_directory(),
    }
    
    print("\n" + "=" * 60)
    print("CONFIGURATION CHECK RESULTS")
    print("=" * 60)
    
    passed = 0
    for check_name, result in checks.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if result:
            passed += 1
    
    print("=" * 60)
    print(f"\nPassed: {passed}/{len(checks)}")
    
    if passed == len(checks):
        print("✅ All checks passed! System is ready.")
        return True
    else:
        print("⚠️ Some checks failed. Please review above.")
        return False


def check_python_version():
    """Check Python version."""
    version = sys.version_info
    if version.major == 3 and version.minor >= 11:
        print(f"  Found Python {version.major}.{version.minor}.{version.micro}")
        return True
    else:
        print(f"  ❌ Python 3.11+ required, found {version.major}.{version.minor}")
        return False


def check_dependencies():
    """Check if key packages are installed."""
    required = [
        "pandas", "numpy", "scikit-learn", "xgboost", "lightgbm",
        "fastapi", "streamlit", "ta", "optuna",
    ]
    
    missing = []
    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
    
    if missing:
        print(f"  ❌ Missing packages: {', '.join(missing)}")
        print(f"  Install with: pip install {' '.join(missing)}")
        return False
    else:
        print(f"  Found all {len(required)} required packages")
        return True


def check_env_file():
    """Check if .env file exists."""
    if Path(".env").exists():
        print("  Found .env file")
        return True
    elif Path(".env.example").exists():
        print("  Found .env.example - copying to .env")
        import shutil
        shutil.copy(".env.example", ".env")
        print("  ✅ Created .env file")
        return True
    else:
        print("  ❌ No .env file found")
        return False


def check_data_directory():
    """Check if data directory exists."""
    data_dir = Path("data")
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Created {data_dir}")
    return True


def check_models_directory():
    """Check if models directory exists."""
    models_dir = Path("models")
    if not models_dir.exists():
        models_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Created {models_dir}")
    return True


def check_logs_directory():
    """Check if logs directory exists."""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        logs_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Created {logs_dir}")
    return True


def setup_git_hooks():
    """Setup git pre-commit hooks."""
    hooks_dir = Path(".git/hooks")
    if not hooks_dir.exists():
        return
    
    pre_commit = hooks_dir / "pre-commit"
    if not pre_commit.exists():
        pre_commit.write_text("""#!/bin/bash
echo "Running tests before commit..."
pytest tests/ -q
if [ $? -ne 0 ]; then
    echo "❌ Tests failed. Commit aborted."
    exit 1
fi
echo "✅ Tests passed."
""")
        pre_commit.chmod(0o755)
        print("✅ Git pre-commit hook installed")


if __name__ == "__main__":
    success = check_environment()
    setup_git_hooks()
    
    sys.exit(0 if success else 1)
