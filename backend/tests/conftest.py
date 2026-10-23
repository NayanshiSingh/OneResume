"""Test fixtures: in-memory database, offline AI providers, signed-in clients, and sample data."""

import hashlib
import re

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import *  # noqa: F401, F403 — ensure all models are registered
from app.services import embedding_service

TEST_PASSWORD = "correct-horse-battery"

# ── Test database ─────────────────────────────────────────────

engine = create_engine(
    "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def fake_embed_batch(texts: list[str]) -> list[list[float]]:
    """Deterministic bag-of-words vectors so tests never call Pinecone."""
    vectors = []
    for text in texts:
        vector = [0.0] * 256
        for token in re.findall(r"[a-z0-9+#.]+", text.lower()):
            vector[int(hashlib.md5(token.encode()).hexdigest(), 16) % 256] += 1.0
        vectors.append(vector)
    return vectors


@pytest.fixture(autouse=True)
def offline_environment(monkeypatch, tmp_path):
    """No live AI calls, and generated files go to a temporary directory."""
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "")
    monkeypatch.setattr(settings, "STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(embedding_service, "_embed_batch", fake_embed_batch)


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
def make_client(db):
    """Factory for independent API clients (each keeps its own cookies)."""
    app.dependency_overrides[get_db] = lambda: db
    clients = []

    def _make() -> TestClient:
        c = TestClient(app)
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.close()
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client(make_client):
    return make_client()


@pytest.fixture
def client(make_client):
    """A client signed in as a fresh user."""
    c = make_client()
    signup(c, "owner@example.com")
    return c


def signup(client: TestClient, email: str, password: str = TEST_PASSWORD) -> dict:
    resp = client.post("/api/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()


# ── Synthetic data ────────────────────────────────────────────


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


def fill_profile(client: TestClient, profile_data: dict) -> dict:
    """Create every profile section through the API and return the stored profile."""
    if "personal_info" in profile_data:
        assert client.put("/api/profile/personal-info", json=profile_data["personal_info"]).status_code == 200
    for section in ["education", "skills", "experience", "projects", "certifications", "achievements"]:
        for item in profile_data.get(section, []):
            assert client.post(f"/api/profile/{section}", json=item).status_code == 201
    for item in profile_data.get("external_profiles", []):
        assert client.post("/api/profile/external-profiles", json=item).status_code == 201
    return client.get("/api/profile").json()
