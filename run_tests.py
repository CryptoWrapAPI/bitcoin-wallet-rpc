#!/usr/bin/env python3
"""Run all tests in the tests/ directory."""

import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent / "tests"
TEST_FILES = sorted(TESTS_DIR.glob("test_*.py"))


def main():
    print("=" * 60)
    print("RUNNING ALL TESTS")
    print("=" * 60)
    print()

    results = []
    for test_file in TEST_FILES:
        print(f"Running {test_file.name}...")
        result = subprocess.run(
            [sys.executable, str(test_file)],
            capture_output=False,
        )
        results.append((test_file.name, result.returncode))
        print()

    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_passed = True
    for name, code in results:
        status = "✓ PASSED" if code == 0 else "✗ FAILED"
        print(f"  {name}: {status}")
        if code != 0:
            all_passed = False

    print()
    if all_passed:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
