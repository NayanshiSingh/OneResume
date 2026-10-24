"""Verified exports, page checks, version comparison, restore, and sent dates."""

import pytest

from app.models.resume import ExportArtifact
from app.services import draft_service, export_service
from tests.conftest import fill_profile, make_draft, signup

try:
    from weasyprint import HTML  # noqa: F401
    HAS_WEASYPRINT = True
except OSError:
    HAS_WEASYPRINT = False

needs_pdf = pytest.mark.skipif(not HAS_WEASYPRINT, reason="WeasyPrint system libraries not installed")


def _approve_and_export(client, draft):
    client.post(f"/api/drafts/{draft['id']}/approve", json={"revision": draft["revision"]})
    resp = client.post(f"/api/drafts/{draft['id']}/export")
    assert resp.status_code == 201, resp.text
    return resp.json()


def _edit(client, draft, *ops):
    resp = client.patch(f"/api/drafts/{draft['id']}", json={"revision": draft["revision"], "ops": list(ops)})
    assert resp.status_code == 200, resp.text
    return resp.json()


@pytest.fixture
def draft(client, db, strong_fit_profile_data, sample_jd_text):
    fill_profile(client, strong_fit_profile_data)
    return make_draft(client, db, sample_jd_text)


class TestVerifiedExports:
    def test_export_records_snapshot(self, client, draft):
        resume = _approve_and_export(client, draft)
        assert resume["can_restore"] is True
        assert "docx" in resume["formats"]

    @needs_pdf
    def test_pdf_page_count_is_recorded(self, client, draft):
        assert _approve_and_export(client, draft)["pdf_pages"] == 1

    def test_file_that_loses_content_is_not_offered(self, client, draft, monkeypatch):
        """Simulates a renderer bug that drops a bullet: the read-back check must catch it."""
        real = export_service.export_to_docx

        def lossy(data):
            data = {**data, "experience": [{**e, "bullets": e["bullets"][:-1]} for e in data["experience"]]}
            return real(data)

        monkeypatch.setattr(export_service, "export_to_docx", lossy)
        resume = _approve_and_export(client, draft)
        assert "docx" not in resume["formats"]
        assert any("DOCX was not offered" in w and "missing" in w for w in resume["warnings"])

    @needs_pdf
    def test_overflow_is_reported(self, client, db, sample_jd_text, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "BULLETS_PER_PAGE", 60)
        monkeypatch.setattr(settings, "MAX_BULLETS_PER_SECTION", 20)
        for i in range(3):
            client.post("/api/profile/experience", json={"company": f"Company {i}", "role": "Python Engineer", "bullets": [
                {"bullet_text": f"Built Python FastAPI and PostgreSQL services for team {i}, part {j}, with tests and docs"}
                for j in range(20)]})
        resume = _approve_and_export(client, make_draft(client, db, sample_jd_text))
        assert resume["pdf_pages"] > 1
        assert any("pages; your target was 1" in w for w in resume["warnings"])

    def test_changed_file_is_not_served(self, client, db, draft, tmp_path):
        resume = _approve_and_export(client, draft)
        artifact = db.query(ExportArtifact).filter_by(resume_id=resume["id"], format="docx").one()
        (tmp_path / "storage" / artifact.storage_key).write_bytes(b"tampered")
        resp = client.get(f"/api/resumes/{resume['id']}/download?format=docx")
        assert resp.status_code == 404
        assert "no longer available" in resp.json()["detail"]


