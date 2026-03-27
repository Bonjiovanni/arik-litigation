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
