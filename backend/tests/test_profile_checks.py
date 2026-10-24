"""Optional profile suggestions: they ask questions, and never block drafts."""

from datetime import date

from tests.conftest import signup


def _checks(client) -> list[dict]:
    resp = client.get("/api/profile/checks")
    assert resp.status_code == 200
    return resp.json()


def _kinds(checks) -> list[str]:
    return [c["kind"] for c in checks]


def test_empty_profile_asks_for_contact_and_an_entry(client):
    checks = _checks(client)
    assert {"contact", "empty"} <= set(_kinds(checks))
    assert all(c["severity"] == "warning" for c in checks if c["kind"] in {"contact", "empty"})


def test_missing_phone_is_only_info(client):
    client.put("/api/profile/personal-info", json={"full_name": "Priya Raman", "email": "priya@example.com"})
    contact = [c for c in _checks(client) if c["kind"] == "contact"]
    assert [c["severity"] for c in contact] == ["info"]


def test_vague_and_short_bullets_get_questions(client):
    client.post("/api/profile/experience", json={"company": "Ledgerly", "role": "Intern", "bullets": [
        {"bullet_text": "Worked on various backend stuff for the payments team"},
        {"bullet_text": "Fixed bugs"},
        {"bullet_text": "Built a Django REST API that reconciles card payments nightly"},
    ]})
    vague = [c for c in _checks(client) if c["kind"] == "vague_bullet"]
    assert [c["message"].split('"')[1] for c in vague] == ["Worked on various backend stuff for the payments team", "Fixed bugs"]
    assert "is vague" in vague[0]["message"] and "is very short" in vague[1]["message"]
    assert all(c["questions"] and c["section"] == "experience" and c["bullet_id"] for c in vague)


def test_upcoming_graduation_without_month(client):
    year = date.today().year
    client.post("/api/profile/education", json={"institution": "State University", "degree": "BS", "end_year": year + 1})
    client.post("/api/profile/education", json={"institution": "City College", "degree": "AS", "end_year": year - 3})
    grad = [c for c in _checks(client) if c["kind"] == "graduation_month"]
    assert len(grad) == 1 and "State University" in grad[0]["message"]


def test_skills_listed_without_evidence(client):
    for name in ["Python", "Docker", "Kubernetes"]:
        client.post("/api/profile/skills", json={"skill_name": name})
    client.post("/api/profile/experience", json={"company": "Ledgerly", "role": "Intern", "bullets": [
        {"bullet_text": "Built a Python service that ships in Docker containers"},
        {"bullet_text": "Helped the team with the Kubernetes deployment rollout"},
    ]})
    listed = [c for c in _checks(client) if c["kind"] == "listed_only_skills"]
    # Kubernetes has a hedged bullet, which is still evidence to confirm, so it is not "listed only".
    assert listed == []
    client.post("/api/profile/skills", json={"skill_name": "Terraform"})
    listed = [c for c in _checks(client) if c["kind"] == "listed_only_skills"]
    assert listed[0]["skills"] == ["Terraform"]


def test_checks_never_block_drafts(client):
    jd = client.post("/api/jd/analyze", json={"raw_text": "Backend Engineer. Requirements: Python."}).json()
    assert _checks(client)  # the empty profile has warnings
    assert client.post("/api/drafts", json={"jd_id": jd["id"], "idempotency_key": "k"}).status_code == 202


def test_checks_are_private(client, make_client):
    client.post("/api/profile/experience", json={"company": "Ledgerly", "role": "Intern", "bullets": [{"bullet_text": "Fixed bugs"}]})
    other = make_client()
    signup(other, "other@example.com")
    assert "vague_bullet" not in _kinds(_checks(other))
