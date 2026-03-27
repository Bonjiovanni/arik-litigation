"""Utilities for loading and processing audio files."""
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


def load_audio(filepath: str, sr: int = 16000) -> tuple[np.ndarray, int]:
    """Load audio file as 16kHz mono numpy array. Returns (audio_array, sample_rate)."""
    audio, sr_out = librosa.load(filepath, sr=sr, mono=True)
    return audio, sr_out


def extract_segment(filepath: str, start_sec: float, end_sec: float, sr: int = 16000) -> np.ndarray:
    """Load and return the audio between start_sec and end_sec."""
    audio, _ = load_audio(filepath, sr=sr)
    start_sample = int(start_sec * sr)
    end_sample = int(end_sec * sr)
    return audio[start_sample:end_sample]
