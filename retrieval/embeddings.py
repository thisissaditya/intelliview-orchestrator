from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from sentence_transformers import SentenceTransformer

_MODEL_NAME = "all-MiniLM-L6-v2"
_DEFAULT_CHUNK_SIZE = 300
_DEFAULT_CHUNK_OVERLAP = 50

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Return the shared embedding model, loading it lazily on first use."""
    global _model

    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)

    return _model


def chunk_text(
    text: str,
    chunk_size: int = _DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping token-based chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")

    if chunk_overlap < 0:
        raise ValueError("chunk_overlap must not be negative")

    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    if not text:
        return []

    tokenizer = get_model().tokenizer

    encoded = tokenizer(
        text,
        add_special_tokens=False,
        return_attention_mask=False,
        return_token_type_ids=False,
    )

    token_ids = encoded["input_ids"]

    if not token_ids:
        return []

    step = chunk_size - chunk_overlap
    chunks = []

    for start in range(0, len(token_ids), step):
        chunk_ids = token_ids[start : start + chunk_size]

        if not chunk_ids:
            break

        chunk = tokenizer.decode(
            chunk_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )

        if chunk.strip():
            chunks.append(chunk)

        if start + chunk_size >= len(token_ids):
            break

    return chunks


def embed_texts(texts: Sequence[str]) -> list[list[float]]:
    """Generate L2-normalized embeddings for multiple texts."""
    if isinstance(texts, str):
        raise TypeError("texts must be a sequence of strings, not a single string")
    if not texts:
        return []
    embeddings = get_model().encode(
        list(texts),
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return np.asarray(embeddings, dtype=np.float32).tolist()


def embed_query(query: str) -> list[float]:
    """Generate one L2-normalized embedding for a query."""
    embedding = get_model().encode(
        query,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    return np.asarray(embedding, dtype=np.float32).tolist()


def get_embedding(text: str) -> list[float]:
    """Backward-compatible wrapper for the existing embedding API."""
    return embed_query(text)
