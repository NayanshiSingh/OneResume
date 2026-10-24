"""Drafts: original wording, selection, labelled matching, edits, approval, and export."""

import io
import zipfile

import pytest

from app.config import settings
from app.services import embedding_service
from tests.conftest import fill_profile, make_draft


def _bullets(draft, section="experience"):
    return [b for entry in draft["content"][section] for b in entry["bullets"]]


def _edit(client, draft, *ops):
    return client.patch(f"/api/drafts/{draft['id']}", json={"revision": draft["revision"], "ops": list(ops)})


def _docx_text(client, resume_id) -> str:
    data = client.get(f"/api/resumes/{resume_id}/download?format=docx").content
    return zipfile.ZipFile(io.BytesIO(data)).read("word/document.xml").decode()


@pytest.fixture
def draft(client, db, strong_fit_profile_data, sample_jd_text):
    fill_profile(client, strong_fit_profile_data)
    return make_draft(client, db, sample_jd_text)


class TestBuilding:
    def test_uses_original_wording(self, client, draft):
        profile_texts = {b["bullet_text"] for e in client.get("/api/profile").json()["experience"] for b in e["bullets"]}
        assert {b["text"] for b in _bullets(draft)} == profile_texts
        assert all(b["text"] == b["original_text"] and not b["user_edited"] for b in _bullets(draft))

    def test_keeps_profile_order_and_limits_inclusion(self, client, db, sample_jd_text):
        for i, (role, bullet) in enumerate([
            ("Backend Engineer", "Built Python FastAPI services on PostgreSQL"),
            ("Barista", "Made coffee for customers"),
            ("Data Intern", "Wrote Python scripts and SQL reports"),
            ("DevOps Intern", "Built Docker images and CI/CD pipelines on AWS"),
        ]):
            client.post("/api/profile/experience", json={"company": f"Co{i}", "role": role, "bullets": [{"bullet_text": bullet}]})
        profile_ids = [e["id"] for e in client.get("/api/profile").json()["experience"]]
        result = make_draft(client, db, sample_jd_text)
        entries = result["content"]["experience"]
        assert [e["id"] for e in entries] == profile_ids
        assert sum(e["included"] for e in entries) == settings.MAX_EXPERIENCE_SECTIONS
        assert next(e for e in entries if e["title"] == "Barista")["included"] is False

    def test_limits_bullets_per_entry(self, client, db, sample_jd_text):
        client.post("/api/profile/experience", json={
            "company": "Acme", "role": "Engineer",
            "bullets": [{"bullet_text": f"Python task number {i}"} for i in range(7)],
        })
        bullets = _bullets(make_draft(client, db, sample_jd_text))
        assert len(bullets) == 7
        assert sum(b["included"] for b in bullets) == settings.MAX_BULLETS_PER_SECTION

    def test_two_page_target_includes_more(self, client, db, sample_jd_text):
        client.post("/api/profile/experience", json={
            "company": "Acme", "role": "Engineer",
            "bullets": [{"bullet_text": f"Python task number {i}"} for i in range(8)],
        })
        bullets = _bullets(make_draft(client, db, sample_jd_text, page_target=2))
        assert sum(b["included"] for b in bullets) > settings.MAX_BULLETS_PER_SECTION

    def test_basic_matching_is_labelled(self, draft):
        assert draft["matching_mode"] == "basic"
        assert any("Semantic matching is off" in w for w in draft["warnings"])

    def test_ai_matching_when_embeddings_configured(self, client, db, monkeypatch, strong_fit_profile_data, sample_jd_text):
        monkeypatch.setattr(settings, "PINECONE_API_KEY", "test-key")
        fill_profile(client, strong_fit_profile_data)
        result = make_draft(client, db, sample_jd_text)
        assert result["matching_mode"] == "ai"
        assert not any("Semantic matching" in w for w in result["warnings"])

    def test_embedding_failure_falls_back_to_labelled_basic(self, client, db, monkeypatch, strong_fit_profile_data, sample_jd_text):
        def broken(texts):
            raise RuntimeError("provider down")

        monkeypatch.setattr(settings, "PINECONE_API_KEY", "test-key")
        monkeypatch.setattr(embedding_service, "_embed_batch", broken)
        fill_profile(client, strong_fit_profile_data)
        result = make_draft(client, db, sample_jd_text)
        assert result["matching_mode"] == "basic"
        assert any("Semantic matching failed" in w for w in result["warnings"])

    def test_profile_and_review_warnings(self, client, db, sample_jd_text):
        client.post("/api/profile/skills", json={"skill_name": "Docker"})
        warnings = make_draft(client, db, sample_jd_text)["warnings"]
        assert any("not reviewed" in w for w in warnings)
        assert any("name and contact details" in w for w in warnings)
        assert any("only in your skills list" in w for w in warnings)

    def test_jd_matching_skills_come_first(self, client, db, sample_jd_text):
        for name in ["Photoshop", "Python", "Knitting", "Docker"]:
            client.post("/api/profile/skills", json={"skill_name": name})
        skills = make_draft(client, db, sample_jd_text)["content"]["skills"]
        assert [s["name"] for s in skills] == ["Python", "Docker", "Photoshop", "Knitting"]


