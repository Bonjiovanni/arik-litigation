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
