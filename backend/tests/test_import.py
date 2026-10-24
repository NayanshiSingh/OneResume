"""Resume import: text extraction, parsing, preview, and applying to the profile."""

import io

import pytest
from docx import Document

from app.config import settings
from app.services import import_service

RESUME_TEXT = """Priya Raman
priya.raman@example.com | +1-555-0101 | https://github.com/example-priya

Education
B.S. Computer Science
Lakeshore State University 2023 - 2027

Experience
Software Engineering Intern | Ledgerly
May 2026 - Aug 2026
• Built 4 REST API endpoints in Django REST Framework
• Wrote PostgreSQL migrations that cut a report query from 9s to 1.2s

Teaching Assistant at Lakeshore State University
Aug 2025 - Present
- Lead weekly lab sections on trees and graphs in Java

Projects
CampusEats | React, Node.js, MongoDB
• Built a React front end and Express API

Skills
Languages: Python, Java, C
Tools: Docker, Git

Certifications
AWS Certified Cloud Practitioner 2026

Achievements
Dean's List: Fall 2024 to Spring 2026
"""


def _docx(text: str) -> bytes:
    doc = Document()
    for line in text.splitlines():
        doc.add_paragraph(line)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


class TestRuleParser:
    @pytest.fixture
    def parsed(self):
        return import_service.parse_with_rules(RESUME_TEXT)

    def test_contact_details(self, parsed):
        assert parsed["personal_info"] == {
            "full_name": "Priya Raman", "email": "priya.raman@example.com", "phone_number": "+1-555-0101",
        }

    def test_experience_entries_dates_and_bullets(self, parsed):
        first, second = parsed["experience"]
        assert (first["role"], first["company"], first["start_date"], first["end_date"]) == (
            "Software Engineering Intern", "Ledgerly", "2026-05", "2026-08")
        assert [b["bullet_text"] for b in first["bullets"]] == [
            "Built 4 REST API endpoints in Django REST Framework",
            "Wrote PostgreSQL migrations that cut a report query from 9s to 1.2s",
        ]
        assert (second["role"], second["company"], second["end_date"]) == (
            "Teaching Assistant", "Lakeshore State University", "Present")

    def test_education(self, parsed):
        assert parsed["education"] == [{
            "institution": "Lakeshore State University", "degree": "B.S. Computer Science",
            "start_year": 2023, "end_year": 2027,
        }]

    def test_projects_skills_certs_achievements_links(self, parsed):
        assert parsed["projects"][0]["project_title"] == "CampusEats"
        assert parsed["projects"][0]["tech_stack"] == "React, Node.js, MongoDB"
        assert [s["skill_name"] for s in parsed["skills"]] == ["Python", "Java", "C", "Docker", "Git"]
        assert parsed["certifications"] == [{"name": "AWS Certified Cloud Practitioner", "year": 2026}]
        assert parsed["achievements"] == [{"title": "Dean's List", "description": "Fall 2024 to Spring 2026"}]
        assert parsed["external_profiles"] == [{"platform": "GitHub", "profile_url": "https://github.com/example-priya"}]

    def test_bullet_wording_is_copied_exactly(self, parsed):
        texts = [b["bullet_text"] for e in parsed["experience"] for b in e["bullets"]]
        assert all(t in RESUME_TEXT for t in texts)


class TestImportEndpoints:
    def test_upload_previews_without_saving_then_apply_saves(self, client):
        resp = client.post("/api/profile/import", files={"file": ("resume.docx", _docx(RESUME_TEXT))})
        assert resp.status_code == 200, resp.text
        preview = resp.json()
        assert preview["mode"] == "basic"
        assert any("basic import" in w.lower() for w in preview["warnings"])
        assert client.get("/api/profile").json()["experience"] == []

        applied = client.post("/api/profile/import/apply", json=preview["profile"])
        assert applied.status_code == 200
        profile = applied.json()
        assert profile["personal_info"]["full_name"] == "Priya Raman"
        assert len(profile["experience"]) == 2
        assert len(profile["experience"][0]["bullets"]) == 2
        assert len(profile["skills"]) == 5

    def test_apply_keeps_existing_entries(self, client):
        client.post("/api/profile/skills", json={"skill_name": "Rust"})
        client.post("/api/profile/import/apply", json={"skills": [{"skill_name": "Go"}]})
        assert [s["skill_name"] for s in client.get("/api/profile").json()["skills"]] == ["Rust", "Go"]

    @pytest.mark.parametrize("filename,data", [
        ("resume.txt", b"plain text " * 20),
        ("resume.pdf", b"not really a pdf" * 10),
        ("resume.docx", b"PK broken zip" * 10),
    ])
    def test_unreadable_files_rejected(self, client, filename, data):
        resp = client.post("/api/profile/import", files={"file": (filename, data)})
        assert resp.status_code == 422

    def test_too_large_rejected(self, client):
        data = b"PK" + b"0" * (import_service.MAX_UPLOAD_BYTES + 1)
        assert client.post("/api/profile/import", files={"file": ("big.docx", data)}).status_code == 422

    def test_document_without_text_rejected(self, client):
        resp = client.post("/api/profile/import", files={"file": ("empty.docx", _docx("Hi"))})
        assert resp.status_code == 422
        assert "No readable text" in resp.json()["detail"]

    def test_requires_sign_in(self, anon_client):
        assert anon_client.post("/api/profile/import", files={"file": ("r.docx", _docx(RESUME_TEXT))}).status_code == 401


class TestGeminiPath:
    def test_ai_mode_drops_invalid_items(self, client, monkeypatch):
        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(import_service, "parse_with_llm", lambda text: {
            "personal_info": {"full_name": "Priya Raman"},
            "skills": [{"skill_name": "Python"}, {"skill_name": ""}],
            "experience": [{"company": "Ledgerly", "role": "Intern", "bullets": [{"bullet_text": "Built APIs"}]}],
        })
        preview = client.post("/api/profile/import", files={"file": ("r.docx", _docx(RESUME_TEXT))}).json()
        assert preview["mode"] == "ai"
        assert [s["skill_name"] for s in preview["profile"]["skills"]] == ["Python"]
        assert any("1 item(s) could not be read" in w for w in preview["warnings"])

    def test_ai_failure_falls_back_to_labelled_basic_import(self, client, monkeypatch):
        def broken(text):
            raise RuntimeError("provider down")

        monkeypatch.setattr(settings, "GEMINI_API_KEY", "test-key")
        monkeypatch.setattr(import_service, "parse_with_llm", broken)
        preview = client.post("/api/profile/import", files={"file": ("r.docx", _docx(RESUME_TEXT))}).json()
        assert preview["mode"] == "basic"
        assert "AI import failed, so a basic import was used." in preview["warnings"]
        assert len(preview["profile"]["experience"]) == 2
