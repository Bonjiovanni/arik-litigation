# Audio Transcription Pipeline — Design Spec
Date: 2026-03-27

## Overview

A Python pipeline that takes in-person conversation recordings from a Pixel 7 phone and produces named, timestamped transcripts ready for import into Descript for final corrections.

**Core tools:** AssemblyAI API (transcription + diarization), resemblyzer (local voice embeddings), Python CLI scripts.

---

## Context & Constraints

- **Source audio:** Pixel 7 stereo recordings, in-person, 2–4 speakers
- **Audio characteristics:** Generally clear; one speaker (elderly, distant) tends to be soft; challenges are rapid speech and overlapping speech — not muffling
- **Speakers:** Known participants; named identification required via voice profiles
- **Output destination:** Descript (SRT import) for final manual corrections
- **Scale:** Manual operation, one file at a time; not automated/batch
- **Environment:** Local Windows PC; cloud APIs permitted

---

## Architecture

Four modules, not eight. ChatGPT's stereo_check, preprocess, diarize, and align modules are eliminated — their responsibilities are either handled by AssemblyAI or unnecessary for this use case.

```
audio_pipeline/
├── config.py           # API key, paths, thresholds
├── enroll.py           # One-time speaker enrollment CLI
├── transcribe.py       # Main pipeline: upload → match → output
├── profiles/           # Speaker profile library (persists across runs)
│   ├── index.json      # name → embedding filename mapping
│   ├── david.npy       # Voice embedding (resemblyzer)
│   └── ...
├── output/             # Generated transcripts per recording
└── utils/
    ├── audio_utils.py  # Audio loading and segment extraction
    ├── embed_utils.py  # Embedding generation and cosine similarity
    └── format_utils.py # SRT and JSON output formatting
```

---

## Workflow 1: Speaker Enrollment (run once per person)

Enrolls a speaker into the persistent profile library. Two input modes:

```bash
# From a timestamp range within a recording
python enroll.py --name "David" --file "meeting.m4a" --start 8:10 --end 8:22

# From a dedicated reference clip
python enroll.py --name "David" --clip "david_ref.m4a"
```

**Process:**
1. Load audio segment (from timestamp range or clip file)
2. Extract voice embedding locally using `resemblyzer`
3. Save embedding to `profiles/<name>.npy`
4. Update `profiles/index.json`

**Enrollment guidance:** When using timestamp mode, pick a segment where the target speaker is talking alone — no overlap, no background crosstalk. 12+ seconds of clean solo speech is sufficient. Once enrolled, the profile is reused for all future recordings automatically.

---

## Workflow 2: Transcribe a Recording (run per file)

```bash
python transcribe.py --file "meeting.m4a"
```

**Process:**
1. Upload audio to AssemblyAI with diarization and word-level timestamps enabled
2. Receive: word-level transcript, generic speaker labels (Speaker A/B/C...), per-word confidence scores, overlap flags
3. For each generic speaker: extract their longest uninterrupted segment → generate local embedding via resemblyzer
4. Compare embedding against each enrolled profile (cosine similarity)
5. Assign real name if similarity ≥ threshold (default: 0.75); else label "Unknown"
6. Flag edge cases (two generic speakers matching same profile) in JSON for review
7. Generate output files

---

## Speaker Matching

- **Method:** Cosine similarity between resemblyzer embeddings
- **Threshold:** 0.75 (configurable in config.py)
- **No match:** Speaker labeled "Unknown" in output
- **Conflict:** Two generic speakers matching same profile → flagged in JSON, not silently resolved

---

## Output Format

### SRT (primary — for Descript import)

- Segments grouped by natural speech runs, broken on pauses
- A continuous paragraph without pause = one SRT block (no artificial sentence-splitting)
- Speaker name prefixed on each block

```
1
00:00:08,100 --> 00:00:11,400
David: Yeah so the issue is really about the timeline we agreed on last month

2
00:00:14,500 --> 00:00:17,800
[crosstalk] Sarah: and I think we need to revisit
```

### Legal transcription markers (applied automatically where detectable)

| Marker | Meaning | Trigger |
|---|---|---|
| `[inaudible]` | Cannot be made out | AssemblyAI confidence very low |
| `[crosstalk]` | Multiple speakers simultaneously | AssemblyAI overlap flag |
| `[pause]` | Significant silence mid-speech | Gap ≥ 1.5s within a speaker's run (configurable) |
| `--` | Interrupted or trailed off | Speaker segment ends abruptly before another begins |
| `[phonetic]` | Transcribed by sound, spelling uncertain | Medium-low confidence single word |

### JSON (reference — full data)

```json
{
  "file": "meeting.m4a",
  "duration_seconds": 3642,
  "speakers_identified": ["David", "Sarah"],
  "speakers_unknown": 1,
  "flags": [],
  "words": [
    {"word": "Yeah", "start": 8.1, "end": 8.4, "speaker": "David", "confidence": 0.97},
    {"word": "[inaudible]", "start": 14.5, "end": 14.9, "speaker": "Sarah", "confidence": 0.18}
  ]
}
```

---

## Key Design Decisions

1. **No stereo preprocessing** — AssemblyAI handles stereo input natively; stereo channel analysis adds complexity with negligible benefit for ambient in-person recordings
2. **No local ASR** — AssemblyAI's production model handles rapid speech and overlapping speech better than a DIY Whisper + pyannote stack for this audio type
3. **Local embeddings only** — Voice profile matching stays local (resemblyzer); audio goes to AssemblyAI but biometric profiles never leave the machine
4. **Descript as final step** — Pipeline produces Descript-ready SRT; manual correction of hard segments happens in Descript's UI, not in code
5. **Simple persistence** — Speaker profiles stored as flat files (.npy + index.json); no database, no framework

---

## Dependencies

```
assemblyai       # API client
resemblyzer      # Local voice embeddings
librosa          # Audio loading and segment extraction
numpy            # Embedding math
```

---

## Configuration (config.py)

```python
ASSEMBLYAI_API_KEY = "..."
PROFILES_DIR = "profiles/"
OUTPUT_DIR = "output/"
SPEAKER_MATCH_THRESHOLD = 0.75
SRT_SEGMENT_PAUSE_THRESHOLD = 1.5  # seconds of silence to break an SRT block
INAUDIBLE_CONFIDENCE_THRESHOLD = 0.20
PHONETIC_CONFIDENCE_THRESHOLD = 0.50
MIN_ENROLLMENT_SECONDS = 12
```
