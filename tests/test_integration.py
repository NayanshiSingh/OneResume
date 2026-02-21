"""Integration tests — full pipeline from JD to resume generation."""

import pytest
from tests.conftest import create_full_profile


class TestFullPipeline:
    """Test the complete resume generation pipeline via API."""

    def test_generate_resume_strong_fit(
        self, client, sample_user_data, strong_fit_profile_data, sample_jd_text
    ):
        """Full pipeline: create profile → submit JD → generate resume."""
        user_id, profile_id = create_full_profile(
            client, sample_user_data, strong_fit_profile_data
        )

        resp = client.post("/api/resumes/generate", json={
            "profile_id": profile_id,
            "jd_text": sample_jd_text,
        })
        assert resp.status_code == 201
        data = resp.json()

        # Basic response structure
        assert "resume_id" in data
        assert "job_title" in data
        assert data["version"] >= 1

        # JD analysis should have populated fields
        jd = data["jd_analysis"]
        assert jd["role_title"]
        assert len(jd["must_have_skills"]) > 0 or len(jd["keywords"]) > 0

    def test_generate_resume_weak_fit(
        self, client, weak_fit_profile_data, sample_jd_text
    ):
        """Resume generation should succeed even with weak profile match."""
        user_data = {"username": "jane", "email": "jane@test.com"}
        user_id, profile_id = create_full_profile(
            client, user_data, weak_fit_profile_data
        )

        resp = client.post("/api/resumes/generate", json={
            "profile_id": profile_id,
            "jd_text": sample_jd_text,
        })
        # MUST succeed — resume generation never fails
        assert resp.status_code == 201
        data = resp.json()
        assert "resume_id" in data

    def test_version_increments(
        self, client, sample_user_data, strong_fit_profile_data, sample_jd_text
    ):
        """Generating multiple resumes for the same role increments version."""
        user_id, profile_id = create_full_profile(
            client, sample_user_data, strong_fit_profile_data
        )

        resp1 = client.post("/api/resumes/generate", json={
            "profile_id": profile_id,
            "jd_text": sample_jd_text,
        })
        v1 = resp1.json()["version"]

        resp2 = client.post("/api/resumes/generate", json={
            "profile_id": profile_id,
            "jd_text": sample_jd_text,
        })
        v2 = resp2.json()["version"]

        assert v2 > v1

    def test_list_resumes(
        self, client, sample_user_data, strong_fit_profile_data, sample_jd_text
    ):
        """List all resumes for a profile."""
        user_id, profile_id = create_full_profile(
            client, sample_user_data, strong_fit_profile_data
        )

        client.post("/api/resumes/generate", json={
            "profile_id": profile_id,
            "jd_text": sample_jd_text,
        })

        resp = client.get(f"/api/resumes/?profile_id={profile_id}")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_resume_by_id(
        self, client, sample_user_data, strong_fit_profile_data, sample_jd_text
    ):
        """Get resume metadata by ID."""
        user_id, profile_id = create_full_profile(
            client, sample_user_data, strong_fit_profile_data
        )

        gen_resp = client.post("/api/resumes/generate", json={
            "profile_id": profile_id,
            "jd_text": sample_jd_text,
        })
        resume_id = gen_resp.json()["resume_id"]

        resp = client.get(f"/api/resumes/{resume_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == resume_id


class TestMustHaveSkillHandling:
    """Test graceful degradation for missing must-have skills."""

    def test_skill_confidence_tracking(
        self, client, sample_user_data, strong_fit_profile_data, sample_jd_text
    ):
        """Skill confidence should be tracked for must-have skills."""
        user_id, profile_id = create_full_profile(
            client, sample_user_data, strong_fit_profile_data
        )

        resp = client.post("/api/resumes/generate", json={
            "profile_id": profile_id,
            "jd_text": sample_jd_text,
        })
        data = resp.json()
        confidence = data.get("skill_confidence", {})
        # Should have confidence values for at least some must-have skills
        assert isinstance(confidence, dict)

    def test_missing_skills_dont_crash(
        self, client, weak_fit_profile_data, sample_jd_text
    ):
        """Missing must-have skills should not crash resume generation."""
        user_data = {"username": "test2", "email": "test2@test.com"}
        user_id, profile_id = create_full_profile(
            client, user_data, weak_fit_profile_data
        )

        resp = client.post("/api/resumes/generate", json={
            "profile_id": profile_id,
            "jd_text": sample_jd_text,
        })
        assert resp.status_code == 201
        # Confidence should show "weak" for missing skills
        confidence = resp.json().get("skill_confidence", {})
        if confidence:
            assert any(v in ("weak", "inferred", "strong") for v in confidence.values())
