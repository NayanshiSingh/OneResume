"""Test fixtures — test database, synthetic profiles, and sample JDs."""

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import *  # noqa: F401, F403 — ensure all models are registered

# ── Test database ─────────────────────────────────────────────

TEST_DB_URL = "sqlite:///./test_oneresume.db"

engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def db():
    """Create fresh tables for each test, yield a session, then drop."""
    Base.metadata.create_all(bind=engine)
    session = TestSession()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    """FastAPI test client with overridden DB dependency."""
    from fastapi.testclient import TestClient

    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ── Synthetic data ────────────────────────────────────────────


@pytest.fixture
def sample_user_data():
    return {"username": "testuser", "email": "test@example.com"}


@pytest.fixture
def strong_fit_profile_data():
    """Profile data that's a strong match for a Python backend role."""
    return {
        "personal_info": {
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone_number": "+1-555-0123",
        },
        "education": [
            {
                "institution": "MIT",
                "degree": "B.S.",
                "field_of_study": "Computer Science",
                "start_year": 2018,
                "end_year": 2022,
                "grade": "3.8",
            }
        ],
        "skills": [
            {"skill_name": "Python", "skill_category": "Programming"},
            {"skill_name": "FastAPI", "skill_category": "Framework"},
            {"skill_name": "PostgreSQL", "skill_category": "Database"},
            {"skill_name": "Docker", "skill_category": "DevOps"},
            {"skill_name": "AWS", "skill_category": "Cloud"},
            {"skill_name": "REST APIs", "skill_category": "Architecture"},
        ],
        "experience": [
            {
                "company": "TechCorp",
                "role": "Backend Engineer",
                "start_date": "2022-06",
                "end_date": "Present",
                "bullets": [
                    {"bullet_text": "Designed and implemented RESTful APIs using Python and FastAPI, serving 10K+ daily active users"},
                    {"bullet_text": "Optimized PostgreSQL queries reducing average response time by 40%"},
                    {"bullet_text": "Built CI/CD pipelines with Docker and AWS, achieving 99.9% deployment success rate"},
                    {"bullet_text": "Led migration from monolithic architecture to microservices, improving scalability by 3x"},
                ],
            },
        ],
        "projects": [
            {
                "project_title": "Distributed Task Queue",
                "description": "High-performance task queue system",
                "tech_stack": "Python, Redis, Celery",
                "bullets": [
                    {"bullet_text": "Built a distributed task queue handling 1M+ tasks per day"},
                    {"bullet_text": "Implemented retry logic with exponential backoff for fault tolerance"},
                ],
            }
        ],
        "certifications": [
            {"name": "AWS Solutions Architect", "issuing_organization": "Amazon", "year": 2023}
        ],
        "achievements": [
            {"title": "Hackathon Winner", "description": "Won first place at HackMIT 2021", "category": "Competition"}
        ],
        "external_profiles": [
            {"platform": "GitHub", "profile_url": "https://github.com/johndoe"},
            {"platform": "LinkedIn", "profile_url": "https://linkedin.com/in/johndoe"},
        ],
    }


@pytest.fixture
def weak_fit_profile_data():
    """Profile data that's a weak match for a Python backend role."""
    return {
        "personal_info": {
            "full_name": "Jane Smith",
            "email": "jane@example.com",
            "phone_number": "+1-555-0456",
        },
        "skills": [
            {"skill_name": "JavaScript", "skill_category": "Programming"},
            {"skill_name": "React", "skill_category": "Framework"},
            {"skill_name": "CSS", "skill_category": "Frontend"},
        ],
        "experience": [
            {
                "company": "WebDesigns Inc",
                "role": "Frontend Developer",
                "start_date": "2021-01",
                "end_date": "2023-12",
                "bullets": [
                    {"bullet_text": "Developed responsive web interfaces using React and TypeScript"},
                    {"bullet_text": "Created reusable component library used across 5 products"},
                ],
            }
        ],
    }


@pytest.fixture
def sample_jd_text():
    """Sample job description for a Python Backend Engineer role."""
    return """
    Senior Python Backend Engineer

    About the Role:
    We are looking for a Senior Python Backend Engineer to join our platform team.
    You will design and build scalable APIs and microservices.

    Requirements:
    - 3+ years of experience with Python
    - Strong experience with FastAPI or Django
    - PostgreSQL and database optimization
    - Docker and containerization
    - AWS cloud services
    - RESTful API design
    - CI/CD pipelines

    Nice to have:
    - Kubernetes experience
    - Message queues (RabbitMQ, Kafka)
    - GraphQL
    - Monitoring tools (Datadog, New Relic)

    Keywords: Python, FastAPI, PostgreSQL, Docker, AWS, REST, microservices, CI/CD
    """


@pytest.fixture
def empty_jd_text():
    """An edge case: very minimal JD."""
    return "Software Engineer at a startup. Must know coding."


@pytest.fixture
def overloaded_jd_text():
    """JD with excessive requirements."""
    return """
    Full Stack Polyglot Engineer

    Must have: Python, Java, JavaScript, TypeScript, Go, Rust, C++, C#,
    Ruby, PHP, Scala, Kotlin, Swift, Dart, R, MATLAB, Haskell, Elixir,
    React, Angular, Vue, Svelte, Next.js, Django, Flask, FastAPI, Spring,
    PostgreSQL, MongoDB, Redis, Elasticsearch, Kafka, RabbitMQ, GraphQL,
    Docker, Kubernetes, Terraform, AWS, GCP, Azure, CI/CD, Agile, Scrum,
    Machine Learning, Deep Learning, NLP, Computer Vision, Blockchain,
    IoT, AR/VR, Quantum Computing

    Experience: 15+ years in all technologies listed above
    """


# ── Helpers ───────────────────────────────────────────────────


def create_full_profile(client, user_data, profile_data):
    """Helper to create a user + profile with all sections via API."""
    # Create user
    user_resp = client.post("/api/users/", json=user_data)
    user_id = user_resp.json()["id"]

    # Create profile
    profile_resp = client.post(f"/api/profiles/{user_id}")
    profile_id = profile_resp.json()["id"]

    # Personal info
    if "personal_info" in profile_data:
        client.put(f"/api/profiles/{profile_id}/personal-info",
                   json=profile_data["personal_info"])

    # Education
    for edu in profile_data.get("education", []):
        client.post(f"/api/profiles/{profile_id}/education", json=edu)

    # Skills
    for skill in profile_data.get("skills", []):
        client.post(f"/api/profiles/{profile_id}/skills", json=skill)

    # Experience
    for exp in profile_data.get("experience", []):
        client.post(f"/api/profiles/{profile_id}/experience", json=exp)

    # Projects
    for proj in profile_data.get("projects", []):
        client.post(f"/api/profiles/{profile_id}/projects", json=proj)

    # Certifications
    for cert in profile_data.get("certifications", []):
        client.post(f"/api/profiles/{profile_id}/certifications", json=cert)

    # Achievements
    for ach in profile_data.get("achievements", []):
        client.post(f"/api/profiles/{profile_id}/achievements", json=ach)

    # External profiles
    for ep in profile_data.get("external_profiles", []):
        client.post(f"/api/profiles/{profile_id}/external-profiles", json=ep)

    return user_id, profile_id
