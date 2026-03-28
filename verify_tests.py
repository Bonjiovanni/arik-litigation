#!/usr/bin/env python3
"""Verify format_utils tests and full suite."""
import sys
import os

# Add current dir to path
sys.path.insert(0, 'C:/Users/arika/OneDrive/CLaude Cowork/audio_pipeline')

# Import and run tests manually to verify they work
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

print("=" * 70)
print("Running format_utils tests")
print("=" * 70)

passed = 0
failed = 0

for name, test_func in tests:
    try:
        test_func()
        print(f"✓ {name}")
        passed += 1
    except Exception as e:
        print(f"✗ {name}")
        print(f"  Error: {e}")
        failed += 1

print("\n" + "=" * 70)
print(f"Results: {passed} passed, {failed} failed out of {len(tests)} tests")
print("=" * 70)

if failed > 0:
    sys.exit(1)
