"""Unit tests for Embedding Service."""

import pytest
import json


class TestEmbeddingService:
    """Test embedding service (requires sentence-transformers model download)."""

    def test_generate_embedding(self):
        from app.services.embedding_service import generate_embedding
        emb = generate_embedding("Python backend engineer with FastAPI experience")
        assert isinstance(emb, list)
        assert len(emb) > 0
        # Should be normalized (L2 norm ≈ 1.0)
        import numpy as np
        assert abs(np.linalg.norm(emb) - 1.0) < 0.01

    def test_batch_generate_embeddings(self):
        from app.services.embedding_service import generate_embeddings
        texts = ["Python developer", "Java developer", "Frontend React"]
        embs = generate_embeddings(texts)
        assert len(embs) == 3
        assert all(len(e) > 0 for e in embs)

    def test_empty_batch(self):
        from app.services.embedding_service import generate_embeddings
        embs = generate_embeddings([])
        assert embs == []

    def test_cosine_similarity(self):
        from app.services.embedding_service import cosine_similarity
        # Same vector → similarity = 1
        assert abs(cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 0.001
        # Orthogonal → similarity = 0
        assert abs(cosine_similarity([1, 0, 0], [0, 1, 0])) < 0.001
        # Opposite → similarity = -1
        assert abs(cosine_similarity([1, 0, 0], [-1, 0, 0]) + 1.0) < 0.001

    def test_similar_texts_have_high_similarity(self):
        from app.services.embedding_service import generate_embedding, cosine_similarity
        e1 = generate_embedding("Python backend developer")
        e2 = generate_embedding("Python server-side engineer")
        e3 = generate_embedding("Watercolor painting techniques")
        sim_related = cosine_similarity(e1, e2)
        sim_unrelated = cosine_similarity(e1, e3)
        assert sim_related > sim_unrelated

    def test_serialization(self):
        from app.services.embedding_service import (
            embedding_to_json, embedding_from_json,
        )
        original = [0.1, 0.2, 0.3, 0.4]
        serialized = embedding_to_json(original)
        deserialized = embedding_from_json(serialized)
        assert deserialized == original

    def test_deserialization_none(self):
        from app.services.embedding_service import embedding_from_json
        assert embedding_from_json(None) is None
        assert embedding_from_json("") is None
