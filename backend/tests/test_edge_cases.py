"""Edge case tests — empty JD, empty profile, long JD, duplicate skills."""

import pytest
from tests.conftest import create_full_profile


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


class TestEmptyProfile:
    def test_generate_with_empty_profile(self, client, sample_user_data, sample_jd_text):
        """Resume generation with empty profile should still work (graceful)."""
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        profile_id = profile_resp.json()["id"]

        resp = client.post("/api/resumes/generate", json={
            "profile_id": profile_id,
            "jd_text": sample_jd_text,
        })
        # Should still succeed (never fail due to missing content)
        assert resp.status_code == 201
        data = resp.json()
        assert "resume_id" in data


class TestDuplicateSkills:
    def test_duplicate_skills_in_profile(self, client, sample_user_data):
        """Adding duplicate skills should be handled without error."""
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        # Add same skill twice
        client.post(f"/api/profiles/{pid}/skills", json={"skill_name": "Python"})
        client.post(f"/api/profiles/{pid}/skills", json={"skill_name": "Python"})

        resp = client.get(f"/api/profiles/{pid}/skills")
        assert resp.status_code == 200
        # Both should exist (dedup happens at resume generation time)
        assert len(resp.json()) == 2


class TestLongJD:
    def test_long_jd_processed(self, client, overloaded_jd_text):
        """Very long JD with many requirements should be handled."""
        resp = client.post("/api/jd/analyze", json={"raw_text": overloaded_jd_text})
        assert resp.status_code == 201
        data = resp.json()
        assert data["structured_data"]["role_title"]


class TestProfileDeletion:
    def test_cascade_delete_profile(self, client, sample_user_data, strong_fit_profile_data):
        """Deleting a profile should cascade to all sections."""
        user_id, profile_id = create_full_profile(
            client, sample_user_data, strong_fit_profile_data
        )
        resp = client.delete(f"/api/profiles/{profile_id}")
        assert resp.status_code == 204

        # Profile should not exist
        resp = client.get(f"/api/profiles/{profile_id}")
        assert resp.status_code == 404

    def test_cascade_delete_user(self, client, sample_user_data, strong_fit_profile_data):
        """Deleting a user should cascade to profiles and all sections."""
        user_id, profile_id = create_full_profile(
            client, sample_user_data, strong_fit_profile_data
        )
        resp = client.delete(f"/api/users/{user_id}")
        assert resp.status_code == 204

        # User should not exist
        resp = client.get(f"/api/users/{user_id}")
        assert resp.status_code == 404


class TestHealthCheck:
    def test_health_endpoint(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