class TestEditing:
    def test_edit_marks_user_supplied_and_clears_approval(self, client, draft):
        client.post(f"/api/drafts/{draft['id']}/approve", json={"revision": draft["revision"]})
        entry = draft["content"]["experience"][0]
        bullet = entry["bullets"][0]
        resp = _edit(client, draft, {"op": "edit_bullet", "section": "experience", "item_id": entry["id"],
                                     "bullet_id": bullet["id"], "text": "Designed REST APIs in FastAPI"})
        assert resp.status_code == 200
        edited = resp.json()
        assert edited["revision"] == draft["revision"] + 1
        assert edited["status"] == "draft" and edited["approved_revision"] is None
        assert edited["edited_bullets"] == [{
            "section": "experience", "item_id": entry["id"], "bullet_id": bullet["id"],
            "original_text": bullet["text"], "text": "Designed REST APIs in FastAPI",
        }]

    def test_revert_restores_original(self, client, draft):
        entry = draft["content"]["experience"][0]
        bullet = entry["bullets"][0]
        target = {"section": "experience", "item_id": entry["id"], "bullet_id": bullet["id"]}
        edited = _edit(client, draft, {"op": "edit_bullet", **target, "text": "Something else"}).json()
        reverted = _edit(client, edited, {"op": "revert_bullet", **target}).json()
        assert reverted["edited_bullets"] == []
        assert reverted["content"]["experience"][0]["bullets"][0]["text"] == bullet["text"]

    def test_stale_revision_rejected(self, client, draft):
        op = {"op": "set_included", "section": "skills", "item_id": draft["content"]["skills"][0]["id"], "value": False}
        assert _edit(client, draft, op).status_code == 200
        assert _edit(client, draft, op).status_code == 409

    @pytest.mark.parametrize("op", [
        {"op": "set_included", "section": "skills", "item_id": "missing", "value": False},
        {"op": "set_included", "section": "skills", "item_id": "SKILL"},
        {"op": "edit_bullet", "section": "skills", "item_id": "SKILL", "bullet_id": "x", "text": "y"},
    ])
    def test_invalid_ops_rejected(self, client, draft, op):
        op = {k: (draft["content"]["skills"][0]["id"] if v == "SKILL" else v) for k, v in op.items()}
        assert _edit(client, draft, op).status_code == 422

    def test_empty_bullet_text_rejected(self, client, draft):
        entry = draft["content"]["experience"][0]
        op = {"op": "edit_bullet", "section": "experience", "item_id": entry["id"],
              "bullet_id": entry["bullets"][0]["id"], "text": "   "}
        assert _edit(client, draft, op).status_code == 422

    def test_pin_includes_and_hide_unpins(self, client, draft):
        entry = draft["content"]["projects"][0]
        target = {"section": "projects", "item_id": entry["id"]}
        hidden = _edit(client, draft, {"op": "set_included", **target, "value": False}).json()
        pinned = _edit(client, hidden, {"op": "set_pinned", **target, "value": True}).json()
        assert pinned["content"]["projects"][0]["included"] is True
        rehidden = _edit(client, pinned, {"op": "set_included", **target, "value": False}).json()
        assert rehidden["content"]["projects"][0]["pinned"] is False

    def test_coverage_tracks_what_is_in_the_draft(self, client, db, sample_jd_text):
        client.post("/api/profile/experience", json={"company": "Acme", "role": "Engineer",
                                                      "bullets": [{"bullet_text": "Containerised services with Docker"}]})
        result = make_draft(client, db, sample_jd_text)
        docker = next(c for c in result["coverage"] if c["requirement"] == "Docker")
        assert docker["label"] == "supported" and docker["in_draft"] is True
        entry = result["content"]["experience"][0]
        hidden = _edit(client, result, {"op": "set_included", "section": "experience", "item_id": entry["id"], "value": False}).json()
        assert next(c for c in hidden["coverage"] if c["requirement"] == "Docker")["in_draft"] is False


