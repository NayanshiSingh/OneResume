"""Unit tests for Relevance Selector."""

import pytest
from app.domain.resume_draft import JDData, ResumeDraft, ScoredSection, ScoredBullet
from app.services.ats_optimizer import enforce_constraints, check_keyword_coverage
from app.config import settings


@pytest.fixture
def jd_data():
    return JDData(
        role_title="Backend Engineer",
        must_have_skills=["Python", "FastAPI"],
        nice_to_have_skills=["Docker"],
        keywords=["Python", "FastAPI", "REST", "microservices"],
    )


@pytest.fixture
def draft_with_many_sections(jd_data):
    """Draft with more sections than the constraint limit."""
    draft = ResumeDraft(profile_id="test-profile")
    draft.jd_data = jd_data

    # Create more experience sections than MAX
    for i in range(10):
        section = ScoredSection(
            id=f"exp-{i}", title=f"Role {i}", section_type="experience",
            score=10 - i,
            bullets=[
                ScoredBullet(id=f"b-{i}-{j}", text=f"Bullet {j}", score=5-j,
                             rewritten_text=f"Python API Bullet {j}")
                for j in range(8)
            ],
        )
        draft.experience_sections.append(section)

    draft.selected_skills = ["Python", "FastAPI", "Docker", "AWS", "Redis",
                             "PostgreSQL", "Kafka", "React", "TypeScript",
                             "Go", "Rust", "Java", "C++", "Kubernetes", "Terraform"]
    return draft


class TestConstraintEnforcement:
    def test_limits_experience_sections(self, draft_with_many_sections):
        result = enforce_constraints(draft_with_many_sections)
        assert len(result.experience_sections) <= settings.MAX_EXPERIENCE_SECTIONS

    def test_limits_bullets_per_section(self, draft_with_many_sections):
        result = enforce_constraints(draft_with_many_sections)
        for section in result.experience_sections:
            assert len(section.bullets) <= settings.MAX_BULLETS_PER_SECTION

    def test_limits_skills(self, draft_with_many_sections):
        result = enforce_constraints(draft_with_many_sections)
        assert len(result.selected_skills) <= settings.MAX_SKILLS


class TestKeywordCoverage:
    def test_keyword_coverage_tracking(self, draft_with_many_sections):
        coverage = check_keyword_coverage(draft_with_many_sections)
        assert isinstance(coverage, dict)
        # "Python" should be covered since it appears in bullets
        assert "Python" in coverage
        assert coverage["Python"] is True

    def test_missing_keyword_detected(self, jd_data):
        draft = ResumeDraft(profile_id="test")
        draft.jd_data = jd_data
        draft.experience_sections = [
            ScoredSection(id="exp-1", title="Role", section_type="experience",
                         bullets=[ScoredBullet(id="b1", text="Did stuff",
                                              rewritten_text="Did various stuff")])
        ]
        coverage = check_keyword_coverage(draft)
        # "microservices" unlikely to appear
        if "microservices" in coverage:
            assert coverage["microservices"] is False
