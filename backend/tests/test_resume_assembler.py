"""Unit tests for Resume Assembler: only included draft content reaches the export."""

import json

import pytest

from app.services.resume_assembler import assemble_resume, resume_to_sections_json


def _bullet(id, text, included=True, original=None):
    return {"id": id, "text": text, "original_text": original or text, "included": included,
            "pinned": False, "user_edited": original is not None, "score": 0.5}


@pytest.fixture
def content():
    return {
        "personal_info": {"full_name": "John Doe", "email": "john@test.com", "phone_number": ""},
        "external_profiles": [{"id": "ep1", "platform": "GitHub", "profile_url": "https://github.com/j", "included": True}],
        "education": [{"id": "ed1", "institution": "MIT", "degree": "B.S.", "included": True}],
        "experience": [
            {"id": "e1", "title": "Backend Engineer", "subtitle": "TechCorp | 2022-06 – Present", "included": True,
             "pinned": False, "score": 0.9,
             "bullets": [_bullet("b1", "Built APIs"), _bullet("b2", "Fixed printers", included=False),
                         _bullet("b3", "Built REST APIs in FastAPI", original="Built APIs in FastAPI")]},
            {"id": "e2", "title": "Barista", "subtitle": "Cafe", "included": False, "pinned": False, "score": 0.1,
             "bullets": [_bullet("b4", "Made coffee")]},
        ],
        "projects": [{"id": "p1", "title": "CLI", "subtitle": "Go", "included": True, "pinned": False, "score": 0.5,
                      "bullets": [_bullet("b5", "Parsed flags")]}],
        "skills": [{"id": "s1", "name": "Python", "included": True, "matches_jd": True},
                   {"id": "s2", "name": "COBOL", "included": False, "matches_jd": False}],
        "certifications": [],
        "achievements": [{"id": "a1", "title": "Winner", "description": "", "included": False}],
    }


def test_only_included_entries_and_bullets(content):
    resume = assemble_resume(content, "Backend Engineer")
    assert [e["title"] for e in resume["experience"]] == ["Backend Engineer"]
    assert resume["experience"][0]["bullets"] == ["Built APIs", "Built REST APIs in FastAPI"]
    assert resume["skills"] == ["Python"]
    assert resume["achievements"] == []


def test_uses_current_text_including_user_edits(content):
    bullets = assemble_resume(content, "Backend Engineer")["experience"][0]["bullets"]
    assert "Built REST APIs in FastAPI" in bullets
    assert "Built APIs in FastAPI" not in bullets


def test_keeps_job_title_and_contact(content):
    resume = assemble_resume(content, "Backend Engineer")
    assert resume["job_title"] == "Backend Engineer"
    assert resume["personal_info"]["full_name"] == "John Doe"


def test_converts_to_sections(content):
    sections = resume_to_sections_json(assemble_resume(content, "Backend Engineer"))
    types = [s["section_type"] for s in sections]
    assert types == ["personal_info", "education", "experience", "projects", "skills"]
    assert all(json.loads(s["content"]) for s in sections)
