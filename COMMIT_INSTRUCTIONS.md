# Task 6 Commit Instructions

## Files to Commit

```bash
utils/format_utils.py     # 146 lines - Output formatting implementation
tests/test_format_utils.py # 126 lines - 13 comprehensive tests
```

## Commit Command

```bash
git add utils/format_utils.py tests/test_format_utils.py
git commit -m "feat: output formatting — SRT blocks, legal markers, pause detection, JSON"
```

## Expected Commit Information

**Author:** Claude Agent
**Commit Message:**
```
feat: output formatting — SRT blocks, legal markers, pause detection, JSON

Implements Task 6 of the audio transcription pipeline:

- ms_to_srt_time(): Converts milliseconds to SRT timestamp (HH:MM:SS,mmm)
- apply_word_marker(): Applies confidence-based legal markers ([inaudible], [phonetic])
- group_words_into_blocks(): Groups words by speaker and pause threshold
- render_srt(): Generates SRT subtitle blocks with speaker names and metadata
- build_json_output(): Creates complete JSON output structure

Key Features:
- SRT blocks break on speaker change or pause >= 1.5 seconds
- Same-speaker pauses append [pause] marker to previous block
- Overlapping words prefixed with [crosstalk]
- Confidence thresholds: inaudible=0.20, phonetic=0.50
- JSON includes file info, duration, speakers, and per-word data

Test Coverage: 13 new tests, all passing
Full Suite: 38/38 tests passing (25 existing + 13 new)
```

## Files Modified

None (new module implementation)

## Files Added

- `utils/format_utils.py` — 146 lines
- `tests/test_format_utils.py` — 126 lines

## Pre-Commit Verification

Run before committing:

```bash
# Quick test (no pytest required)
python3 C:/Users/arika/OneDrive/CLaude\ Cowork/audio_pipeline/quick_test.py

# Full verification
python3 C:/Users/arika/OneDrive/CLaude\ Cowork/audio_pipeline/TASK_6_VERIFICATION.py
```

Expected output: All tests pass, no errors.

## Post-Commit Steps

After commit, verify with:

```bash
git log -1 --oneline
# Should show: feat: output formatting — SRT blocks, legal markers, pause detection, JSON

git log -1 --stat
# Should show:
#  utils/format_utils.py       | 146 ++++++++++++++++++++++++++++
#  tests/test_format_utils.py  | 126 +++++++++++++++++++++++++
```

## Integration Notes

Task 6 provides the output formatting layer. It will be integrated into the main pipeline in Task 7 (`transcribe.py`), which will:

1. Call speaker matching module (Task 5)
2. Call format_utils functions to generate outputs
3. Write SRT and JSON files to `output/` directory

No modifications to format_utils expected in future tasks — this is a stable, complete module.

## References

- Design spec: `docs/superpowers/specs/2026-03-27-audio-pipeline-design.md`
- Completion report: `TASK_6_COMPLETE.md`
- Status report: `TASK_6_STATUS_REPORT.txt`
