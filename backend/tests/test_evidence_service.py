"""Evidence matching: token-aware terms and the skills-list rule."""

from types import SimpleNamespace as NS

import pytest

from app.domain.resume_draft import JDData
from app.services.evidence_service import (
    NEEDS_CONFIRMATION, NOT_FOUND, SUPPORTED, alternatives, contains_term, coverage, tokens,
)


def profile(bullets=(), skills=(), tech_stack=None, certs=()):
    return NS(
        experience=[NS(id="exp1", role="Engineer", company="Acme",
                       bullets=[NS(id=f"b{i}", bullet_text=t) for i, t in enumerate(bullets)])],
        projects=[NS(id="proj1", project_title="Side project", description=None, tech_stack=tech_stack, bullets=[])],
        education=[], achievements=[],
        certifications=[NS(id=f"c{i}", name=n, issuing_organization=None) for i, n in enumerate(certs)],
        skills=[NS(id=f"s{i}", skill_name=n) for i, n in enumerate(skills)],
    )


def label_for(requirement, **kwargs):
    return coverage(profile(**kwargs), JDData(must_have_skills=[requirement]))[0]


@pytest.mark.parametrize("term,text,expected", [
    ("Java", "Built React apps in JavaScript", False),
    ("JavaScript", "Built React apps in JavaScript", True),
    ("C", "Services in C# and .NET", False),
    ("C#", "Services in C# and .NET", True),
    (".NET", "Services in C# and .NET", True),
    ("C++", "Wrote a parser in C", False),
    ("C", "Wrote a parser in C.", True),
    ("R", "React and Redux front end", False),
    ("R", "Statistical models in R", True),
    ("CI/CD", "Set up CI/CD pipelines", True),
    ("REST APIs", "Added two REST API endpoints", True),
    ("Node.js", "Express API on Node", True),
    ("Kubernetes", "Deployed to k8s", True),
    ("PostgreSQL", "Tuned Postgres queries", True),
    ("Go", "Rewrote the service in Golang", True),
])
def test_contains_term(term, text, expected):
    assert contains_term(tokens(text), term) is expected


def test_alternatives_split_but_slashes_stay():
    assert alternatives("Python, Java, or C++") == ["Python", "Java", "C++"]
    assert alternatives("Python or Go") == ["Python", "Go"]
    assert alternatives("CI/CD") == ["CI/CD"]


def test_bullet_evidence_is_supported():
    match = label_for("Python", bullets=["Built FastAPI services in Python"])
    assert match.label == SUPPORTED
    assert [e.id for e in match.evidence] == ["b0"]


def test_project_tech_stack_is_supported():
    assert label_for("Docker", tech_stack="Python, Docker").label == SUPPORTED


def test_certification_is_supported():
    assert label_for("AWS", certs=["AWS Certified Developer"]).label == SUPPORTED


def test_skills_list_alone_needs_confirmation():
    match = label_for("Kafka", skills=["Kafka"], bullets=["Built APIs"])
    assert match.label == NEEDS_CONFIRMATION
    assert [e.kind for e in match.evidence] == ["skill"]


def test_missing_requirement_not_found():
    assert label_for("Kubernetes", bullets=["Deployed to ECS"]).label == NOT_FOUND


def test_javascript_never_supports_java():
    assert label_for("Java", bullets=["Built a React and JavaScript front end"], skills=["JavaScript"]).label == NOT_FOUND


def test_any_alternative_counts():
    assert label_for("Python or Java", bullets=["JUnit tests for a Java service"]).label == SUPPORTED


def test_importance_is_kept():
    result = coverage(profile(bullets=["Python"]), JDData(must_have_skills=["Python"], nice_to_have_skills=["Docker"]))
    assert [(m.requirement, m.importance) for m in result] == [("Python", "required"), ("Docker", "preferred")]


def test_hedged_evidence_needs_confirmation():
    match = label_for("Kubernetes", bullets=["Helped the team with the Kubernetes deployment"])
    assert match.label == NEEDS_CONFIRMATION
    assert [e.id for e in match.evidence] == ["b0"]


def test_any_unhedged_evidence_is_supported():
    match = label_for("Kubernetes", bullets=["Helped with Kubernetes upgrades", "Ran Kubernetes clusters in production"])
    assert match.label == SUPPORTED


def test_endpoints_count_as_apis():
    assert label_for("REST APIs", bullets=["Added two REST endpoints to a Spring service"]).label == SUPPORTED
