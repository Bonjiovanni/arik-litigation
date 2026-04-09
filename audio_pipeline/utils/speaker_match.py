"""Utilities for matching AssemblyAI speaker labels to enrolled voice profiles."""
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
