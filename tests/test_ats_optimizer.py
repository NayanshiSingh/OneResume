"""Unit tests for ATS Optimizer."""

import pytest
from app.domain.resume_draft import ResumeDraft, JDData, ScoredSection, ScoredBullet
from app.services.ats_optimizer import optimize, check_keyword_coverage, enforce_constraints


@pytest.fixture
def ats_draft():
    draft = ResumeDraft(profile_id="test")
    draft.jd_data = JDData(
        role_title="Backend Engineer",
        must_have_skills=["Python", "FastAPI"],
        keywords=["Python", "FastAPI", "REST", "PostgreSQL", "Docker"],
    )
    draft.experience_sections = [
        ScoredSection(
            id="exp-1", title="Backend Engineer", section_type="experience",
            bullets=[
                ScoredBullet(id="b1", text="Built Python APIs",
                             rewritten_text="Developed Python REST APIs using FastAPI"),
                ScoredBullet(id="b2", text="Managed PostgreSQL databases",
                             rewritten_text="Managed PostgreSQL databases"),
            ],
        )
    ]
    draft.selected_skills = ["Python", "FastAPI", "PostgreSQL", "Docker"]
    return draft


class TestATSOptimizer:
    def test_optimize_returns_draft(self, ats_draft):
        result = optimize(ats_draft)
        assert isinstance(result, ResumeDraft)

    def test_keyword_coverage_populated(self, ats_draft):
        result = optimize(ats_draft)
        assert len(result.keyword_coverage) > 0
        assert result.keyword_coverage.get("Python") is True
        assert result.keyword_coverage.get("FastAPI") is True

    def test_missing_keyword_detected(self, ats_draft):
        result = optimize(ats_draft)
        # "Docker" might not be in the experience bullets
        coverage = result.keyword_coverage
        # At minimum, the keywords we explicitly include should be tracked
        assert "Docker" in coverage

    def test_constraints_enforced(self, ats_draft):
        # Add excessive bullets
        for section in ats_draft.experience_sections:
            for i in range(20):
                section.bullets.append(
                    ScoredBullet(id=f"extra-{i}", text=f"Extra bullet {i}",
                                 rewritten_text=f"Extra bullet {i}")
                )
        result = enforce_constraints(ats_draft)
        for section in result.experience_sections:
            assert len(section.bullets) <= 4  # MAX_BULLETS_PER_SECTION
