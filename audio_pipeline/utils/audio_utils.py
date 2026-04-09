"""Utilities for loading and processing audio files."""
import os
import shutil
import subprocess
import tempfile

import numpy as np
import librosa

# Formats soundfile/librosa can handle natively without ffmpeg
_NATIVE_FORMATS = {".wav", ".flac", ".aiff", ".aif", ".ogg"}


def _find_ffmpeg() -> str:
    """Return path to ffmpeg executable, checking PATH then common install locations."""
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    # WinGet default install path
    winget_path = os.path.expandvars(
        r"%LOCALAPPDATA%\Microsoft\WinGet\Packages"
    )
    if os.path.isdir(winget_path):
        for entry in os.listdir(winget_path):
            if "FFmpeg" in entry or "ffmpeg" in entry:
                candidate = os.path.join(winget_path, entry)
                for root, _dirs, files in os.walk(candidate):
                    if "ffmpeg.exe" in files:
                        return os.path.join(root, "ffmpeg.exe")
    raise RuntimeError(
        "ffmpeg not found. Install it and ensure it is on PATH, "
        "or install via WinGet: winget install Gyan.FFmpeg"
    )


def _convert_to_wav(filepath: str) -> str:
    """Convert audio file to a temporary WAV file. Caller must delete it."""
    ffmpeg = _find_ffmpeg()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run(
        [ffmpeg, "-y", "-i", filepath, tmp.name],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return tmp.name


def parse_timestamp(ts_str: str) -> float:
    """Convert 'MM:SS' or 'HH:MM:SS' string to total seconds."""
    parts = ts_str.strip().split(":")
    if len(parts) == 2:
        return int(parts[0]) * 60 + float(parts[1])
    elif len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    raise ValueError(f"Cannot parse timestamp: {ts_str!r}")


def load_audio(filepath: str, sr: int = 16000) -> tuple[np.ndarray, int]:
    """Load audio file as 16kHz mono numpy array. Returns (audio_array, sample_rate).

    Files in formats not natively supported by soundfile (e.g. .m4a, .mp3)
    are converted to a temporary WAV via ffmpeg before loading.
    """
    ext = os.path.splitext(filepath)[1].lower()
    tmp_path = None
    try:
        if ext not in _NATIVE_FORMATS:
            tmp_path = _convert_to_wav(filepath)
            load_path = tmp_path
        else:
            load_path = filepath
        audio, sr_out = librosa.load(load_path, sr=sr, mono=True)
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
    return audio, sr_out


def extract_segment(filepath: str, start_sec: float, end_sec: float, sr: int = 16000) -> np.ndarray:
    """Load and return the audio between start_sec and end_sec."""
    audio, _ = load_audio(filepath, sr=sr)
    start_sample = int(start_sec * sr)
    end_sample = int(end_sec * sr)
    return audio[start_sample:end_sample]
