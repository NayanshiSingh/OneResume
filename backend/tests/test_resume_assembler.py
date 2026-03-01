"""Unit tests for Resume Assembler."""

import json
import pytest
from app.domain.resume_draft import ResumeDraft, JDData, ScoredSection, ScoredBullet
from app.services.resume_assembler import assemble_resume, resume_to_sections_json


@pytest.fixture
def complete_draft():
    draft = ResumeDraft(profile_id="test-profile")
    draft.jd_data = JDData(
        role_title="Backend Engineer",
        must_have_skills=["Python"],
        keywords=["Python", "API"],
    )
    draft.job_title = "Backend Engineer"
    draft.personal_info = {
        "full_name": "John Doe",
        "email": "john@test.com",
        "phone_number": "+1-555-0123",
    }
    draft.education = [
        {"institution": "MIT", "degree": "B.S.", "field_of_study": "CS",
         "start_year": 2018, "end_year": 2022, "grade": "3.8"}
    ]
    draft.experience_sections = [
        ScoredSection(
            id="exp-1", title="Backend Engineer",
            subtitle="TechCorp | 2022-06 – Present",
            section_type="experience", score=0.9,
            bullets=[
                ScoredBullet(id="b1", text="Built APIs", score=0.8,
                             rewritten_text="Designed and implemented RESTful APIs"),
                ScoredBullet(id="b2", text="Optimized DB", score=0.7,
                             rewritten_text="Optimized database queries"),
            ],
        )
    ]
    draft.project_sections = [
        ScoredSection(
            id="proj-1", title="Task Queue",
            subtitle="Python, Redis",
            section_type="project", score=0.7,
            bullets=[
                ScoredBullet(id="pb1", text="Built queue", score=0.6,
                             rewritten_text="Engineered distributed task queue"),
            ],
        )
    ]
    draft.selected_skills = ["Python", "FastAPI", "PostgreSQL"]
    draft.certifications = [{"name": "AWS SAA", "issuing_organization": "Amazon", "year": 2023}]
    draft.achievements = [{"title": "Hackathon Winner", "description": "Won HackMIT"}]
    draft.skill_confidence = {"Python": "strong"}
    draft.keyword_coverage = {"Python": True, "API": True}
    return draft


class TestResumeAssembly:
    def test_assemble_returns_all_sections(self, complete_draft):
        result = assemble_resume(complete_draft)
        assert result["job_title"] == "Backend Engineer"
        assert result["personal_info"]["full_name"] == "John Doe"
        assert len(result["education"]) == 1
        assert len(result["experience"]) == 1
        assert len(result["projects"]) == 1
        assert len(result["skills"]) == 3
        assert len(result["certifications"]) == 1
        assert len(result["achievements"]) == 1

    def test_uses_rewritten_text(self, complete_draft):
        result = assemble_resume(complete_draft)
        exp_bullets = result["experience"][0]["bullets"]
        assert "Designed and implemented RESTful APIs" in exp_bullets

    def test_falls_back_to_original_text(self, complete_draft):
        # Remove rewritten text
        complete_draft.experience_sections[0].bullets[0].rewritten_text = ""
        result = assemble_resume(complete_draft)
        exp_bullets = result["experience"][0]["bullets"]
        assert "Built APIs" in exp_bullets

    def test_section_structure(self, complete_draft):
        result = assemble_resume(complete_draft)
        exp = result["experience"][0]
        assert "title" in exp
        assert "subtitle" in exp
        assert "bullets" in exp


class TestResumeSectionsJSON:
    def test_converts_to_sections(self, complete_draft):
        resume_data = assemble_resume(complete_draft)
        sections = resume_to_sections_json(resume_data)
        section_types = [s["section_type"] for s in sections]
        assert "personal_info" in section_types
        assert "education" in section_types
        assert "experience" in section_types
        assert "projects" in section_types
        assert "skills" in section_types

    def test_sections_have_valid_json(self, complete_draft):
        resume_data = assemble_resume(complete_draft)
        sections = resume_to_sections_json(resume_data)
        for section in sections:
            # content should be valid JSON
            parsed = json.loads(section["content"])
            assert parsed is not None
