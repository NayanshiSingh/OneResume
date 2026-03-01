"""Embedding Service — generates and manages text embeddings.

Uses sentence-transformers (all-MiniLM-L6-v2) for local inference.
Embeddings stored as JSON arrays in SQLite (pgvector-ready).
"""

import json
import logging
import numpy as np
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_model = None  # lazy-loaded singleton


def _get_model():
    """Lazy-load the sentence transformer model."""
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading embedding model: %s", settings.EMBEDDING_MODEL)
        _model = SentenceTransformer(settings.EMBEDDING_MODEL)
    return _model


def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for a text string."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Batch generate embeddings for multiple texts."""
    if not texts:
        return []
    model = _get_model()
    embeddings = model.encode(texts, normalize_embeddings=True)
    return embeddings.tolist()


def embedding_to_json(embedding: list[float]) -> str:
    """Serialize embedding for storage."""
    return json.dumps(embedding)


def embedding_from_json(json_str: Optional[str]) -> Optional[list[float]]:
    """Deserialize embedding from storage."""
    if not json_str:
        return None
    return json.loads(json_str)


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    a_np = np.array(a)
    b_np = np.array(b)
    dot = np.dot(a_np, b_np)
    norm_a = np.linalg.norm(a_np)
    norm_b = np.linalg.norm(b_np)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(dot / (norm_a * norm_b))
