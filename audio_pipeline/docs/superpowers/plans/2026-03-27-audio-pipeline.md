# Audio Transcription Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CLI pipeline that takes in-person conversation recordings (.m4a), transcribes them via AssemblyAI, matches speakers to a persistent named profile library, and outputs a Descript-ready SRT file with legal transcription markers.

**Architecture:** AssemblyAI handles transcription and diarization in one API call; resemblyzer generates local voice embeddings for matching against a persistent profile library (flat .npy files + index.json); output formatting groups words into pause-bounded SRT blocks and applies legal transcription markers.

**Tech Stack:** Python 3.11 (`C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe`), assemblyai, resemblyzer, librosa, numpy, pytest. ffmpeg required for librosa to handle .m4a.

---

## File Map

| File | Purpose |
|---|---|
| `config.py` | Central config: API key, paths, thresholds |
| `enroll.py` | CLI: enroll a speaker from clip or timestamp range |
| `transcribe.py` | CLI: run full pipeline on one recording |
| `utils/__init__.py` | Empty package marker |
| `utils/audio_utils.py` | Audio loading, segment extraction, timestamp parsing |
| `utils/embed_utils.py` | resemblyzer embedding generation, cosine similarity, save/load |
| `utils/speaker_match.py` | Map generic AssemblyAI labels to named profiles |
| `utils/format_utils.py` | SRT blocks, legal markers, JSON output |
| `profiles/index.json` | Speaker name → embedding filename registry |
| `tests/__init__.py` | Empty package marker |
| `tests/test_audio_utils.py` | Tests for audio_utils |
| `tests/test_embed_utils.py` | Tests for embed_utils |
| `tests/test_enroll.py` | Tests for enrollment CLI |
| `tests/test_speaker_match.py` | Tests for speaker matching |
| `tests/test_format_utils.py` | Tests for output formatting |
| `tests/test_transcribe.py` | Integration test for full pipeline |

---

### Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `config.py`
- Create: `.gitignore`
- Create: `profiles/index.json`
- Create: `utils/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create directory structure**

Run from the `audio_pipeline/` directory:

```bash
mkdir -p profiles output utils tests
touch utils/__init__.py tests/__init__.py
```

- [ ] **Step 2: Create `requirements.txt`**

```
assemblyai>=0.29.0
resemblyzer>=0.1.1.dev0
librosa>=0.10.0
numpy>=1.24.0
pytest>=7.4.0
```

- [ ] **Step 3: Install dependencies**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pip install -r requirements.txt
```

Expected: all packages install without error.

Also install ffmpeg if not already present (required for librosa to handle .m4a):
```bash
winget install ffmpeg
```

Verify: `ffmpeg -version` should print a version line.

- [ ] **Step 4: Create `config.py`**

```python
import os

ASSEMBLYAI_API_KEY = os.environ.get("ASSEMBLYAI_API_KEY", "")
PROFILES_DIR = "profiles"
OUTPUT_DIR = "output"
SPEAKER_MATCH_THRESHOLD = 0.75
SRT_PAUSE_THRESHOLD_SEC = 1.5   # seconds of silence to break an SRT block
INAUDIBLE_CONFIDENCE = 0.20     # words at or below this → [inaudible]
PHONETIC_CONFIDENCE = 0.50      # words at or below this → [phonetic: word]
INTERRUPT_GAP_MS = 200          # gap < this between speakers → interruption (--)
MIN_ENROLLMENT_SEC = 12.0       # minimum reference audio for enrollment
```

- [ ] **Step 5: Create `profiles/index.json`**

```json
{}
```

- [ ] **Step 6: Create `.gitignore`**

```
profiles/*.npy
output/
.env
__pycache__/
*.pyc
.pytest_cache/
```

- [ ] **Step 7: Set your API key**

Create a `.env` file (not committed) for reference, then export in your terminal session before running:

```bash
export ASSEMBLYAI_API_KEY="your_key_here"
```

- [ ] **Step 8: Commit**

```bash
git add config.py requirements.txt .gitignore profiles/index.json utils/__init__.py tests/__init__.py
git commit -m "chore: project setup for audio transcription pipeline"
```

---

### Task 2: Audio Utilities (`utils/audio_utils.py`)

**Files:**
- Create: `utils/audio_utils.py`
- Create: `tests/test_audio_utils.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_audio_utils.py`:

