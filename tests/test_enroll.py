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
FAKE_EMBEDDING = np.ones(256, dtype=np.float32)


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


def test_enroll_rejects_short_timestamp_segment():
    profiles_dir = make_temp_profiles_dir()
    try:
        with patch.object(enroll, "extract_segment", return_value=np.zeros(16000 * 5, dtype=np.float32)), \
             patch.object(enroll, "PROFILES_DIR", profiles_dir), \
             patch.object(enroll, "MIN_ENROLLMENT_SEC", 12.0):
            with pytest.raises(ValueError, match="too short"):
                enroll_speaker(name="Eve", file_path="meeting.m4a", start="0:10", end="0:15")
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
