#!/usr/bin/env python3
"""
Check git status and get commit information for Task 6
"""
import subprocess
import os

os.chdir('C:/Users/arika/OneDrive/CLaude Cowork/audio_pipeline')

print("\n" + "=" * 75)
print("GIT STATUS FOR TASK 6")
print("=" * 75)

# Check git status
print("\n[Current branch]")
result = subprocess.run(
    ["git", "branch", "--show-current"],
    capture_output=True,
    text=True,
)
print(f"Branch: {result.stdout.strip()}")

# Check if there are uncommitted changes
print("\n[Git status]")
result = subprocess.run(
    ["git", "status", "--short"],
    capture_output=True,
    text=True,
)

if result.stdout.strip():
    print("Uncommitted changes:")
    for line in result.stdout.strip().split('\n'):
        print(f"  {line}")
else:
    print("No uncommitted changes")

# Show recent commits
print("\n[Recent commits]")
result = subprocess.run(
    ["git", "log", "--oneline", "-10"],
    capture_output=True,
    text=True,
)
print(result.stdout.strip())

# Check if format_utils files are tracked
print("\n[File tracking status]")
for f in ["utils/format_utils.py", "tests/test_format_utils.py"]:
    result = subprocess.run(
        ["git", "ls-files", f],
        capture_output=True,
        text=True,
    )
    status = "tracked" if result.stdout.strip() else "untracked"
    print(f"  {f}: {status}")

print("\n" + "=" * 75)
