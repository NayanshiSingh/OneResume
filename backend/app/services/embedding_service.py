"""Embedding Service — generates and manages text embeddings.

Uses Pinecone Inference API (multilingual-e5-large) for hosted inference.
Embeddings stored as JSON arrays in SQLite (pgvector-ready).
"""

import json
import logging
import numpy as np
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

_client = None  # lazy-loaded singleton


def _get_client():
    """Lazy-load the Pinecone client."""
    global _client
    if _client is None:
        from pinecone import Pinecone
        logger.info("Initializing Pinecone client with model: %s", settings.EMBEDDING_MODEL)
        _client = Pinecone(api_key=settings.PINECONE_API_KEY)
    return _client


def _embed_batch(texts: list[str]) -> list[list[float]]:
    """The only call to the embedding provider; tests replace this function."""
    pc = _get_client()
    result = pc.inference.embed(
        model=settings.EMBEDDING_MODEL,
        inputs=[{"text": t} for t in texts],
        parameters={"input_type": "passage", "truncate": "END"},
    )
    return [list(item.values) for item in result.data]


def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for a text string."""
    return _embed_batch([text])[0]


def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Batch generate embeddings for multiple texts."""
    if not texts:
        return []
    return _embed_batch(texts)


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