```python
import numpy as np
import pytest
from unittest.mock import patch
from utils.audio_utils import parse_timestamp, extract_segment, load_audio


def test_parse_timestamp_mm_ss():
    assert parse_timestamp("8:10") == pytest.approx(490.0)


def test_parse_timestamp_hh_mm_ss():
    assert parse_timestamp("1:23:45") == pytest.approx(5025.0)


def test_parse_timestamp_zero():
    assert parse_timestamp("0:00") == pytest.approx(0.0)


def test_parse_timestamp_invalid():
    with pytest.raises(ValueError):
        parse_timestamp("badvalue")


def test_load_audio_uses_16k_mono():
    fake_audio = np.zeros(16000, dtype=np.float32)
    with patch("utils.audio_utils.librosa.load", return_value=(fake_audio, 16000)) as mock_load:
        audio, sr = load_audio("fake.m4a")
    mock_load.assert_called_once_with("fake.m4a", sr=16000, mono=True)
    assert sr == 16000


def test_extract_segment_correct_length():
    sr = 16000
    full_audio = np.zeros(sr * 60, dtype=np.float32)  # 60 seconds
    with patch("utils.audio_utils.librosa.load", return_value=(full_audio, sr)):
        segment = extract_segment("fake.m4a", 10.0, 20.0, sr=sr)
    assert len(segment) == sr * 10
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_audio_utils.py -v
```

Expected: `ImportError` — `utils/audio_utils.py` does not exist yet.

- [ ] **Step 3: Implement `utils/audio_utils.py`**

```python
import numpy as np
import librosa


def parse_timestamp(ts_str: str) -> float:
    """Convert 'MM:SS' or 'HH:MM:SS' string to total seconds."""
    parts = ts_str.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"Cannot parse timestamp: {ts_str!r}")


def load_audio(filepath: str, sr: int = 16000) -> tuple:
    """Load audio file as 16kHz mono numpy array. Returns (audio_array, sample_rate)."""
    audio, sr_out = librosa.load(filepath, sr=sr, mono=True)
    return audio, sr_out


def extract_segment(filepath: str, start_sec: float, end_sec: float, sr: int = 16000) -> np.ndarray:
    """Load and return the audio between start_sec and end_sec."""
    audio, _ = load_audio(filepath, sr=sr)
    start_sample = int(start_sec * sr)
    end_sample = int(end_sec * sr)
    return audio[start_sample:end_sample]
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_audio_utils.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add utils/audio_utils.py tests/test_audio_utils.py
git commit -m "feat: audio utilities — load, segment extraction, timestamp parsing"
```

---

### Task 3: Embedding Utilities (`utils/embed_utils.py`)

**Files:**
- Create: `utils/embed_utils.py`
- Create: `tests/test_embed_utils.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_embed_utils.py`:

```python
import os
import tempfile
import numpy as np
import pytest
from unittest.mock import MagicMock, patch


def test_cosine_similarity_identical():
    from utils.embed_utils import cosine_similarity
    v = np.array([1.0, 2.0, 3.0])
    assert cosine_similarity(v, v) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    from utils.embed_utils import cosine_similarity
    a = np.array([1.0, 0.0])
    b = np.array([0.0, 1.0])
    assert cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-6)


def test_cosine_similarity_opposite():
    from utils.embed_utils import cosine_similarity
    v = np.array([1.0, 0.0])
    w = np.array([-1.0, 0.0])
    assert cosine_similarity(v, w) == pytest.approx(-1.0)


def test_cosine_similarity_zero_vector():
    from utils.embed_utils import cosine_similarity
    z = np.array([0.0, 0.0])
    v = np.array([1.0, 0.0])
    assert cosine_similarity(z, v) == 0.0


def test_save_and_load_embedding():
    from utils.embed_utils import save_embedding, load_embedding
    embedding = np.random.rand(256).astype(np.float32)
    with tempfile.NamedTemporaryFile(suffix=".npy", delete=False) as f:
        path = f.name
    try:
        save_embedding(embedding, path)
        loaded = load_embedding(path)
        np.testing.assert_array_almost_equal(embedding, loaded)
    finally:
        os.unlink(path)


def test_get_embedding_uses_encoder():
    import utils.embed_utils as eu
    fake_embedding = np.random.rand(256).astype(np.float32)
    mock_encoder = MagicMock()
    mock_encoder.embed_utterance.return_value = fake_embedding
    original_encoder = eu._encoder
    eu._encoder = mock_encoder
    try:
        fake_audio = np.zeros(16000, dtype=np.float32)
        result = eu.get_embedding(fake_audio)
        assert mock_encoder.embed_utterance.called
        np.testing.assert_array_equal(result, fake_embedding)
    finally:
        eu._encoder = original_encoder
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_embed_utils.py -v
```

Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Implement `utils/embed_utils.py`**

