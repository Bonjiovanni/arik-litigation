#!/usr/bin/env python3
"""Run pytest and report results."""
import subprocess
import sys

# Run format_utils tests
print("=" * 60)
print("Running format_utils tests...")
print("=" * 60)
result_fmt = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_format_utils.py", "-v"],
    cwd="C:/Users/arika/OneDrive/CLaude Cowork/audio_pipeline",
)

print("\n" + "=" * 60)
print("Running full test suite...")
print("=" * 60)
result_full = subprocess.run(
    [sys.executable, "-m", "pytest", "-v"],
    cwd="C:/Users/arika/OneDrive/CLaude Cowork/audio_pipeline",
)

sys.exit(max(result_fmt.returncode, result_full.returncode))