class TestVersions:
    def test_compare_shows_what_changed(self, client, draft):
        first = _approve_and_export(client, draft)
        entry = draft["content"]["experience"][0]
        kept, dropped = entry["bullets"][0], next(b for b in entry["bullets"][1:] if b["included"])
        current = client.get(f"/api/drafts/{draft['id']}").json()
        updated = _edit(client, current,
                        {"op": "edit_bullet", "section": "experience", "item_id": entry["id"], "bullet_id": kept["id"],
                         "text": "Designed REST APIs in FastAPI"},
                        {"op": "set_included", "section": "experience", "item_id": entry["id"], "bullet_id": dropped["id"], "value": False})
        second = _approve_and_export(client, updated)
        diff = client.get(f"/api/resumes/{first['id']}/compare/{second['id']}").json()
        assert (diff["from_version"], diff["to_version"]) == (1, 2)
        kinds = {(c["kind"], c["text"]) for c in diff["changes"]}
        assert ("added_bullet", "Designed REST APIs in FastAPI") in kinds
        assert ("removed_bullet", kept["text"]) in kinds
        assert ("removed_bullet", dropped["text"]) in kinds

    def test_restore_creates_a_new_draft_with_the_old_content(self, client, draft):
        first = _approve_and_export(client, draft)
        entry = draft["content"]["experience"][0]
        current = client.get(f"/api/drafts/{draft['id']}").json()
        _edit(client, current, {"op": "set_included", "section": "experience", "item_id": entry["id"], "value": False})

        resp = client.post(f"/api/resumes/{first['id']}/restore")
        assert resp.status_code == 201
        restored = resp.json()
        assert restored["id"] != draft["id"]
        assert (restored["revision"], restored["status"]) == (1, "draft")
        assert restored["content"]["experience"][0]["included"] is True
        assert any("Restored from version 1" in w for w in restored["warnings"])
        assert client.get(f"/api/drafts/{draft['id']}").json()["content"]["experience"][0]["included"] is False

    def test_restored_version_exports_identically(self, client, draft, db):
        first = _approve_and_export(client, draft)
        restored = client.post(f"/api/resumes/{first['id']}/restore").json()
        again = _approve_and_export(client, restored)
        diff = client.get(f"/api/resumes/{first['id']}/compare/{again['id']}").json()
        assert diff["changes"] == []

    def test_versions_without_snapshot_cannot_be_restored(self, client, draft, db):
        from app.models.resume import Resume
        resume = _approve_and_export(client, draft)
        db.get(Resume, resume["id"]).content_snapshot = None
        db.commit()
        assert client.get(f"/api/resumes/{resume['id']}").json()["can_restore"] is False
        assert client.post(f"/api/resumes/{resume['id']}/restore").status_code == 422

    def test_mark_sent_and_clear(self, client, draft):
        resume = _approve_and_export(client, draft)
        sent = client.patch(f"/api/resumes/{resume['id']}", json={"sent_at": "2026-10-20T09:00:00"}).json()
        assert sent["sent_at"].startswith("2026-10-20")
        assert client.patch(f"/api/resumes/{resume['id']}", json={"sent_at": None}).json()["sent_at"] is None

    def test_versions_are_private(self, client, make_client, draft):
        resume = _approve_and_export(client, draft)
        other = make_client()
        signup(other, "other@example.com")
        assert other.post(f"/api/resumes/{resume['id']}/restore").status_code == 404
        assert other.patch(f"/api/resumes/{resume['id']}", json={"sent_at": None}).status_code == 404
        assert other.get(f"/api/resumes/{resume['id']}/compare/{resume['id']}").status_code == 404


class TestLayout:
    @needs_pdf
    def test_short_draft_fits(self, client, draft):
        layout = client.get(f"/api/drafts/{draft['id']}/layout").json()
        assert (layout["available"], layout["pages"], layout["fits"], layout["candidates"]) == (True, 1, True, [])

    @needs_pdf
    def test_long_draft_suggests_cuts_starting_with_unsupported_bullets(self, client, db, sample_jd_text, monkeypatch):
        from app.config import settings
        monkeypatch.setattr(settings, "BULLETS_PER_PAGE", 60)
        monkeypatch.setattr(settings, "MAX_BULLETS_PER_SECTION", 30)
        bullets = [f"Organised the office plant watering rota for week {j}, kept careful notes in a shared binder, "
                   "and reminded every colleague on the floor about their turn by email each Monday morning" for j in range(28)]
        bullets.append("Built Python FastAPI services on PostgreSQL")
        client.post("/api/profile/experience", json={"company": "Acme", "role": "Engineer",
                                                      "bullets": [{"bullet_text": b} for b in bullets]})
        long_draft = make_draft(client, db, sample_jd_text)
        layout = client.get(f"/api/drafts/{long_draft['id']}/layout").json()
        assert layout["pages"] > 1 and layout["fits"] is False
        assert len(layout["candidates"]) == draft_service.MAX_REMOVAL_CANDIDATES
        assert all(c["covers"] == [] for c in layout["candidates"])

    def test_unavailable_renderer_is_reported(self, client, draft, monkeypatch):
        def broken(data):
            raise OSError("no pango")

        monkeypatch.setattr(draft_service, "render_resume_pdf", broken)
        assert client.get(f"/api/drafts/{draft['id']}/layout").json()["available"] is False