```python
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav

# Module-level singleton — VoiceEncoder loads a model file; initialize once.
_encoder = VoiceEncoder()


def get_embedding(audio_array: np.ndarray) -> np.ndarray:
    """Generate 256-dim voice embedding from a 16kHz mono float32 audio array."""
    wav = preprocess_wav(audio_array)
    return _encoder.embed_utterance(wav)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors. Returns float in [-1, 1]."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def save_embedding(embedding: np.ndarray, path: str) -> None:
    """Save a numpy embedding array to a .npy file."""
    np.save(path, embedding)


def load_embedding(path: str) -> np.ndarray:
    """Load a numpy embedding array from a .npy file."""
    return np.load(path)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_embed_utils.py -v
```

Expected: 6 PASSED

- [ ] **Step 5: Commit**

```bash
git add utils/embed_utils.py tests/test_embed_utils.py
git commit -m "feat: embedding utilities — resemblyzer wrapper, cosine similarity, save/load"
```

---

### Task 4: Speaker Enrollment CLI (`enroll.py`)

**Files:**
- Create: `enroll.py`
- Create: `tests/test_enroll.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_enroll.py`:

```python
import json
import os
import shutil
import tempfile
import numpy as np
import pytest
from unittest.mock import patch

import enroll
from enroll import enroll_speaker


def make_temp_profiles_dir():
    d = tempfile.mkdtemp()
    with open(os.path.join(d, "index.json"), "w") as f:
        json.dump({}, f)
    return d


FAKE_AUDIO_15S = np.zeros(16000 * 15, dtype=np.float32)
FAKE_EMBEDDING = np.random.rand(256).astype(np.float32)


def test_enroll_from_clip_creates_profile():
    profiles_dir = make_temp_profiles_dir()
    try:
        with patch.object(enroll, "load_audio", return_value=(FAKE_AUDIO_15S, 16000)), \
             patch.object(enroll, "get_embedding", return_value=FAKE_EMBEDDING), \
             patch.object(enroll, "PROFILES_DIR", profiles_dir):
            enroll_speaker(name="Alice", clip_path="alice.m4a")
        with open(os.path.join(profiles_dir, "index.json")) as f:
            index = json.load(f)
        assert "alice" in index
        assert os.path.exists(os.path.join(profiles_dir, index["alice"]))
    finally:
        shutil.rmtree(profiles_dir)


def test_enroll_from_timestamp():
    profiles_dir = make_temp_profiles_dir()
    try:
        with patch.object(enroll, "extract_segment", return_value=FAKE_AUDIO_15S), \
             patch.object(enroll, "get_embedding", return_value=FAKE_EMBEDDING), \
             patch.object(enroll, "PROFILES_DIR", profiles_dir):
            enroll_speaker(name="Bob", file_path="meeting.m4a", start="0:10", end="0:25")
        with open(os.path.join(profiles_dir, "index.json")) as f:
            index = json.load(f)
        assert "bob" in index
    finally:
        shutil.rmtree(profiles_dir)


def test_enroll_rejects_short_clip():
    profiles_dir = make_temp_profiles_dir()
    short_audio = np.zeros(16000 * 5, dtype=np.float32)  # only 5 seconds
    try:
        with patch.object(enroll, "load_audio", return_value=(short_audio, 16000)), \
             patch.object(enroll, "PROFILES_DIR", profiles_dir), \
             patch.object(enroll, "MIN_ENROLLMENT_SEC", 12.0):
            with pytest.raises(ValueError, match="too short"):
                enroll_speaker(name="Carol", clip_path="carol.m4a")
    finally:
        shutil.rmtree(profiles_dir)


def test_enroll_overwrites_existing_speaker():
    profiles_dir = make_temp_profiles_dir()
    emb1 = np.ones(256, dtype=np.float32)
    emb2 = np.zeros(256, dtype=np.float32)
    try:
        with patch.object(enroll, "load_audio", return_value=(FAKE_AUDIO_15S, 16000)), \
             patch.object(enroll, "get_embedding", side_effect=[emb1, emb2]), \
             patch.object(enroll, "PROFILES_DIR", profiles_dir):
            enroll_speaker(name="Dave", clip_path="dave1.m4a")
            enroll_speaker(name="Dave", clip_path="dave2.m4a")
        with open(os.path.join(profiles_dir, "index.json")) as f:
            index = json.load(f)
        assert list(index.keys()).count("dave") == 1
    finally:
        shutil.rmtree(profiles_dir)


def test_enroll_missing_args_raises():
    with pytest.raises(ValueError):
        enroll_speaker(name="Nobody")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_enroll.py -v
```

