"""Unit tests for Profile CRUD operations."""

import pytest
from tests.conftest import create_full_profile


class TestUserCRUD:
    def test_create_user(self, client, sample_user_data):
        resp = client.post("/api/users/", json=sample_user_data)
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "testuser"
        assert data["email"] == "test@example.com"
        assert "id" in data

    def test_list_users(self, client, sample_user_data):
        client.post("/api/users/", json=sample_user_data)
        resp = client.get("/api/users/")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_user(self, client, sample_user_data):
        create_resp = client.post("/api/users/", json=sample_user_data)
        user_id = create_resp.json()["id"]
        resp = client.get(f"/api/users/{user_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == user_id

    def test_get_user_not_found(self, client):
        resp = client.get("/api/users/nonexistent-id")
        assert resp.status_code == 404

    def test_delete_user(self, client, sample_user_data):
        create_resp = client.post("/api/users/", json=sample_user_data)
        user_id = create_resp.json()["id"]
        resp = client.delete(f"/api/users/{user_id}")
        assert resp.status_code == 204
        assert client.get(f"/api/users/{user_id}").status_code == 404


class TestProfileCRUD:
    def test_create_profile(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        user_id = user_resp.json()["id"]
        resp = client.post(f"/api/profiles/{user_id}")
        assert resp.status_code == 201
        assert resp.json()["user_id"] == user_id

    def test_get_profile(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        user_id = user_resp.json()["id"]
        profile_resp = client.post(f"/api/profiles/{user_id}")
        profile_id = profile_resp.json()["id"]
        resp = client.get(f"/api/profiles/{profile_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == profile_id


class TestEducationCRUD:
    def test_add_education(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        edu = {"institution": "MIT", "degree": "B.S.", "field_of_study": "CS",
               "start_year": 2018, "end_year": 2022, "grade": "3.8"}
        resp = client.post(f"/api/profiles/{pid}/education", json=edu)
        assert resp.status_code == 201
        assert resp.json()["institution"] == "MIT"

    def test_list_education(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        client.post(f"/api/profiles/{pid}/education",
                    json={"institution": "MIT", "degree": "B.S."})
        client.post(f"/api/profiles/{pid}/education",
                    json={"institution": "Stanford", "degree": "M.S."})

        resp = client.get(f"/api/profiles/{pid}/education")
        assert resp.status_code == 200
        assert len(resp.json()) == 2

    def test_delete_education(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        edu_resp = client.post(f"/api/profiles/{pid}/education",
                               json={"institution": "MIT", "degree": "B.S."})
        edu_id = edu_resp.json()["id"]
        resp = client.delete(f"/api/profiles/education/{edu_id}")
        assert resp.status_code == 204


class TestSkillsCRUD:
    def test_add_skill(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        resp = client.post(f"/api/profiles/{pid}/skills",
                           json={"skill_name": "Python", "skill_category": "Programming"})
        assert resp.status_code == 201
        assert resp.json()["skill_name"] == "Python"

    def test_list_skills(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        client.post(f"/api/profiles/{pid}/skills", json={"skill_name": "Python"})
        client.post(f"/api/profiles/{pid}/skills", json={"skill_name": "FastAPI"})

        resp = client.get(f"/api/profiles/{pid}/skills")
        assert len(resp.json()) == 2


class TestExperienceCRUD:
    def test_add_experience_with_bullets(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        exp = {
            "company": "TechCorp",
            "role": "Engineer",
            "start_date": "2022-01",
            "end_date": "Present",
            "bullets": [
                {"bullet_text": "Built APIs"},
                {"bullet_text": "Optimized databases"},
            ],
        }
        resp = client.post(f"/api/profiles/{pid}/experience", json=exp)
        assert resp.status_code == 201
        data = resp.json()
        assert data["company"] == "TechCorp"
        assert len(data["bullets"]) == 2


class TestProjectCRUD:
    def test_add_project_with_bullets(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        proj = {
            "project_title": "Task Queue",
            "description": "Distributed task queue",
            "tech_stack": "Python, Redis",
            "bullets": [
                {"bullet_text": "Handled 1M tasks/day"},
            ],
        }
        resp = client.post(f"/api/profiles/{pid}/projects", json=proj)
        assert resp.status_code == 201
        assert len(resp.json()["bullets"]) == 1


class TestPersonalInfoCRUD:
    def test_upsert_personal_info(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        info = {"full_name": "John Doe", "email": "john@test.com", "phone_number": "+1-555-0123"}
        resp = client.put(f"/api/profiles/{pid}/personal-info", json=info)
        assert resp.status_code == 200
        assert resp.json()["full_name"] == "John Doe"

        # Update
        resp2 = client.put(f"/api/profiles/{pid}/personal-info",
                           json={"full_name": "John Updated", "email": "new@test.com"})
        assert resp2.json()["full_name"] == "John Updated"


class TestCertificationCRUD:
    def test_add_certification(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        resp = client.post(f"/api/profiles/{pid}/certifications",
                           json={"name": "AWS SAA", "issuing_organization": "Amazon", "year": 2023})
        assert resp.status_code == 201


class TestAchievementCRUD:
    def test_add_achievement(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        resp = client.post(f"/api/profiles/{pid}/achievements",
                           json={"title": "Hackathon Winner", "description": "Won HackMIT"})
        assert resp.status_code == 201


class TestExternalProfileCRUD:
    def test_add_external_profile(self, client, sample_user_data):
        user_resp = client.post("/api/users/", json=sample_user_data)
        profile_resp = client.post(f"/api/profiles/{user_resp.json()['id']}")
        pid = profile_resp.json()["id"]

        resp = client.post(f"/api/profiles/{pid}/external-profiles",
                           json={"platform": "GitHub", "profile_url": "https://github.com/test"})
        assert resp.status_code == 201


class TestFullProfileCreation:
    def test_create_full_profile(self, client, sample_user_data, strong_fit_profile_data):
        user_id, profile_id = create_full_profile(client, sample_user_data, strong_fit_profile_data)
        resp = client.get(f"/api/profiles/{profile_id}")
        data = resp.json()
        assert data["personal_info"]["full_name"] == "John Doe"
        assert len(data["education"]) == 1
        assert len(data["skills"]) == 6
        assert len(data["experience"]) == 1
        assert len(data["projects"]) == 1
        assert len(data["certifications"]) == 1
        assert len(data["achievements"]) == 1
        assert len(data["external_profiles"]) == 2
