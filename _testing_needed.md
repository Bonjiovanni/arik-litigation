# Testing Needed

## Completed as of 2026-03-28

43 tests passing. Recent changes that affected tests:

### audio_utils — ffmpeg conversion path (NEW)
`load_audio` now auto-converts non-native formats (.m4a, .mp3, etc.) to a
temporary WAV via ffmpeg before loading with librosa.

Tests updated:
- `test_load_audio_uses_16k_mono`: now mocks `_convert_to_wav` and `os.unlink`
  in addition to `librosa.load`; asserts librosa receives the converted path
- `test_extract_segment_correct_length`: same mocking pattern
- `test_load_audio_native_format_skips_conversion` (NEW): verifies `.wav` input
  bypasses `_convert_to_wav` entirely

### format_utils — special token passthrough (NEW)
`apply_word_marker` now passes bracket-wrapped tokens (e.g. `[CROSSTALK]`,
`[Speaker]`) through unchanged instead of wrapping them in `[phonetic: ...]`.

Tests added:
- `test_apply_word_marker_special_token_passthrough`: asserts `[CROSSTALK]` at
  inaudible/phonetic/high confidence all return `[CROSSTALK]` unchanged.

DONE ✓
