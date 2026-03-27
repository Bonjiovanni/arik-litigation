"""Utilities for generating and comparing voice embeddings."""
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
