"""Unit tests for Scoring Engine."""

import pytest
from app.services.scoring_engine import (
    compute_recency_weight, compute_keyword_bonus,
    compute_skill_importance, score_bullet, score_section,
    SECTION_PRIORITY, SKILL_IMPORTANCE, KEYWORD_BONUS,
)
from app.domain.resume_draft import JDData


@pytest.fixture
def jd_data():
    return JDData(
        role_title="Backend Engineer",
        experience_level="senior",
        must_have_skills=["Python", "FastAPI", "PostgreSQL"],
        nice_to_have_skills=["Docker", "Kubernetes"],
        keywords=["Python", "FastAPI", "PostgreSQL", "REST", "microservices"],
        role_category="Software Engineering",
    )


class TestRecencyWeight:
    def test_present_returns_1(self):
        assert compute_recency_weight("Present") == 1.0
        assert compute_recency_weight("present") == 1.0

    def test_none_returns_1(self):
        assert compute_recency_weight(None) == 1.0

    def test_current_year_returns_high(self):
        from datetime import datetime
        current_year = datetime.now().year
        assert compute_recency_weight(f"{current_year}-06") >= 0.95

    def test_old_date_returns_lower(self):
        result = compute_recency_weight("2015-01")
        assert result < 1.0
        assert result >= 0.6  # minimum cap

    def test_minimum_cap(self):
        result = compute_recency_weight("1990-01")
        assert result == 0.6


class TestKeywordBonus:
    def test_matching_keywords(self, jd_data):
        text = "Built REST APIs using Python and FastAPI"
        bonus = compute_keyword_bonus(text, jd_data)
        assert bonus > 0

    def test_no_matching_keywords(self, jd_data):
        text = "Organized team meetings and presentations"
        bonus = compute_keyword_bonus(text, jd_data)
        assert bonus == 0.0

    def test_bonus_capped(self, jd_data):
        # Text with all keywords
        text = "Python FastAPI PostgreSQL REST microservices Docker Kubernetes"
        bonus = compute_keyword_bonus(text, jd_data)
        assert bonus <= 0.3


class TestSkillImportance:
    def test_must_have_skill(self, jd_data):
        result = compute_skill_importance("Built APIs with Python and FastAPI", jd_data)
        assert result == SKILL_IMPORTANCE["must_have"]

    def test_nice_to_have_skill(self, jd_data):
        result = compute_skill_importance("Deployed using Docker containers", jd_data)
        assert result == SKILL_IMPORTANCE["nice_to_have"]

    def test_no_matching_skill(self, jd_data):
        result = compute_skill_importance("Organized team lunches", jd_data)
        assert result == 1.0


class TestScoreBullet:
    def test_score_with_embeddings(self, jd_data):
        # Mock embeddings (normalized unit vectors)
        bullet_emb = [1.0, 0.0, 0.0]
        jd_emb = [0.9, 0.1, 0.0]
        score = score_bullet(
            "Built Python APIs", bullet_emb, jd_emb,
            jd_data, "experience", "Present",
        )
        assert score > 0

    def test_score_without_embeddings(self, jd_data):
        score = score_bullet(
            "Built Python APIs", None, [],
            jd_data, "experience", "Present",
        )
        assert score > 0  # should still work with defaults

    def test_section_priority_affects_score(self, jd_data):
        emb = [1.0, 0.0, 0.0]
        jd_emb = [0.9, 0.1, 0.0]
        exp_score = score_bullet("Built APIs", emb, jd_emb, jd_data, "experience")
        proj_score = score_bullet("Built APIs", emb, jd_emb, jd_data, "project")
        # Experience should score higher than projects
        assert exp_score >= proj_score

    def test_recency_affects_score(self, jd_data):
        emb = [1.0, 0.0, 0.0]
        jd_emb = [0.9, 0.1, 0.0]
        recent = score_bullet("Built APIs", emb, jd_emb, jd_data, "experience", "Present")
        old = score_bullet("Built APIs", emb, jd_emb, jd_data, "experience", "2010-01")
        assert recent >= old


class TestScoreSection:
    def test_section_scoring(self, jd_data):
        score = score_section(
            "Backend Engineer at TechCorp",
            [1.0, 0.0, 0.0], [0.9, 0.1, 0.0],
            jd_data, "experience", "Present",
        )
        assert score > 0
