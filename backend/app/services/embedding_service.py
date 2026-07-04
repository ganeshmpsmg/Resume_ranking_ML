from __future__ import annotations

import numpy as np

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    _HAS_ST = True
except ImportError:
    _HAS_ST = False


class EmbeddingService:
    _model = None

    @classmethod
    def load(cls):
        if cls._model is None:
            if not _HAS_ST:
                raise RuntimeError("sentence-transformers not installed")
            logger.info(f"Loading model: {settings.SBERT_MODEL_NAME}")
            cls._model = SentenceTransformer(settings.SBERT_MODEL_NAME)

    @classmethod
    def is_loaded(cls):
        return cls._model is not None

    @classmethod
    def encode(cls, texts, batch_size=32, normalize=True):
        if cls._model is None:
            cls.load()

        embeddings = cls._model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=normalize,
        )

        return embeddings.astype("float32")

    @classmethod
    def encode_single(cls, text):
        return cls.encode([text])[0]

    @classmethod
    def cosine_similarity(cls, embeddings_a, embedding_b):
        b = embedding_b.reshape(1, -1)
        sims = (embeddings_a @ b.T).flatten()
        return np.clip(sims, 0.0, 1.0)