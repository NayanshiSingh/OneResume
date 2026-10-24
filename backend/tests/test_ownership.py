"""One user can never read, change, or download another user's data."""

import pytest

from tests.conftest import fill_profile, signup


@pytest.fixture
def alice(make_client, strong_fit_profile_data, sample_jd_text):
    c = make_client()
    signup(c, "alice@example.com")
    profile = fill_profile(c, strong_fit_profile_data)
    jd = c.post("/api/jd/analyze", json={"raw_text": sample_jd_text}).json()
    resume = c.post("/api/resumes/generate", json={"jd_text": sample_jd_text}).json()
    return {"client": c, "profile": profile, "jd": jd, "resume": resume}


@pytest.fixture
def bob(make_client):
    c = make_client()
    signup(c, "bob@example.com")
    return c


SECTION_ITEMS = [
    ("education", "education"),
    ("skills", "skills"),
    ("experience", "experience"),
    ("projects", "projects"),
    ("certifications", "certifications"),
    ("achievements", "achievements"),
    ("external-profiles", "external_profiles"),
]


@pytest.mark.parametrize("path,key", SECTION_ITEMS)
def test_cannot_update_or_delete_another_users_section_item(alice, bob, path, key):
    item_id = alice["profile"][key][0]["id"]
    assert bob.patch(f"/api/profile/{path}/{item_id}", json={}).status_code == 404
    assert bob.delete(f"/api/profile/{path}/{item_id}").status_code == 404
    assert len(alice["client"].get("/api/profile").json()[key]) == len(alice["profile"][key])


@pytest.mark.parametrize("path,key", [("experience", "experience"), ("projects", "projects")])
def test_cannot_touch_another_users_bullets(alice, bob, path, key):
    entry = alice["profile"][key][0]
    bullet_id = entry["bullets"][0]["id"]
    assert bob.post(f"/api/profile/{path}/{entry['id']}/bullets", json={"bullet_text": "Injected"}).status_code == 404
    assert bob.patch(f"/api/profile/{path}/bullets/{bullet_id}", json={"bullet_text": "Changed"}).status_code == 404
    assert bob.delete(f"/api/profile/{path}/bullets/{bullet_id}").status_code == 404
    ids = [b["id"] for b in entry["bullets"]]
    assert bob.put(f"/api/profile/{path}/{entry['id']}/bullets/order", json={"ids": ids}).status_code == 404
    stored = alice["client"].get("/api/profile").json()[key][0]["bullets"]
    assert [b["bullet_text"] for b in stored] == [b["bullet_text"] for b in entry["bullets"]]


def test_cannot_reorder_with_another_users_ids(alice, bob):
    ids = [s["id"] for s in alice["profile"]["skills"]]
    assert bob.put("/api/profile/skills/order", json={"ids": ids}).status_code == 422


def test_profiles_are_separate(alice, bob):
    bob_profile = bob.get("/api/profile").json()
    assert bob_profile["id"] != alice["profile"]["id"]
    assert bob_profile["skills"] == []


def test_cannot_read_another_users_job_description(alice, bob):
    assert bob.get(f"/api/jd/{alice['jd']['id']}").status_code == 404
    assert bob.get("/api/jd").json() == []


def test_cannot_read_download_or_delete_another_users_resume(alice, bob):
    resume_id = alice["resume"]["resume_id"]
    assert bob.get(f"/api/resumes/{resume_id}").status_code == 404
    assert bob.get(f"/api/resumes/{resume_id}/download?format=docx").status_code == 404
    assert bob.delete(f"/api/resumes/{resume_id}").status_code == 404
    assert bob.get("/api/resumes").json() == []
    assert alice["client"].get(f"/api/resumes/{resume_id}/download?format=docx").status_code == 200
