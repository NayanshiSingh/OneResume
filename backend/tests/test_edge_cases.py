"""Edge case tests — empty JD, empty profile, long JD, duplicate skills."""

from app.config import settings
from app.services import embedding_service

REAL_EMBED_BATCH = embedding_service._embed_batch


class TestEmptyJD:
    def test_empty_jd_rejected(self, client):
        """Empty/short JD should fail validation."""
        resp = client.post("/api/jd/analyze", json={"raw_text": "short"})
        assert resp.status_code == 422

    def test_minimal_jd_accepted(self, client):
        """JD meeting minimum length should be accepted."""
        resp = client.post("/api/jd/analyze",
                           json={"raw_text": "Software Engineer role requiring Python programming skills and experience"})
        assert resp.status_code == 201

    def test_oversized_jd_rejected(self, client):
        resp = client.post("/api/jd/analyze", json={"raw_text": "x" * 20001})
        assert resp.status_code == 422


class TestEmptyProfile:
    def test_generate_with_empty_profile(self, client, sample_jd_text):
        """Resume generation with empty profile should still work (graceful)."""
        resp = client.post("/api/resumes/generate", json={"jd_text": sample_jd_text})
        # Should still succeed (never fail due to missing content)
        assert resp.status_code == 201
        assert "resume_id" in resp.json()


class TestDuplicateSkills:
    def test_duplicate_skills_in_profile(self, client):
        """Adding duplicate skills should be handled without error."""
        client.post("/api/profile/skills", json={"skill_name": "Python"})
        client.post("/api/profile/skills", json={"skill_name": "Python"})
        # Both should exist (dedup happens at resume generation time)
        assert len(client.get("/api/profile").json()["skills"]) == 2


class TestLongJD:
    def test_long_jd_processed(self, client, overloaded_jd_text):
        """Very long JD with many requirements should be handled."""
        resp = client.post("/api/jd/analyze", json={"raw_text": overloaded_jd_text})
        assert resp.status_code == 201
        assert resp.json()["structured_data"]["role_title"]


class TestHealthCheck:
    def test_health_endpoint(self, anon_client):
        resp = anon_client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestMissingProvider:
    def test_generation_without_embedding_key_explains_itself(self, client, monkeypatch, sample_jd_text):
        monkeypatch.setattr(embedding_service, "_embed_batch", REAL_EMBED_BATCH)
        monkeypatch.setattr(settings, "PINECONE_API_KEY", "")
        resp = client.post("/api/resumes/generate", json={"jd_text": sample_jd_text})
        assert resp.status_code == 503
        assert "PINECONE_API_KEY" in resp.json()["detail"]
