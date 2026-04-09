from typing import Dict, List, Any, Tuple


def ms_to_srt_time(ms: int) -> str:
    """Convert milliseconds to SRT timestamp: HH:MM:SS,mmm"""
    total_seconds, millis = divmod(ms, 1000)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def apply_word_marker(
    word: str,
    confidence: float,
    inaudible_threshold: float,
    phonetic_threshold: float,
) -> str:
    """Apply legal transcription marker based on confidence score."""
    if inaudible_threshold > phonetic_threshold:
        raise ValueError(
            f"inaudible_threshold ({inaudible_threshold}) must be <= phonetic_threshold ({phonetic_threshold})"
        )
    # Special tokens emitted by the model (e.g. [CROSSTALK], [Speaker]) — pass through unchanged.
    if word.startswith("[") and word.endswith("]"):
        return word
    if confidence <= inaudible_threshold:
        return "[inaudible]"
    if confidence <= phonetic_threshold:
        return f"[phonetic: {word}]"
    return word


def group_words_into_blocks(
    words: List[Dict],
    pause_threshold_sec: float,
) -> Tuple[List[List[Dict]], List[str]]:
    """
    Group words into SRT blocks. A new block starts on speaker change or long pause.

    Returns:
        blocks: list of word-groups
        reasons: list of break reasons between blocks ("pause" or "speaker_change")
                 len(reasons) == len(blocks) - 1
    """
    if not words:
        return [], []

    pause_threshold_ms = int(pause_threshold_sec * 1000)
    blocks = []
    reasons = []
    current_block = [words[0]]

    for word in words[1:]:
        prev = current_block[-1]
        gap_ms = word["start_ms"] - prev["end_ms"]
        speaker_changed = word["speaker"] != prev["speaker"]

        if speaker_changed:
            blocks.append(current_block)
            reasons.append("speaker_change")
            current_block = [word]
        elif gap_ms >= pause_threshold_ms:  # gap equal to threshold counts as a pause (spec: "≥ threshold")
            blocks.append(current_block)
            reasons.append("pause")
            current_block = [word]
        else:
            current_block.append(word)

    blocks.append(current_block)
    return blocks, reasons


def render_srt(
    blocks: List[List[Dict]],
    reasons: List[str],
    inaudible_threshold: float,
    phonetic_threshold: float,
) -> str:
    """
    Render word blocks as an SRT string.

    Appends [pause] to blocks followed by a same-speaker pause.
    Prefixes [crosstalk] when block contains overlapping words.
    """
    lines = []
    for i, block in enumerate(blocks):
        start_time = ms_to_srt_time(block[0]["start_ms"])
        end_time = ms_to_srt_time(block[-1]["end_ms"])
        speaker = block[0]["speaker"].capitalize()
        has_overlap = any(w["overlap"] for w in block)

        marked_words = [
            apply_word_marker(w["word"], w["confidence"], inaudible_threshold, phonetic_threshold)
            for w in block
        ]

        # Append [pause] if same speaker continues after a pause break
        is_pause_break = (
            i < len(reasons)
            and reasons[i] == "pause"
            and i + 1 < len(blocks)
            and blocks[i + 1][0]["speaker"] == block[0]["speaker"]
        )
        if is_pause_break:
            marked_words.append("[pause]")

        text = " ".join(marked_words)
        prefix = "[crosstalk] " if has_overlap else ""

        lines.append(str(i + 1))
        lines.append(f"{start_time} --> {end_time}")
        lines.append(f"{prefix}{speaker}: {text}")
        lines.append("")

    return "\n".join(lines)


def build_json_output(
    filename: str,
    duration_ms: int,
    label_map: Dict[str, str],
    words: List[Dict],
    conflicts: List[str],
    inaudible_threshold: float,
    phonetic_threshold: float,
) -> Dict[str, Any]:
    """Build full JSON output structure."""
    identified = sorted({name for name in label_map.values() if name != "Unknown"})
    unknown_count = sum(1 for name in label_map.values() if name == "Unknown")

    word_records = []
    for w in words:
        marked = apply_word_marker(
            w["word"], w["confidence"], inaudible_threshold, phonetic_threshold
        )
        word_records.append({
            "word": marked,
            "start": round(w["start_ms"] / 1000, 3),
            "end": round(w["end_ms"] / 1000, 3),
            "speaker": w["speaker"],
            "confidence": round(w["confidence"], 4),
            "overlap": w["overlap"],
        })

    return {
        "file": filename,
        "duration_seconds": round(duration_ms / 1000, 3),
        "speakers_identified": identified,
        "speakers_unknown": unknown_count,
        "flags": conflicts,
        "words": word_records,
    }
