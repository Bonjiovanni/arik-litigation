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
