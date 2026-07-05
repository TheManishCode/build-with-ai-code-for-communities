"""Sentence embeddings for submission dedup clustering (Phase 2 step 4).

Loaded lazily/once (module-level singleton) since the model load is the expensive part,
not individual encode() calls.
"""

from __future__ import annotations

from functools import lru_cache

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def embed(text: str) -> list[float]:
    return _model().encode(text, normalize_embeddings=True).tolist()


def embed_many(texts: list[str]) -> list[list[float]]:
    return _model().encode(texts, normalize_embeddings=True).tolist()
