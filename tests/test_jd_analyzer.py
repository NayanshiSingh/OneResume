"""Unit tests for JD Analyzer."""

import pytest
from app.services.jd_analyzer import analyze_jd_rules
from app.domain.resume_draft import JDData


class TestJDAnalyzerRules:
    """Test the rule-based JD analyzer (deterministic, no LLM needed)."""

    def test_basic_jd_parsing(self, sample_jd_text):
        result = analyze_jd_rules(sample_jd_text)
        assert isinstance(result, JDData)
        assert result.role_title  # should extract something
        assert len(result.keywords) > 0

    def test_extracts_tech_keywords(self, sample_jd_text):
        result = analyze_jd_rules(sample_jd_text)
        keywords_lower = [k.lower() for k in result.keywords]
        assert "python" in keywords_lower
        assert "fastapi" in keywords_lower or "django" in keywords_lower

    def test_senior_experience_level(self, sample_jd_text):
        result = analyze_jd_rules(sample_jd_text)
        assert result.experience_level == "senior"

    def test_entry_level_detection(self):
        jd = "Junior Software Engineer. Entry level position. Must know Python."
        result = analyze_jd_rules(jd)
        assert result.experience_level == "entry"

    def test_empty_jd(self):
        result = analyze_jd_rules("No specific requirements listed here for now")
        assert isinstance(result, JDData)
        assert result.role_title  # should still return something

    def test_overloaded_jd(self, overloaded_jd_text):
        result = analyze_jd_rules(overloaded_jd_text)
        # Should extract many keywords but cap them
        assert len(result.must_have_skills) <= 10
        assert len(result.keywords) > 5


class TestJDAnalyzerAPI:
    def test_analyze_jd_endpoint(self, client, sample_jd_text):
        resp = client.post("/api/jd/analyze", json={"raw_text": sample_jd_text})
        assert resp.status_code == 201
        data = resp.json()
        assert "id" in data
        assert "structured_data" in data
        assert data["structured_data"]["role_title"]

    def test_analyze_jd_validation_error(self, client):
        resp = client.post("/api/jd/analyze", json={"raw_text": "too short"})
        assert resp.status_code == 422  # Pydantic min_length=20

    def test_get_jd_analysis(self, client, sample_jd_text):
        create_resp = client.post("/api/jd/analyze", json={"raw_text": sample_jd_text})
        jd_id = create_resp.json()["id"]
        resp = client.get(f"/api/jd/{jd_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == jd_id