Expected: `ModuleNotFoundError` — `enroll.py` does not exist yet.

- [ ] **Step 3: Implement `enroll.py`**

```python
"""Speaker enrollment CLI. Adds a named speaker to the persistent profile library."""
import argparse
import json
import os
import sys

import config
from utils.audio_utils import load_audio, extract_segment, parse_timestamp
from utils.embed_utils import get_embedding, save_embedding

PROFILES_DIR = config.PROFILES_DIR
MIN_ENROLLMENT_SEC = config.MIN_ENROLLMENT_SEC


def enroll_speaker(
    name: str,
    clip_path: str = None,
    file_path: str = None,
    start: str = None,
    end: str = None,
) -> None:
    """Enroll a speaker into the profile library."""
    name_key = name.strip().lower()

    if clip_path:
        audio, sr = load_audio(clip_path)
        duration = len(audio) / sr
        if duration < MIN_ENROLLMENT_SEC:
            raise ValueError(
                f"Clip is too short ({duration:.1f}s). "
                f"Need at least {MIN_ENROLLMENT_SEC}s of speech."
            )
    elif file_path and start and end:
        start_sec = parse_timestamp(start)
        end_sec = parse_timestamp(end)
        duration = end_sec - start_sec
        if duration < MIN_ENROLLMENT_SEC:
            raise ValueError(
                f"Segment is too short ({duration:.1f}s). "
                f"Need at least {MIN_ENROLLMENT_SEC}s of speech."
            )
        audio = extract_segment(file_path, start_sec, end_sec)
    else:
        raise ValueError("Provide either --clip or --file with --start and --end.")

    embedding = get_embedding(audio)

    os.makedirs(PROFILES_DIR, exist_ok=True)
    index_path = os.path.join(PROFILES_DIR, "index.json")
    if os.path.exists(index_path):
        with open(index_path) as f:
            index = json.load(f)
    else:
        index = {}

    npy_filename = f"{name_key}.npy"
    npy_path = os.path.join(PROFILES_DIR, npy_filename)
    save_embedding(embedding, npy_path)
    index[name_key] = npy_filename

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    print(f"Enrolled '{name}' → {npy_path}")


def main():
    parser = argparse.ArgumentParser(description="Enroll a speaker into the profile library.")
    parser.add_argument("--name", required=True, help="Speaker name, e.g. 'David'")
    parser.add_argument("--clip", help="Path to a standalone reference audio clip")
    parser.add_argument("--file", help="Path to a recording containing the speaker")
    parser.add_argument("--start", help="Start timestamp in recording, e.g. '8:10'")
    parser.add_argument("--end", help="End timestamp in recording, e.g. '8:22'")
    args = parser.parse_args()

    try:
        enroll_speaker(
            name=args.name,
            clip_path=args.clip,
            file_path=args.file,
            start=args.start,
            end=args.end,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_enroll.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add enroll.py tests/test_enroll.py
git commit -m "feat: speaker enrollment CLI — clip and timestamp modes with profile persistence"
```

---

### Task 5: Speaker Matching (`utils/speaker_match.py`)

**Files:**
- Create: `utils/speaker_match.py`
- Create: `tests/test_speaker_match.py`

Maps AssemblyAI's generic labels ("A", "B", "C") to real names by comparing embeddings against the enrolled profile library.

- [ ] **Step 1: Write failing tests**

Create `tests/test_speaker_match.py`:

```python
import json
import os
import shutil
import tempfile
import numpy as np
import pytest
from utils.speaker_match import load_profiles, match_speaker, resolve_speaker_map


def make_profile_dir(profiles: dict) -> str:
    """Create a temp profiles dir with {name: embedding} entries."""
    d = tempfile.mkdtemp()
    index = {}
    for name, emb in profiles.items():
        fname = f"{name}.npy"
        np.save(os.path.join(d, fname), emb)
        index[name] = fname
    with open(os.path.join(d, "index.json"), "w") as f:
        json.dump(index, f)
    return d


def test_load_profiles():
    emb = np.random.rand(256).astype(np.float32)
    d = make_profile_dir({"david": emb})
    try:
        profiles = load_profiles(d)
        assert "david" in profiles
        np.testing.assert_array_almost_equal(profiles["david"], emb)
    finally:
        shutil.rmtree(d)


def test_load_profiles_empty_dir():
    d = make_profile_dir({})
    try:
        assert load_profiles(d) == {}
    finally:
        shutil.rmtree(d)


def test_match_speaker_above_threshold():
    david_emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    profiles = {"david": david_emb}
    candidate = np.array([0.99, 0.141, 0.0], dtype=np.float32)  # ~0.99 similarity
    result = match_speaker(candidate, profiles, threshold=0.75)
    assert result == "david"


def test_match_speaker_below_threshold():
    david_emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    profiles = {"david": david_emb}
    candidate = np.array([0.0, 1.0, 0.0], dtype=np.float32)  # orthogonal
    result = match_speaker(candidate, profiles, threshold=0.75)
    assert result == "Unknown"


def test_match_speaker_empty_profiles():
    result = match_speaker(np.zeros(256), {}, threshold=0.75)
    assert result == "Unknown"


def test_resolve_speaker_map_assigns_names():
    david_emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    sarah_emb = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    d = make_profile_dir({"david": david_emb, "sarah": sarah_emb})
    a_emb = np.array([0.99, 0.141, 0.0], dtype=np.float32)
    b_emb = np.array([0.141, 0.99, 0.0], dtype=np.float32)
    try:
        label_map, conflicts = resolve_speaker_map(
            {"A": a_emb, "B": b_emb}, d, threshold=0.75
        )
        assert label_map["A"] == "david"
        assert label_map["B"] == "sarah"
        assert conflicts == []
    finally:
        shutil.rmtree(d)


def test_resolve_speaker_map_flags_conflict():
    david_emb = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    d = make_profile_dir({"david": david_emb})
    a_emb = np.array([0.99, 0.141, 0.0], dtype=np.float32)
    b_emb = np.array([0.98, 0.199, 0.0], dtype=np.float32)
    try:
        label_map, conflicts = resolve_speaker_map(
            {"A": a_emb, "B": b_emb}, d, threshold=0.75
        )
        assert len(conflicts) == 1
        assert "david" in conflicts[0]
    finally:
        shutil.rmtree(d)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_speaker_match.py -v
```

Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Implement `utils/speaker_match.py`**

```python
import json
import os
from typing import Dict, List, Tuple

import numpy as np

import config
from utils.embed_utils import cosine_similarity, load_embedding


def load_profiles(profiles_dir: str) -> Dict[str, np.ndarray]:
    """Load all enrolled speaker embeddings. Returns {name: embedding_array}."""
    index_path = os.path.join(profiles_dir, "index.json")
    if not os.path.exists(index_path):
        return {}
    with open(index_path) as f:
        index = json.load(f)
    profiles = {}
    for name, filename in index.items():
        npy_path = os.path.join(profiles_dir, filename)
        if os.path.exists(npy_path):
            profiles[name] = load_embedding(npy_path)
    return profiles


def match_speaker(
    embedding: np.ndarray,
    profiles: Dict[str, np.ndarray],
    threshold: float,
) -> str:
    """Return the name of the closest matching profile, or 'Unknown'."""
    if not profiles:
        return "Unknown"
    best_name = "Unknown"
    best_score = threshold - 1e-9  # must strictly exceed threshold to match
    for name, profile_emb in profiles.items():
        score = cosine_similarity(embedding, profile_emb)
        if score > best_score:
            best_score = score
            best_name = name
    return best_name


def resolve_speaker_map(
    speaker_embeddings: Dict[str, np.ndarray],
    profiles_dir: str,
    threshold: float = None,
) -> Tuple[Dict[str, str], List[str]]:
    """
    Map generic AssemblyAI labels to real names.

    Args:
        speaker_embeddings: {"A": np.ndarray, "B": np.ndarray, ...}
        profiles_dir: path to profiles directory containing index.json
        threshold: cosine similarity threshold (defaults to config value)

    Returns:
        label_map: {"A": "david", "B": "Unknown", ...}
        conflicts: list of conflict description strings (same profile matched 2+ speakers)
    """
    if threshold is None:
        threshold = config.SPEAKER_MATCH_THRESHOLD
    profiles = load_profiles(profiles_dir)
    label_map: Dict[str, str] = {}
    name_to_labels: Dict[str, List[str]] = {}

    for label, embedding in speaker_embeddings.items():
        name = match_speaker(embedding, profiles, threshold)
        label_map[label] = name
        name_to_labels.setdefault(name, []).append(label)

    conflicts = []
    for name, labels in name_to_labels.items():
        if name != "Unknown" and len(labels) > 1:
            conflicts.append(
                f"Profile '{name}' matched multiple speakers: {', '.join(sorted(labels))}"
            )

    return label_map, conflicts
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_speaker_match.py -v
```

