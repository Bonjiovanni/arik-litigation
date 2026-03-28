#!/usr/bin/env python3
"""Quick test of format_utils without pytest dependency."""
import os
import sys

os.chdir('C:/Users/arika/OneDrive/CLaude Cowork/audio_pipeline')
sys.path.insert(0, os.getcwd())

# Test 1: Import the module
try:
    from utils.format_utils import (
        ms_to_srt_time,
        apply_word_marker,
        group_words_into_blocks,
        render_srt,
        build_json_output,
    )
    print("✓ All imports successful")
except Exception as e:
    print(f"✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Basic function calls
try:
    # Test ms_to_srt_time
    result = ms_to_srt_time(8100)
    assert result == "00:00:08,100", f"Expected '00:00:08,100', got '{result}'"
    print("✓ ms_to_srt_time(8100) = '00:00:08,100'")

    # Test apply_word_marker
    result = apply_word_marker("hello", 0.95, 0.20, 0.50)
    assert result == "hello", f"Expected 'hello', got '{result}'"
    print("✓ apply_word_marker('hello', 0.95, 0.20, 0.50) = 'hello'")

    result = apply_word_marker("test", 0.15, 0.20, 0.50)
    assert result == "[inaudible]", f"Expected '[inaudible]', got '{result}'"
    print("✓ apply_word_marker('test', 0.15, 0.20, 0.50) = '[inaudible]'")

    # Test group_words_into_blocks
    words = [
        {"word": "Hello", "start_ms": 0, "end_ms": 500, "speaker": "david", "confidence": 0.95, "overlap": False},
        {"word": "there", "start_ms": 600, "end_ms": 1100, "speaker": "david", "confidence": 0.95, "overlap": False},
    ]
    blocks, reasons = group_words_into_blocks(words, pause_threshold_sec=1.5)
    assert len(blocks) == 1, f"Expected 1 block, got {len(blocks)}"
    assert len(reasons) == 0, f"Expected 0 reasons, got {len(reasons)}"
    print("✓ group_words_into_blocks: continuous speech grouped in 1 block")

    # Test render_srt
    blocks = [[
        {"word": "Hello", "start_ms": 8100, "end_ms": 8500, "speaker": "david", "confidence": 0.95, "overlap": False},
        {"word": "there", "start_ms": 8600, "end_ms": 9000, "speaker": "david", "confidence": 0.95, "overlap": False},
    ]]
    srt = render_srt(blocks, [], inaudible_threshold=0.20, phonetic_threshold=0.50)
    assert "1\n" in srt, "Missing block number"
    assert "David: Hello there" in srt, "Missing speaker name and words"
    assert "00:00:08,100 --> 00:00:09,000" in srt, "Missing timestamp"
    print("✓ render_srt: generates proper SRT format")

    # Test build_json_output
    output = build_json_output(
        filename="test.m4a",
        duration_ms=60000,
        label_map={"A": "david"},
        words=[
            {"word": "Hello", "start_ms": 0, "end_ms": 500, "speaker": "david", "confidence": 0.95, "overlap": False},
        ],
        conflicts=[],
        inaudible_threshold=0.20,
        phonetic_threshold=0.50,
    )
    assert output["file"] == "test.m4a", f"Expected file='test.m4a', got {output['file']}"
    assert output["duration_seconds"] == 60.0, f"Expected duration=60.0, got {output['duration_seconds']}"
    assert "david" in output["speakers_identified"], "Missing speaker in output"
    print("✓ build_json_output: generates proper JSON structure")

    print("\n✓ All quick tests passed!")

except Exception as e:
    print(f"\n✗ Test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
