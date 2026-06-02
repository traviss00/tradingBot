"""Utility scripts for trading system management."""

import subprocess
import sys
from pathlib import Path


def run_tests():
    """Run all tests."""
    print("🧪 Running tests...")
    result = subprocess.run(
        ["pytest", "tests/", "-v", "--tb=short"],
        cwd=Path(__file__).parent,
    )
    return result.returncode == 0


def run_linting():
    """Run code linting (if configured)."""
    print("🔍 Running linting...")
    try:
        subprocess.run(
            ["pylint", "app/"],
            cwd=Path(__file__).parent,
        )
    except FileNotFoundError:
        print("  ⚠️ pylint not installed, skipping")


def format_code():
    """Format code with black (if installed)."""
    print("🎨 Formatting code...")
    try:
        subprocess.run(
            ["black", "app/", "tests/"],
            cwd=Path(__file__).parent,
        )
    except FileNotFoundError:
        print("  ⚠️ black not installed, skipping")


def generate_requirements():
    """Generate requirements.txt from pipdeptree."""
    print("📦 Generating requirements...")
    try:
        result = subprocess.run(
            ["pip", "freeze"],
            capture_output=True,
            text=True,
        )
        
        with open(Path(__file__).parent / "requirements_full.txt", "w") as f:
            f.write(result.stdout)
        
        print("✅ Generated requirements_full.txt")
    except Exception as e:
        print(f"⚠️ Failed to generate requirements: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Trading System utilities")
    parser.add_argument("command", choices=["test", "lint", "format", "requirements"])
    
    args = parser.parse_args()
    
    if args.command == "test":
        success = run_tests()
        sys.exit(0 if success else 1)
    elif args.command == "lint":
        run_linting()
    elif args.command == "format":
        format_code()
    elif args.command == "requirements":
        generate_requirements()