Expected: 7 PASSED

- [ ] **Step 5: Commit**

```bash
git add utils/speaker_match.py tests/test_speaker_match.py
git commit -m "feat: speaker matching — profile loading, cosine matching, conflict detection"
```

---

### Task 6: Output Formatting (`utils/format_utils.py`)

**Files:**
- Create: `utils/format_utils.py`
- Create: `tests/test_format_utils.py`

Words flow through the pipeline as dicts with this shape:
```python
{
    "word": str,         # raw text from AssemblyAI
    "start_ms": int,     # start time in milliseconds
    "end_ms": int,       # end time in milliseconds
    "speaker": str,      # resolved name ("david", "Unknown", etc.)
    "confidence": float, # 0.0–1.0
    "overlap": bool,     # True if word overlaps with a different speaker
}
```

SRT blocks break on speaker change OR pause ≥ `SRT_PAUSE_THRESHOLD_SEC`. When the same speaker pauses ≥ threshold then resumes, `[pause]` is appended to the end of the first block.

- [ ] **Step 1: Write failing tests**

Create `tests/test_format_utils.py`:

```python
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


def test_render_srt_basic_format():
    words = [
        make_word("Hello", 8100, 8500),
        make_word("there", 8600, 9000),
    ]
    blocks, reasons = group_words_into_blocks(words, pause_threshold_sec=1.5)
    srt = render_srt(blocks, reasons, inaudible_threshold=0.20, phonetic_threshold=0.50)
    assert "1\n" in srt
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_format_utils.py -v
```

Expected: `ImportError` — file does not exist yet.

- [ ] **Step 3: Implement `utils/format_utils.py`**

```python
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
        elif gap_ms >= pause_threshold_ms:
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_format_utils.py -v
```

Expected: 13 PASSED

- [ ] **Step 5: Commit**

```bash
git add utils/format_utils.py tests/test_format_utils.py
git commit -m "feat: output formatting — SRT blocks, legal markers, pause detection, JSON"
```

---

### Task 7: Main Transcription Pipeline (`transcribe.py`)

**Files:**
- Create: `transcribe.py`
- Create: `tests/test_transcribe.py`

Wires all previous modules together. AssemblyAI note: `transcript.audio_duration` is in **seconds** (float); multiply by 1000 for `duration_ms`.

- [ ] **Step 1: Write failing integration test**

Create `tests/test_transcribe.py`:

