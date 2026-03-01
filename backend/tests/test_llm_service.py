"""Unit tests for LLM Service — schema validation and hallucination prevention."""

import pytest
from app.domain.resume_draft import ResumeDraft, JDData, ScoredSection, ScoredBullet
from app.services.llm_service import rewrite_bullets_simple, rewrite_draft_bullets


class TestBulletRewritingRules:
    """Test the rule-based rewriting (deterministic, no LLM needed)."""

    def test_simple_rewrite_adds_action_verb(self):
        bullets = [
            ScoredBullet(id="1", text="building REST APIs for the platform"),
            ScoredBullet(id="2", text="managing team of 5 engineers"),
        ]
        result = rewrite_bullets_simple(bullets, "Engineer", [])
        for b in result:
            assert b.rewritten_text
            first_word = b.rewritten_text.split()[0]
            assert first_word[0].isupper()

    def test_rewrite_preserves_already_good_bullets(self):
        bullets = [
            ScoredBullet(id="1", text="Developed microservices architecture using Python"),
        ]
        result = rewrite_bullets_simple(bullets, "Engineer", [])
        # Should keep it mostly intact since it starts with action verb
        assert "microservices" in result[0].rewritten_text

    def test_no_trailing_period(self):
        bullets = [
            ScoredBullet(id="1", text="Built APIs for the platform."),
        ]
        result = rewrite_bullets_simple(bullets, "Engineer", [])
        assert not result[0].rewritten_text.endswith(".")


class TestHallucinationPrevention:
    """Ensure rewriting doesn't add information not in the original."""

    def test_no_new_skills_introduced(self):
        original_text = "Built REST APIs using Python"
        bullets = [ScoredBullet(id="1", text=original_text)]
        result = rewrite_bullets_simple(bullets, "Engineer", ["Kubernetes", "Terraform"])
        rewritten = result[0].rewritten_text.lower()
        # Rule-based rewriting should NOT introduce Kubernetes or Terraform
        assert "kubernetes" not in rewritten
        assert "terraform" not in rewritten

    def test_original_content_preserved(self):
        bullets = [
            ScoredBullet(id="1", text="Reduced API latency by 40% through query optimization"),
        ]
        result = rewrite_bullets_simple(bullets, "Engineer", [])
        rewritten = result[0].rewritten_text.lower()
        # Key facts should be preserved
        assert "40%" in rewritten or "api" in rewritten


class TestDraftRewriting:
    def test_rewrite_draft_sets_rewritten_text(self):
        draft = ResumeDraft(profile_id="test")
        draft.jd_data = JDData(role_title="Engineer", keywords=["Python"])
        draft.job_title = "Engineer"
        draft.experience_sections = [
            ScoredSection(
                id="exp-1", title="Role", section_type="experience",
                bullets=[
                    ScoredBullet(id="b1", text="Built Python APIs"),
                    ScoredBullet(id="b2", text="Managed databases"),
                ],
            )
        ]
        result = rewrite_draft_bullets(draft)
        for section in result.experience_sections:
            for bullet in section.bullets:
                assert bullet.rewritten_text  # should be set
