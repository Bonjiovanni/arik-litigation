# Task 6: Output Formatting — COMPLETE

**Date:** 2026-03-27
**Status:** DONE
**Implementation:** ✓ Complete
**Tests:** ✓ 13/13 passing
**Full Suite:** ✓ 38/38 passing (25 existing + 13 new)

---

## Summary

Task 6 implements the output formatting module (`utils/format_utils.py`) for the audio transcription pipeline. This module converts processed words (with speaker labels, confidence scores, and timing) into publication-ready SRT and JSON formats suitable for import into Descript.

---

## Files Implemented

### `utils/format_utils.py` (146 lines)

Five core functions for output formatting:

1. **`ms_to_srt_time(ms: int) -> str`**
   - Converts milliseconds to SRT timestamp format: `HH:MM:SS,mmm`
   - Example: `8100` → `"00:00:08,100"`

2. **`apply_word_marker(word, confidence, inaudible_threshold, phonetic_threshold) -> str`**
   - Applies legal transcription markers based on confidence score:
     - `confidence ≤ inaudible_threshold` → `[inaudible]`
     - `confidence ≤ phonetic_threshold` → `[phonetic: word]`
     - Otherwise → word as-is
   - Default thresholds: `inaudible=0.20`, `phonetic=0.50`

3. **`group_words_into_blocks(words, pause_threshold_sec) -> (blocks, reasons)`**
   - Groups words into SRT blocks
   - Breaks occur on:
     - Speaker change (transitions between different speakers)
     - Pause ≥ `pause_threshold_sec` (default: 1.5 seconds)
   - Returns: `(blocks, reasons)` where `reasons` is a list of break types

4. **`render_srt(blocks, reasons, inaudible_threshold, phonetic_threshold) -> str`**
   - Renders word blocks as an SRT subtitle string
   - Features:
     - Block numbering (1-indexed)
     - Time range: `HH:MM:SS,mmm --> HH:MM:SS,mmm`
     - Speaker name (capitalized) followed by text
     - `[crosstalk]` prefix if block contains overlapping words
     - `[pause]` appended when same speaker resumes after a pause
   - Output is ready for import into Descript

5. **`build_json_output(filename, duration_ms, label_map, words, conflicts, inaudible_threshold, phonetic_threshold) -> dict`**
   - Builds complete JSON output structure
   - Includes:
     - File name and duration (in seconds)
     - List of identified speakers and unknown speaker count
     - Per-word records with:
       - Word (with markers applied)
       - Start/end times (in seconds, rounded to 3 decimals)
       - Speaker name
       - Confidence (4 decimals)
       - Overlap flag
     - Conflict flags (e.g., ambiguous speaker matches)

---

## Test Suite: `tests/test_format_utils.py`

**13 tests** covering all functions and edge cases:

| Test | Purpose |
|------|---------|
| `test_ms_to_srt_time_basic` | Converts 8100 ms → "00:00:08,100" |
| `test_ms_to_srt_time_over_one_hour` | Handles timestamps > 1 hour |
| `test_ms_to_srt_time_zero` | Edge case: 0 ms → "00:00:00,000" |
| `test_apply_word_marker_inaudible` | Low confidence → [inaudible] |
| `test_apply_word_marker_phonetic` | Medium confidence → [phonetic: word] |
| `test_apply_word_marker_normal` | High confidence → word unchanged |
| `test_group_words_pause_breaks_block` | Pause ≥ 1.5s creates new block |
| `test_group_words_speaker_change_breaks_block` | Speaker change creates new block |
| `test_group_words_no_break_within_speaker` | Continuous same-speaker speech in 1 block |
| `test_render_srt_basic_format` | Proper SRT format with numbering & speaker |
| `test_render_srt_crosstalk_prefix` | [crosstalk] prefixes blocks with overlap |
| `test_render_srt_pause_marker` | [pause] appended at pause boundaries |
| `test_build_json_output_structure` | JSON includes file, duration, speakers, words |

**Results:** ✓ All 13 tests PASS

---

## Word Data Structure

Words flow through the pipeline as dictionaries:

```python
{
    "word": str,         # Raw text from AssemblyAI
    "start_ms": int,     # Start time in milliseconds
    "end_ms": int,       # End time in milliseconds
    "speaker": str,      # Resolved name ("david", "Unknown", etc.)
    "confidence": float, # 0.0–1.0 (from AssemblyAI)
    "overlap": bool,     # True if overlaps with different speaker
}
```

---

## Configuration

Thresholds are read from `config.py`:

```python
SRT_PAUSE_THRESHOLD_SEC = 1.5   # Pause required to break SRT block
INAUDIBLE_CONFIDENCE = 0.20     # Words at or below → [inaudible]
PHONETIC_CONFIDENCE = 0.50      # Words at or below → [phonetic: word]
```

---

## Example Output

### SRT Block

```
1
00:00:08,100 --> 00:00:09,000
David: Hello there

2
00:00:10,500 --> 00:00:11,200
Sarah: Hi David
```

With markers:

```
1
00:00:08,100 --> 00:00:15,500
[crosstalk] David: This is clear [phonetic: krznky] [inaudible] we can see
[pause]
```

### JSON Record (per word)

```json
{
    "word": "hello",
    "start": 8.1,
    "end": 8.5,
    "speaker": "david",
    "confidence": 0.95,
    "overlap": false
}
```

---

## Test Results Summary

| Suite | Count | Status |
|-------|-------|--------|
| test_audio_utils.py | 6 | ✓ PASS |
| test_embed_utils.py | 6 | ✓ PASS |
| test_enroll.py | 6 | ✓ PASS |
| test_speaker_match.py | 7 | ✓ PASS |
| **test_format_utils.py** | **13** | **✓ PASS** |
| **TOTAL** | **38** | **✓ PASS** |

---

## Git Commit

Ready to commit with:

```bash
git add utils/format_utils.py tests/test_format_utils.py
git commit -m "feat: output formatting — SRT blocks, legal markers, pause detection, JSON"
```

---

## Next Steps (Task 7+)

The output formatting module is now ready for integration into the main `transcribe.py` pipeline script, which will:

1. Receive word-level transcript from AssemblyAI
2. Run speaker matching (existing module)
3. Call formatting functions to generate SRT and JSON outputs
4. Write files to `output/` directory

No changes to format_utils.py expected in future tasks.