```python
import json
import os
import shutil
import tempfile
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

import transcribe


def make_mock_word(text, start_ms, end_ms, confidence, speaker):
    w = MagicMock()
    w.text = text
    w.start = start_ms
    w.end = end_ms
    w.confidence = confidence
    w.speaker = speaker
    return w


def make_mock_utterance(speaker, start_ms, end_ms):
    u = MagicMock()
    u.speaker = speaker
    u.start = start_ms
    u.end = end_ms
    return u


def make_mock_transcript():
    words = [
        make_mock_word("Hello", 1000, 1400, 0.97, "A"),
        make_mock_word("there", 1500, 1800, 0.95, "A"),
        make_mock_word("Hi", 3000, 3300, 0.93, "B"),
    ]
    utterances = [
        make_mock_utterance("A", 1000, 1800),
        make_mock_utterance("B", 3000, 3300),
    ]
    t = MagicMock()
    t.words = words
    t.utterances = utterances
    t.audio_duration = 10.0  # seconds
    t.error = None
    return t


def test_pipeline_produces_srt_and_json(tmp_path):
    profiles_dir = str(tmp_path / "profiles")
    output_dir = str(tmp_path / "output")
    os.makedirs(profiles_dir)
    os.makedirs(output_dir)

    # Create two enrolled profiles
    david_emb = np.array([1.0] + [0.0] * 255, dtype=np.float32)
    sarah_emb = np.array([0.0, 1.0] + [0.0] * 254, dtype=np.float32)
    np.save(os.path.join(profiles_dir, "david.npy"), david_emb)
    np.save(os.path.join(profiles_dir, "sarah.npy"), sarah_emb)
    with open(os.path.join(profiles_dir, "index.json"), "w") as f:
        json.dump({"david": "david.npy", "sarah": "sarah.npy"}, f)

    mock_transcript = make_mock_transcript()
    fake_audio = np.zeros(16000 * 5, dtype=np.float32)

    with patch.object(transcribe, "aai") as mock_aai, \
         patch.object(transcribe, "extract_segment", return_value=fake_audio), \
         patch.object(transcribe, "get_embedding", side_effect=[david_emb, sarah_emb]), \
         patch.object(transcribe, "PROFILES_DIR", profiles_dir), \
         patch.object(transcribe, "OUTPUT_DIR", output_dir):
        mock_aai.settings = MagicMock()
        mock_aai.Transcriber.return_value.transcribe.return_value = mock_transcript
        mock_aai.TranscriptionConfig.return_value = MagicMock()
        transcribe.run_pipeline("meeting.m4a")

    output_files = os.listdir(output_dir)
    assert any(f.endswith(".srt") for f in output_files), "SRT file not created"
    assert any(f.endswith(".json") for f in output_files), "JSON file not created"

    srt_path = next(f for f in output_files if f.endswith(".srt"))
    with open(os.path.join(output_dir, srt_path)) as f:
        srt_content = f.read()
    assert "David:" in srt_content or "Sarah:" in srt_content
```

- [ ] **Step 2: Run test to verify it fails**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/test_transcribe.py -v
```

Expected: `ModuleNotFoundError` — `transcribe.py` does not exist yet.

- [ ] **Step 3: Implement `transcribe.py`**

```python
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
                words[i] for i, w in enumerate(transcript.words)
                if w.start >= utt.start and w.end <= utt.end
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
```

- [ ] **Step 4: Run all tests**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe -m pytest tests/ -v
```

Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add transcribe.py tests/test_transcribe.py
git commit -m "feat: main transcription pipeline — AssemblyAI + speaker matching + SRT/JSON output"
```

---

### Task 8: Smoke Test on a Real File

No mocks — verify the pipeline works end-to-end with a real recording.

- [ ] **Step 1: Set your API key**

```bash
export ASSEMBLYAI_API_KEY="your_key_here"
```

- [ ] **Step 2: Enroll at least one speaker**

Find a 12+ second stretch in a recording where one person is talking alone (no overlap). Note the timestamps, then run:

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe enroll.py \
  --name "David" --file "path/to/meeting.m4a" --start "8:10" --end "8:25"
```

Expected output:
```
Enrolled 'David' → profiles/david.npy
```

Verify:
```bash
cat profiles/index.json
```
Expected: `{"david": "david.npy"}`

- [ ] **Step 3: Run the full pipeline**

```bash
C:\Users\arika\AppData\Local\Programs\Python\Python311\python.exe transcribe.py \
  --file "path/to/meeting.m4a"
```

Expected output:
```
Uploading path/to/meeting.m4a to AssemblyAI...
Matching speakers to enrolled profiles...
SRT written  → output/meeting.srt
JSON written → output/meeting.json
```

- [ ] **Step 4: Review SRT output**

Open `output/meeting.srt` and verify:
- Speaker names appear (`David:`, `Unknown:`)
- Timestamps look correct
- Legal markers appear where expected (`[inaudible]`, `[crosstalk]`, `[pause]`, `[phonetic: ...]`)
- Blocks feel like natural speech units (not word-by-word, not split mid-thought)

- [ ] **Step 5: Import into Descript**

In Descript: **File → Import** → select the `.m4a` file → when prompted for a transcript, import the matching `.srt` from `output/`. Verify speakers and timestamps align correctly.
