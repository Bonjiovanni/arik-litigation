import pytest
from utils.format_utils import (
    ms_to_srt_time,
    apply_word_marker,
    group_words_into_blocks,
    render_srt,
    build_json_output,
)


def test_ms_to_srt_time_basic():
    assert ms_to_srt_time(8100) == "00:00:08,100"


def test_ms_to_srt_time_over_one_hour():
    assert ms_to_srt_time(3661500) == "01:01:01,500"


def test_ms_to_srt_time_zero():
    assert ms_to_srt_time(0) == "00:00:00,000"


def test_apply_word_marker_inaudible():
    assert apply_word_marker("the", 0.10, 0.20, 0.50) == "[inaudible]"


def test_apply_word_marker_phonetic():
    assert apply_word_marker("krznky", 0.35, 0.20, 0.50) == "[phonetic: krznky]"


def test_apply_word_marker_normal():
    assert apply_word_marker("hello", 0.95, 0.20, 0.50) == "hello"


def test_apply_word_marker_special_token_passthrough():
    # Bracket-wrapped tokens must pass through unchanged regardless of confidence.
    # Low confidence (below phonetic threshold) should NOT produce [phonetic: [CROSSTALK]].
    assert apply_word_marker("[CROSSTALK]", 0.05, 0.20, 0.50) == "[CROSSTALK]"
    # Also passes through even at inaudible-level confidence (should NOT produce [inaudible]).
    assert apply_word_marker("[Speaker]", 0.01, 0.20, 0.50) == "[Speaker]"
    # High confidence also passes through (sanity check).
    assert apply_word_marker("[CROSSTALK]", 0.99, 0.20, 0.50) == "[CROSSTALK]"


def make_word(word, start_ms, end_ms, speaker="david", confidence=0.95, overlap=False):
    return {
        "word": word,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "speaker": speaker,
        "confidence": confidence,
        "overlap": overlap,
    }


def test_group_words_pause_breaks_block():
    words = [
        make_word("Hello", 0, 500),
        make_word("there", 600, 1100),
        make_word("World", 3100, 3600),  # 2000ms gap > 1.5s threshold
    ]
    blocks, reasons = group_words_into_blocks(words, pause_threshold_sec=1.5)
    assert len(blocks) == 2
    assert blocks[0][0]["word"] == "Hello"
    assert blocks[1][0]["word"] == "World"
    assert reasons[0] == "pause"


def test_group_words_speaker_change_breaks_block():
    words = [
        make_word("Hello", 0, 500, speaker="david"),
        make_word("there", 600, 1100, speaker="sarah"),
    ]
    blocks, reasons = group_words_into_blocks(words, pause_threshold_sec=1.5)
    assert len(blocks) == 2
    assert reasons[0] == "speaker_change"


def test_group_words_no_break_within_speaker():
    words = [
        make_word("Hello", 0, 500),
        make_word("world", 600, 1100),
        make_word("today", 1200, 1700),
    ]
    blocks, reasons = group_words_into_blocks(words, pause_threshold_sec=1.5)
    assert len(blocks) == 1
    assert reasons == []


def test_group_words_pause_at_exact_threshold():
    # A gap of exactly pause_threshold_sec should trigger a break (>= boundary)
    words = [
        make_word("A", 0, 500),
        make_word("B", 2000, 2500),  # exactly 1500ms gap = 1.5s threshold
    ]
    blocks, reasons = group_words_into_blocks(words, pause_threshold_sec=1.5)
    assert len(blocks) == 2
    assert reasons[0] == "pause"


def test_render_srt_basic_format():
    words = [
        make_word("Hello", 8100, 8500),
        make_word("there", 8600, 9000),
    ]
    blocks, reasons = group_words_into_blocks(words, pause_threshold_sec=1.5)
    srt = render_srt(blocks, reasons, inaudible_threshold=0.20, phonetic_threshold=0.50)
    lines = srt.split("\n")
    assert lines[0] == "1"
    assert "00:00:08,100 --> 00:00:09,000" in srt
    assert "David: Hello there" in srt


def test_render_srt_crosstalk_prefix():
    words = [make_word("Yeah", 1000, 1400, overlap=True)]
    blocks, reasons = group_words_into_blocks(words, pause_threshold_sec=1.5)
    srt = render_srt(blocks, reasons, inaudible_threshold=0.20, phonetic_threshold=0.50)
    assert "[crosstalk]" in srt


def test_render_srt_pause_marker():
    words = [
        make_word("Well", 0, 500, speaker="david"),
        make_word("actually", 2100, 2600, speaker="david"),  # 1600ms gap > 1.5s
    ]
    blocks, reasons = group_words_into_blocks(words, pause_threshold_sec=1.5)
    srt = render_srt(blocks, reasons, inaudible_threshold=0.20, phonetic_threshold=0.50)
    assert "[pause]" in srt


def test_render_srt_empty_blocks():
    srt = render_srt([], [], inaudible_threshold=0.20, phonetic_threshold=0.50)
    assert srt == ""


def test_build_json_output_structure():
    words = [make_word("Hello", 0, 500, speaker="david")]
    output = build_json_output(
        filename="test.m4a",
        duration_ms=60000,
        label_map={"A": "david"},
        words=words,
        conflicts=[],
        inaudible_threshold=0.20,
        phonetic_threshold=0.50,
    )
    assert output["file"] == "test.m4a"
    assert output["duration_seconds"] == 60.0
    assert "david" in output["speakers_identified"]
    assert output["speakers_unknown"] == 0
    assert output["words"][0]["speaker"] == "david"
    assert output["words"][0]["start"] == 0.0
