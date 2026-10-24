"""Profile editing: create, update, delete, reorder, and persistence of edits."""

import pytest

from app.models.profile import Experience, ExperienceBullet
from tests.conftest import fill_profile


class TestSections:
    def test_full_profile_round_trip(self, client, strong_fit_profile_data):
        data = fill_profile(client, strong_fit_profile_data)
        assert data["personal_info"]["full_name"] == "John Doe"
        assert len(data["education"]) == 1
        assert len(data["skills"]) == 6
        assert len(data["experience"][0]["bullets"]) == 4
        assert len(data["projects"]) == 1
        assert len(data["certifications"]) == 1
        assert len(data["achievements"]) == 1
        assert len(data["external_profiles"]) == 2

    @pytest.mark.parametrize("path,key,create,change", [
        ("education", "education", {"institution": "MIT", "degree": "B.S."}, {"end_year": 2027, "end_month": 5}),
        ("skills", "skills", {"skill_name": "Python"}, {"skill_category": "Languages"}),
        ("experience", "experience", {"company": "Acme", "role": "Intern"}, {"role": "Engineer", "end_date": "Present"}),
        ("projects", "projects", {"project_title": "CLI"}, {"tech_stack": "Go"}),
        ("certifications", "certifications", {"name": "CKA"}, {"year": 2025}),
        ("achievements", "achievements", {"title": "Winner"}, {"description": "First place"}),
        ("external-profiles", "external_profiles", {"platform": "GitHub", "profile_url": "https://github.com/a"}, {"profile_url": "https://github.com/b"}),
    ])
    def test_update_persists(self, client, path, key, create, change):
        item = client.post(f"/api/profile/{path}", json=create).json()
        resp = client.patch(f"/api/profile/{path}/{item['id']}", json=change)
        assert resp.status_code == 200
        stored = client.get("/api/profile").json()[key][0]
        assert {k: stored[k] for k in change} == change
        assert {k: stored[k] for k in create if k not in change} == {k: v for k, v in create.items() if k not in change}

    def test_optional_field_can_be_cleared(self, client):
        item = client.post("/api/profile/education", json={"institution": "MIT", "degree": "B.S.", "grade": "3.9"}).json()
        client.patch(f"/api/profile/education/{item['id']}", json={"grade": None})
        assert client.get("/api/profile").json()["education"][0]["grade"] is None

    def test_required_field_cannot_be_cleared(self, client):
        item = client.post("/api/profile/skills", json={"skill_name": "Python"}).json()
        assert client.patch(f"/api/profile/skills/{item['id']}", json={"skill_name": None}).status_code == 422

    def test_month_must_be_valid(self, client):
        resp = client.post("/api/profile/education", json={"institution": "MIT", "degree": "B.S.", "end_month": 13})
        assert resp.status_code == 422

    def test_delete(self, client):
        item = client.post("/api/profile/skills", json={"skill_name": "Python"}).json()
        assert client.delete(f"/api/profile/skills/{item['id']}").status_code == 204
        assert client.get("/api/profile").json()["skills"] == []

    def test_unknown_item_is_404(self, client):
        assert client.patch("/api/profile/skills/does-not-exist", json={}).status_code == 404

    def test_reorder(self, client):
        ids = [client.post("/api/profile/skills", json={"skill_name": n}).json()["id"] for n in ["A", "B", "C"]]
        assert client.put("/api/profile/skills/order", json={"ids": ids[::-1]}).status_code == 204
        assert [s["skill_name"] for s in client.get("/api/profile").json()["skills"]] == ["C", "B", "A"]

    def test_reorder_must_list_every_item_once(self, client):
        ids = [client.post("/api/profile/skills", json={"skill_name": n}).json()["id"] for n in ["A", "B"]]
        assert client.put("/api/profile/skills/order", json={"ids": ids[:1]}).status_code == 422
        assert client.put("/api/profile/skills/order", json={"ids": [ids[0], ids[0]]}).status_code == 422

    def test_new_items_go_last(self, client):
        for name in ["First", "Second", "Third"]:
            client.post("/api/profile/skills", json={"skill_name": name})
        assert [s["skill_name"] for s in client.get("/api/profile").json()["skills"]] == ["First", "Second", "Third"]

    def test_personal_info_upsert(self, client):
        client.put("/api/profile/personal-info", json={"full_name": "John Doe", "email": "john@test.com"})
        client.put("/api/profile/personal-info", json={"full_name": "John Updated"})
        info = client.get("/api/profile").json()["personal_info"]
        assert info["full_name"] == "John Updated"
        assert info["email"] is None


class TestBullets:
    @pytest.fixture
    def experience(self, client):
        return client.post("/api/profile/experience", json={
            "company": "Acme", "role": "Engineer",
            "bullets": [{"bullet_text": "Built APIs"}, {"bullet_text": "Fixed bugs"}],
        }).json()

    def test_add_update_delete_reorder(self, client, experience):
        exp_id = experience["id"]
        added = client.post(f"/api/profile/experience/{exp_id}/bullets", json={"bullet_text": "Wrote tests"}).json()
        client.patch(f"/api/profile/experience/bullets/{added['id']}", json={"bullet_text": "Wrote pytest suites"})
        first = experience["bullets"][0]["id"]
        assert client.delete(f"/api/profile/experience/bullets/{first}").status_code == 204
        remaining = [b["id"] for b in client.get("/api/profile").json()["experience"][0]["bullets"]]
        client.put(f"/api/profile/experience/{exp_id}/bullets/order", json={"ids": remaining[::-1]})
        texts = [b["bullet_text"] for b in client.get("/api/profile").json()["experience"][0]["bullets"]]
        assert texts == ["Wrote pytest suites", "Fixed bugs"]

    def test_project_bullets(self, client):
        proj = client.post("/api/profile/projects", json={"project_title": "CLI", "bullets": [{"bullet_text": "Parsed args"}]}).json()
        client.post(f"/api/profile/projects/{proj['id']}/bullets", json={"bullet_text": "Added tests"})
        assert len(client.get("/api/profile").json()["projects"][0]["bullets"]) == 2

    def test_editing_bullet_clears_stale_embeddings(self, client, experience, db):
        bullet = db.get(ExperienceBullet, experience["bullets"][0]["id"])
        bullet.embedding = "[1.0]"
        bullet.experience.experience_embedding = "[1.0]"
        db.commit()
        client.patch(f"/api/profile/experience/bullets/{bullet.id}", json={"bullet_text": "Built REST APIs"})
        db.expire_all()
        assert db.get(ExperienceBullet, bullet.id).embedding is None
        assert db.get(Experience, experience["id"]).experience_embedding is None

    def test_unchanged_bullet_keeps_embedding(self, client, experience, db):
        bullet = db.get(ExperienceBullet, experience["bullets"][0]["id"])
        bullet.embedding = "[1.0]"
        db.commit()
        client.patch(f"/api/profile/experience/bullets/{bullet.id}", json={"bullet_text": "Built APIs"})
        db.expire_all()
        assert db.get(ExperienceBullet, bullet.id).embedding == "[1.0]"

    def test_empty_bullet_rejected(self, client, experience):
        resp = client.post(f"/api/profile/experience/{experience['id']}/bullets", json={"bullet_text": ""})
        assert resp.status_code == 422
