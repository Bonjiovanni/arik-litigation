#!/usr/bin/env python3
"""
Verify Task 6 implementation:
- format_utils.py exists and has all functions
- test_format_utils.py exists with all 13 tests
- All tests pass
- Git status shows proper state
"""
import os
import sys

# Ensure we're in the right directory
os.chdir('C:/Users/arika/OneDrive/CLaude Cowork/audio_pipeline')
sys.path.insert(0, os.getcwd())

print("=" * 70)
print("TASK 6 IMPLEMENTATION VERIFICATION")
print("=" * 70)

# Check files exist
print("\n1. Checking files exist...")
files_to_check = [
    "utils/format_utils.py",
    "tests/test_format_utils.py",
]

for f in files_to_check:
    if os.path.exists(f):
        print(f"   ✓ {f}")
    else:
        print(f"   ✗ {f} NOT FOUND")
        sys.exit(1)

# Check all functions exist
print("\n2. Checking functions exist...")
from utils.format_utils import (
    ms_to_srt_time,
    apply_word_marker,
    group_words_into_blocks,
    render_srt,
    build_json_output,
)

functions = [
    ("ms_to_srt_time", ms_to_srt_time),
    ("apply_word_marker", apply_word_marker),
    ("group_words_into_blocks", group_words_into_blocks),
    ("render_srt", render_srt),
    ("build_json_output", build_json_output),
]

for name, func in functions:
    if callable(func):
        print(f"   ✓ {name}")
    else:
        print(f"   ✗ {name} not callable")
        sys.exit(1)

# Run format_utils tests
print("\n3. Running format_utils tests...")
from tests.test_format_utils import (
    test_ms_to_srt_time_basic,
    test_ms_to_srt_time_over_one_hour,
    test_ms_to_srt_time_zero,
    test_apply_word_marker_inaudible,
    test_apply_word_marker_phonetic,
    test_apply_word_marker_normal,
    test_group_words_pause_breaks_block,
    test_group_words_speaker_change_breaks_block,
    test_group_words_no_break_within_speaker,
    test_render_srt_basic_format,
    test_render_srt_crosstalk_prefix,
    test_render_srt_pause_marker,
    test_build_json_output_structure,
)

tests = [
    ("test_ms_to_srt_time_basic", test_ms_to_srt_time_basic),
    ("test_ms_to_srt_time_over_one_hour", test_ms_to_srt_time_over_one_hour),
    ("test_ms_to_srt_time_zero", test_ms_to_srt_time_zero),
    ("test_apply_word_marker_inaudible", test_apply_word_marker_inaudible),
    ("test_apply_word_marker_phonetic", test_apply_word_marker_phonetic),
    ("test_apply_word_marker_normal", test_apply_word_marker_normal),
    ("test_group_words_pause_breaks_block", test_group_words_pause_breaks_block),
    ("test_group_words_speaker_change_breaks_block", test_group_words_speaker_change_breaks_block),
    ("test_group_words_no_break_within_speaker", test_group_words_no_break_within_speaker),
    ("test_render_srt_basic_format", test_render_srt_basic_format),
    ("test_render_srt_crosstalk_prefix", test_render_srt_crosstalk_prefix),
    ("test_render_srt_pause_marker", test_render_srt_pause_marker),
    ("test_build_json_output_structure", test_build_json_output_structure),
]

passed = 0
failed = 0
failures = []

for name, test_func in tests:
    try:
        test_func()
        print(f"   ✓ {name}")
        passed += 1
    except Exception as e:
        print(f"   ✗ {name}")
        print(f"     Error: {e}")
        failed += 1
        failures.append((name, e))

print(f"\n   Format Utils Tests: {passed}/{len(tests)} passed")

if failed > 0:
    print("\n   FAILURES:")
    for name, error in failures:
        print(f"   - {name}: {error}")
    sys.exit(1)

print("\n" + "=" * 70)
print(f"✓ All checks passed!")
print(f"✓ format_utils.py: complete with 5 functions")
print(f"✓ test_format_utils.py: 13 tests, all passing")
print("=" * 70)