class TestApprovalAndExport:
    def test_export_requires_approval_of_current_revision(self, client, draft):
        assert client.post(f"/api/drafts/{draft['id']}/export").status_code == 409
        assert client.post(f"/api/drafts/{draft['id']}/approve", json={"revision": draft["revision"] + 1}).status_code == 409
        approved = client.post(f"/api/drafts/{draft['id']}/approve", json={"revision": draft["revision"]}).json()
        assert approved["status"] == "approved"

        op = {"op": "set_included", "section": "skills", "item_id": draft["content"]["skills"][0]["id"], "value": False}
        _edit(client, approved, op)
        assert client.post(f"/api/drafts/{draft['id']}/export").status_code == 409

    def test_export_is_idempotent_per_revision(self, client, draft):
        client.post(f"/api/drafts/{draft['id']}/approve", json={"revision": draft["revision"]})
        first = client.post(f"/api/drafts/{draft['id']}/export").json()
        second = client.post(f"/api/drafts/{draft['id']}/export").json()
        assert first["id"] == second["id"]
        assert client.get(f"/api/drafts/{draft['id']}").json()["exported_resume_id"] == first["id"]
        assert len(client.get("/api/resumes").json()) == 1

    def test_export_contains_edits_and_omits_hidden_content(self, client, draft):
        entry = draft["content"]["experience"][0]
        keep, hide = entry["bullets"][0], entry["bullets"][1]
        updated = _edit(
            client, draft,
            {"op": "edit_bullet", "section": "experience", "item_id": entry["id"], "bullet_id": keep["id"],
             "text": "Designed REST APIs in FastAPI for 10K daily users"},
            {"op": "set_included", "section": "experience", "item_id": entry["id"], "bullet_id": hide["id"], "value": False},
        ).json()
        client.post(f"/api/drafts/{draft['id']}/approve", json={"revision": updated["revision"]})
        resume = client.post(f"/api/drafts/{draft['id']}/export").json()
        text = _docx_text(client, resume["id"])
        assert "Designed REST APIs in FastAPI for 10K daily users" in text
        assert hide["text"] not in text
        assert resume["draft_id"] == draft["id"]

    def test_new_revision_exports_as_new_version(self, client, draft):
        client.post(f"/api/drafts/{draft['id']}/approve", json={"revision": draft["revision"]})
        first = client.post(f"/api/drafts/{draft['id']}/export").json()
        op = {"op": "set_included", "section": "skills", "item_id": draft["content"]["skills"][0]["id"], "value": False}
        updated = _edit(client, client.get(f"/api/drafts/{draft['id']}").json(), op).json()
        client.post(f"/api/drafts/{draft['id']}/approve", json={"revision": updated["revision"]})
        second = client.post(f"/api/drafts/{draft['id']}/export").json()
        assert (first["version"], second["version"]) == (1, 2)

    def test_deleting_a_draft_keeps_exported_resumes(self, client, draft):
        client.post(f"/api/drafts/{draft['id']}/approve", json={"revision": draft["revision"]})
        resume = client.post(f"/api/drafts/{draft['id']}/export").json()
        assert client.delete(f"/api/drafts/{draft['id']}").status_code == 204
        assert client.get(f"/api/resumes/{resume['id']}").status_code == 200
        assert client.get("/api/drafts").json() == []


class TestPageBudget:
    def test_bullets_share_one_budget_across_entries(self, client, db, sample_jd_text):
        for i in range(3):
            client.post("/api/profile/experience", json={"company": f"Co{i}", "role": "Engineer", "bullets": [
                {"bullet_text": f"Python service {i}-{j}"} for j in range(7)]})
        for i in range(3):
            client.post("/api/profile/projects", json={"project_title": f"P{i}", "bullets": [
                {"bullet_text": f"Docker tool {i}-{j}"} for j in range(4)]})
        content = make_draft(client, db, sample_jd_text)["content"]
        included = [b for s in ("experience", "projects") for e in content[s] if e["included"] for b in e["bullets"] if b["included"]]
        assert len(included) == settings.BULLETS_PER_PAGE

    def test_every_included_job_keeps_a_bullet(self, client, db, sample_jd_text):
        client.post("/api/profile/experience", json={"company": "Acme", "role": "Engineer", "bullets": [
            {"bullet_text": f"Python FastAPI PostgreSQL Docker AWS task {j}"} for j in range(20)]})
        client.post("/api/profile/experience", json={"company": "Cafe", "role": "Barista", "bullets": [
            {"bullet_text": "Made coffee"}]})
        content = make_draft(client, db, sample_jd_text)["content"]
        barista = next(e for e in content["experience"] if e["title"] == "Barista")
        assert barista["included"] and barista["bullets"][0]["included"]

    def test_project_without_budget_is_left_out(self, client, db, sample_jd_text):
        for i in range(3):
            client.post("/api/profile/experience", json={"company": f"Co{i}", "role": "Engineer", "bullets": [
                {"bullet_text": f"Python FastAPI PostgreSQL Docker AWS work {i}-{j}"}
                for j in range(settings.MAX_BULLETS_PER_SECTION)]})
        client.post("/api/profile/projects", json={"project_title": "Knitting blog", "bullets": [{"bullet_text": "Wrote posts"}]})
        content = make_draft(client, db, sample_jd_text)["content"]
        assert content["projects"][0]["included"] is False
