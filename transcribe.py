"""Transcription pipeline CLI. Processes one audio file end-to-end."""
import argparse
import json
import os
import sys
from pathlib import Path

import assemblyai as aai

import config
from utils.audio_utils import extract_segment
from utils.embed_utils import get_embedding
from utils.speaker_match import resolve_speaker_map
from utils.format_utils import (
    group_words_into_blocks,
    render_srt,
    build_json_output,
)

PROFILES_DIR = config.PROFILES_DIR
OUTPUT_DIR = config.OUTPUT_DIR


def _get_longest_utterance(utterances, speaker_label):
    """Return the longest utterance for a given speaker (by duration in ms)."""
    speaker_utts = [u for u in utterances if u.speaker == speaker_label]
    if not speaker_utts:
        return None
    return max(speaker_utts, key=lambda u: u.end - u.start)


def _detect_overlaps(words) -> set:
    """Return indices of words whose time ranges intersect with a different speaker's word."""
    overlapping = set()
    for i, w1 in enumerate(words):
        for j, w2 in enumerate(words):
            if i >= j:
                continue
            if w1.speaker == w2.speaker:
                continue
            if w1.start < w2.end and w2.start < w1.end:
                overlapping.add(i)
                overlapping.add(j)
    return overlapping


def _detect_interruptions(utterances) -> set:
    """
    Return a set of (speaker, end_ms) keys for utterances that were interrupted.
    Interruption = next speaker starts within INTERRUPT_GAP_MS of this utterance ending.
    """
    interrupted = set()
    for i in range(len(utterances) - 1):
        curr = utterances[i]
        nxt = utterances[i + 1]
        if curr.speaker != nxt.speaker:
            gap_ms = nxt.start - curr.end
            if gap_ms < config.INTERRUPT_GAP_MS:
                interrupted.add((curr.speaker, curr.end))
    return interrupted


def run_pipeline(filepath: str) -> None:
    """Run full transcription pipeline on a single audio file."""
    print(f"Uploading {filepath} to AssemblyAI...")
    aai.settings.api_key = config.ASSEMBLYAI_API_KEY

    transcriber = aai.Transcriber()
    aai_config = aai.TranscriptionConfig(speaker_labels=True)
    transcript = transcriber.transcribe(filepath, config=aai_config)

    if transcript.error:
        print(f"Transcription failed: {transcript.error}", file=sys.stderr)
        sys.exit(1)

    print("Matching speakers to enrolled profiles...")
    unique_speakers = sorted({w.speaker for w in transcript.words if w.speaker})
    speaker_embeddings = {}
    for label in unique_speakers:
        utt = _get_longest_utterance(transcript.utterances, label)
        if utt is None:
            continue
        start_sec = utt.start / 1000.0
        end_sec = utt.end / 1000.0
        audio_seg = extract_segment(filepath, start_sec, end_sec)
        speaker_embeddings[label] = get_embedding(audio_seg)

    label_map, conflicts = resolve_speaker_map(speaker_embeddings, PROFILES_DIR)
    if conflicts:
        print("Warning — speaker conflicts detected:")
        for c in conflicts:
            print(f"  {c}")

    overlapping_indices = _detect_overlaps(transcript.words)
    interrupted_keys = _detect_interruptions(transcript.utterances)

    # Build normalized word dicts
    words = []
    for i, w in enumerate(transcript.words):
        resolved = label_map.get(w.speaker, "Unknown")
        words.append({
            "word": w.text,
            "start_ms": w.start,
            "end_ms": w.end,
            "speaker": resolved,
            "confidence": w.confidence if w.confidence is not None else 1.0,
            "overlap": i in overlapping_indices,
        })

    # Mark interruptions: append -- to last word of interrupted utterances
    for utt in transcript.utterances:
        key = (utt.speaker, utt.end)
        if key in interrupted_keys:
            utt_words = [
                norm for norm, raw in zip(words, transcript.words)
                if raw.start >= utt.start and raw.end <= utt.end
            ]
            if utt_words:
                utt_words[-1]["word"] = utt_words[-1]["word"].rstrip() + "--"

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    stem = Path(filepath).stem

    blocks, reasons = group_words_into_blocks(words, config.SRT_PAUSE_THRESHOLD_SEC)
    srt_content = render_srt(
        blocks, reasons,
        inaudible_threshold=config.INAUDIBLE_CONFIDENCE,
        phonetic_threshold=config.PHONETIC_CONFIDENCE,
    )
    srt_path = os.path.join(OUTPUT_DIR, f"{stem}.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
    print(f"SRT written  → {srt_path}")

    # audio_duration from AssemblyAI is in seconds — convert to ms for build_json_output
    duration_ms = int((transcript.audio_duration or 0) * 1000)
    json_data = build_json_output(
        filename=os.path.basename(filepath),
        duration_ms=duration_ms,
        label_map=label_map,
        words=words,
        conflicts=conflicts,
        inaudible_threshold=config.INAUDIBLE_CONFIDENCE,
        phonetic_threshold=config.PHONETIC_CONFIDENCE,
    )
    json_path = os.path.join(OUTPUT_DIR, f"{stem}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    print(f"JSON written → {json_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe a recording with named speaker labels."
    )
    parser.add_argument("--file", required=True, help="Path to audio file (.m4a, .mp3, .wav)")
    args = parser.parse_args()
    run_pipeline(args.file)


if __name__ == "__main__":
    main()
