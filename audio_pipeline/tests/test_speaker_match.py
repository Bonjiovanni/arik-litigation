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
